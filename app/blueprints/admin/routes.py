import csv
import io
import sqlite3
import tempfile

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, jsonify, session
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError, IntegrityError
import time

from ...extensions import db
from ...models import (
    ClearanceState, ClearanceStatus, Course, Faculty, InstructorCourse, User,
    StudentGroup, StudentGroupMember, StudentCourse, FacultyUserRole, FacultyRole, Role
)
from ...utils.qr import verify_student_token

bp = Blueprint("admin", __name__, url_prefix="/faculty")
COURSE_DEPARTMENT = "College of Computer Studies"


def _commit_with_retry(max_retries=5, base_delay=0.01):
    """Commit database changes with retry on lock errors."""
    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                db.session.rollback()
                delay = base_delay * (1.5 ** attempt)  # Reduced backoff factor
                time.sleep(delay)
                continue
            else:
                db.session.rollback()
                raise e
    return False


def _require_faculty():
    if not current_user.is_authenticated or not getattr(current_user, "is_faculty", False):
        abort(403)
    if not current_user.assigned_faculties and not current_user.course_assignments:
        abort(403)


def _require_admin():
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        abort(403)


def _student_payload(row):
    """Normalize CSV/database rows into the fields accepted by User."""
    lowered = {str(key).strip().lower(): (value or "").strip() for key, value in row.items()}
    student_number = lowered.get("student_number") or lowered.get("student id") or lowered.get("student_id")
    email = lowered.get("email") or lowered.get("domain_account") or lowered.get("school_email")
    last_name = (lowered.get("last_name") or lowered.get("ln") or "").upper()
    first_name = (lowered.get("first_name") or lowered.get("fn") or "").upper()
    middle_name = (lowered.get("middle_name") or lowered.get("mn") or "").upper()
    full_name = lowered.get("full_name") or " ".join(
        part for part in (first_name, middle_name, last_name) if part
    )
    return {
        "student_number": student_number,
        "email": email.lower(),
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "full_name": full_name,
        "department": lowered.get("department"),
        "program": lowered.get("program"),
    }


def _validate_student_payloads(rows):
    seen_ids = set()
    seen_emails = set()
    preview = []
    for row_number, row in enumerate(rows, start=2):
        record = _student_payload(row)
        errors = []
        student_number = record["student_number"]
        email = record["email"]
        if not student_number:
            errors.append("missing Student ID")
        elif student_number in seen_ids or db.session.execute(
            db.select(User).where(User.student_number == student_number)
        ).scalar_one_or_none():
            errors.append("duplicate Student ID")
        if not email or "@" not in email or not email.endswith("@gordoncollege.edu.ph"):
            errors.append("invalid school email")
        elif email in seen_emails or db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none():
            errors.append("duplicate domain account")
        if not record["last_name"] or not record["first_name"]:
            errors.append("missing name")
        if student_number:
            seen_ids.add(student_number)
        if email:
            seen_emails.add(email)
        record["row_number"] = row_number
        record["errors"] = errors
        preview.append(record)
    return preview


@bp.get("/admin/dashboard")
@login_required
def admin_dashboard():
    _require_admin()
    students = db.session.execute(
           db.select(User).where(User.role == Role.STUDENT.value).order_by(User.student_number.asc())
    ).scalars().all()
    instructors = db.session.execute(
        db.select(User).where(User.role.in_([Role.INSTRUCTOR.value, Role.FACULTY.value])).order_by(User.full_name.asc())
    ).scalars().all()
    courses = db.session.execute(db.select(Course).order_by(Course.code.asc())).scalars().all()
    groups = db.session.execute(db.select(StudentGroup).order_by(StudentGroup.name.asc())).scalars().all()
    return render_template(
        "admin/admin_dashboard.html",
        students=students,
        instructors=instructors,
        courses=courses,
        groups=groups,
    )


@bp.get("/admin/instructors")
@login_required
def instructors():
    _require_admin()
    users = db.session.execute(
        db.select(User).where(User.role.in_([Role.INSTRUCTOR.value, Role.FACULTY.value])).order_by(User.full_name.asc())
    ).scalars().all()
    return render_template("admin/instructors.html", instructors=users)


@bp.post("/admin/students/create")
@login_required
def create_student():
    _require_admin()
    record = _student_payload(request.form)
    errors = _validate_student_payloads([request.form])[0]["errors"]
    password = request.form.get("password") or "student123"
    if errors:
        flash("Student was not added: " + ", ".join(errors), "error")
        return redirect(url_for("admin.admin_dashboard"))
    user = User(role=Role.STUDENT.value, qr_salt=str(__import__("uuid").uuid4()), **record)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Student added successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@bp.post("/admin/students/<int:student_id>/update")
