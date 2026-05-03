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

    # Student login field
    student_number = db.Column(db.String(32), unique=True, nullable=True, index=True)

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
    password_hash = db.Column(db.String(255), nullable=False)

    # Student-specific fields
    department = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    qr_salt = db.Column(db.String(64), nullable=True)

    @property
    def assigned_courses(self):
        """Get all courses assigned to this user (for instructor users)"""
        if self.is_faculty:
            return [assignment.course for assignment in self.course_assignments]
        return []

    @property
    def enrolled_courses(self):
        """Get all courses enrolled by this student"""
        if self.is_student:
            return [enrollment.course for enrollment in self.student_courses]
        return []

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

    def get_roles_for_faculty(self, faculty_id: int):
        """Get all roles this user has in a specific faculty"""
        roles = db.session.query(FacultyUserRole).filter_by(
            user_id=self.id, faculty_id=faculty_id
        ).all()
        return [FacultyRole(role.role) for role in roles]

    def has_faculty_role(self, faculty_id: int, role) -> bool:
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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


class Semester(db.Model):
    """Academic semester for organizing clearance events"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)  # e.g., "2024-2025 2nd Semester"
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    default_signatories = db.relationship("DefaultSignatory", back_populates="semester", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Semester {self.name}>"


class DefaultSignatory(db.Model):
    """Default signatories (College Dean, CCS Council, etc.) that should be auto-assigned to students per semester"""
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)  # e.g., "College Dean", "CCS Council", "SPEC Organization"
    description = db.Column(db.String(500), nullable=True)
    order = db.Column(db.Integer, default=0)  # For sorting
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    semester = db.relationship("Semester", back_populates="default_signatories")

    __table_args__ = (db.UniqueConstraint("semester_id", "name", name="uq_semester_signatory_name"),)

    def __repr__(self):
        return f"<DefaultSignatory {self.name} (semester_id={self.semester_id})>"


class Event(db.Model):
    """Event within a semester (e.g., College Dean clearance, CCS Council clearance)"""
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)  # e.g., "College Dean", "CCS Council"
    description = db.Column(db.String(500), nullable=True)
    is_signatory = db.Column(db.Boolean, default=False, nullable=False)  # True if this is a default signatory
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    semester = db.relationship("Semester", foreign_keys=[semester_id])
    enrollments = db.relationship("EventEnrollment", back_populates="event", cascade="all, delete-orphan")
    clearances = db.relationship("EventClearance", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("semester_id", "name", name="uq_semester_event_name"),)

    def __repr__(self):
        return f"<Event {self.name} (semester_id={self.semester_id})>"


class EventEnrollment(db.Model):
    """Student enrollment in an event"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("Event", back_populates="enrollments")
    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("event_id", "student_id", name="uq_event_student_enrollment"),)

    def __repr__(self):
        return f"<EventEnrollment student={self.student_id} event={self.event_id}>"


class EventClearance(db.Model):
    """Clearance status for event (similar to ClearanceStatus but for events/signatories)"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    state = db.Column(db.String(20), nullable=False, default=ClearanceState.PENDING.value)
    note = db.Column(db.String(255), nullable=True)
    cleared_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = db.relationship("Event", back_populates="clearances")
    student = db.relationship("User", foreign_keys=[student_id])
    cleared_by = db.relationship("User", foreign_keys=[cleared_by_user_id])

    __table_args__ = (db.UniqueConstraint("event_id", "student_id", name="uq_event_student_clearance"),)

    def __repr__(self):
        return f"<EventClearance student={self.student_id} event={self.event_id} {self.state}>"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

