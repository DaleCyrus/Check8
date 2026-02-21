import argparse

from app import create_app
from app.extensions import db
from app.models import ClearanceState, ClearanceStatus, Office, Role, User


# You can freely add more offices / students here.
# Just append new tuples following the same pattern.
OFFICE_DEFS: list[tuple[str, str, str, str]] = [
    # (office_name, username, full_name, password)
    ("Registrar", "registrar", "Registrar Office", "office123"),
    ("Library", "library", "Library Office", "office123"),
    ("CS Department", "csdept", "CS Department Office", "office123"),
]

STUDENT_DEFS: list[tuple[str, str, str]] = [
    # (student_number, full_name, password)
    ("2022-0001", "Gian Karlo Student", "student123"),
    ("2022-0002", "Sample Student Two", "student123"),
]


def get_or_create_office(name: str) -> Office:
    office = db.session.execute(db.select(Office).where(Office.name == name)).scalar_one_or_none()
    if office:
        return office
    office = Office(name=name)
    db.session.add(office)
    db.session.commit()
    return office


def get_or_create_student(student_number: str, full_name: str, password: str) -> User:
    u = db.session.execute(db.select(User).where(User.student_number == student_number)).scalar_one_or_none()
    if u:
        return u
    u = User(role=Role.STUDENT.value, student_number=student_number, full_name=full_name, username=None)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def get_or_create_office_user(username: str, full_name: str, password: str, office: Office) -> User:
    u = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if u:
        return u
    u = User(
        role=Role.OFFICE.value,
        username=username,
        full_name=full_name,
        office_id=office.id,
        student_number=None,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def ensure_clearance_rows(student: User, offices: list[Office]) -> None:
    for office in offices:
        cs = db.session.execute(
            db.select(ClearanceStatus).where(
                ClearanceStatus.student_id == student.id,
                ClearanceStatus.office_id == office.id,
            )
        ).scalar_one_or_none()
        if cs:
            continue
        db.session.add(
            ClearanceStatus(
                student_id=student.id,
                office_id=office.id,
                state=ClearanceState.PENDING.value,
            )
        )
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed CHECK8 database with sample data.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            db.drop_all()
            db.create_all()

        # Offices + office users
        offices_by_name: dict[str, Office] = {}
        for office_name, username, full_name, password in OFFICE_DEFS:
            office = get_or_create_office(office_name)
            offices_by_name[office_name] = office
            get_or_create_office_user(username, full_name, password, office)

        offices = list(offices_by_name.values())

        # Students
        students: list[User] = []
        for stud_num, full_name, password in STUDENT_DEFS:
            s = get_or_create_student(stud_num, full_name, password)
            students.append(s)
            ensure_clearance_rows(s, offices)

        print("Seed complete.")
        for stud_num, _full_name, password in STUDENT_DEFS:
            print(f"Student: {stud_num} / {password}")
        for office_name, username, _full_name, password in OFFICE_DEFS:
            print(f"Office: {username} ({office_name}) / {password}")


if __name__ == "__main__":
    main()

