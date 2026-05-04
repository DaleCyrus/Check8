#!/usr/bin/env python3
"""
Migration script to add StudentGroup and StudentGroupMember tables for student group management.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_add_student_groups():
    """Add StudentGroup and StudentGroupMember tables."""
    app = create_app()

    with app.app_context():
        print("Adding StudentGroup and StudentGroupMember tables...")

        with db.engine.connect() as conn:
            # Check if student_group table exists
            student_group_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='student_group'")
            ).scalar()
            
            if not student_group_exists:
                # Create StudentGroup table
                conn.execute(text("""
                    CREATE TABLE student_group (
                        id INTEGER NOT NULL,
                        faculty_id INTEGER NOT NULL,
                        created_by_user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description VARCHAR(500),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (faculty_id, name),
                        FOREIGN KEY (faculty_id) REFERENCES faculty (id),
                        FOREIGN KEY (created_by_user_id) REFERENCES user (id)
                    )
                """))
                print("✓ StudentGroup table created")

                # Create index on faculty_id for faster queries
                conn.execute(text("""
                    CREATE INDEX ix_student_group_faculty_id ON student_group (faculty_id)
                """))
                print("✓ Index on faculty_id created")
            else:
                print("✓ StudentGroup table already exists")

            # Check if student_group_member table exists
            student_group_member_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='student_group_member'")
            ).scalar()
            
            if not student_group_member_exists:
                # Create StudentGroupMember junction table
                conn.execute(text("""
                    CREATE TABLE student_group_member (
                        id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        added_at DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE (group_id, student_id),
                        FOREIGN KEY (group_id) REFERENCES student_group (id),
                        FOREIGN KEY (student_id) REFERENCES user (id)
                    )
                """))
                print("✓ StudentGroupMember table created")

                # Create indexes for faster queries
                conn.execute(text("""
                    CREATE INDEX ix_student_group_member_group_id ON student_group_member (group_id)
                """))
                conn.execute(text("""
                    CREATE INDEX ix_student_group_member_student_id ON student_group_member (student_id)
                """))
                print("✓ Indexes on group_id and student_id created")
            else:
                print("✓ StudentGroupMember table already exists")

            conn.commit()

        print("✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_student_groups()
