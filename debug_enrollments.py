#!/usr/bin/env python
"""Check student course enrollments."""

import sys
from app import create_app, db
from app.models import User, StudentCourse, ClearanceStatus, Course

app = create_app()

with app.app_context():
    students = db.session.query(User).filter(User.role == "student").all()
    
    if not students:
        print("❌ No students found")
        sys.exit(1)
    
    print(f"\nChecking enrollments for {len(students)} student(s)\n")
    print("=" * 90)
    
    for student in students:
        print(f"\n📌 {student.full_name} ({student.student_number})")
        print(f"   ID: {student.id}")
        
        # Check course enrollments (StudentCourse)
        course_enrollments = db.session.query(StudentCourse, Course).join(
            Course, StudentCourse.course_id == Course.id
        ).filter(StudentCourse.user_id == student.id).all()
        
        if course_enrollments:
            print(f"\n   Enrolled in {len(course_enrollments)} course(s):")
            for enrollment, course in course_enrollments:
                # Check if clearance status exists
                clearance = db.session.query(ClearanceStatus).filter_by(
                    student_id=student.id,
                    course_id=course.id
                ).first()
                status = "✅ Has clearance" if clearance else "⚠️  No clearance status"
                print(f"     - {course.code}: {course.name} ({status})")
        else:
            print(f"   ❌ NOT enrolled in any courses")
    
    print("\n" + "=" * 90)
    print("\n🎯 TO FIX QR VERIFICATION ISSUES:")
    print("   1. If student shows ❌ NOT enrolled in any courses:")
    print("      → Add student to course via dashboard")
    print("   2. If student shows ⚠️  No clearance status:")
    print("      → Clearance record should auto-create on first QR scan")
