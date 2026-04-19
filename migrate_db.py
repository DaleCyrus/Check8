"""
Migration script to add department and program columns to the User table.
Run this after updating the User model with the new fields.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_database():
    """Add department and program columns to existing User table."""
    app = create_app()

    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]

        if 'department' not in columns:
            print("Adding department column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE user ADD COLUMN department VARCHAR(100)'))
                conn.commit()
            print("✓ Department column added")

        if 'program' not in columns:
            print("Adding program column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE user ADD COLUMN program VARCHAR(100)'))
                conn.commit()
            print("✓ Program column added")

        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
