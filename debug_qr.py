#!/usr/bin/env python
"""Debug QR token verification issues."""

import sys
from app import create_app, db
from app.models import User
from app.utils.qr import make_student_token, verify_student_token

app = create_app()

with app.app_context():
    # Get all students
    students = db.session.query(User).filter(User.role == "student").all()
    
    if not students:
        print("❌ No students found in database")
        sys.exit(1)
    
    print(f"\nFound {len(students)} student(s)\n")
    print("=" * 70)
    
    for student in students:
        print(f"\nStudent: {student.full_name} ({student.student_number})")
        print(f"  ID: {student.id}")
        print(f"  QR Salt: {student.qr_salt}")
        print(f"  QR Salt is NULL: {student.qr_salt is None}")
        
        if student.qr_salt is None:
            print("  ⚠️  WARNING: No QR salt! Cannot generate valid token")
            continue
        
        try:
            # Generate a token like the student would get
            token = make_student_token(student)
            print(f"  Generated Token: {token[:30]}...")
            
            # Try to verify it
            verified = verify_student_token(token)
            if verified and verified.id == student.id:
                print(f"  ✅ Token verification: SUCCESS")
            else:
                print(f"  ❌ Token verification: FAILED (verified as: {verified})")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("\n📋 ANALYSIS:")
    print("  - If all students show ✅, QR tokens should work")
    print("  - If you see ⚠️  warnings, those students need qr_salt initialized")
    print("  - If you see ❌ failures, there's a verification logic issue")
    print("\n💡 COMMON ISSUES:")
    print("  1. Student not enrolled in the course yet")
    print("  3. Token was scanned from an old QR code (before qr_salt was set)")
