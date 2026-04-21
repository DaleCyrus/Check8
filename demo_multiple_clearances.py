"""
Demo script to show a student with multiple clearances from different courses.
"""

from app import create_app
from app.extensions import db
from app.models import ClearanceState, ClearanceStatus, Course, Faculty, FacultyAssignment, Role, User

def demo_multiple_clearances():
    app = create_app()
    with app.app_context():
        # Create faculties if they don't exist
        faculty_names = ["Registrar", "Library", "College of Computer Studies"]
        faculties = []
        for name in faculty_names:
            faculty = db.session.execute(
                db.select(Faculty).where(Faculty.name == name)
            ).scalar_one_or_none()
            if not faculty:
                faculty = Faculty(name=name)
                db.session.add(faculty)
                db.session.commit()
            faculties.append(faculty)
        
        # Create faculty users
        for i, faculty in enumerate(faculties):
            username = f"faculty{i+1}"
            user = db.session.execute(
                db.select(User).where(User.username == username)
            ).scalar_one_or_none()
            if not user:
                user = User(
                    role=Role.FACULTY.value,
                    username=username,
                    full_name=f"{faculty.name} Officer",
                    email=f"{username}@school.edu",
                )
                user.set_password("faculty123")
                db.session.add(user)
                db.session.commit()
                
                # Assign user to faculty
                assignment = FacultyAssignment(user_id=user.id, faculty_id=faculty.id)
                db.session.add(assignment)
                db.session.commit()
            faculty_users.append((user, faculty))
        
        student = db.session.execute(
            db.select(User).where(User.student_number == "2022-0001")
        ).scalar_one_or_none()
        
        if not student:
            student = User(
                role=Role.STUDENT.value,
                student_number="2022-0001",
                full_name="Gian Karlo Reguindin",
                email="student@school.edu",
                department="College of Computer Studies",
                program="Bachelor of Science in Computer Science",
            )
            student.set_password("student123")
            db.session.add(student)
            db.session.commit()
        
        print(f"Adding student {student.full_name} ({student.student_number}) to multiple course clearances:")
        
        # Add student to each faculty's clearance list
        for faculty in faculties:
            # Check if already exists
            existing = db.session.execute(
                db.select(ClearanceStatus).where(
                    ClearanceStatus.student_id == student.id,
                    ClearanceStatus.course_id == course.id,
                )
            ).scalar_one_or_none()
            
            if existing:
                print(f"  - Already in {course.name} clearance list")
            else:
                cs = ClearanceStatus(
                    student_id=student.id,
                    course_id=course.id,
                    state=ClearanceState.PENDING.value,
                )
                db.session.add(cs)
                print(f"  - Added to {course.name} clearance list")
        
        db.session.commit()
        
        clearances = db.session.execute(
            db.select(ClearanceStatus, Course, Faculty)
            .join(Course, ClearanceStatus.course_id == Course.id)
            .join(Faculty, Course.faculty_id == Faculty.id)
            .where(ClearanceStatus.student_id == student.id)
        ).all()
        
        print(f"\nStudent {student.full_name} has clearances from:")
        for cs, course, faculty in clearances:
            print(f"  - {course.name} ({faculty.name}): {cs.state}")
        
        print("\nDemo complete!")
        print("You can now:")
        print("1. Login as student (2022-0001 / student123) to see multiple course clearances")
        print("2. Login as faculty1 (faculty1 / faculty123) to manage Registrar course clearances")
        print("3. Login as faculty2 (faculty2 / faculty123) to manage Library course clearances")
        print("4. Login as faculty3 (faculty3 / faculty123) to manage CS Department clearances")

if __name__ == "__main__":
    demo_multiple_clearances()
        print("4. Login as faculty3 (faculty3 / faculty123) to manage CS Department clearances")

if __name__ == "__main__":
    demo_multiple_clearances()
