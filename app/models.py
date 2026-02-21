import enum
import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class Role(enum.Enum):
    STUDENT = "student"
    OFFICE = "office"


class ClearanceState(enum.Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    BLOCKED = "blocked"


class Office(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f"<Office {self.name}>"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)

    # Student login field
    student_number = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Office login field
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)
    office_id = db.Column(db.Integer, db.ForeignKey("office.id"), nullable=True)
    office = db.relationship("Office")

    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    qr_salt = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT.value

    @property
    def is_office(self) -> bool:
        return self.role == Role.OFFICE.value

    def __repr__(self):
        return f"<User {self.id} {self.role}>"


class ClearanceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    office_id = db.Column(db.Integer, db.ForeignKey("office.id"), nullable=False, index=True)

    state = db.Column(db.String(20), nullable=False, default=ClearanceState.PENDING.value)
    note = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    office = db.relationship("Office")

    __table_args__ = (db.UniqueConstraint("student_id", "office_id", name="uq_student_office"),)

    def __repr__(self):
        return f"<ClearanceStatus student={self.student_id} office={self.office_id} {self.state}>"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

