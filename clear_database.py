#!/usr/bin/env python3
"""
Clear all data from the database while keeping the database file
"""

from app import create_app
from app.extensions import db

def clear_database():
    app = create_app()
    with app.app_context():
        print("Clearing all data from database...")
        db.drop_all()
        db.create_all()
        print("✓ Database cleared successfully. Ready for new data.")

if __name__ == "__main__":
    clear_database()
