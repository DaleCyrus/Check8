
from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required, current_user
import io

bp = Blueprint("student", __name__, url_prefix="/student")

from ...extensions import db
from ...models import ClearanceStatus, Faculty, User
from ...utils.qr import token_to_png_bytes, make_student_token



@bp.get("/qr.png")
@login_required
def qr_png():
    _require_student()
    try:
        token = make_student_token(current_user)
        png = token_to_png_bytes(token)
        return send_file(
            io.BytesIO(png),
            mimetype="image/png",
            as_attachment=False,
            download_name="student-token-qr.png",
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
    
    # Get all clearances for this student with course and faculty info
    clearances_data = []
    from ...models import Course
    clearances = db.session.execute(
        db.select(ClearanceStatus, Course, Faculty)
        .join(Course, ClearanceStatus.course_id == Course.id)
        .join(Faculty, Course.faculty_id == Faculty.id)
        .where(ClearanceStatus.student_id == current_user.id)
        .order_by(Course.name.asc())
    ).all()
    
    for cs, course, faculty in clearances:
        clearances_data.append((cs, course, faculty))
    
    return render_template("student/dashboard.html", clearances=clearances_data)



