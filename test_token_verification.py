from app import create_app, db
from app.models import User
from app.utils.qr import make_student_token, verify_student_token

app = create_app()
with app.app_context():
    student = db.session.execute(db.select(User).where(User.student_number == '202410740')).scalar_one_or_none()
    if not student:
        print('Student not found')
    else:
        print(f'Student: {student.full_name}')
        print(f'QR Salt in DB: {student.qr_salt}')
        
        # Generate a fresh token
        fresh_token = make_student_token(student)
        print(f'\nFresh token: {fresh_token}')
        
        # Verify the fresh token
        verified_student = verify_student_token(fresh_token)
        if verified_student:
            print(f'✓ Fresh token verifies successfully')
            print(f'  Verified student: {verified_student.full_name}')
        else:
            print(f'✗ Fresh token verification FAILED')
        
        # Try with an old token (if available from QR code)
        print('\n--- If you scanned a QR, paste the token below to test it ---')