@login_required
def update_student(student_id):
    _require_admin()
    student = db.session.get(User, student_id)
    if not student or student.role != Role.STUDENT.value:
        abort(404)
    student.last_name = (request.form.get("last_name") or student.last_name or "").strip().upper()
    student.first_name = (request.form.get("first_name") or student.first_name or "").strip().upper()
    student.middle_name = (request.form.get("middle_name") or student.middle_name or "").strip().upper() or None
    student.full_name = " ".join(part for part in (student.first_name, student.middle_name, student.last_name) if part)
    student.department = (request.form.get("department") or student.department or "").strip() or None
    student.program = (request.form.get("program") or student.program or "").strip() or None
    db.session.commit()
    flash("Student record updated.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@bp.post("/admin/students/<int:student_id>/toggle")
@login_required
def toggle_student(student_id):
    _require_admin()
    student = db.session.get(User, student_id)
    if not student or student.role != Role.STUDENT.value:
        abort(404)
    student.is_active = not student.is_active
    db.session.commit()
    flash("Student record " + ("activated." if student.is_active else "deactivated."), "success")
    return redirect(url_for("admin.admin_dashboard"))


@bp.post("/admin/import-students/preview")
@login_required
def import_students_preview():
    _require_admin()
    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("Select a CSV or SQLite database file.", "error")
        return redirect(url_for("admin.admin_dashboard"))
    try:
        if upload.filename.lower().endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(upload.read().decode("utf-8-sig"))))
        elif upload.filename.lower().endswith(".db"):
            with tempfile.NamedTemporaryFile(suffix=".db") as database_file:
                database_file.write(upload.read())
                database_file.flush()
                connection = sqlite3.connect(database_file.name)
                connection.row_factory = sqlite3.Row
                table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchone()[0]
                rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
                connection.close()
        else:
            raise ValueError("Only .csv and .db files are supported")
        preview = _validate_student_payloads(rows)
        session["student_import_preview"] = preview
        return render_template("admin/import_students.html", preview=preview)
    except Exception as error:
        flash(f"Could not read import file: {error}", "error")
        return redirect(url_for("admin.admin_dashboard"))


@bp.post("/admin/import-students/confirm")
@login_required
def import_students_confirm():
    _require_admin()
    preview = session.pop("student_import_preview", [])
    added = 0
    for record in preview:
        if record["errors"]:
            continue
        user = User(
            role=Role.STUDENT.value,
            qr_salt=str(__import__("uuid").uuid4()),
            **{key: record.get(key) for key in ("student_number", "email", "last_name", "first_name", "middle_name", "full_name", "department", "program")},
        )
        user.set_password("student123")
        db.session.add(user)
        added += 1
    db.session.commit()
    flash(f"Imported {added} valid student record(s).", "success")
    return redirect(url_for("admin.admin_dashboard"))


