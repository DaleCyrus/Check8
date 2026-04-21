#!/usr/bin/env python3
"""
Migration script to add email column to the User table.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_add_email():
    """Add email column to User table."""
    app = create_app()

    with app.app_context():
        print("Adding email column to User table...")

        # For SQLite, we need to recreate the table to add the column
        # First, create a temporary table with the correct schema
        with db.engine.connect() as conn:
            # Create new table with email column
            conn.execute(text("""
                CREATE TABLE user_new (
                    id INTEGER NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    student_number VARCHAR(32),
                    username VARCHAR(64),
                    email VARCHAR(120) NOT NULL,
                    full_name VARCHAR(120) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    department VARCHAR(100),
                    program VARCHAR(100),
                    qr_salt VARCHAR(64),
                    PRIMARY KEY (id),
                    UNIQUE (student_number),
                    UNIQUE (username),
                    UNIQUE (email)
                )
            """))

            # Migrate existing data - use a temporary placeholder for email if needed
            # This assumes all existing users need a default email
            conn.execute(text("""
                INSERT INTO user_new (id, role, student_number, username, email, full_name, password_hash, department, program, qr_salt)
                SELECT id, role, student_number, username, 
                       COALESCE(student_number || '@gordoncollege.edu.ph', username || '@gordoncollege.edu.ph'),
                       full_name, password_hash, department, program, qr_salt
                FROM user
            """))

            # Drop old table and rename new one
            conn.execute(text("DROP TABLE user"))
            conn.execute(text("ALTER TABLE user_new RENAME TO user"))

            conn.commit()

        print("✓ Email column added successfully!")
        print("Note: Existing users have been assigned default emails based on their identifiers.")
        print("Please update them with proper institutional emails.")

if __name__ == "__main__":
    migrate_add_email()
