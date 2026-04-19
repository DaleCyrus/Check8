"""
Cleanup script to remove demo data created by demo_multiple_clearances.py
"""

from app import create_app
from app.extensions import db
from app.models import ClearanceStatus, Faculty, User

def cleanup_demo_data():
    app = create_app()
    with app.app_context():
        print("Cleaning up demo data...")

        # Remove clearance statuses for demo student
        demo_student = db.session.execute(
            db.select(User).where(User.student_number == "2022-0001")
        ).scalar_one_or_none()

        if demo_student:
            clearances_deleted = db.session.execute(
                db.delete(ClearanceStatus).where(ClearanceStatus.student_id == demo_student.id)
            ).rowcount
            print(f"Removed {clearances_deleted} clearance records for demo student")

        demo_usernames = ["faculty1", "faculty2", "faculty3"]
        for username in demo_usernames:
            user = db.session.execute(
                db.select(User).where(User.username == username)
            ).scalar_one_or_none()
            if user:
                db.session.delete(user)
                print(f"Removed faculty user: {username}")

        if demo_student:
            db.session.delete(demo_student)
            print("Removed demo student: Gian Karlo Student (2022-0001)")

        demo_faculty_names = ["Registrar", "Library", "CS Department"]
        for faculty_name in demo_faculty_names:
            faculty = db.session.execute(
                db.select(Faculty).where(Faculty.name == faculty_name)
            ).scalar_one_or_none()
            if faculty:
                db.session.delete(faculty)
                print(f"Removed faculty: {faculty_name}")

        db.session.commit()
        print("Cleanup complete!")

if __name__ == "__main__":
    cleanup_demo_data()
