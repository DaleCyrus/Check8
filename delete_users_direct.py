"""
Delete specific user records using direct SQLite connection
"""

import sqlite3
import os

def delete_users_direct():
    """Delete users directly using sqlite3"""
    
    db_path = r"c:\College Days\2nd year college\2nd Sem\MAJOR COURSES\Soft. Engr\PRJ.CODES\check8\instance\check8_fixed.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
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
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        cursor = conn.cursor()
        
        # Find user IDs
        user_ids = []
        
        print("Finding faculty users...")
        for username in faculty_usernames:
            cursor.execute("SELECT id FROM user WHERE username = ?", (username,))
            result = cursor.fetchone()
            if result:
                user_ids.append(result[0])
                print(f"  Found: {username} (ID: {result[0]})")
            else:
                print(f"  Not found: {username}")
        
        print("\nFinding student users...")
        for student_number in student_numbers:
            cursor.execute("SELECT id FROM user WHERE student_number = ?", (student_number,))
            result = cursor.fetchone()
            if result:
                user_ids.append(result[0])
                print(f"  Found: {student_number} (ID: {result[0]})")
            else:
                print(f"  Not found: {student_number}")
        
        if not user_ids:
            print("\nNo users found to delete")
            conn.close()
            return
        
        print(f"\nDeleting {len(user_ids)} user(s)...")
        placeholders = ','.join('?' * len(user_ids))
        
        # Disable foreign keys
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Delete related records
        print("  Deleting related faculty assignments...")
        cursor.execute(f"DELETE FROM faculty_assignment WHERE user_id IN ({placeholders})", user_ids)
        
        print("  Deleting related course assignments...")
        cursor.execute(f"DELETE FROM instructor_course WHERE user_id IN ({placeholders})", user_ids)
        
        print("  Deleting related student courses...")
        cursor.execute(f"DELETE FROM student_course WHERE user_id IN ({placeholders})", user_ids)
        
        print("  Deleting related clearance statuses...")
        cursor.execute(f"DELETE FROM clearance_status WHERE student_id IN ({placeholders})", user_ids)
        
        print("  Deleting related group members...")
        cursor.execute(f"DELETE FROM student_group_member WHERE student_id IN ({placeholders})", user_ids)
        
        print("  Deleting related faculty user roles...")
        cursor.execute(f"DELETE FROM faculty_user_role WHERE user_id IN ({placeholders})", user_ids)
        
        print("  Deleting related student groups...")
        cursor.execute(f"DELETE FROM student_group WHERE created_by_user_id IN ({placeholders})", user_ids)
        
        print("  Deleting users...")
        cursor.execute(f"DELETE FROM user WHERE id IN ({placeholders})", user_ids)
        
        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Commit
        conn.commit()
        print(f"\n✓ Successfully deleted {len(user_ids)} user(s)")
        
    except sqlite3.OperationalError as e:
        print(f"\n✗ Database error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    delete_users_direct()
