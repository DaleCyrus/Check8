#!/usr/bin/env python3
"""
Debug script to list all students in the database with their IDs.
Use this to find the correct student IDs to use in bulk add.
"""

from app import create_app
from app.models import User, Role

def list_all_students():
    app = create_app()
    
    with app.app_context():
        # Get all students from database
        students = User.query.filter_by(role=Role.STUDENT.value).order_by(User.student_number.asc()).all()
        
        if not students:
            print("❌ No students found in database!")
            return
        
        print(f"\n📋 Found {len(students)} students in database:\n")
        print(f"{'ID':<6} {'Student No.':<15} {'Name':<30} {'Role':<10}")
        print("-" * 65)
        
        for student in students:
            print(f"{student.id:<6} {student.student_number:<15} {student.full_name:<30} {student.role:<10}")
        
        print("\n✅ Use the ID numbers from the first column for bulk add!")
        print("\nExample: To add these students to a group, use:")
        if len(students) >= 3:
            ids = [str(s.id) for s in students[:3]]
            print(f"  {', '.join(ids)}")
            print(f"  OR on separate lines:")
            print(f"  {chr(10).join(ids)}")

if __name__ == "__main__":
    list_all_students()
