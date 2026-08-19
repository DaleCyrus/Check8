from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import OperationalError
from datetime import datetime
import uuid
import time

from ...extensions import db
from ...models import Faculty, Role, User

bp = Blueprint("auth", __name__)
ALLOWED_EMAIL_DOMAIN = "@gordoncollege.edu.ph"


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


def _normalize_institutional_email(raw_email: str) -> str | None:
    email = (raw_email or "").strip().lower()
    if not email:
        return ""

    # Support login with username-only input by attaching the institutional domain.
    if "@" not in email:
        email = f"{email}{ALLOWED_EMAIL_DOMAIN}"

    if email.count("@") != 1:
        return None

    local_part, domain = email.split("@", 1)
    if not local_part or domain != ALLOWED_EMAIL_DOMAIN.lstrip("@"):
        return None

    return email


@bp.get("/")
def home():
    if current_user.is_authenticated:
        if getattr(current_user, "is_student", False):
            return redirect(url_for("student.dashboard"))
        if getattr(current_user, "is_admin", False):
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("admin.instructor_dashboard"))
    # Default landing: login screen
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        raw_email = request.form.get("email") or ""
        email = _normalize_institutional_email(raw_email)
        password = request.form.get("password") or ""

        if email is None:
            flash("Email must be from @gordoncollege.edu.ph domain.", "error")
            return render_template("auth/login.html")

        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user or not user.is_active or not user.check_password(password):
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
        last_name = (request.form.get("last_name") or "").strip().upper()
        first_name = (request.form.get("first_name") or "").strip().upper()
        middle_name = (request.form.get("middle_name") or "").strip().upper()
        full_name = " ".join(part for part in (first_name, middle_name, last_name) if part)
        full_name = full_name or (request.form.get("full_name") or "").strip()
        raw_email = request.form.get("email") or ""
        email = _normalize_institutional_email(raw_email)
        department = (request.form.get("department") or "").strip()
        program = (request.form.get("program") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        # Basic validation
        if not student_number or not last_name or not first_name or not raw_email.strip() or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
                department=department,
                program=program,
            )

        # Validate email domain
        if email is None:
            flash("Email must be from @gordoncollege.edu.ph domain.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
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
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
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
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
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
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            email=email,
            department=department,
            program=program,
            username=None,
            qr_salt=str(uuid.uuid4()),
        )
        user.set_password(password)
        db.session.add(user)
        _commit_with_retry()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup_student.html")


@bp.route("/signup/instructor", methods=["GET", "POST"])
def signup_instructor():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        employee_number = (request.form.get("employee_number") or "").strip()
        last_name = (request.form.get("last_name") or "").strip().upper()
        first_name = (request.form.get("first_name") or "").strip().upper()
        middle_name = (request.form.get("middle_name") or "").strip().upper()
        full_name = " ".join(part for part in (first_name, middle_name, last_name) if part)
        raw_email = request.form.get("email") or ""
        email = _normalize_institutional_email(raw_email)
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not employee_number or not last_name or not first_name or not raw_email.strip() or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_instructor.html",
                employee_number=employee_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )

        # Validate email domain
        if email is None:
            flash("Email must be from @gordoncollege.edu.ph domain.", "error")
            return render_template(
                "auth/signup_instructor.html",
                employee_number=employee_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template(
                "auth/signup_instructor.html",
                employee_number=employee_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template(
                "auth/signup_instructor.html",
                employee_number=employee_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
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
                full_name=full_name,
                email=email,
            )

        existing_employee = db.session.execute(
            db.select(User).where(User.employee_number == employee_number)
        ).scalar_one_or_none()
        if existing_employee:
            flash("That employee ID is already registered.", "error")
            return render_template(
                "auth/signup_instructor.html",
                employee_number=employee_number,
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )

        # Generate username from email
        username = email.split('@')[0]

        user = User(
            role=Role.INSTRUCTOR.value,
            username=username,
            full_name=full_name,
            email=email,
            student_number=None,
            employee_number=employee_number,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )
        user.set_password(password)
        db.session.add(user)
        _commit_with_retry()

        flash("Instructor account created successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup_instructor.html")


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

