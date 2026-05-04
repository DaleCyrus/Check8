#!/usr/bin/env python
"""Test QR verification end-to-end."""

import sys
from app import create_app, db
from app.models import User, ClearanceStatus
from app.utils.qr import make_student_token, verify_student_token

app = create_app()

with app.app_context():
    # Get a student with enrollment and clearance
    students = db.session.query(User).filter(
        User.role == "student",
        User.id.in_(
            db.session.query(ClearanceStatus.student_id)
        )
    ).all()
    
    if not students:
        print("❌ No students with clearance records found")
        sys.exit(1)
    
    print(f"Testing QR verification for {len(students)} student(s)\n")
    print("=" * 80)
    
    test_passed = 0
    test_failed = 0
    
    for student in students[:3]:  # Test first 3
        print(f"\nTesting: {student.full_name} ({student.student_number})")
        
        try:
            # Step 1: Generate token
            token = make_student_token(student)
            print(f"  ✓ Token generated: {token[:40]}...")
            
            # Step 2: Verify token
            verified = verify_student_token(token)
            if not verified:
                print(f"  ❌ Token verification failed!")
                test_failed += 1
                continue
            
            if verified.id != student.id:
                print(f"  ❌ Token verified as wrong student!")
                test_failed += 1
                continue
                
            print(f"  ✓ Token verified successfully")
            
            # Step 3: Check clearance status
            clearances = db.session.query(ClearanceStatus).filter_by(
                student_id=student.id
            ).all()
            
            if not clearances:
                print(f"  ❌ No clearance records found!")
                test_failed += 1
                continue
            
            print(f"  ✓ Found {len(clearances)} clearance record(s)")
            for cs in clearances:
                course = cs.course
                print(f"    - {course.code}: {cs.state}")
            
            test_passed += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            test_failed += 1
    
    print("\n" + "=" * 80)
    print(f"\n📊 Results: {test_passed} passed, {test_failed} failed")
    
    if test_failed == 0:
        print("\n✅ QR verification should work now!")
        print("\n🎯 Next steps:")
        print("  1. Go to 'Clearance Validation' page")
        print("  2. Select a course")
        print("  3. Scan or paste a student's QR token")
        print("  4. Student should appear with status!")
    else:
        print("\n⚠️  Some tests failed - check the errors above")
        sys.exit(1)
