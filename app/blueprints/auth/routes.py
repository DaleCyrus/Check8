from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ...extensions import db
from ...models import ClearanceState, ClearanceStatus, Office, Role, User

bp = Blueprint("auth", __name__)


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
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        # Basic validation
        if not student_number or not full_name or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
            )

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template(
                "auth/signup_student.html",
                student_number=student_number,
                full_name=full_name,
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
            )

        # Create the student user
        user = User(
            role=Role.STUDENT.value,
            student_number=student_number,
            full_name=full_name,
            username=None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create default clearance rows for all offices as pending
        offices = db.session.execute(db.select(Office)).scalars().all()
        for office in offices:
            db.session.add(
                ClearanceStatus(
                    student_id=user.id,
                    office_id=office.id,
                    state=ClearanceState.PENDING.value,
                )
            )
        db.session.commit()

        login_user(user)
        flash("Account created. Welcome!", "success")
        return redirect(url_for("student.dashboard"))

    return render_template("auth/signup_student.html")


@bp.route("/signup/instructor", methods=["GET", "POST"])
def signup_instructor():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        office_name = (request.form.get("office_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not office_name or not username or not full_name or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=office_name,
                username=username,
                full_name=full_name,
            )

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=office_name,
                username=username,
                full_name=full_name,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=office_name,
                username=username,
                full_name=full_name,
            )

        # Username must be unique across office users
        existing = db.session.execute(
            db.select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing:
            flash("That username is already taken.", "error")
            return render_template(
                "auth/signup_instructor.html",
                office_name=office_name,
                username=username,
                full_name=full_name,
            )

        # Office: create or reuse by name
        office = db.session.execute(
            db.select(Office).where(Office.name == office_name)
        ).scalar_one_or_none()
        if not office:
            office = Office(name=office_name)
            db.session.add(office)
            db.session.commit()

        user = User(
            role=Role.OFFICE.value,
            username=username,
            full_name=full_name,
            office_id=office.id,
            student_number=None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Instructor account created. You can now manage clearances for your office.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/signup_instructor.html")


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

