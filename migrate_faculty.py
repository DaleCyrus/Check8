#!/usr/bin/env python3
"""
Database migration script to convert from single faculty assignment to multiple faculty assignments
"""

from app import create_app
from app.extensions import db
from app.models import Faculty, FacultyAssignment, User

def migrate_to_multiple_faculties():
    app = create_app()
    with app.app_context():
        print("Starting migration to multiple faculty assignments...")

        # Create the new FacultyAssignment table
        db.create_all()

        # For migration, we need to access the old faculty_id column directly
        # Since we removed it from the model, we'll use raw SQL or access the table directly
        from sqlalchemy import text
        
        # Get faculty users with their faculty_id using raw SQL
        result = db.session.execute(text("""
            SELECT id, faculty_id FROM user 
            WHERE role = 'faculty' AND faculty_id IS NOT NULL
        """))
        
        faculty_users = result.fetchall()
        print(f"Found {len(faculty_users)} faculty users with existing assignments")

        for user_id, faculty_id in faculty_users:
            # Check if assignment already exists
            existing = db.session.execute(
                db.select(FacultyAssignment).where(
                    FacultyAssignment.user_id == user_id,
                    FacultyAssignment.faculty_id == faculty_id
                )
            ).scalar_one_or_none()

            if not existing:
                assignment = FacultyAssignment(
                    user_id=user_id,
                    faculty_id=faculty_id
                )
                db.session.add(assignment)
                faculty = db.session.get(Faculty, faculty_id)
                print(f"  Migrated user {user_id} -> {faculty.name if faculty else 'Unknown'}")

        try:
            db.session.commit()
            print("Migration completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            return False

        return True

if __name__ == "__main__":
    migrate_to_multiple_faculties()