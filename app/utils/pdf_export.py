"""
PDF export utilities for clearance status certificates and reports
"""

from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_clearance_certificate(student, clearances_data):
    """
    Generate a PDF certificate of clearance status for a student.
    
    Args:
        student: User object (student)
        clearances_data: List of tuples (ClearanceStatus, Course, Faculty, InstructorNames)
    
    Returns:
        BytesIO object containing PDF data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#ff9900"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#ff9900"),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph("CLEARANCE STATUS CERTIFICATE", title_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Generation date
    gen_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"Generated on {gen_date}", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Student Information
    story.append(Paragraph("STUDENT INFORMATION", heading_style))
    
    student_info = [
        ['Student Number:', student.student_number],
        ['Full Name:', student.full_name],
        ['Email:', student.email],
        ['Department:', student.department or 'N/A'],
        ['Program:', student.program or 'N/A'],
    ]
    
    student_table = Table(student_info, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eef7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
    ]))
    
    story.append(student_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Clearance Status Table
    story.append(Paragraph("CLEARANCE STATUS", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Build clearance table data
    clearance_table_data = [
        ['Course Code', 'Course Name', 'Instructor', 'Faculty', 'Status', 'Updated'],
    ]
    
    # Color mapping for status
    status_colors = {
        'cleared': colors.HexColor('#28a745'),
        'pending': colors.HexColor('#ffc107'),
        'blocked': colors.HexColor('#dc3545'),
    }
    
    for item in clearances_data:
        cs, course, faculty, instructor_names = item
        status = cs.state.upper()
        updated = cs.updated_at.strftime("%b %d, %Y") if cs.updated_at else "N/A"
        clearance_table_data.append([
            course.code,
            course.name,
            instructor_names,
            faculty.name,
            status,
            updated,
        ])
    
    clearance_table = Table(clearance_table_data, colWidths=[1*inch, 1.4*inch, 1.3*inch, 1.6*inch, 0.8*inch, 0.9*inch])
    
    # Apply table styling
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ff9900")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]
    
    # Add status-based colors
    for idx, item in enumerate(clearances_data, start=1):
        cs = item[0]
        status_color = status_colors.get(cs.state, colors.gray)
        table_style.append(('TEXTCOLOR', (4, idx), (4, idx), status_color))
        table_style.append(('FONTNAME', (4, idx), (4, idx), 'Helvetica-Bold'))
    
    clearance_table.setStyle(TableStyle(table_style))
    story.append(clearance_table)
    
    # Summary
    story.append(Spacer(1, 0.15*inch))
    
    # Count statuses
    cleared_count = sum(1 for item in clearances_data if item[0].state == 'cleared')
    pending_count = sum(1 for item in clearances_data if item[0].state == 'pending')
    blocked_count = sum(1 for item in clearances_data if item[0].state == 'blocked')
    total_count = len(clearances_data)
    
    summary_text = f"""
    <b>Summary:</b> {cleared_count} Cleared | {pending_count} Pending | {blocked_count} Blocked | <b>Total: {total_count}</b>
    """
    story.append(Paragraph(summary_text, styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        borderPadding=5,
    )
    footer_text = "This is an auto-generated document from the CHECK8 Clearance Management System.<br/>For official records, contact your institution's administration."
    story.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_clearance_report_admin(students_data):
    """
    Generate a bulk clearance report for admins (list of students with status).
    
    Args:
        students_data: List of dicts with student and clearance info
    
    Returns:
        BytesIO object containing PDF data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("CLEARANCE STATUS REPORT", title_style))
    story.append(Spacer(1, 0.1*inch))
    
    gen_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated on {gen_date}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Report table
    report_data = [
        ['Student #', 'Name', 'Cleared', 'Pending', 'Blocked', 'Total'],
    ]
    
    for student_info in students_data:
        report_data.append([
            student_info['student_number'],
            student_info['full_name'][:20],
            str(student_info['cleared']),
            str(student_info['pending']),
            str(student_info['blocked']),
            str(student_info['total']),
        ])
    
    report_table = Table(report_data, colWidths=[1*inch, 2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    
    story.append(report_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer
