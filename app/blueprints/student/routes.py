from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required, current_user

from ...extensions import db
from ...models import ClearanceStatus, Office
from ...utils.qr import make_student_token, token_to_png_bytes

import io

bp = Blueprint("student", __name__, url_prefix="/student")


def _require_student():
    if not current_user.is_authenticated or not getattr(current_user, "is_student", False):
        abort(403)


@bp.get("/dashboard")
@login_required
def dashboard():
    _require_student()
    offices = db.session.execute(db.select(Office).order_by(Office.name.asc())).scalars().all()
    statuses = (
        db.session.execute(
            db.select(ClearanceStatus).where(ClearanceStatus.student_id == current_user.id)
        )
        .scalars()
        .all()
    )
    status_by_office = {s.office_id: s for s in statuses}
    token = make_student_token(current_user)
    return render_template(
        "student/dashboard.html",
        offices=offices,
        status_by_office=status_by_office,
        token=token,
    )


@bp.get("/qr.png")
@login_required
def qr_png():
    _require_student()
    token = make_student_token(current_user)
    png = token_to_png_bytes(token)
    return send_file(
        io.BytesIO(png),
        mimetype="image/png",
        as_attachment=False,
        download_name="check8-qr.png",
    )

