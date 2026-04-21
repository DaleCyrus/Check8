#!/usr/bin/env python3
"""
Migration script to add StudentCourse enrollment table and update ClearanceStatus to use course_id.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_student_course_and_clearance():
    """Add StudentCourse table and migrate ClearanceStatus to course-based."""
    app = create_app()

    with app.app_context():
        print("Migrating to course-based enrollment and clearance system...")

        with db.engine.connect() as conn:
            # Check if student_course table exists
            student_course_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='student_course'")
            ).scalar()
            
            if not student_course_exists:
                print("Creating StudentCourse table...")
                conn.execute(text("""
                    CREATE TABLE student_course (
                        id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (user_id, course_id),
                        FOREIGN KEY (user_id) REFERENCES user (id),
                        FOREIGN KEY (course_id) REFERENCES course (id)
                    )
                """))
                print("✓ StudentCourse table created")
            else:
                print("✓ StudentCourse table already exists")

            # Check if clearance_status has course_id column
            clearance_columns = conn.execute(
                text("PRAGMA table_info(clearance_status)")
            ).fetchall()
            column_names = [col[1] for col in clearance_columns]
            
            if 'course_id' not in column_names:
                print("Migrating ClearanceStatus from faculty to course-based...")
                
                # Rename old table
                conn.execute(text("ALTER TABLE clearance_status RENAME TO clearance_status_old"))
                
                # Create new table with course_id
                conn.execute(text("""
                    CREATE TABLE clearance_status (
                        id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        state VARCHAR(20) NOT NULL,
                        note VARCHAR(255),
                        updated_at DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (student_id, course_id),
                        FOREIGN KEY (student_id) REFERENCES user (id),
                        FOREIGN KEY (course_id) REFERENCES course (id)
                    )
                """))
                
                # Migrate data: For each old clearance record, find courses in that faculty
                # and create clearance records for each course
                print("Migrating clearance records...")
                conn.execute(text("""
                    INSERT INTO clearance_status (student_id, course_id, state, note, updated_at)
                    SELECT 
                        cs.student_id,
                        c.id,
                        cs.state,
                        cs.note,
                        cs.updated_at
                    FROM clearance_status_old cs
                    JOIN course c ON c.faculty_id = cs.faculty_id
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE clearance_status_old"))
                print("✓ ClearanceStatus migrated to course-based system")
            else:
                print("✓ ClearanceStatus already uses course_id")

            conn.commit()

        print("\n✓ Migration completed successfully!")
        print("\nNew relationships:")
        print("  - One instructor → many courses")
        print("  - One course → many students (via StudentCourse)")
        print("  - One student → many courses (via StudentCourse)")
        print("  - One student + one course → one clearance record")

if __name__ == "__main__":
    migrate_student_course_and_clearance()
