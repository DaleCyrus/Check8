import argparse
import uuid

from app import create_app
from app.extensions import db
from app.models import ClearanceState, ClearanceStatus, Course, Faculty, FacultyAssignment, Role, StudentCourse, User


# You can freely add more faculties / students here.
# Just append new tuples following the same pattern.
FACULTY_DEFS: list[tuple[str, str, str, str, str]] = [
    # (faculty_name, username, full_name, email, password)
    ("Registrar", "registrar", "Registrar Office", "registrar@institution.edu", "office123"),
    ("Library", "library", "Library Office", "library@institution.edu", "office123"),
    ("CS Department", "csdept", "CS Department Office", "csdept@institution.edu", "office123"),
]

STUDENT_DEFS: list[tuple[str, str, str, str, str, str]] = [
    # (student_number, full_name, department, program, email, password)
    ("2022-0001", "Gian Karlo Student", "College of Computer Studies", "Bachelor of Science in Computer Science", "2022-0001@student.edu", "student123"),
    ("2022-0002", "Sample Student Two", "College of Engineering", "Bachelor of Science in Civil Engineering", "2022-0002@student.edu", "student123"),
]

COURSES_DEFS: list[tuple[str, str, str]] = [
    # (course_code, course_name, faculty_name)
    ("CS101", "Introduction to Programming", "CS Department"),
    ("CS102", "Data Structures", "CS Department"),
    ("CS103", "Database Management", "CS Department"),
]

# Define student-course enrollments
# (student_number, course_code)
STUDENT_COURSE_DEFS: list[tuple[str, str]] = [
    ("2022-0001", "CS101"),
    ("2022-0001", "CS102"),
    ("2022-0001", "CS103"),
    ("2022-0002", "CS101"),
]


def get_or_create_faculty(name: str) -> Faculty:
    faculty = db.session.execute(db.select(Faculty).where(Faculty.name == name)).scalar_one_or_none()
    if faculty:
        return faculty
    faculty = Faculty(name=name)
    db.session.add(faculty)
    db.session.commit()
    return faculty


def get_or_create_student(student_number: str, full_name: str, department: str, program: str, email: str, password: str) -> User:
    u = db.session.execute(db.select(User).where(User.student_number == student_number)).scalar_one_or_none()
    if u:
        return u
    u = User(
        role=Role.STUDENT.value, 
        student_number=student_number, 
        full_name=full_name,
        email=email,
        department=department,
        program=program,
        username=None,
        qr_salt=str(uuid.uuid4())
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def get_or_create_faculty_user(username: str, full_name: str, email: str, password: str, faculty: Faculty) -> User:
    u = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if u:
        return u
    u = User(
        role=Role.FACULTY.value,
        username=username,
        full_name=full_name,
        email=email,
        student_number=None,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()

    # Create faculty assignment
    assignment = FacultyAssignment(
        user_id=u.id,
        faculty_id=faculty.id
    )
    db.session.add(assignment)
    db.session.commit()
    return u


def get_or_create_course(code: str, name: str, faculty: Faculty) -> Course:
    course = db.session.execute(db.select(Course).where(Course.code == code)).scalar_one_or_none()
    if course:
        return course
    course = Course(
        code=code,
        name=name,
        faculty_id=faculty.id
    )
    db.session.add(course)
    db.session.commit()
    return course


def enroll_student_in_course(student: User, course: Course) -> StudentCourse:
    enrollment = db.session.execute(
        db.select(StudentCourse).where(
            (StudentCourse.user_id == student.id) & (StudentCourse.course_id == course.id)
        )
    ).scalar_one_or_none()
    if enrollment:
        return enrollment
    enrollment = StudentCourse(user_id=student.id, course_id=course.id)
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


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
        for faculty_name, username, full_name, email, password in FACULTY_DEFS:
            faculty = get_or_create_faculty(faculty_name)
            faculties_by_name[faculty_name] = faculty
            get_or_create_faculty_user(username, full_name, email, password, faculty)

        faculties = list(faculties_by_name.values())

        # Students
        students: list[User] = []
        students_by_number: dict[str, User] = {}
        for stud_num, full_name, department, program, email, password in STUDENT_DEFS:
            s = get_or_create_student(stud_num, full_name, department, program, email, password)
            students.append(s)
            students_by_number[stud_num] = s
            ensure_clearance_rows(s, faculties)

        # Courses
        courses_by_code: dict[str, Course] = {}
        for course_code, course_name, faculty_name in COURSES_DEFS:
            faculty = faculties_by_name[faculty_name]
            course = get_or_create_course(course_code, course_name, faculty)
            courses_by_code[course_code] = course

        # Student enrollments
        for student_number, course_code in STUDENT_COURSE_DEFS:
            student = students_by_number[student_number]
            course = courses_by_code[course_code]
            enroll_student_in_course(student, course)

        print("Seed complete.")
        for stud_num, full_name, department, program, email, password in STUDENT_DEFS:
            print(f"Student: {stud_num} ({department} - {program}) / {email} / {password}")
        for faculty_name, username, _full_name, email, password in FACULTY_DEFS:
            print(f"Faculty: {username} ({faculty_name}) / {email} / {password}")
        for course_code, course_name, faculty_name in COURSES_DEFS:
            print(f"Course: {course_code} - {course_name} ({faculty_name})")


if __name__ == "__main__":
    main()

