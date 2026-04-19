from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError
import time

from ...extensions import db
from ...models import ClearanceState, ClearanceStatus, Faculty, User
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

    # Get all clearance statuses for all assigned faculties
    faculty_ids = [f.id for f in assigned_faculties]
    rows = (
        db.session.execute(
            db.select(ClearanceStatus, User, Faculty)
            .join(User, ClearanceStatus.student_id == User.id)
            .join(Faculty, ClearanceStatus.faculty_id == Faculty.id)
            .where(ClearanceStatus.faculty_id.in_(faculty_ids))
            .order_by(Faculty.name.asc(), User.student_number.asc())
        )
        .all()
    )

    return render_template("admin/dashboard.html",
                         assigned_faculties=assigned_faculties,
                         assigned_faculties_json=[{"id": f.id, "name": f.name} for f in assigned_faculties],
                         primary_faculty=assigned_faculties[0] if assigned_faculties else None,
                         rows=rows)


@bp.post("/set-status")
@login_required
def set_status():
    _require_faculty()
    student_id = int(request.form.get("student_id"))
    faculty_id = int(request.form.get("faculty_id"))
    state = request.form.get("state") or ClearanceState.PENDING.value
    note = (request.form.get("note") or "").strip() or None

    # Validate that the faculty_id is one of the user's assigned faculties
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if faculty_id not in assigned_faculty_ids:
        flash("You don't have permission to manage this faculty.", "error")
        return redirect(url_for("admin.dashboard"))

    if state not in {s.value for s in ClearanceState}:
        flash("Invalid status value.", "error")
        return redirect(url_for("admin.dashboard"))

    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.faculty_id == faculty_id,
        )
    ).scalar_one_or_none()

    if not cs:
        cs = ClearanceStatus(student_id=student_id, faculty_id=faculty_id)
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

    # Check if student has clearance with any of the faculty user's assigned faculties
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student.id,
            ClearanceStatus.faculty_id.in_(assigned_faculty_ids),
        )
    ).scalar_one_or_none()

    return jsonify(
        {
            "ok": True,
            "student": {
                "id": student.id,
                "full_name": student.full_name,
                "student_number": student.student_number,
            },
            "faculty_id": current_user.faculty_id,
            "clearance": {
                "state": (cs.state if cs else ClearanceState.PENDING.value),
                "note": (cs.note if cs else None),
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

    # Get students already in any of this user's assigned faculties' clearance lists
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    existing_student_ids = set()
    for faculty_id in assigned_faculty_ids:
        faculty_existing = db.session.execute(
            db.select(ClearanceStatus.student_id).where(
                ClearanceStatus.faculty_id == faculty_id
            )
        ).scalars().all()
        existing_student_ids.update(faculty_existing)

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
        # Check which faculties this student is already added to
        already_added_faculties = []
        for faculty in current_user.assigned_faculties:
            exists = db.session.execute(
                db.select(ClearanceStatus).where(
                    ClearanceStatus.student_id == student.id,
                    ClearanceStatus.faculty_id == faculty.id,
                )
            ).scalar_one_or_none()
            if exists:
                already_added_faculties.append(faculty.id)

        results.append({
            "id": student.id,
            "student_number": student.student_number,
            "full_name": student.full_name,
            "already_added_faculties": already_added_faculties,
        })

    return jsonify({"ok": True, "results": results})


@bp.post("/add-student")
@login_required
def add_student():
    """Add a student to a specific faculty's clearance list."""
    _require_faculty()
    student_id = request.form.get("student_id", type=int)
    faculty_id = request.form.get("faculty_id", type=int)

    if not student_id or not faculty_id:
        flash("Invalid student ID or faculty ID.", "error")
        return redirect(url_for("admin.dashboard"))

    # Validate that the faculty_id is one of the user's assigned faculties
    assigned_faculty_ids = [f.id for f in current_user.assigned_faculties]
    if faculty_id not in assigned_faculty_ids:
        flash("You don't have permission to manage this faculty.", "error")
        return redirect(url_for("admin.dashboard"))

    # Verify student exists
    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        flash("Student not found.", "error")
        return redirect(url_for("admin.dashboard"))

    # Check if already in clearance list for this faculty
    existing = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.faculty_id == faculty_id,
        )
    ).scalar_one_or_none()

    if existing:
        faculty = db.session.get(Faculty, faculty_id)
        flash(f"Student {student.student_number} is already in {faculty.name} clearance list.", "info")
        return redirect(url_for("admin.dashboard"))

    # Add student to clearance list
    cs = ClearanceStatus(
        student_id=student_id,
        faculty_id=faculty_id,
        state=ClearanceState.PENDING.value,
    )
    db.session.add(cs)
    try:
        _commit_with_retry()
        faculty = db.session.get(Faculty, faculty_id)
        flash(f"Added {student.full_name} ({student.student_number}) to {faculty.name} clearance list.", "success")
    except Exception as e:
        flash(f"Error adding student: {str(e)}", "error")
    return redirect(url_for("admin.dashboard"))

