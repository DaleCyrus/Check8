#!/usr/bin/env python3
"""
Fixed migration script that disables WAL mode to avoid locking issues.
"""

import sqlite3
import os
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "instance" / "check8_new.db"

def migrate_with_sqlite3():
    """Use raw sqlite3 to perform migration without WAL issues."""
    
    # Connect without WAL mode
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("Connecting to database...")
        
        # Disable WAL mode temporarily
        cursor.execute("PRAGMA journal_mode=DELETE")
        
        print("Checking StudentCourse table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_course'")
        if not cursor.fetchone():
            print("Creating StudentCourse table...")
            cursor.execute("""
                CREATE TABLE student_course (
                    id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE (user_id, course_id),
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (course_id) REFERENCES course (id)
                )
            """)
            print("✓ StudentCourse table created")
        else:
            print("✓ StudentCourse table already exists")
        
        print("Checking ClearanceStatus table...")
        cursor.execute("PRAGMA table_info(clearance_status)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'course_id' not in columns:
            print("Migrating ClearanceStatus from faculty to course-based...")
            
            # Check if old table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clearance_status_old'")
            if cursor.fetchone():
                cursor.execute("DROP TABLE clearance_status_old")
            
            # Rename old table
            cursor.execute("ALTER TABLE clearance_status RENAME TO clearance_status_old")
            
            # Create new table with course_id
            cursor.execute("""
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
            """)
            
            # Migrate data: For each old clearance record, find courses in that faculty
            print("Migrating clearance records...")
            cursor.execute("""
                INSERT INTO clearance_status (student_id, course_id, state, note, updated_at)
                SELECT 
                    cs.student_id,
                    c.id,
                    cs.state,
                    cs.note,
                    cs.updated_at
                FROM clearance_status_old cs
                JOIN course c ON c.faculty_id = cs.faculty_id
            """)
            
            # Drop old table
            cursor.execute("DROP TABLE clearance_status_old")
            print("✓ ClearanceStatus migrated to course-based system")
        else:
            print("✓ ClearanceStatus already uses course_id")
        
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_with_sqlite3()
