#!/usr/bin/env python3
"""
Migration script to add Course and InstructorCourse tables to support instructor-course assignments.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_add_courses():
    """Add Course and InstructorCourse tables."""
    app = create_app()

    with app.app_context():
        print("Adding Course and InstructorCourse tables...")

        with db.engine.connect() as conn:
            # Check if course table exists
            course_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='course'")
            ).scalar()
            
            if not course_exists:
                # Create Course table
                conn.execute(text("""
                    CREATE TABLE course (
                        id INTEGER NOT NULL,
                        code VARCHAR(20) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        faculty_id INTEGER NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (code),
                        FOREIGN KEY (faculty_id) REFERENCES faculty (id)
                    )
                """))
                print("✓ Course table created")
            else:
                print("✓ Course table already exists")

            # Check if instructor_course table exists
            instructor_course_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='instructor_course'")
            ).scalar()
            
            if not instructor_course_exists:
                # Create InstructorCourse junction table
                conn.execute(text("""
                    CREATE TABLE instructor_course (
                        id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (user_id, course_id),
                        FOREIGN KEY (user_id) REFERENCES user (id),
                        FOREIGN KEY (course_id) REFERENCES course (id)
                    )
                """))
                print("✓ InstructorCourse table created")
            else:
                print("✓ InstructorCourse table already exists")

            conn.commit()

        print("✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_courses()
