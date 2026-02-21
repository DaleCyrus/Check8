from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from ...extensions import db
from ...models import ClearanceState, ClearanceStatus, Office, User
from ...utils.qr import verify_student_token

bp = Blueprint("admin", __name__, url_prefix="/office")


def _require_office():
    if not current_user.is_authenticated or not getattr(current_user, "is_office", False):
        abort(403)
    if not current_user.office_id:
        abort(403)


@bp.get("/dashboard")
@login_required
def dashboard():
    _require_office()
    office = db.session.get(Office, current_user.office_id)
    rows = (
        db.session.execute(
            db.select(ClearanceStatus, User)
            .join(User, ClearanceStatus.student_id == User.id)
            .where(ClearanceStatus.office_id == current_user.office_id)
            .order_by(User.student_number.asc())
        )
        .all()
    )
    return render_template("admin/dashboard.html", office=office, rows=rows)


@bp.post("/set-status")
@login_required
def set_status():
    _require_office()
    student_id = int(request.form.get("student_id"))
    state = request.form.get("state") or ClearanceState.PENDING.value
    note = (request.form.get("note") or "").strip() or None

    if state not in {s.value for s in ClearanceState}:
        flash("Invalid status value.", "error")
        return redirect(url_for("admin.dashboard"))

    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student_id,
            ClearanceStatus.office_id == current_user.office_id,
        )
    ).scalar_one_or_none()

    if not cs:
        cs = ClearanceStatus(student_id=student_id, office_id=current_user.office_id)
        db.session.add(cs)

    cs.state = state
    cs.note = note
    db.session.commit()

    flash("Status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    _require_office()
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
    _require_office()
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    student = verify_student_token(token)
    if not student:
        return jsonify({"ok": False, "error": "Invalid token"}), 400

    cs = db.session.execute(
        db.select(ClearanceStatus).where(
            ClearanceStatus.student_id == student.id,
            ClearanceStatus.office_id == current_user.office_id,
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
            "office_id": current_user.office_id,
            "clearance": {
                "state": (cs.state if cs else ClearanceState.PENDING.value),
                "note": (cs.note if cs else None),
            },
        }
    )

