"""PDF certificate generation utilities."""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime


def generate_clearance_certificate(user, clearances_data) -> bytes:
    """
    Generate a PDF clearance certificate for a student.
    
    Args:
        user: User object (student)
        clearances_data: List of tuples (ClearanceStatus, Course, Faculty, instructor_names)
        
    Returns:
        PDF bytes
    """
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    
    # Build content
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=30,
        alignment=1,  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
    )
    
    # Title
    story.append(Paragraph("CLEARANCE CERTIFICATE", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Student Info Section
    story.append(Paragraph("Student Information", heading_style))
    
    student_info = [
        ['Field', 'Details'],
        ['Full Name', user.full_name],
        ['Email', user.email],
        ['Student Number', getattr(user, 'student_number', 'N/A')],
        ['Department', getattr(user, 'department', 'N/A')],
        ['Program', getattr(user, 'program', 'N/A')],
    ]
    
    student_table = Table(student_info, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    
    story.append(student_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Clearance Status Section
    story.append(Paragraph("Clearance Status by Course", heading_style))
    
    if clearances_data:
        clearance_info = [
            ['Course', 'Faculty', 'Instructors', 'Status'],
        ]
        
        for cs, course, faculty, instructor_names in clearances_data:
            status = 'CLEARED' if cs.is_cleared else 'BLOCKED'
            clearance_info.append([
                course.name,
                faculty.name,
                instructor_names,
                status,
            ])
        
        clearance_table = Table(clearance_info, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1*inch])
        clearance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        
        story.append(clearance_table)
    else:
        story.append(Paragraph("No clearance records found.", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1,
    )
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Generated on {now}", footer_style))
    
    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    
    return pdf_buffer.getvalue()
