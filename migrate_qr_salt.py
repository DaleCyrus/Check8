"""
Migration script to add qr_salt column to the User table.
Run this after updating the User model with the qr_salt field.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text
import uuid

def migrate_database():
    """Add qr_salt column to existing User table."""
    app = create_app()

    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]

        if 'qr_salt' not in columns:
            print("Adding qr_salt column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE user ADD COLUMN qr_salt VARCHAR(64)'))
                conn.commit()

                student_users = conn.execute(text("SELECT id FROM user WHERE role = 'student'")).fetchall()
                for user in student_users:
                    qr_salt = str(uuid.uuid4())
                    conn.execute(text(f'UPDATE user SET qr_salt = "{qr_salt}" WHERE id = {user[0]}'))
                conn.commit()

            print("✓ qr_salt column added and populated for students")
        else:
            print("✓ qr_salt column already exists")

        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