def _require_faculty_json(f):
    """Decorator for JSON endpoints that checks faculty permission."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_faculty", False):
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        if not current_user.assigned_faculties and not current_user.course_assignments:
            return jsonify({"ok": False, "error": "No assigned faculties"}), 403
        return f(*args, **kwargs)
    return decorated_function


@bp.get("/dashboard")
@login_required
def dashboard():
    if not getattr(current_user, "is_faculty", False):
        abort(403)

    # Get all faculties assigned to this user
    assigned_faculties = current_user.assigned_faculties

    # Get only courses the instructor is directly assigned to
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    
    assigned_faculty_ids = [f.id for f in assigned_faculties]
    
    if not assigned_courses:
        # If instructor has no course assignments, show empty dashboard
        return render_template("admin/dashboard.html",
                             assigned_faculties=assigned_faculties,
                             assigned_faculties_json=[{"id": f.id, "name": f.name} for f in assigned_faculties],
                             assigned_courses=[],
                             assigned_courses_json=[],
                             primary_faculty=assigned_faculties[0] if assigned_faculties else None,
                             rows=[],
                             groups_data=[],
                             total_students=0,
                             pending_count=0,
                             approved_count=0,
                             rejected_count=0)

    assigned_course_ids = [c.id for c in assigned_courses]
    
    # Get all clearance statuses only for this instructor's courses
    rows = (
        db.session.execute(
            db.select(ClearanceStatus, User, Course, Faculty)
            .join(User, ClearanceStatus.student_id == User.id)
            .join(Course, ClearanceStatus.course_id == Course.id)
            .join(Faculty, Course.faculty_id == Faculty.id)
            .where(Course.id.in_(assigned_course_ids))
            .order_by(Course.name.asc(), User.student_number.asc())
        )
        .all()
    )

    # Calculate statistics
    total_students = len(rows)
    pending_count = sum(1 for cs, u, c, f in rows if cs.state == ClearanceState.PENDING.value)
    approved_count = sum(1 for cs, u, c, f in rows if cs.state == ClearanceState.CLEARED.value)
    rejected_count = sum(1 for cs, u, c, f in rows if cs.state == ClearanceState.BLOCKED.value)

    # Get all groups with their members and clearance status
    groups = db.session.execute(
        db.select(StudentGroup)
        .where(
            StudentGroup.course_id.in_(assigned_course_ids)
        )
        .order_by(StudentGroup.created_at.desc())
    ).scalars().all()
    
    groups_data = []
    for group in groups:
        # Get all members in this group with their clearance status
        members = db.session.execute(
            db.select(StudentGroupMember, User)
            .join(User, StudentGroupMember.student_id == User.id)
            .where(StudentGroupMember.group_id == group.id)
            .order_by(User.student_number.asc())
        ).all()
        
        members_with_status = []
        for member, student in members:
            # Get clearance status for this student in assigned courses
            clearance_statuses = db.session.execute(
                db.select(ClearanceStatus, Course)
                .join(Course, ClearanceStatus.course_id == Course.id)
                .where(
                    ClearanceStatus.student_id == student.id,
                    Course.id.in_(assigned_course_ids)
                )
            ).all()
            
            members_with_status.append({
                'member': member,
                'student': student,
                'clearance_statuses': clearance_statuses
            })
        
        groups_data.append({
            'group': group,
            'members': members_with_status
        })

    return render_template("admin/dashboard.html",
                         assigned_faculties=assigned_faculties,
                         assigned_faculties_json=[{"id": f.id, "name": f.name} for f in assigned_faculties],
                         assigned_courses=[{"id": c.id, "code": c.code, "name": c.name, "faculty_id": c.faculty_id} for c in assigned_courses],
                         assigned_courses_json=[{"id": c.id, "name": c.name, "faculty_id": c.faculty_id} for c in assigned_courses],
                         primary_faculty=assigned_faculties[0] if assigned_faculties else None,
                         rows=rows,
                         groups_data=groups_data,
                         total_students=total_students,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count)


@bp.get("/instructor/dashboard")
@login_required
def instructor_dashboard():
    """Instructor view for assigned clearance work."""
    return dashboard()


@bp.post("/set-status")
@login_required
def set_status():
    _require_faculty()
    
    # Validate required form fields
    student_id_str = request.form.get("student_id", "").strip()
    course_id_str = request.form.get("course_id", "").strip()
    
    if not student_id_str or not course_id_str:
        flash("Invalid student ID or course ID.", "error")
        return redirect(url_for("admin.dashboard"))
    
    try:
        student_id = int(student_id_str)
        course_id = int(course_id_str)
    except ValueError:
        flash("Invalid student ID or course ID.", "error")
        return redirect(url_for("admin.dashboard"))
    
    state = request.form.get("state")
    group_id_str = request.form.get("group_id")
    group_id = int(group_id_str) if group_id_str else None  # Optional: if updating from a group page

    # Get the course and validate user has permission
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "error")
        if group_id:
            return redirect(url_for("admin.view_group", group_id=group_id))
        return redirect(url_for("admin.dashboard"))
    
    instructor_assignment = db.session.execute(
        db.select(InstructorCourse).where(
            InstructorCourse.user_id == current_user.id,
            InstructorCourse.course_id == course_id,
        )
    ).scalar_one_or_none()
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if course.faculty_id not in assigned_faculty_ids and not instructor_assignment:
        flash("You don't have permission to manage this course.", "error")
        if group_id:
            return redirect(url_for("admin.view_group", group_id=group_id))
        return redirect(url_for("admin.dashboard"))

    # Validate state if provided
    if state and state not in {s.value for s in ClearanceState}:
        flash("Invalid status value.", "error")
        if group_id:
            return redirect(url_for("admin.view_group", group_id=group_id))
        return redirect(url_for("admin.dashboard"))

    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.course_id == course_id,
        )
    ).scalar_one_or_none()

    if not cs:
        cs = ClearanceStatus(student_id=student_id, course_id=course_id)
        db.session.add(cs)
        # Only set default state for new records
        if state:
            cs.state = state
        else:
            cs.state = ClearanceState.PENDING.value
    else:
        # Only update state if explicitly provided in the request
        if state:
            cs.state = state
    
    # Only update note if it's explicitly provided in the request
    if "note" in request.form:
        note = (request.form.get("note") or "").strip() or None
        cs.note = note
    
    try:
        _commit_with_retry()
        flash("Status updated.", "success")
    except Exception as e:
        flash(f"Error updating status: {str(e)}", "error")
    
    # Redirect back to where the update came from
    if group_id:
        return redirect(url_for("admin.view_group", group_id=group_id))
    return redirect(url_for("admin.dashboard", tab="groups"))


@bp.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    _require_faculty()
    token = None
    student = None
    course = None
    
    # Get all courses assigned to this user
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    
    if request.method == "POST":
        token = (request.form.get("token") or "").strip()
        course_id_str = request.form.get("course_id")
        course_id = int(course_id_str) if course_id_str else None
        
        student = verify_student_token(token)
        if not student:
            flash("Invalid or tampered QR token.", "error")
        elif not course_id:
            flash("Please select a course.", "error")
        else:
            # PER-COURSE VERIFICATION: Check if student is in THIS SPECIFIC COURSE
            course = db.session.get(Course, course_id)
            if not course:
                flash("Course not found.", "error")
            else:
                cs = db.session.execute(
                    db.select(ClearanceStatus).where(
                        ClearanceStatus.student_id == student.id,
                        ClearanceStatus.course_id == course_id,
                    )
                ).scalar_one_or_none()
                
                if not cs:
                    flash("Student not enrolled in this course.", "error")
                    student = None
    
    return render_template("admin/verify.html", token=token, student=student, course=course, assigned_courses=assigned_courses)


@bp.post("/verify.json")
@login_required
@_require_faculty_json
def verify_json():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    course_id = data.get("course_id")
    if course_id:
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Invalid course ID"}), 400
    
    # Validate course_id is provided
    if not course_id:
        return jsonify({"ok": False, "error": "Course must be selected"}), 400
    
    # Verify the course exists and user teaches it
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"ok": False, "error": "Course not found"}), 404
    
    # Check if user is assigned to this course
    instructor_assignment = db.session.execute(
        db.select(InstructorCourse).where(
            InstructorCourse.user_id == current_user.id,
            InstructorCourse.course_id == course_id
        )
    ).scalar_one_or_none()
    
    if not instructor_assignment:
        return jsonify({"ok": False, "error": "You are not assigned to this course"}), 403
    
    student = verify_student_token(token)
    if not student:
        return jsonify({"ok": False, "error": "Invalid token"}), 400

    # PER-COURSE VERIFICATION: Check if student is enrolled in THIS SPECIFIC COURSE
    cs = db.session.execute(
        db.select(ClearanceStatus)
        .where(
            ClearanceStatus.student_id == student.id,
            ClearanceStatus.course_id == course_id,
        )
    ).scalar_one_or_none()

    # Student must be explicitly added to this specific course
    if not cs:
        return jsonify({"ok": False, "error": "Student not enrolled in this course"}), 403

    # Return course and clearance info
    course_info = {
        "id": course.id,
        "name": course.name,
        "faculty_id": course.faculty_id,
    }
    state = cs.state
    note = cs.note

    return jsonify(
        {
            "ok": True,
            "student": {
                "id": student.id,
                "full_name": student.full_name,
                "student_number": student.student_number,
            },
            "course": course_info,
            "clearance": {
                "state": state,
                "note": note,
            },
        }
    )


@bp.post("/search-students.json")
@login_required
@_require_faculty_json
def search_students():
    """Search for students by student number or name."""
    try:
        data = request.get_json(silent=True) or {}
        query = (data.get("q") or "").strip().lower()

        if not query or len(query) < 2:
            return jsonify({"ok": False, "error": "Search query must be at least 2 characters"}), 400

        # Get only courses the instructor is directly assigned to teach
        assigned_courses = db.session.execute(
            db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
        ).scalars().all()
        assigned_course_ids = [c.id for c in assigned_courses]

        # Search for all students
        students = db.session.execute(
            db.select(User)
            .where(
                User.role == "student",
                or_(User.student_number.ilike(f"%{query}%"), User.full_name.ilike(f"%{query}%")),
            )
            .limit(10)
        ).scalars().all()

        results = []
        for student in students:
            # Check which courses this student is already added to
            already_added_courses = []
            for course in assigned_courses:
                try:
                    exists = db.session.execute(
                        db.select(ClearanceStatus).where(
                            ClearanceStatus.student_id == student.id,
                            ClearanceStatus.course_id == course.id,
                        )
                    ).scalar_one_or_none()
                    if exists:
                        already_added_courses.append(course.id)
                except OperationalError:
                    # If database is locked, continue with what we have
                    pass

            results.append({
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
                "already_added_courses": already_added_courses,
            })

        return jsonify({"ok": True, "results": results})
    except OperationalError as e:
        return jsonify({"ok": False, "error": "Database is temporarily locked. Please try again."}), 503
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Search error: {str(e)}"}), 500


@bp.post("/add-student")
@login_required
def add_student():
    """Add a student to a specific course's clearance list."""
    _require_admin()
    student_id_str = request.form.get("student_id")
    course_id_str = request.form.get("course_id")
    student_id = int(student_id_str) if student_id_str else None
    course_id = int(course_id_str) if course_id_str else None

    if not student_id or not course_id:
        flash("Invalid student ID or course ID.", "error")
        return redirect(url_for("admin.dashboard"))

    # Get the course and validate user has permission
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin.dashboard"))
    
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if course.faculty_id not in assigned_faculty_ids:
        flash("You don't have permission to manage this course.", "error")
        return redirect(url_for("admin.dashboard"))

    # Verify student exists
    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        flash("Student not found.", "error")
        return redirect(url_for("admin.dashboard"))

    # Check if already in clearance list for this course
    existing = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.course_id == course_id,
        )
    ).scalar_one_or_none()

    if existing:
        flash(f"Student {student.student_number} is already in {course.name} clearance list.", "info")
        return redirect(url_for("admin.dashboard"))

    # Add student to clearance list
    cs = ClearanceStatus(
        student_id=student_id,
        course_id=course_id,
        state=ClearanceState.PENDING.value,
    )
    db.session.add(cs)
    
    # Automatically enroll student in the course
    existing_enrollment = db.session.execute(
        db.select(StudentCourse).where(
            StudentCourse.user_id == student_id,
            StudentCourse.course_id == course_id,
        )
    ).scalar_one_or_none()
    
    if not existing_enrollment:
        enrollment = StudentCourse(user_id=student_id, course_id=course_id)
        db.session.add(enrollment)
    
    try:
        _commit_with_retry()
        flash(f"Added {student.full_name} ({student.student_number}) to {course.name} clearance list.", "success")
    except Exception as e:
        flash(f"Error adding student: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))


@bp.post("/bulk-add-students")
@login_required
def bulk_add_students():
    """Bulk add multiple students to a course's clearance list."""
    _require_admin()
    
    try:
        data = request.get_json()
        student_ids = data.get("student_ids", [])
        course_id = data.get("course_id")
        
        if not student_ids or not course_id:
            return jsonify({"ok": False, "error": "Missing student IDs or course ID"}), 400
        
        # Get the course and validate user has permission
        course = db.session.get(Course, course_id)
        if not course:
            return jsonify({"ok": False, "error": "Course not found"}), 404
        
        assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
        if course.faculty_id not in assigned_faculty_ids:
            return jsonify({"ok": False, "error": "You don't have permission to manage this course"}), 403
        
        added_count = 0
        skipped_count = 0
        
        for student_id in student_ids:
            student = db.session.get(User, int(student_id))
            if not student or student.role != "student":
                skipped_count += 1
                continue
            
            # Check if already in clearance list for this course
            existing = db.session.execute(
                db.select(ClearanceStatus).where(
                    ClearanceStatus.student_id == student_id,
                    ClearanceStatus.course_id == course_id,
                )
            ).scalar_one_or_none()
            
            if existing:
                skipped_count += 1
                continue
            
            # Add student to clearance list
            cs = ClearanceStatus(
                student_id=student_id,
                course_id=course_id,
                state=ClearanceState.PENDING.value,
            )
            db.session.add(cs)
            
            # Automatically enroll student in the course
            existing_enrollment = db.session.execute(
                db.select(StudentCourse).where(
                    StudentCourse.user_id == student_id,
                    StudentCourse.course_id == course_id,
                )
            ).scalar_one_or_none()
            
            if not existing_enrollment:
                enrollment = StudentCourse(user_id=student_id, course_id=course_id)
                db.session.add(enrollment)
            
            added_count += 1
        
        _commit_with_retry()
        
        message = f"✓ Added {added_count} student(s) to {course.name} clearance list."
        if skipped_count > 0:
            message += f" {skipped_count} student(s) were skipped (already added or invalid)."
        
        return jsonify({
            "ok": True,
            "added_count": added_count,
            "skipped_count": skipped_count,
            "message": message
        }), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error adding students: {str(e)}"}), 500


@bp.post("/remove-student")
@login_required
def remove_student():
    """Remove a student from a specific course's clearance list."""
    _require_admin()
    student_id_str = request.form.get("student_id")
    course_id_str = request.form.get("course_id")
    student_id = int(student_id_str) if student_id_str else None
    course_id = int(course_id_str) if course_id_str else None

    if not student_id or not course_id:
        flash("Invalid student ID or course ID.", "error")
        return redirect(url_for("admin.dashboard"))

    # Get the course and validate user has permission
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin.dashboard"))
    
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if course.faculty_id not in assigned_faculty_ids:
        flash("You don't have permission to manage this course.", "error")
        return redirect(url_for("admin.dashboard"))

    # Get and delete the clearance status
    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.course_id == course_id,
        )
    ).scalar_one_or_none()

    if not cs:
        flash("Student not found in clearance list.", "error")
        return redirect(url_for("admin.dashboard"))

    # Get student info for the flash message
    student = db.session.get(User, student_id)

    try:
        # Delete the clearance status
        db.session.delete(cs)
        
        # Also remove student from all groups for this course
        group_members = db.session.execute(
            db.select(StudentGroupMember)
            .join(StudentGroup, StudentGroupMember.group_id == StudentGroup.id)
            .where(
                StudentGroup.course_id == course_id,
                StudentGroupMember.student_id == student_id
            )
        ).scalars().all()
        
        for member in group_members:
            db.session.delete(member)
        
        _commit_with_retry()
        flash(f"Removed {student.full_name} ({student.student_number}) from {course.name} clearance list and associated groups.", "success")
    except Exception as e:
        flash(f"Error removing student: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))


# ====== STUDENT GROUP MANAGEMENT ROUTES ======

@bp.get("/groups")
@login_required
def list_groups():
    """Display all student groups created by the current faculty member."""
    if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_faculty):
        abort(403)
    
    if current_user.is_admin:
        assigned_courses = db.session.execute(db.select(Course).order_by(Course.code.asc())).scalars().all()
        groups = db.session.execute(db.select(StudentGroup).order_by(StudentGroup.created_at.desc())).scalars().all()
    else:
        assigned_courses = db.session.execute(
            db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
        ).scalars().all()
        assigned_course_ids = [c.id for c in assigned_courses]
        groups = db.session.execute(
            db.select(StudentGroup)
            .where(
                StudentGroup.course_id.in_(assigned_course_ids)
            )
            .order_by(StudentGroup.created_at.desc())
        ).scalars().all()
    
    instructor_users = db.session.execute(
        db.select(User)
        .where(User.role.in_([Role.INSTRUCTOR.value, Role.FACULTY.value]))
        .order_by(User.full_name.asc())
    ).scalars().all()
    return render_template(
        "admin/groups.html",
        groups=groups,
        assigned_courses=assigned_courses,
        instructors=instructor_users,
        course_department=COURSE_DEPARTMENT,
    )


