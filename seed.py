import argparse
import uuid

from app import create_app
from app.extensions import db
from app.models import ClearanceState, ClearanceStatus, Faculty, Role, User


# You can freely add more faculties / students here.
# Just append new tuples following the same pattern.
FACULTY_DEFS: list[tuple[str, str, str, str]] = [
    # (faculty_name, username, full_name, password)
    ("Registrar", "registrar", "Registrar Office", "office123"),
    ("Library", "library", "Library Office", "office123"),
    ("CS Department", "csdept", "CS Department Office", "office123"),
]

STUDENT_DEFS: list[tuple[str, str, str, str, str]] = [
    # (student_number, full_name, department, program, password)
    ("2022-0001", "Gian Karlo Student", "College of Computer Studies", "Bachelor of Science in Computer Science", "student123"),
    ("2022-0002", "Sample Student Two", "College of Engineering", "Bachelor of Science in Civil Engineering", "student123"),
]


def get_or_create_faculty(name: str) -> Faculty:
    faculty = db.session.execute(db.select(Faculty).where(Faculty.name == name)).scalar_one_or_none()
    if faculty:
        return faculty
    faculty = Faculty(name=name)
    db.session.add(faculty)
    db.session.commit()
    return faculty


def get_or_create_student(student_number: str, full_name: str, department: str, program: str, password: str) -> User:
    u = db.session.execute(db.select(User).where(User.student_number == student_number)).scalar_one_or_none()
    if u:
        return u
    u = User(
        role=Role.STUDENT.value, 
        student_number=student_number, 
        full_name=full_name,
        department=department,
        program=program,
        username=None,
        qr_salt=str(uuid.uuid4())
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def get_or_create_faculty_user(username: str, full_name: str, password: str, faculty: Faculty) -> User:
    u = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if u:
        return u
    u = User(
        role=Role.FACULTY.value,
        username=username,
        full_name=full_name,
        student_number=None,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()

    # Create faculty assignment
    from .models import FacultyAssignment
    assignment = FacultyAssignment(
        user_id=u.id,
        faculty_id=faculty.id
    )
    db.session.add(assignment)
    db.session.commit()
    return u


# Removed automatic clearance row creation.
# Staff now explicitly add students via the "Add Students to Clearance List" feature.
# This ensures staff only see students they've specifically added.
def ensure_clearance_rows(student: User, faculties: list[Faculty]) -> None:
    pass


def main():
    parser = argparse.ArgumentParser(description="Seed CHECK8 database with sample data.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            db.drop_all()
            db.create_all()

        # Faculties + faculty users
        faculties_by_name: dict[str, Faculty] = {}
        for faculty_name, username, full_name, password in FACULTY_DEFS:
            faculty = get_or_create_faculty(faculty_name)
            faculties_by_name[faculty_name] = faculty
            get_or_create_faculty_user(username, full_name, password, faculty)

        faculties = list(faculties_by_name.values())

        # Students
        students: list[User] = []
        for stud_num, full_name, department, program, password in STUDENT_DEFS:
            s = get_or_create_student(stud_num, full_name, department, program, password)
            students.append(s)
            ensure_clearance_rows(s, faculties)

        print("Seed complete.")
        for stud_num, full_name, department, program, password in STUDENT_DEFS:
            print(f"Student: {stud_num} ({department} - {program}) / {password}")
        for faculty_name, username, _full_name, password in FACULTY_DEFS:
            print(f"Faculty: {username} ({faculty_name}) / {password}")


if __name__ == "__main__":
    main()

