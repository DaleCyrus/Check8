import enum
import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class Role(enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"


class ClearanceState(enum.Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    BLOCKED = "blocked"


class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    # Many-to-many relationship with users (faculty members)
    assigned_users = db.relationship("FacultyAssignment", back_populates="faculty")

    def __repr__(self):
        return f"<Faculty {self.name}>"


class FacultyAssignment(db.Model):
    """Junction table for faculty user assignments to multiple faculties"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)

    user = db.relationship("User", back_populates="faculty_assignments")
    faculty = db.relationship("Faculty", back_populates="assigned_users")

    __table_args__ = (db.UniqueConstraint("user_id", "faculty_id", name="uq_user_faculty"),)

    def __repr__(self):
        return f"<FacultyAssignment user={self.user_id} faculty={self.faculty_id}>"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)

    # Student login field
    student_number = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Faculty login field
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)

    # Remove direct faculty_id relationship - now handled by FacultyAssignment
    # faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=True)
    # faculty = db.relationship("Faculty")

    # Add many-to-many relationship for faculty assignments
    faculty_assignments = db.relationship("FacultyAssignment", back_populates="user")

    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Student-specific fields
    department = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    qr_salt = db.Column(db.String(64), nullable=True)

    @property
    def assigned_faculties(self):
        """Get all faculties assigned to this user (for faculty users)"""
        if self.is_faculty:
            return [assignment.faculty for assignment in self.faculty_assignments]
        return []

    @property
    def primary_faculty(self):
        """Get the first assigned faculty (for backward compatibility)"""
        faculties = self.assigned_faculties
        return faculties[0] if faculties else None

    @property
    def faculty_id(self):
        """Backward compatibility property"""
        primary = self.primary_faculty
        return primary.id if primary else None

    @property
    def faculty(self):
        """Backward compatibility property"""
        return self.primary_faculty

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT.value

    @property
    def is_faculty(self) -> bool:
        return self.role == Role.FACULTY.value

    def __repr__(self):
        return f"<User {self.id} {self.role}>"


class ClearanceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False, index=True)

    state = db.Column(db.String(20), nullable=False, default=ClearanceState.PENDING.value)
    note = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    faculty = db.relationship("Faculty")

    __table_args__ = (db.UniqueConstraint("student_id", "faculty_id", name="uq_student_faculty"),)

    def __repr__(self):
        return f"<ClearanceStatus student={self.student_id} faculty={self.faculty_id} {self.state}>"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