@bp.post("/group/create")
@login_required
def create_group():
    """Create a new student group for a specific course."""
    _require_admin()
    
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    course_code = (request.form.get("course_code") or "").strip().upper()
    course_name = (request.form.get("course_name") or "").strip()
    instructor_id_str = request.form.get("instructor_id")
    try:
        instructor_id = int(instructor_id_str) if instructor_id_str else None
    except ValueError:
        instructor_id = None
    
    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("admin.list_groups"))
    
    if len(name) > 255:
        flash("Group name must be 255 characters or less.", "error")
        return redirect(url_for("admin.list_groups"))
    
    if not course_code or not course_name or not instructor_id:
        flash("Course code, course name, and instructor are required.", "error")
        return redirect(url_for("admin.list_groups"))

    instructor = db.session.get(User, instructor_id)
    if not instructor or instructor.role not in {Role.INSTRUCTOR.value, Role.FACULTY.value}:
        flash("Select a valid instructor.", "error")
        return redirect(url_for("admin.list_groups"))

    department = db.session.execute(
        db.select(Faculty).where(Faculty.name == COURSE_DEPARTMENT)
    ).scalar_one_or_none()
    if not department:
        department = Faculty(name=COURSE_DEPARTMENT)
        db.session.add(department)
        db.session.flush()

    course = db.session.execute(db.select(Course).where(Course.code == course_code)).scalar_one_or_none()
    if course and course.faculty_id != department.id:
        flash(f"Course code '{course_code}' already belongs to another department.", "error")
        return redirect(url_for("admin.list_groups"))
    if not course:
        course = Course(code=course_code, name=course_name, faculty_id=department.id)
        db.session.add(course)
        db.session.flush()

    instructor_assignment = db.session.execute(
        db.select(InstructorCourse).where(
            InstructorCourse.user_id == instructor.id,
            InstructorCourse.course_id == course.id
        )
    ).scalar_one_or_none()
    
    # Check for duplicate name within this user's groups for this course
    existing = db.session.execute(
        db.select(StudentGroup).where(
            StudentGroup.created_by_user_id == current_user.id,
            StudentGroup.course_id == course.id,
            StudentGroup.name == name,
        )
    ).scalar_one_or_none()
    
    if existing:
        flash(f"A group named '{name}' already exists for this course.", "error")
        return redirect(url_for("admin.list_groups"))
    
    group = StudentGroup(
        faculty_id=course.faculty_id,
        course_id=course.id,
        created_by_user_id=current_user.id,
        name=name,
        description=description,
    )
    db.session.add(group)
    if not instructor_assignment:
        db.session.add(InstructorCourse(user_id=instructor.id, course_id=course.id))
    try:
        _commit_with_retry()
        flash(f"Group '{name}' created successfully for {course.code}; instructor assigned.", "success")
    except Exception as e:
        flash(f"Error creating group: {str(e)}", "error")
    
    return redirect(url_for("admin.list_groups"))


