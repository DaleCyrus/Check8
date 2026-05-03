
from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required, current_user
import io
from datetime import datetime

bp = Blueprint("student", __name__, url_prefix="/student")

from ...extensions import db
from ...models import ClearanceStatus, Faculty, User, Course, InstructorCourse
from ...utils.qr import token_to_png_bytes, make_student_token
from ...utils.pdf_export import generate_clearance_certificate



@bp.get("/qr.png")
@login_required
def qr_png():
    _require_student()
    try:
        token = make_student_token(current_user)
        png = token_to_png_bytes(token)
        return send_file(
            io.BytesIO(png),
            mimetype="image/png",
            as_attachment=False,
            download_name="student-token-qr.png",
        )
    except Exception as e:
        import traceback
        print("[QR ERROR]", e)
        traceback.print_exc()
        return "QR code generation error: {}".format(e), 500


def _require_student():
    if not current_user.is_authenticated or not getattr(current_user, "is_student", False):
        abort(403)


@bp.get("/dashboard")
@login_required
def dashboard():
    _require_student()
    
    # Get all clearances for this student with course and faculty info
    clearances_data = []
    clearances = db.session.execute(
        db.select(ClearanceStatus, Course, Faculty)
        .join(Course, ClearanceStatus.course_id == Course.id)
        .join(Faculty, Course.faculty_id == Faculty.id)
        .where(ClearanceStatus.student_id == current_user.id)
        .order_by(Course.name.asc())
    ).all()
    
    for cs, course, faculty in clearances:
        # Get instructors for this course
        instructors = db.session.execute(
            db.select(User).join(InstructorCourse).where(InstructorCourse.course_id == course.id)
        ).scalars().all()
        instructor_names = ', '.join([instr.full_name for instr in instructors]) if instructors else 'N/A'
        
        clearances_data.append((cs, course, faculty, instructor_names))
    
    return render_template("student/dashboard.html", clearances=clearances_data)


@bp.get("/download-clearance-pdf")
@login_required
def download_clearance_pdf():
    """Download clearance status as PDF certificate"""
    _require_student()
    
    # Get all clearances for this student with course and faculty info
    clearances_data = []
    clearances = db.session.execute(
        db.select(ClearanceStatus, Course, Faculty)
        .join(Course, ClearanceStatus.course_id == Course.id)
        .join(Faculty, Course.faculty_id == Faculty.id)
        .where(ClearanceStatus.student_id == current_user.id)
        .order_by(Course.name.asc())
    ).all()
    
    for cs, course, faculty in clearances:
        # Get instructors for this course
        instructors = db.session.execute(
            db.select(User).join(InstructorCourse).where(InstructorCourse.course_id == course.id)
        ).scalars().all()
        instructor_names = ', '.join([instr.full_name for instr in instructors]) if instructors else 'N/A'
        
        clearances_data.append((cs, course, faculty, instructor_names))
    
    # Generate PDF
    try:
        pdf_buffer = generate_clearance_certificate(current_user, clearances_data)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Clearance_Certificate_{current_user.student_number}_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        import traceback
        print("[PDF GENERATION ERROR]", e)
        traceback.print_exc()
        return "PDF generation error: {}".format(e), 500

