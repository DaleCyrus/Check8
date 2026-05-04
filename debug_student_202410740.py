from app import create_app, db
from app.models import User, ClearanceStatus, Course, StudentCourse

app = create_app()
with app.app_context():
    student = db.session.execute(db.select(User).where(User.student_number == '202410740')).scalar_one_or_none()
    if not student:
        print('Student not found')
    else:
        print(f'Student ID: {student.id}')
        print(f'Full Name: {student.full_name}')
        print(f'QR Salt: {student.qr_salt}')
        print(f'Is Student: {student.is_student}')
        
        # Check courses
        courses = db.session.execute(db.select(StudentCourse).where(StudentCourse.user_id == student.id)).scalars().all()
        print(f'\nEnrolled in {len(courses)} courses:')
        for sc in courses:
            course = db.session.get(Course, sc.course_id)
            clearance = db.session.execute(db.select(ClearanceStatus).where(ClearanceStatus.student_id == student.id, ClearanceStatus.course_id == sc.course_id)).scalar_one_or_none()
            state_str = clearance.state if clearance else "NO RECORD"
            print(f'  - {course.code}: Clearance State = {state_str}')
