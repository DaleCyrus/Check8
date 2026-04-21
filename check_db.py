"""
Check current database contents
"""

from app import create_app
from app.extensions import db
from app.models import ClearanceStatus, Course, Faculty, User

def check_database():
    app = create_app()
    with app.app_context():
        print("=== CURRENT DATABASE CONTENTS ===\n")

        print("FACULTIES:")
        faculties = db.session.execute(db.select(Faculty)).scalars().all()
        if faculties:
            for faculty in faculties:
                print(f"  - {faculty.name} (ID: {faculty.id})")
        else:
            print("  No faculties found")

        print("\nUSERS:")
        users = db.session.execute(db.select(User)).scalars().all()
        if users:
            for user in users:
                role = "Student" if user.is_student else "Faculty"
                if user.is_faculty:
                    assigned_faculty_names = [f.name for f in user.assigned_faculties]
                    faculty_info = f" - {', '.join(assigned_faculty_names)}" if assigned_faculty_names else ""
                else:
                    faculty_info = ""
                print(f"  - {user.full_name} ({user.student_number or user.username}) - {role}{faculty_info}")
        else:
            print("  No users found")

        print("\nCLEARANCE STATUSES:")
        clearances = db.session.execute(
            db.select(ClearanceStatus, User, Course, Faculty)
            .join(User, ClearanceStatus.student_id == User.id)
            .join(Course, ClearanceStatus.course_id == Course.id)
            .join(Faculty, Course.faculty_id == Faculty.id)
        ).all()
        if clearances:
            for cs, student, course, faculty in clearances:
                print(f"  - {student.full_name} ({student.student_number}) - {course.name} ({faculty.name}): {cs.state}")
        else:
            print("  No clearance statuses found")

if __name__ == "__main__":
    check_database()
