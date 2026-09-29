import enum
from datetime import datetime, timezone
from typing import Any, cast

from flask_login import UserMixin  # type: ignore[import-untyped]
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class Role(enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class ClearanceState(enum.Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    BLOCKED = "blocked"


class FacultyRole(enum.Enum):
    INSTRUCTOR = "instructor"
    COORDINATOR = "coordinator"
    DEAN = "dean"


class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    # Many-to-many relationship with users (faculty members)
    assigned_users = db.relationship("FacultyAssignment", back_populates="faculty")
    courses = db.relationship("Course", back_populates="faculty")

    def __repr__(self):
        return f"<Faculty {self.name}>"


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    
    # Many-to-many relationship with instructors
    instructor_assignments = db.relationship("InstructorCourse", back_populates="course", cascade="all, delete-orphan")
    # Many-to-many relationship with students
    student_enrollments = db.relationship("StudentCourse", back_populates="course", cascade="all, delete-orphan")
    # Clearance records for this course
    clearance_statuses = db.relationship("ClearanceStatus", cascade="all, delete-orphan")
    # Student groups for this course
    student_groups = db.relationship("StudentGroup", cascade="all, delete-orphan")
    faculty = db.relationship("Faculty", back_populates="courses")

    def __repr__(self):
        return f"<Course {self.code} {self.name}>"


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


class InstructorCourse(db.Model):
    """Junction table for instructor assignments to courses"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    user = db.relationship("User", back_populates="course_assignments")
    course = db.relationship("Course", back_populates="instructor_assignments")

    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="uq_instructor_course"),)

    def __repr__(self):
        return f"<InstructorCourse user={self.user_id} course={self.course_id}>"


class StudentCourse(db.Model):
    """Junction table for student course enrollments"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    user = db.relationship("User", back_populates="student_courses")
    course = db.relationship("Course", back_populates="student_enrollments")

    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="uq_student_course"),)

    def __repr__(self):
        return f"<StudentCourse user={self.user_id} course={self.course_id}>"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # type: ignore[assignment]

    # Student login field
    student_number = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Instructor login field
    employee_number = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Faculty login field
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)

    # Email field (institutional)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Remove direct faculty_id relationship - now handled by FacultyAssignment
    # faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=True)
    # faculty = db.relationship("Faculty")

    # Add many-to-many relationship for faculty assignments
    faculty_assignments = db.relationship("FacultyAssignment", back_populates="user")
    course_assignments = db.relationship("InstructorCourse", back_populates="user")
    student_courses = db.relationship("StudentCourse", back_populates="user")

    full_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(60), nullable=True)
    first_name = db.Column(db.String(60), nullable=True)
    middle_name = db.Column(db.String(60), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Student-specific fields
    department = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    qr_salt = db.Column(db.String(64), nullable=True)

    @property
    def assigned_courses(self) -> list[Course]:
        """Get all courses assigned to this user (for instructor users)"""
        if self.is_faculty:
            assignments = cast(list[InstructorCourse], self.course_assignments)
            return [cast(Course, assignment.course) for assignment in assignments]
        return []

    @property
    def enrolled_courses(self) -> list[Course]:
        """Get all courses enrolled by this student"""
        if self.is_student:
            enrollments = cast(list[StudentCourse], self.student_courses)
            return [cast(Course, enrollment.course) for enrollment in enrollments]
        return []

    @property
    def assigned_faculties(self) -> list[Faculty]:
        """Get all faculties assigned to this user (for faculty users)"""
        if self.is_faculty:
            assignments = cast(list[FacultyAssignment], self.faculty_assignments)
            return [cast(Faculty, assignment.faculty) for assignment in assignments]
        return []

    @property
    def primary_faculty(self) -> Faculty | None:
        """Get the first assigned faculty (for backward compatibility)"""
        faculties = self.assigned_faculties
        return faculties[0] if faculties else None

    @property
    def faculty_id(self) -> int | None:
        """Backward compatibility property"""
        primary = self.primary_faculty
        return primary.id if primary else None

    @property
    def faculty(self) -> Faculty | None:
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
        return self.role in {Role.FACULTY.value, Role.INSTRUCTOR.value}

    @property
    def is_instructor(self) -> bool:
        return self.role in {Role.FACULTY.value, Role.INSTRUCTOR.value}

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN.value

    def get_roles_for_faculty(self, faculty_id: int) -> list[FacultyRole]:
        """Get all roles this user has in a specific faculty"""
        roles = db.session.query(FacultyUserRole).filter_by(
            user_id=self.id, faculty_id=faculty_id
        ).all()
        return [FacultyRole(role.role) for role in roles]

    def has_faculty_role(self, faculty_id: int, role: FacultyRole | str) -> bool:
        """Check if user has a specific role in a faculty"""
        role_value = role.value if isinstance(role, FacultyRole) else role
        return db.session.query(FacultyUserRole).filter_by(
            user_id=self.id, faculty_id=faculty_id, role=role_value
        ).first() is not None

    def get_managed_students_for_course(self, course_id: int):
        """Get all students this user can manage for a course"""
        return db.session.query(User).join(
            StudentCourse, User.id == StudentCourse.user_id
        ).filter(
            StudentCourse.course_id == course_id,
            User.role == Role.STUDENT.value
        ).all()

    def __repr__(self):
        return f"<User {self.id} {self.role}>"


class ClearanceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True)

    state = db.Column(db.String(20), nullable=False, default=ClearanceState.PENDING.value)
    note = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    course = db.relationship("Course", foreign_keys=[course_id], back_populates="clearance_statuses")

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", name="uq_student_course_clearance"),)

    def __repr__(self):
        return f"<ClearanceStatus student={self.student_id} course={self.course_id} {self.state}>"


class StudentGroup(db.Model):
    """Group/Block of students created by faculty for easier management"""
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    faculty = db.relationship("Faculty")
    course = db.relationship("Course", foreign_keys=[course_id], back_populates="student_groups")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    members = db.relationship("StudentGroupMember", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("created_by_user_id", "course_id", "name", name="uq_group_name_per_user_course"),)

    def __repr__(self):
        return f"<StudentGroup {self.name} (course_id={self.course_id})>"


class StudentGroupMember(db.Model):
    """Junction table for student group memberships"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("student_group.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    group = db.relationship("StudentGroup", back_populates="members")
    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("group_id", "student_id", name="uq_group_student"),)

    def __repr__(self):
        return f"<StudentGroupMember group_id={self.group_id} student_id={self.student_id}>"


class FacultyUserRole(db.Model):
    """Junction table for multiple faculty roles per user per faculty"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])
    faculty = db.relationship("Faculty")

    __table_args__ = (db.UniqueConstraint("user_id", "faculty_id", "role", name="uq_user_faculty_role"),)

    def __repr__(self):
        return f"<FacultyUserRole user={self.user_id} faculty={self.faculty_id} role={self.role}>"





@cast(Any, login_manager).user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except ValueError:
        return None

