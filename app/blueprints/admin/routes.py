from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError, IntegrityError
import time

from ...extensions import db
from ...models import (
    ClearanceState, ClearanceStatus, Course, Faculty, InstructorCourse, User,
    StudentGroup, StudentGroupMember, StudentCourse, FacultyUserRole, FacultyRole, Role,
    Semester, DefaultSignatory, Event, EventEnrollment, EventClearance
)
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
                             groups_data=[])

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

    # Get all groups with their members and clearance status
    groups = db.session.execute(
        db.select(StudentGroup)
        .where(
            StudentGroup.created_by_user_id == current_user.id,
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
                         groups_data=groups_data)


@bp.post("/set-status")
@login_required
def set_status():
    _require_faculty()
    student_id = int(request.form.get("student_id"))
    course_id = int(request.form.get("course_id"))
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
    
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if course.faculty_id not in assigned_faculty_ids:
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
def verify_json():
    _require_faculty()
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
def search_students():
    """Search for students by student number or name."""
    _require_faculty()
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
    _require_faculty()
    
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
    _require_faculty()
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
    _require_faculty()
    
    # Get all courses assigned to this user
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    assigned_course_ids = [c.id for c in assigned_courses]
    
    # Get all groups created by this user for assigned courses
    groups = db.session.execute(
        db.select(StudentGroup)
        .where(
            StudentGroup.created_by_user_id == current_user.id,
            StudentGroup.course_id.in_(assigned_course_ids)
        )
        .order_by(StudentGroup.created_at.desc())
    ).scalars().all()
    
    return render_template("admin/groups.html", groups=groups, assigned_courses=assigned_courses)


@bp.post("/group/create")
@login_required
def create_group():
    """Create a new student group for a specific course."""
    _require_faculty()
    
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    course_id_str = request.form.get("course_id")
    course_id = int(course_id_str) if course_id_str else None
    
    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("admin.list_groups"))
    
    if len(name) > 255:
        flash("Group name must be 255 characters or less.", "error")
        return redirect(url_for("admin.list_groups"))
    
    if not course_id:
        flash("Course is required.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Verify course exists and user has permission to teach it
    course = db.session.get(Course, course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Check if user is assigned to this course
    instructor_assignment = db.session.execute(
        db.select(InstructorCourse).where(
            InstructorCourse.user_id == current_user.id,
            InstructorCourse.course_id == course_id
        )
    ).scalar_one_or_none()
    
    if not instructor_assignment:
        flash("You don't have permission to create a group for this course.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Check for duplicate name within this user's groups for this course
    existing = db.session.execute(
        db.select(StudentGroup).where(
            StudentGroup.created_by_user_id == current_user.id,
            StudentGroup.course_id == course_id,
            StudentGroup.name == name,
        )
    ).scalar_one_or_none()
    
    if existing:
        flash(f"A group named '{name}' already exists for this course.", "error")
        return redirect(url_for("admin.list_groups"))
    
    group = StudentGroup(
        faculty_id=course.faculty_id,
        course_id=course_id,
        created_by_user_id=current_user.id,
        name=name,
        description=description,
    )
    db.session.add(group)
    try:
        _commit_with_retry()
        flash(f"Group '{name}' created successfully for {course.code}.", "success")
    except Exception as e:
        flash(f"Error creating group: {str(e)}", "error")
    
    return redirect(url_for("admin.list_groups"))


@bp.post("/group/delete/<int:group_id>")
@login_required
def delete_group(group_id):
    """Delete a student group."""
    _require_faculty()
    
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
    _require_faculty()
    
    group = db.session.get(StudentGroup, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Verify user is the creator
    if group.created_by_user_id != current_user.id:
        flash("You don't have permission to view this group.", "error")
        return redirect(url_for("admin.list_groups"))
    
    # Get assigned courses for this user
    assigned_courses = db.session.execute(
        db.select(Course).join(InstructorCourse).where(InstructorCourse.user_id == current_user.id)
    ).scalars().all()
    assigned_course_ids = [c.id for c in assigned_courses]
    
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
    _require_faculty()
    
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
    _require_faculty()
    
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




# ====== SEMESTER & SIGNATORY MANAGEMENT ROUTES ======

@bp.get("/semesters")
@login_required
def list_semesters():
    """List all semesters (Admin only)"""
    # Allow faculty admin users to manage semesters
    semesters = db.session.execute(db.select(Semester).order_by(Semester.name.desc())).scalars().all()
    return render_template("admin/semesters.html", semesters=semesters)


@bp.post("/semester/create")
@login_required
def create_semester():
    """Create a new semester"""
    name = (request.form.get("name") or "").strip()
    
    if not name:
        flash("Semester name is required.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    # Check if semester already exists
    existing = db.session.execute(
        db.select(Semester).where(Semester.name == name)
    ).scalar_one_or_none()
    
    if existing:
        flash("A semester with this name already exists.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    try:
        semester = Semester(name=name, is_active=False)
        db.session.add(semester)
        _commit_with_retry()
        flash(f"Semester '{name}' created successfully!", "success")
    except Exception as e:
        flash(f"Error creating semester: {str(e)}", "error")
    
    return redirect(url_for("admin.list_semesters"))


@bp.post("/semester/<int:semester_id>/set-active")
@login_required
def set_active_semester(semester_id):
    """Set a semester as active (and deactivate others)"""
    semester = db.session.get(Semester, semester_id)
    if not semester:
        flash("Semester not found.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    try:
        # Deactivate all other semesters
        db.session.execute(db.update(Semester).values(is_active=False))
        # Activate this one
        semester.is_active = True
        _commit_with_retry()
        flash(f"Semester '{semester.name}' is now active.", "success")
    except Exception as e:
        flash(f"Error setting active semester: {str(e)}", "error")
    
    return redirect(url_for("admin.list_semesters"))


@bp.get("/semester/<int:semester_id>/signatories")
@login_required
def manage_signatories(semester_id):
    """Manage default signatories for a semester"""
    semester = db.session.get(Semester, semester_id)
    if not semester:
        flash("Semester not found.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    signatories = db.session.execute(
        db.select(DefaultSignatory)
        .where(DefaultSignatory.semester_id == semester_id)
        .order_by(DefaultSignatory.order)
    ).scalars().all()
    
    return render_template("admin/manage_signatories.html", semester=semester, signatories=signatories)


@bp.post("/semester/<int:semester_id>/signatory/add")
@login_required
def add_signatory(semester_id):
    """Add a new default signatory to a semester"""
    semester = db.session.get(Semester, semester_id)
    if not semester:
        flash("Semester not found.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    
    if not name:
        flash("Signatory name is required.", "error")
        return redirect(url_for("admin.manage_signatories", semester_id=semester_id))
    
    # Check if signatory already exists for this semester
    existing = db.session.execute(
        db.select(DefaultSignatory).where(
            DefaultSignatory.semester_id == semester_id,
            DefaultSignatory.name == name
        )
    ).scalar_one_or_none()
    
    if existing:
        flash(f"Signatory '{name}' already exists for this semester.", "error")
        return redirect(url_for("admin.manage_signatories", semester_id=semester_id))
    
    try:
        # Get the max order and add 1
        max_order = db.session.execute(
            db.select(db.func.max(DefaultSignatory.order))
            .where(DefaultSignatory.semester_id == semester_id)
        ).scalar() or 0
        
        signatory = DefaultSignatory(
            semester_id=semester_id,
            name=name,
            description=description,
            order=max_order + 1
        )
        db.session.add(signatory)
        _commit_with_retry()
        flash(f"Signatory '{name}' added successfully!", "success")
    except Exception as e:
        flash(f"Error adding signatory: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_signatories", semester_id=semester_id))


@bp.post("/semester/<int:semester_id>/signatory/<int:signatory_id>/delete")
@login_required
def delete_signatory(semester_id, signatory_id):
    """Delete a default signatory"""
    signatory = db.session.get(DefaultSignatory, signatory_id)
    if not signatory or signatory.semester_id != semester_id:
        flash("Signatory not found.", "error")
        return redirect(url_for("admin.manage_signatories", semester_id=semester_id))
    
    try:
        db.session.delete(signatory)
        _commit_with_retry()
        flash(f"Signatory '{signatory.name}' deleted.", "success")
    except Exception as e:
        flash(f"Error deleting signatory: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_signatories", semester_id=semester_id))


@bp.post("/semester/<int:semester_id>/reset-signatories")
@login_required
def reset_semester_signatories(semester_id):
    """Reset/recreate signatories for all students in a semester (preserve student dashboard view)"""
    semester = db.session.get(Semester, semester_id)
    if not semester:
        flash("Semester not found.", "error")
        return redirect(url_for("admin.list_semesters"))
    
    try:
        # Get all default signatories for this semester
        default_sigs = db.session.execute(
            db.select(DefaultSignatory).where(DefaultSignatory.semester_id == semester_id)
        ).scalars().all()
        
        # Delete old events for this semester
        old_events = db.session.execute(
            db.select(Event).where(Event.semester_id == semester_id)
        ).scalars().all()
        
        for event in old_events:
            # Delete clearances
            db.session.execute(
                db.delete(EventClearance).where(EventClearance.event_id == event.id)
            )
            # Delete enrollments
            db.session.execute(
                db.delete(EventEnrollment).where(EventEnrollment.event_id == event.id)
            )
            db.session.delete(event)
        
        # Recreate events from default signatories
        for sig in default_sigs:
            event = Event(
                semester_id=semester_id,
                name=sig.name,
                description=sig.description,
                is_signatory=True,
                order=sig.order
            )
            db.session.add(event)
        
        _commit_with_retry()
        
        # Now re-enroll all students in these new events
        students = db.session.execute(
            db.select(User).where(User.role == Role.STUDENT.value)
        ).scalars().all()
        
        events = db.session.execute(
            db.select(Event).where(Event.semester_id == semester_id)
        ).scalars().all()
        
        for student in students:
            for event in events:
                # Check if enrollment already exists
                existing_enrollment = db.session.execute(
                    db.select(EventEnrollment).where(
                        EventEnrollment.event_id == event.id,
                        EventEnrollment.student_id == student.id
                    )
                ).scalar_one_or_none()
                
                if not existing_enrollment:
                    enrollment = EventEnrollment(
                        event_id=event.id,
                        student_id=student.id
                    )
                    db.session.add(enrollment)
                
                # Check if clearance already exists
                existing_clearance = db.session.execute(
                    db.select(EventClearance).where(
                        EventClearance.event_id == event.id,
                        EventClearance.student_id == student.id
                    )
                ).scalar_one_or_none()
                
                if not existing_clearance:
                    clearance = EventClearance(
                        event_id=event.id,
                        student_id=student.id,
                        state=ClearanceState.PENDING.value
                    )
                    db.session.add(clearance)
        
        _commit_with_retry()
        flash(f"Signatories for semester '{semester.name}' have been reset for all students!", "success")
    except Exception as e:
        flash(f"Error resetting signatories: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_signatories", semester_id=semester_id))


# ====== EMAIL-BASED EVENT CLEARANCE MANAGEMENT ======

@bp.get("/event-clearances")
@login_required
def list_event_clearances():
    """List all event clearances that can be managed by the current instructor"""
    _require_faculty()
    
    # Get the active semester
    active_semester = db.session.execute(
        db.select(Semester).where(Semester.is_active == True)
    ).scalar_one_or_none()
    
    if not active_semester:
        flash("No active semester found. Please activate a semester first.", "warning")
        return redirect(url_for("admin.list_semesters"))
    
    # Get all events for the active semester
    events = db.session.execute(
        db.select(Event)
        .where(Event.semester_id == active_semester.id)
        .order_by(Event.order, Event.created_at.desc())
    ).scalars().all()
    
    # Get events summary with clearance statistics
    events_summary = []
    for event in events:
        cleared_count = db.session.execute(
            db.select(db.func.count(EventClearance.id))
            .where(
                EventClearance.event_id == event.id,
                EventClearance.state == ClearanceState.CLEARED.value
            )
        ).scalar() or 0
        
        pending_count = db.session.execute(
            db.select(db.func.count(EventClearance.id))
            .where(
                EventClearance.event_id == event.id,
                EventClearance.state == ClearanceState.PENDING.value
            )
        ).scalar() or 0
        
        blocked_count = db.session.execute(
            db.select(db.func.count(EventClearance.id))
            .where(
                EventClearance.event_id == event.id,
                EventClearance.state == ClearanceState.BLOCKED.value
            )
        ).scalar() or 0
        
        events_summary.append({
            'event': event,
            'cleared': cleared_count,
            'pending': pending_count,
            'blocked': blocked_count,
            'total': cleared_count + pending_count + blocked_count
        })
    
    return render_template("admin/event_clearances.html", 
                         semester=active_semester, 
                         events=events_summary,
                         current_user_email=current_user.email)


@bp.get("/event/<int:event_id>/clearances")
@login_required
def manage_event_clearance(event_id):
    """Manage clearances for a specific event"""
    _require_faculty()
    
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.list_event_clearances"))
    
    # Get all clearances for this event
    clearances = db.session.execute(
        db.select(EventClearance, User)
        .join(User, EventClearance.student_id == User.id)
        .where(EventClearance.event_id == event_id)
        .order_by(User.student_number.asc())
    ).all()
    
    # Get all faculty members (instructors) for dropdown
    all_instructors = db.session.execute(
        db.select(User)
        .where(User.role == Role.FACULTY.value)
        .order_by(User.full_name.asc())
    ).scalars().all()
    
    return render_template("admin/manage_event_clearance.html", 
                         event=event, 
                         clearances=clearances,
                         instructors=all_instructors,
                         current_user_email=current_user.email)


@bp.post("/event/<int:event_id>/clearance/set-status")
@login_required
def set_event_clearance_status(event_id):
    """Set clearance status for a student in an event"""
    _require_faculty()
    
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"ok": False, "error": "Event not found"}), 404
    
    try:
        data = request.get_json() if request.is_json else request.form
        student_id = int(data.get("student_id", 0))
        state = (data.get("state") or "").strip()
        note = (data.get("note") or "").strip() or None
        instructor_email = (data.get("instructor_email") or "").strip()
        
        # Validate inputs
        if not student_id or not state:
            return jsonify({"ok": False, "error": "Student ID and state are required"}), 400
        
        if state not in {s.value for s in ClearanceState}:
            return jsonify({"ok": False, "error": "Invalid state"}), 400
        
        # Lookup instructor by email (if provided)
        cleared_by_user_id = None
        if instructor_email:
            instructor = db.session.execute(
                db.select(User).where(
                    User.email == instructor_email,
                    User.role == Role.FACULTY.value
                )
            ).scalar_one_or_none()
            
            if not instructor:
                return jsonify({"ok": False, "error": f"Instructor with email '{instructor_email}' not found"}), 404
            
            cleared_by_user_id = instructor.id
        else:
            # Use current user if no instructor email provided
            if state == ClearanceState.CLEARED.value:
                cleared_by_user_id = current_user.id
        
        # Get or create clearance record
        clearance = db.session.execute(
            db.select(EventClearance).where(
                EventClearance.event_id == event_id,
                EventClearance.student_id == student_id
            )
        ).scalar_one_or_none()
        
        if not clearance:
            clearance = EventClearance(
                event_id=event_id,
                student_id=student_id
            )
            db.session.add(clearance)
        
        # Update clearance
        clearance.state = state
        clearance.note = note
        if state == ClearanceState.CLEARED.value or state == ClearanceState.BLOCKED.value:
            clearance.cleared_by_user_id = cleared_by_user_id
        
        _commit_with_retry()
        
        return jsonify({"ok": True, "message": "Clearance status updated"}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.post("/event/<int:event_id>/clearance/search-students")
@login_required
def search_event_students(event_id):
    """Search for students to add to an event"""
    _require_faculty()
    
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"ok": False, "error": "Event not found"}), 404
    
    try:
        data = request.get_json() or {}
        query = (data.get("q") or "").strip().lower()
        
        if not query or len(query) < 2:
            return jsonify({"ok": False, "error": "Search query must be at least 2 characters"}), 400
        
        # Search for students
        students = db.session.execute(
            db.select(User)
            .where(
                User.role == Role.STUDENT.value,
                or_(
                    User.student_number.ilike(f"%{query}%"),
                    User.full_name.ilike(f"%{query}%")
                )
            )
            .limit(10)
        ).scalars().all()
        
        results = []
        for student in students:
            # Check if already enrolled in this event
            existing = db.session.execute(
                db.select(EventEnrollment).where(
                    EventEnrollment.event_id == event_id,
                    EventEnrollment.student_id == student.id
                )
            ).scalar_one_or_none()
            
            results.append({
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
                "already_added": existing is not None
            })
        
        return jsonify({"ok": True, "results": results}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.post("/event/<int:event_id>/clearance/add-student")
@login_required
def add_student_to_event(event_id):
    """Add a student to an event and create clearance record"""
    _require_faculty()
    
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"ok": False, "error": "Event not found"}), 404
    
    try:
        data = request.get_json() or {}
        student_id = int(data.get("student_id", 0))
        
        if not student_id:
            return jsonify({"ok": False, "error": "Student ID is required"}), 400
        
        # Verify student exists
        student = db.session.get(User, student_id)
        if not student or student.role != Role.STUDENT.value:
            return jsonify({"ok": False, "error": "Student not found"}), 404
        
        # Check if already enrolled
        existing_enrollment = db.session.execute(
            db.select(EventEnrollment).where(
                EventEnrollment.event_id == event_id,
                EventEnrollment.student_id == student_id
            )
        ).scalar_one_or_none()
        
        if existing_enrollment:
            return jsonify({"ok": False, "error": "Student already enrolled in this event"}), 400
        
        # Create enrollment
        enrollment = EventEnrollment(
            event_id=event_id,
            student_id=student_id
        )
        db.session.add(enrollment)
        
        # Create clearance record
        clearance = EventClearance(
            event_id=event_id,
            student_id=student_id,
            state=ClearanceState.PENDING.value
        )
        db.session.add(clearance)
        
        _commit_with_retry()
        
        return jsonify({
            "ok": True,
            "message": f"Added {student.full_name} to {event.name}",
            "student": {
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name
            }
        }), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.post("/instructor-lookup")
@login_required
def lookup_instructor_by_email():
    """Lookup instructor by email (for clearance authorization)"""
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        
        if not email:
            return jsonify({"ok": False, "error": "Email is required"}), 400
        
        # Search for instructor
        instructor = db.session.execute(
            db.select(User).where(
                User.email == email,
                User.role == Role.FACULTY.value
            )
        ).scalar_one_or_none()
        
        if not instructor:
            return jsonify({"ok": False, "error": f"No instructor found with email {email}"}), 404
        
        return jsonify({
            "ok": True,
            "instructor": {
                "id": instructor.id,
                "email": instructor.email,
                "full_name": instructor.full_name
            }
        }), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

