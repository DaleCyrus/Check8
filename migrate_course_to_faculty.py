#!/usr/bin/env python3
"""
Migration: Change ClearanceStatus.course_id back to faculty_id
This reverts a previous schema change that broke the application.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        print("Migrating ClearanceStatus schema: course_id -> faculty_id...")
        
        try:
            # Get the database connection
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Check if course_id column exists
            cursor.execute("PRAGMA table_info(clearance_status)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if 'course_id' in columns:
                print("  - Dropping old clearance_status table...")
                # Drop the old table (requires dropping referencing tables first)
                cursor.execute("DROP TABLE IF EXISTS clearance_status")
                connection.commit()
                print("  - Old table dropped")
            
            # Create new table with correct schema
            print("  - Creating new clearance_status table with faculty_id...")
            cursor.execute("""
                CREATE TABLE clearance_status (
                    id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    faculty_id INTEGER NOT NULL,
                    state VARCHAR(20) NOT NULL DEFAULT 'pending',
                    note VARCHAR(255),
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY(student_id) REFERENCES "user"(id),
                    FOREIGN KEY(faculty_id) REFERENCES faculty(id),
                    UNIQUE (student_id, faculty_id)
                )
            """)
            
            # Create indices
            cursor.execute("CREATE INDEX ix_clearance_status_student_id ON clearance_status (student_id)")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("✓ Migration completed successfully!")
            print("  Database is now ready for the fixed model.")
            
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate()