@bp.post("/admin/import-courses")
@login_required
def import_courses():
    _require_admin()
    upload = request.files.get("file")
    if not upload or not upload.filename.lower().endswith(".csv"):
        flash("Select a CSV course file.", "error")
        return redirect(url_for("admin.list_groups"))

    added = 0
    skipped = 0
    try:
        rows = csv.DictReader(io.StringIO(upload.read().decode("utf-8-sig")))
        department = db.session.execute(
            db.select(Faculty).where(Faculty.name == COURSE_DEPARTMENT)
        ).scalar_one_or_none()
        if not department:
            department = Faculty(name=COURSE_DEPARTMENT)
            db.session.add(department)
            db.session.flush()
        for row in rows:
            code = (row.get("course_code") or row.get("code") or "").strip().upper()
            name = (row.get("course_name") or row.get("name") or "").strip()
            if not code or not name:
                skipped += 1
                continue
            if db.session.execute(db.select(Course).where(Course.code == code)).scalar_one_or_none():
                skipped += 1
                continue
            db.session.add(Course(code=code, name=name, faculty_id=department.id))
            added += 1
        db.session.commit()
        flash(f"Imported {added} course(s); skipped {skipped} row(s).", "success")
    except Exception as error:
        db.session.rollback()
        flash(f"Could not import courses: {error}", "error")
    return redirect(url_for("admin.list_groups"))


