from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError
import time

from ...extensions import db
from ...models import ClearanceState, ClearanceStatus, Course, Faculty, InstructorCourse, User
from ...utils.qr import verify_student_token

bp = Blueprint("admin", __name__, url_prefix="/faculty")


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
    if not current_user.assigned_faculties:
        abort(403)


@bp.get("/dashboard")
@login_required
def dashboard():
    _require_faculty()

    # Get all faculties assigned to this user
    assigned_faculties = current_user.assigned_faculties

    # Get only courses the instructor is directly assigned to
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    
    if not assigned_courses:
        # If instructor has no course assignments, show empty dashboard
        return render_template("admin/dashboard.html",
                             assigned_faculties=assigned_faculties,
                             assigned_faculties_json=[{"id": f.id, "name": f.name} for f in assigned_faculties],
                             assigned_courses=[],
                             assigned_courses_json=[],
                             primary_faculty=assigned_faculties[0] if assigned_faculties else None,
                             rows=[])

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

    return render_template("admin/dashboard.html",
                         assigned_faculties=assigned_faculties,
                         assigned_faculties_json=[{"id": f.id, "name": f.name} for f in assigned_faculties],
                         assigned_courses=[{"id": c.id, "code": c.code, "name": c.name, "faculty_id": c.faculty_id} for c in assigned_courses],
                         assigned_courses_json=[{"id": c.id, "name": c.name, "faculty_id": c.faculty_id} for c in assigned_courses],
                         primary_faculty=assigned_faculties[0] if assigned_faculties else None,
                         rows=rows)


@bp.post("/set-status")
@login_required
def set_status():
    _require_faculty()
    student_id = int(request.form.get("student_id"))
    course_id = int(request.form.get("course_id"))
    state = request.form.get("state") or ClearanceState.PENDING.value
    note = (request.form.get("note") or "").strip() or None

    # Get the course and validate user has permission
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin.dashboard"))
    
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if course.faculty_id not in assigned_faculty_ids:
        flash("You don't have permission to manage this course.", "error")
        return redirect(url_for("admin.dashboard"))

    if state not in {s.value for s in ClearanceState}:
        flash("Invalid status value.", "error")
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

    cs.state = state
    cs.note = note
    try:
        _commit_with_retry()
        flash("Status updated.", "success")
    except Exception as e:
        flash(f"Error updating status: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))


@bp.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    _require_faculty()
    token = None
    student = None
    if request.method == "POST":
        token = (request.form.get("token") or "").strip()
        student = verify_student_token(token)
        if not student:
            flash("Invalid or tampered QR token.", "error")
    return render_template("admin/verify.html", token=token, student=student)


@bp.post("/verify.json")
@login_required
def verify_json():
    _require_faculty()
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    student = verify_student_token(token)
    if not student:
        return jsonify({"ok": False, "error": "Invalid token"}), 400

    # Check if student has clearance with any course from assigned faculties
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    cs = db.session.execute(
        db.select(ClearanceStatus, Course)
        .join(Course, ClearanceStatus.course_id == Course.id)
        .where(
            ClearanceStatus.student_id == student.id,
            Course.faculty_id.in_(assigned_faculty_ids),
        )
    ).first()

    # Return course and faculty info if exists
    course_info = None
    state = ClearanceState.PENDING.value
    note = None
    
    if cs:
        # Student has an existing clearance record
        clearance, course = cs
        course_info = {
            "id": course.id,
            "name": course.name,
            "faculty_id": course.faculty_id,
        }
        state = clearance.state
        note = clearance.note
    else:
        # Student has no clearance record yet - pick the first course from assigned faculties
        first_course = db.session.execute(
            db.select(Course).where(Course.faculty_id.in_(assigned_faculty_ids))
        ).scalars().first()
        
        if first_course:
            course_info = {
                "id": first_course.id,
                "name": first_course.name,
                "faculty_id": first_course.faculty_id,
            }

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
def search_students():
    """Search for students by student number or name."""
    _require_faculty()
    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip().lower()

    if not query or len(query) < 2:
        return jsonify({"ok": False, "error": "Search query must be at least 2 characters"}), 400

    # Get all courses for assigned faculties
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    assigned_courses = db.session.execute(
        db.select(Course).where(Course.faculty_id.in_(assigned_faculty_ids))
    ).scalars().all()
    assigned_course_ids = [c.id for c in assigned_courses]

    # Get students already in any of these courses' clearance lists
    existing_students = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.course_id.in_(assigned_course_ids)
        )
    ).scalars().all()
    existing_student_ids = {cs.student_id for cs in existing_students}

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
            exists = db.session.execute(
                db.select(ClearanceStatus).where(
                    ClearanceStatus.student_id == student.id,
                    ClearanceStatus.course_id == course.id,
                )
            ).scalar_one_or_none()
            if exists:
                already_added_courses.append(course.id)

        results.append({
            "id": student.id,
            "student_number": student.student_number,
            "full_name": student.full_name,
            "already_added_courses": already_added_courses,
        })

    return jsonify({"ok": True, "results": results})


@bp.post("/add-student")
@login_required
def add_student():
    """Add a student to a specific course's clearance list."""
    _require_faculty()
    student_id = request.form.get("student_id", type=int)
    course_id = request.form.get("course_id", type=int)

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
    try:
        _commit_with_retry()
        flash(f"Added {student.full_name} ({student.student_number}) to {course.name} clearance list.", "success")
    except Exception as e:
        flash(f"Error adding student: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))


@bp.post("/remove-student")
@login_required
def remove_student():
    """Remove a student from a specific course's clearance list."""
    _require_faculty()
    student_id = request.form.get("student_id", type=int)
    course_id = request.form.get("course_id", type=int)

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
        db.session.delete(cs)
        _commit_with_retry()
        flash(f"Removed {student.full_name} ({student.student_number}) from {course.name} clearance list.", "success")
    except Exception as e:
        flash(f"Error removing student: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))

