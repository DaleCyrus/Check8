#!/usr/bin/env python3
"""
Check all courses in database and remove trial001 course if it exists.
"""

from app import create_app
from app.extensions import db
from app.models import Course, ClearanceStatus

def check_and_remove_trial():
    """Check all courses and remove trial001."""
    app = create_app()
    
    with app.app_context():
        print("Checking all courses in database...\n")
        
        # Get all courses
        all_courses = db.session.execute(
            db.select(Course)
        ).scalars().all()
        
        print(f"Total courses: {len(all_courses)}\n")
        for course in all_courses:
            clearances = db.session.execute(
                db.select(ClearanceStatus).where(ClearanceStatus.course_id == course.id)
            ).scalars().all()
            print(f"  ID: {course.id} | Code: {course.code} | Name: {course.name} | Clearances: {len(clearances)}")
        
        # Find and remove trial001
        print("\n" + "="*60)
        trial_courses = db.session.execute(
            db.select(Course).where(
                (Course.code == "trial001") | (Course.name == "trial001") | (Course.name.like("%trial%"))
            )
        ).scalars().all()
        
        if trial_courses:
            print(f"\nFound {len(trial_courses)} trial course(s) to remove:\n")
            for course in trial_courses:
                print(f"  Removing: {course.code} - {course.name}")
                db.session.delete(course)
            
            db.session.commit()
            print(f"\n[OK] Deleted {len(trial_courses)} trial course(s)")
            
            print("\nRemaining courses:")
            remaining = db.session.execute(
                db.select(Course)
            ).scalars().all()
            for course in remaining:
                print(f"  - {course.code} - {course.name}")
        else:
            print("\n[INFO] No trial courses found to remove")

if __name__ == "__main__":
    check_and_remove_trial()
