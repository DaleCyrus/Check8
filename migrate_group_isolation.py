"""
Migration script to update StudentGroup unique constraint to isolate groups per user.
This ensures each Faculty/Officer has separate groups (not shared with other faculty in same department).

Previously: Groups were shared at Faculty/Department level
Now: Groups are isolated per user (each faculty member has separate groups)

Run this after updating the StudentGroup model.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_database():
    """Update the unique constraint on StudentGroup table."""
    app = create_app()

    with app.app_context():
        inspector = db.inspect(db.engine)
        
        # Get existing constraints on student_group table
        constraints = inspector.get_unique_constraints('student_group')
        constraint_names = [c['name'] for c in constraints]
        
        print("Current constraints on student_group table:")
        for c in constraints:
            print(f"  - {c['name']}: {c['column_names']}")
        
        # Drop the old constraint if it exists
        old_constraint = 'uq_group_name_per_faculty'
        if old_constraint in constraint_names:
            print(f"\nDropping old constraint: {old_constraint}")
            with db.engine.connect() as conn:
                # SQLite: drop and recreate
                conn.execute(text(f'DROP INDEX IF EXISTS {old_constraint}'))
                conn.commit()
            print(f"✓ Old constraint '{old_constraint}' dropped")
        
        # Create the new constraint
        new_constraint = 'uq_group_name_per_user_faculty'
        if new_constraint not in constraint_names:
            print(f"\nCreating new constraint: {new_constraint}")
            with db.engine.connect() as conn:
                # Add the new unique constraint
                conn.execute(text(f'''
                    CREATE UNIQUE INDEX IF NOT EXISTS {new_constraint} 
                    ON student_group (created_by_user_id, faculty_id, name)
                '''))
                conn.commit()
            print(f"✓ New constraint '{new_constraint}' created")
        
        print("\n✅ Migration completed successfully!")
        print("Groups are now isolated per user (Faculty/Officer)")

if __name__ == "__main__":
    migrate_database()
