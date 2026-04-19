def name_to_png_bytes(name: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(name)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
import base64
import io

import qrcode
from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

from ..extensions import db
from ..models import User


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="check8-qr")


def make_student_token(student: User) -> str:
    if not student.is_student:
        raise ValueError("QR token can only be generated for student users")
    payload = {"sid": student.id, "salt": student.qr_salt}
    return _serializer().dumps(payload)


def verify_student_token(token: str) -> User | None:
    try:
        payload = _serializer().loads(token)
    except BadSignature:
        return None

    sid = payload.get("sid")
    salt = payload.get("salt")
    if not sid or not salt:
        return None

    student = db.session.get(User, int(sid))
    if not student or not student.is_student:
        return None

    if student.qr_salt != salt:
        return None
    return student


def token_to_png_bytes(token: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def token_to_data_uri(token: str) -> str:
    png = token_to_png_bytes(token)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"

