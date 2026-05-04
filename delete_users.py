"""
Delete specific user records from the database
"""

from app import create_app
from app.extensions import db
from app.models import User
from sqlalchemy import text
import time

def delete_users():
    """Delete specific users by username or student_number"""
    app = create_app()
    with app.app_context():
        # Faculty usernames to delete
        faculty_usernames = [
            'registrar',
            'library',
            'csdept',
            'Siklab 2026',
            'College Dean CCS',
            'try001'
        ]
        
        # Student numbers to delete
        student_numbers = [
            '2022-0001',
            '2022-0002'
        ]
        
        deleted_count = 0
        
        try:
            # Find all user IDs to delete
            user_ids_to_delete = []
            
            # Delete faculty users by username
            print("Finding faculty users to delete...")
            for username in faculty_usernames:
                user = db.session.query(User).filter_by(username=username).first()
                if user:
                    user_ids_to_delete.append(user.id)
                    print(f"  Found: {username} (ID: {user.id})")
                else:
                    print(f"  Not found: {username}")
            
            # Delete student users by student_number
            print("\nFinding student users to delete...")
            for student_number in student_numbers:
                user = db.session.query(User).filter_by(student_number=student_number).first()
                if user:
                    user_ids_to_delete.append(user.id)
                    print(f"  Found: {student_number} (ID: {user.id})")
                else:
                    print(f"  Not found: {student_number}")
            
            if not user_ids_to_delete:
                print("\nNo users found to delete")
                return
            
            # Delete using raw SQL to bypass cascading issues
            print(f"\nDeleting {len(user_ids_to_delete)} user(s)...")
            
            # Disable foreign key constraints temporarily
            db.session.execute(text("PRAGMA foreign_keys = OFF"))
            
            # Delete related records first
            print("  Deleting related faculty assignments...")
            db.session.execute(text(f"DELETE FROM faculty_assignment WHERE user_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting related course assignments...")
            db.session.execute(text(f"DELETE FROM instructor_course WHERE user_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting related student courses...")
            db.session.execute(text(f"DELETE FROM student_course WHERE user_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting related clearance statuses...")
            db.session.execute(text(f"DELETE FROM clearance_status WHERE student_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting related group members...")
            db.session.execute(text(f"DELETE FROM student_group_member WHERE student_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting related faculty user roles...")
            db.session.execute(text(f"DELETE FROM faculty_user_role WHERE user_id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            print("  Deleting users...")
            db.session.execute(text(f"DELETE FROM user WHERE id IN ({','.join(map(str, user_ids_to_delete))})"))
            
            # Re-enable foreign key constraints
            db.session.execute(text("PRAGMA foreign_keys = ON"))
            
            # Commit changes
            db.session.commit()
            print(f"\n✓ Successfully deleted {len(user_ids_to_delete)} user(s)")
            
        except Exception as e:
            db.session.rollback()
            db.session.execute(text("PRAGMA foreign_keys = ON"))
            print(f"\n✗ Error during deletion: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    delete_users()