@bp.post("/group/delete/<int:group_id>")
@login_required
def delete_group(group_id):
    """Delete a student group."""
    _require_admin()
    
    group = db.session.get(StudentGroup, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Verify user is the creator
    if group.created_by_user_id != current_user.id:
        flash("You don't have permission to delete this group.", "error")
        return redirect(url_for("admin.list_groups"))
    
    group_name = group.name
    try:
        db.session.delete(group)
        _commit_with_retry()
        flash(f"Group '{group_name}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting group: {str(e)}", "error")
    
    return redirect(url_for("admin.list_groups"))


@bp.get("/group/<int:group_id>")
@login_required
def view_group(group_id):
    """View a specific student group and its members."""
    if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_faculty):
        abort(403)
    
    group = db.session.get(StudentGroup, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Get assigned courses for this user
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    assigned_course_ids = [c.id for c in assigned_courses]
    if not current_user.is_admin and group.course_id not in assigned_course_ids:
        flash("You don't have permission to view this class.", "error")
        return redirect(url_for("admin.dashboard"))
    
    # Get group members with their details
    members = db.session.execute(
        db.select(StudentGroupMember, User)
        .join(User, StudentGroupMember.student_id == User.id)
        .where(StudentGroupMember.group_id == group_id)
        .order_by(User.student_number.asc())
    ).all()
    
    members_with_status = []
    for member, student in members:
        # Get clearance status for this student in assigned courses
        clearance_statuses = db.session.execute(
            db.select(ClearanceStatus, Course)
            .join(Course, ClearanceStatus.course_id == Course.id)
            .where(
                ClearanceStatus.student_id == student.id,
                Course.id.in_(assigned_course_ids)
            )
        ).all()
        
        members_with_status.append({
            'member': member,
            'student': student,
            'clearance_statuses': clearance_statuses
        })
    
    # Get all students not in this group (available to add)
    group_member_ids = {m[1].id for m in members}
    
    # ISOLATION FIX: Get students already in groups of the SAME COURSE
    # A student can be in groups from different courses, but not multiple groups in same course
    students_in_same_course_groups = db.session.execute(
        db.select(StudentGroupMember.student_id)
        .join(StudentGroup, StudentGroupMember.group_id == StudentGroup.id)
        .where(StudentGroup.course_id == group.course_id)
        .distinct()
    ).scalars().all()
    
    available_students = db.session.execute(
        db.select(User)
        .where(
            User.role == "student",
            User.id.notin_(group_member_ids),
            User.id.notin_(students_in_same_course_groups)  # Exclude students already in other groups of this course
        )
        .order_by(User.student_number.asc())
    ).scalars().all()
    
    return render_template("admin/group_detail.html", group=group, members=members_with_status, assigned_courses=assigned_courses, available_students=available_students)


@bp.post("/group/add-students")
@login_required
def add_students_to_group():
    """Add multiple students to a group at once."""
    _require_admin()
    
    group_id_str = request.form.get("group_id")
    group_id = int(group_id_str) if group_id_str else None
    student_ids_str = (request.form.get("student_ids") or "").strip()
    
    if not group_id:
        flash("Invalid group.", "error")
        return redirect(url_for("admin.list_groups"))
    
    group = db.session.get(StudentGroup, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Verify user is the creator
    if group.created_by_user_id != current_user.id:
        flash("You don't have permission to manage this group.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Parse student IDs (comma-separated)
    student_ids = []
    if student_ids_str:
        for id_str in student_ids_str.split(","):
            id_str = id_str.strip()
            if id_str and id_str.isdigit():
                student_ids.append(int(id_str))
    
    if not student_ids:
        flash("No valid student IDs provided.", "error")
        return redirect(url_for("admin.view_group", group_id=group_id))
    
    # Add students to group
    added_count = 0
    duplicate_count = 0
    invalid_count = 0
    isolation_conflict_count = 0
    
    for student_id in student_ids:
        student = db.session.get(User, student_id)
        
        # Validate it's a student
        if not student or student.role != "student":
            invalid_count += 1
            continue
        
        # Check if already in group
        existing = db.session.execute(
            db.select(StudentGroupMember).where(
                StudentGroupMember.group_id == group_id,
                StudentGroupMember.student_id == student.id,
            )
        ).scalar_one_or_none()
        
        if existing:
            duplicate_count += 1
            continue
        
        # ISOLATION FIX: Check if student is already in another group of the SAME COURSE
        # Allow student to be in groups from different courses, but not multiple groups in same course
        student_in_same_course_group = db.session.execute(
            db.select(StudentGroupMember)
            .join(StudentGroup, StudentGroupMember.group_id == StudentGroup.id)
            .where(
                StudentGroupMember.student_id == student.id,
                StudentGroup.course_id == group.course_id,
                StudentGroup.id != group_id  # Exclude current group
            )
        ).scalar_one_or_none()
        
        if student_in_same_course_group:
            isolation_conflict_count += 1
            continue
        
        member = StudentGroupMember(group_id=group_id, student_id=student.id)
        db.session.add(member)
        
        # Automatically add student to the course associated with this group
        course_id = group.course_id
        
        # Check if already in clearance list
        existing_clearance = db.session.execute(
            db.select(ClearanceStatus).where(
                ClearanceStatus.student_id == student.id,
                ClearanceStatus.course_id == course_id,
            )
        ).scalar_one_or_none()
        
        if not existing_clearance:
            cs = ClearanceStatus(
                student_id=student.id,
                course_id=course_id,
                state=ClearanceState.PENDING.value,
            )
            db.session.add(cs)
        
        # Also ensure student is enrolled in the course
        existing_enrollment = db.session.execute(
            db.select(StudentCourse).where(
                StudentCourse.user_id == student.id,
                StudentCourse.course_id == course_id,
            )
        ).scalar_one_or_none()
        
        if not existing_enrollment:
            enrollment = StudentCourse(user_id=student.id, course_id=course_id)
            db.session.add(enrollment)
        
        added_count += 1
    
    try:
        _commit_with_retry()
        msg = f"✓ Added {added_count} student(s) to the group."
        if duplicate_count > 0:
            msg += f" {duplicate_count} student(s) were already in the group."
        if invalid_count > 0:
            msg += f" {invalid_count} student(s) were invalid."
        if isolation_conflict_count > 0:
            msg += f" {isolation_conflict_count} student(s) cannot be added (already in another group in this course)."
        flash(msg, "success")
    except Exception as e:
        flash(f"Error adding students: {str(e)}", "error")
    
    return redirect(url_for("admin.view_group", group_id=group_id))


@bp.post("/group/remove-student/<int:group_id>/<int:student_id>")
@login_required
def remove_student_from_group(group_id, student_id):
    """Remove a student from a group."""
    _require_admin()
    
    group = db.session.get(StudentGroup, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Verify user is the creator
    if group.created_by_user_id != current_user.id:
        flash("You don't have permission to manage this group.", "error")
        return redirect(url_for("admin.list_groups"))
    
    member = db.session.execute(
        db.select(StudentGroupMember).where(
            StudentGroupMember.group_id == group_id,
            StudentGroupMember.student_id == student_id,
        )
    ).scalar_one_or_none()
    
    if not member:
        flash("Student not found in group.", "error")
        return redirect(url_for("admin.view_group", group_id=group_id))
    
    student = db.session.get(User, student_id)
    try:
        db.session.delete(member)
        _commit_with_retry()
        flash(f"Removed {student.full_name} from the group.", "success")
    except Exception as e:
        flash(f"Error removing student: {str(e)}", "error")
    
    return redirect(url_for("admin.view_group", group_id=group_id))


# ====== ROLE MANAGEMENT ROUTES ======

@bp.post("/user/<int:user_id>/role/add")
@login_required
def add_user_role(user_id):
    """Add a role to a faculty user"""
    # Only super-admins should be able to do this
    # Implement your own admin check here
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.role != Role.FACULTY.value:
        flash("User must be faculty member", "error")
        return redirect(request.referrer or "/")
    
    faculty_id_str = request.form.get('faculty_id')
    faculty_id = int(faculty_id_str) if faculty_id_str else None
    role = request.form.get('role', '').strip()
    
    if not faculty_id or not role:
        flash("Faculty and role are required", "error")
        return redirect(request.referrer or "/")
    
    # Validate role
    valid_roles = [r.value for r in FacultyRole]
    if role not in valid_roles:
        flash(f"Invalid role. Valid roles: {', '.join(valid_roles)}", "error")
        return redirect(request.referrer or "/")
    
    # Check if role already exists
    existing = FacultyUserRole.query.filter_by(
        user_id=user.id,
        faculty_id=faculty_id,
        role=role
    ).first()
    
    if existing:
        flash(f"User already has '{role}' role in this faculty", "warning")
        return redirect(request.referrer or "/")
    
    # Create role assignment
    user_role = FacultyUserRole(
        user_id=user.id,
        faculty_id=faculty_id,
        role=role
    )
    db.session.add(user_role)
    db.session.commit()
    
    flash(f"Added '{role}' role to {user.full_name}", "success")
    return redirect(request.referrer or "/")


@bp.post("/user/<int:user_id>/role/<int:role_id>/remove")
@login_required
def remove_user_role(user_id, role_id):
    """Remove a role from a faculty user"""
    # Only super-admins should be able to do this
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        abort(403)
    
    user_role = FacultyUserRole.query.get_or_404(role_id)
    
    if user_role.user_id != user_id:
        abort(403)
    
    role_name = user_role.role
    user_name = user_role.user.full_name
    
    db.session.delete(user_role)
    db.session.commit()
    
    flash(f"Removed '{role_name}' role from {user_name}", "success")
    return redirect(request.referrer or "/")



