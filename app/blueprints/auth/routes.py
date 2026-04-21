from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import OperationalError
import uuid
import time

from ...extensions import db
from ...models import ClearanceState, ClearanceStatus, Faculty, Role, User

bp = Blueprint("auth", __name__)


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


@bp.get("/")
def home():
    if current_user.is_authenticated:
        if getattr(current_user, "is_student", False):
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("admin.dashboard"))
    # Default landing: login screen
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        login_as = request.form.get("login_as") or "student"

        user = None
        if login_as == Role.STUDENT.value:
            user = db.session.execute(
                db.select(User).where(User.student_number == identifier)
            ).scalar_one_or_none()
        else:
            user = db.session.execute(
                db.select(User).where(User.username == identifier)
            ).scalar_one_or_none()

        if not user or not user.check_password(password):
            flash("Invalid credentials.", "error")
            return render_template("auth/login.html")

        login_user(user)
        return redirect(url_for("auth.home"))

    return render_template("auth/login.html")


@bp.get("/signup")
def signup():
    # Role selection page
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))
    return render_template("auth/signup.html")


@bp.route("/signup/student", methods=["GET", "POST"])
def signup_student():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        student_number = (request.form.get("student_number") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        department = (request.form.get("department") or "").strip()
        program = (request.form.get("program") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        # Basic validation
        if not student_number or not full_name or not email or not department or not program or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                email=email,
                department=department,
                program=program,
            )

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                email=email,
                department=department,
                program=program,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                email=email,
                department=department,
                program=program,
            )

        # Ensure student number is unique
        existing = db.session.execute(
            db.select(User).where(User.student_number == student_number)
        ).scalar_one_or_none()
        if existing:
            flash("That student number is already registered.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                email=email,
                department=department,
                program=program,
            )

        # Ensure email is unique
        existing_email = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing_email:
            flash("That email is already registered.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                email=email,
                department=department,
                program=program,
            )

        # Create the student user
        user = User(
            role=Role.STUDENT.value,
            student_number=student_number,
            full_name=full_name,
            email=email,
            department=department,
            program=program,
            username=None,
            qr_salt=str(uuid.uuid4()),
        )
        user.set_password(password)
        db.session.add(user)
        _commit_with_retry()

        # Do not automatically add the student to the faculty's clearance list.
        # Faculty should add students manually via the dashboard search.
        login_user(user)
        flash("Account created. Welcome!", "success")
        return redirect(url_for("student.dashboard"))

    return render_template("auth/signup_student.html")


@bp.route("/signup/instructor", methods=["GET", "POST"])
def signup_instructor():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        faculty_name = (request.form.get("office_name") or "").strip()
        course_code = (request.form.get("course_code") or "").strip()
        course_name = (request.form.get("course_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not faculty_name or not course_code or not course_name or not username or not full_name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=faculty_name,
                course_code=course_code,
                course_name=course_name,
                username=username,
                full_name=full_name,
                email=email,
            )

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=faculty_name,
                course_code=course_code,
                course_name=course_name,
                username=username,
                full_name=full_name,
                email=email,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=faculty_name,
                course_code=course_code,
                course_name=course_name,
                username=username,
                full_name=full_name,
                email=email,
            )

        # Username must be unique across office users
        existing = db.session.execute(
            db.select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing:
            flash("That username is already taken.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=faculty_name,
                course_code=course_code,
                course_name=course_name,
                username=username,
                full_name=full_name,
                email=email,
            )

        # Ensure email is unique
        existing_email = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing_email:
            flash("That email is already registered.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=faculty_name,
                course_code=course_code,
                course_name=course_name,
                username=username,
                full_name=full_name,
                email=email,
            )

        # Faculty: create or reuse by name
        faculty = db.session.execute(
            db.select(Faculty).where(Faculty.name == faculty_name)
        ).scalar_one_or_none()
        if not faculty:
            faculty = Faculty(name=faculty_name)
            db.session.add(faculty)
            db.session.flush()

        # Create course directly linked to faculty
        from ...models import Course
        course = db.session.execute(
            db.select(Course).where(Course.code == course_code)
        ).scalar_one_or_none()
        
        if not course:
            course = Course(
                code=course_code,
                name=course_name,
                faculty_id=faculty.id
            )
            db.session.add(course)
            db.session.flush()

        user = User(
            role=Role.FACULTY.value,
            username=username,
            full_name=full_name,
            email=email,
            student_number=None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Ensure user has ID without committing

        # Create faculty assignment
        from ...models import FacultyAssignment, InstructorCourse
        assignment = FacultyAssignment(
            user_id=user.id,
            faculty_id=faculty.id
        )
        db.session.add(assignment)

        # Create course assignment
        course_assignment = InstructorCourse(
            user_id=user.id,
            course_id=course.id
        )
        db.session.add(course_assignment)
        _commit_with_retry()  # Single commit for all operations

        login_user(user)
        flash("Instructor account created. You can now manage clearances for your course.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/signup_instructor.html")


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

