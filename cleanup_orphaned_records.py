#!/usr/bin/env python3
"""
Cleanup script to remove orphaned ClearanceStatus and StudentGroup records
that reference non-existent courses (e.g., deleted courses like trial-001).
"""

from app import create_app
from app.extensions import db
from app.models import ClearanceStatus, StudentGroup, Course
from sqlalchemy import and_

def cleanup_orphaned_records():
    """Remove all orphaned clearance and group records."""
    app = create_app()
    
    with app.app_context():
        print("Cleaning up orphaned records...\n")
        
        # Find all courses that still exist
        existing_courses = db.session.execute(
            db.select(Course.id)
        ).scalars().all()
        existing_course_ids = set(existing_courses)
        
        print(f"Found {len(existing_course_ids)} valid courses in database")
        
        # Find orphaned ClearanceStatus records
        orphaned_clearances = db.session.execute(
            db.select(ClearanceStatus).where(
                ~ClearanceStatus.course_id.in_(existing_course_ids)
            )
        ).scalars().all()
        
        orphaned_count = len(orphaned_clearances)
        if orphaned_count > 0:
            print(f"\nFound {orphaned_count} orphaned clearance record(s):")
            for cs in orphaned_clearances:
                print(f"  - Student ID {cs.student_id}, Course ID {cs.course_id} (state: {cs.state})")
                db.session.delete(cs)
            db.session.commit()
            print(f"[OK] Deleted {orphaned_count} orphaned clearance record(s)")
        else:
            print("\n[OK] No orphaned clearance records found")
        
        # Find orphaned StudentGroup records
        orphaned_groups = db.session.execute(
            db.select(StudentGroup).where(
                ~StudentGroup.course_id.in_(existing_course_ids)
            )
        ).scalars().all()
        
        orphaned_groups_count = len(orphaned_groups)
        if orphaned_groups_count > 0:
            print(f"\nFound {orphaned_groups_count} orphaned student group(s):")
            for group in orphaned_groups:
                print(f"  - Group '{group.name}' (Course ID {group.course_id})")
                db.session.delete(group)
            db.session.commit()
            print(f"[OK] Deleted {orphaned_groups_count} orphaned student group(s)")
        else:
            print("\n[OK] No orphaned student groups found")
        
        print("\n[OK] Cleanup completed successfully!")
        print("\nNote: From now on, when you delete a course, all related")
        print("clearance records and student groups will be automatically removed.")

if __name__ == "__main__":
    cleanup_orphaned_records()
