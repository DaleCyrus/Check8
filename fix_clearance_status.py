#!/usr/bin/env python
"""Fix missing ClearanceStatus records for students enrolled in courses."""

import sys
from app import create_app, db
from app.models import StudentCourse, ClearanceStatus, ClearanceState

app = create_app()

with app.app_context():
    # Find all StudentCourse enrollments that don't have ClearanceStatus
    missing = db.session.query(StudentCourse).outerjoin(
        ClearanceStatus,
        (StudentCourse.user_id == ClearanceStatus.student_id) &
        (StudentCourse.course_id == ClearanceStatus.course_id)
    ).filter(ClearanceStatus.id.is_(None)).all()
    
    if not missing:
        print("✅ All students have ClearanceStatus records!")
        sys.exit(0)
    
    print(f"Found {len(missing)} student(s) with missing ClearanceStatus records\n")
    print("Creating ClearanceStatus records...")
    
    created_count = 0
    for enrollment in missing:
        try:
            cs = ClearanceStatus(
                student_id=enrollment.user_id,
                course_id=enrollment.course_id,
                state=ClearanceState.PENDING.value
            )
            db.session.add(cs)
            student = enrollment.user
            course = enrollment.course
            print(f"  ✓ {student.student_number} → {course.code}")
            created_count += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    try:
        db.session.commit()
        print(f"\n✅ Created {created_count} ClearanceStatus record(s)")
        print("\n🎉 QR verification should now work!")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error saving: {e}")
        sys.exit(1)
