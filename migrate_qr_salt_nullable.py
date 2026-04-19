#!/usr/bin/env python3
"""
Migration script to make qr_salt column nullable in the User table.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_qr_salt_nullable():
    """Make qr_salt column nullable."""
    app = create_app()

    with app.app_context():
        print("Making qr_salt column nullable...")

        # For SQLite, we need to recreate the table to change nullability
        # First, create a temporary table with the correct schema
        with db.engine.connect() as conn:
            # Create new table with nullable qr_salt
            conn.execute(text("""
                CREATE TABLE user_new (
                    id INTEGER NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    student_number VARCHAR(32),
                    username VARCHAR(64),
                    full_name VARCHAR(120) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    department VARCHAR(100),
                    program VARCHAR(100),
                    qr_salt VARCHAR(64),
                    PRIMARY KEY (id),
                    UNIQUE (student_number),
                    UNIQUE (username)
                )
            """))

            
            conn.execute(text("""
                INSERT INTO user_new (id, role, student_number, username, full_name, password_hash, department, program, qr_salt)
                SELECT id, role, student_number, username, full_name, password_hash, department, program, qr_salt
                FROM user
            """))

            
            conn.execute(text("DROP TABLE user"))
            conn.execute(text("ALTER TABLE user_new RENAME TO user"))

            conn.commit()

        print("✓ qr_salt column made nullable")

        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_qr_salt_nullable()