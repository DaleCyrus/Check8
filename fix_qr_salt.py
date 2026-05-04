#!/usr/bin/env python
"""Initialize qr_salt for students who don't have one yet."""

import uuid
import sys

try:
    from app import create_app, db
    from app.models import User, Role

    app = create_app()
    with app.app_context():
        # Find all students with NULL qr_salt
        students_without_salt = db.session.query(User).filter(
            User.role == Role.STUDENT.value,
            User.qr_salt.is_(None)
        ).all()

        if not students_without_salt:
            print("✓ All students already have qr_salt initialized!")
            sys.exit(0)

        print(f"Found {len(students_without_salt)} student(s) without qr_salt")
        print("Initializing...")

        for student in students_without_salt:
            student.qr_salt = str(uuid.uuid4())
            print(f"  ✓ {student.student_number} - {student.full_name}")

        db.session.commit()
        print(f"\n✅ Successfully initialized qr_salt for {len(students_without_salt)} student(s)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
