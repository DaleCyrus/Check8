
from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required, current_user
import io

bp = Blueprint("student", __name__, url_prefix="/student")

from ...extensions import db
from ...models import ClearanceStatus, Faculty, User
from ...utils.qr import name_to_png_bytes



@bp.get("/qr.png")
@login_required
def qr_png():
    _require_student()
    try:
        png = name_to_png_bytes(current_user.full_name)
        return send_file(
            io.BytesIO(png),
            mimetype="image/png",
            as_attachment=False,
            download_name="student-name-qr.png",
        )
    except Exception as e:
        import traceback
        print("[QR ERROR]", e)
        traceback.print_exc()
        return "QR code generation error: {}".format(e), 500


def _require_student():
    if not current_user.is_authenticated or not getattr(current_user, "is_student", False):
        abort(403)


@bp.get("/dashboard")
@login_required
def dashboard():
    _require_student()
    
    # Get all clearances for this student with faculty and instructor info
    clearances_data = []
    clearances = db.session.execute(
        db.select(ClearanceStatus, Faculty)
        .join(Faculty, ClearanceStatus.faculty_id == Faculty.id)
        .where(ClearanceStatus.student_id == current_user.id)
        .order_by(Faculty.name.asc())
    ).all()
    
    for cs, faculty in clearances:
        # Get all instructors for this faculty
        from ...models import FacultyAssignment
        instructors = db.session.execute(
            db.select(User)
            .join(FacultyAssignment, User.id == FacultyAssignment.user_id)
            .where(
                User.role == "faculty",
                FacultyAssignment.faculty_id == faculty.id,
            )
        ).scalars().all()
        
        # Format instructors as comma-separated string
        instructor_names = ", ".join([instr.full_name for instr in instructors]) if instructors else None
        clearances_data.append((cs, faculty, instructor_names))
    
    return render_template("student/dashboard.html", clearances=clearances_data)



