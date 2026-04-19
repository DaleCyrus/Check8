#!/usr/bin/env python3
"""
Demo script to show a faculty user managing multiple courses/faculties
"""

from app import create_app
from app.extensions import db
from app.models import Faculty, FacultyAssignment, User

def demo_multiple_faculty_management():
    app = create_app()
    with app.app_context():
        print("=== DEMO: Faculty User Managing Multiple Courses ===\n")

        # Get existing faculty user (Prof. Arnie)
        faculty_user = db.session.execute(
            db.select(User).where(User.username == "Sir Arnie")
        ).scalar_one_or_none()

        if not faculty_user:
            print("Faculty user 'Sir Arnie' not found.")
            return

        print(f"Faculty User: {faculty_user.full_name} ({faculty_user.username})")
        print(f"Currently assigned to: {[f.name for f in faculty_user.assigned_faculties]}")

        # Assign this faculty user to manage DSA as well (in addition to Software Engr.1)
        dsa_faculty = db.session.execute(
            db.select(Faculty).where(Faculty.name == "DSA")
        ).scalar_one_or_none()

        if dsa_faculty:
            # Check if assignment already exists
            existing = db.session.execute(
                db.select(FacultyAssignment).where(
                    FacultyAssignment.user_id == faculty_user.id,
                    FacultyAssignment.faculty_id == dsa_faculty.id
                )
            ).scalar_one_or_none()

            if not existing:
                assignment = FacultyAssignment(
                    user_id=faculty_user.id,
                    faculty_id=dsa_faculty.id
                )
                db.session.add(assignment)
                db.session.commit()
                print(f"✅ Assigned {faculty_user.full_name} to also manage: {dsa_faculty.name}")
            else:
                print(f"ℹ️  {faculty_user.full_name} is already assigned to {dsa_faculty.name}")

        # Show updated assignments
        print(f"\nUpdated assignments for {faculty_user.full_name}:")
        for faculty in faculty_user.assigned_faculties:
            print(f"  - {faculty.name}")

        print("\n🎉 Now this faculty user can manage clearances for:")
        print("   • Software Engr.1")
        print("   • DSA")
        print("\n💡 Login as 'Sir Arnie' to see both courses in the dashboard!")
        print("\n💡 The dashboard will show clearances from all assigned faculties!")
        print("\n💡 When searching for students, you can add them to any of your assigned faculties!")
if __name__ == "__main__":
    demo_multiple_faculty_management()