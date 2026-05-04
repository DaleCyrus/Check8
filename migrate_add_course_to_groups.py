#!/usr/bin/env python3
"""
Migration script to add course_id to StudentGroup table and update group isolation to be per-course.
This allows students to be in different groups of the same faculty if they're for different courses.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_add_course_to_groups():
    """Add course_id column to student_group table and migrate data."""
    app = create_app()

    with app.app_context():
        print("Adding course_id to StudentGroup table...")

        with db.engine.connect() as conn:
            # Check if course_id column exists
            result = conn.execute(
                text("PRAGMA table_info(student_group)")
            ).fetchall()
            
            column_names = [row[1] for row in result]
            
            if "course_id" not in column_names:
                print("Adding course_id column to student_group table...")
                
                # For SQLite, we need to:
                # 1. Create a backup
                # 2. Create new table with course_id
                # 3. Copy data
                # 4. Drop old table
                # 5. Rename new table
                
                # Since we can't easily get course context from existing groups,
                # we'll make course_id nullable temporarily for the migration
                conn.execute(text("""
                    ALTER TABLE student_group ADD COLUMN course_id INTEGER
                """))
                
                print("✓ course_id column added (nullable)")
                
                # Create a temporary mapping: for each group, use the first course of its faculty
                # This is a safe default that maintains the existing behavior
                print("Migrating existing groups to courses...")
                
                conn.execute(text("""
                    UPDATE student_group
                    SET course_id = (
                        SELECT id FROM course 
                        WHERE faculty_id = student_group.faculty_id 
                        LIMIT 1
                    )
                """))
                
                conn.commit()
                print("✓ Existing groups migrated to courses")
                
                # Now make course_id NOT NULL and add foreign key constraint
                # Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT, 
                # so we need to recreate the table
                print("Recreating table with NOT NULL constraint...")
                
                # Backup existing data
                conn.execute(text("ALTER TABLE student_group RENAME TO student_group_old"))
                
                # Create new table with proper constraints
                conn.execute(text("""
                    CREATE TABLE student_group (
                        id INTEGER NOT NULL,
                        faculty_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        created_by_user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description VARCHAR(500),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (created_by_user_id, course_id, name),
                        FOREIGN KEY (faculty_id) REFERENCES faculty (id),
                        FOREIGN KEY (course_id) REFERENCES course (id),
                        FOREIGN KEY (created_by_user_id) REFERENCES user (id)
                    )
                """))
                
                # Create indices if they don't exist
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_student_group_faculty_id ON student_group (faculty_id)
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_student_group_course_id ON student_group (course_id)
                """))
                
                # Copy data back
                conn.execute(text("""
                    INSERT INTO student_group 
                    SELECT * FROM student_group_old
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE student_group_old"))
                
                conn.commit()
                print("✓ Table recreated with NOT NULL constraint")
                print("✓ Unique constraint updated to (created_by_user_id, course_id, name)")
                print("✓ Indices created on course_id")
            else:
                print("✓ course_id column already exists")
        
        print("\n✓ Migration completed successfully!")
        print("\nNow you need to update the routes:")
        print("1. Update create_group() to accept course_id instead of faculty_id")
        print("2. Update view_group() to check isolation by course")
        print("3. Update add_students_to_group() to check isolation by course")
        print("4. Update the form to select course instead of faculty")

if __name__ == "__main__":
    migrate_add_course_to_groups()
