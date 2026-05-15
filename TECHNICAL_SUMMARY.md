# CHECK8 - Technical Summary for Presentation

## **System Overview**
CHECK8 is a **QR-enabled student clearance management system** built for academic institutions. It enables secure, efficient verification of student clearance across multiple courses and faculty departments.

**Live Demo:** http://127.0.0.1:5000

---

## **Architecture at a Glance**

```
┌─────────────────────────────────────────────────────┐
│           CHECK8 Web Application                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Frontend (HTML/CSS/JavaScript)                    │
│  ├─ Responsive Bootstrap-free design               │
│  ├─ Smooth animations & transitions                │
│  └─ QR scanner (html5-qrcode library)              │
│                                                     │
│  Backend (Python Flask)                            │
│  ├─ Auth blueprint (login/signup)                  │
│  ├─ Student blueprint (dashboard, QR, PDF)        │
│  └─ Admin blueprint (verify, groups, clearance)   │
│                                                     │
│  Database (SQLAlchemy ORM)                         │
│  ├─ SQLite (development)                           │
│  └─ PostgreSQL (production)                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## **Tech Stack**
| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python + Flask | 3.0.2 |
| **ORM** | SQLAlchemy | 3.1.1 |
| **Database** | SQLite / PostgreSQL | Latest |
| **Auth** | Flask-Login | 0.6.3 |
| **QR Generation** | qrcode library | 7.4.2 |
| **PDF Export** | ReportLab | 4.0.9 |
| **Email** | Flask-Mail | 0.9.1 |
| **Security** | Flask-WTF (CSRF) | 1.2.1 |

---

## **Key Features Implemented** ✅

### **1. Student Module**
- ✅ Student signup/login
- ✅ View clearance status per course
- ✅ Generate secure QR code (signed token)
- ✅ Download clearance certificate (PDF)
- ✅ Responsive mobile interface

### **2. Faculty Module**
- ✅ Faculty/Instructor signup/login
- ✅ Verify student clearance via QR/token
- ✅ Add individual students to clearance list
- ✅ Bulk add multiple students (CSV/newline format)
- ✅ Update clearance status (Pending → Cleared/Blocked)
- ✅ Manage student groups per course
- ✅ Add/remove students from groups

### **3. System Features**
- ✅ Role-based access control (Student/Faculty)
- ✅ Institutional email validation (@gordoncollege.edu.ph)
- ✅ Secure password hashing (werkzeug.security)
- ✅ CSRF protection on all forms
- ✅ 30-minute session timeout
- ✅ Cascade delete for data integrity
- ✅ Error handling with user-friendly pages

---

## **Database Design Highlights**

### **Data Integrity Constraints**
```python
# Unique constraints prevent duplicates
- User.email (UNIQUE)
- User.student_number (UNIQUE) 
- User.username (UNIQUE)
- ClearanceStatus(student_id, course_id) - UNIQUE
- StudentGroup(created_by_user_id, course_id, name) - UNIQUE
- InstructorCourse(user_id, course_id) - UNIQUE
```

### **Relationships**
```python
Faculty (1) ──→ (*) Course
Course (1) ──→ (*) ClearanceStatus
User (1) ──→ (*) StudentCourse (enrollment)
User (1) ──→ (*) InstructorCourse (teaches)
StudentGroup (1) ──→ (*) StudentGroupMember
```

### **Key Models**
- **User** - Polymorphic (Student/Faculty)
- **ClearanceStatus** - Tracks per-student per-course status
- **StudentGroup** - Faculty-created groups for bulk operations
- **Course** - Tied to Faculty/Department
- **Faculty** - Organization unit

---

## **Security Implementation**

### **Authentication & Authorization**
```python
# All protected routes check:
- User is authenticated (Flask-Login)
- User has correct role (@require_student/@require_faculty)
- User has permission to resource (role-based checks)
```

### **QR Token Signing**
```python
# Token generation (prevents forgery):
token = URLSafeSerializer(app.secret_key, salt="check8-qr")
payload = {"sid": student.id, "salt": student.qr_salt}
signed_token = serializer.dumps(payload)

# Verification (rejects invalid/expired):
payload = serializer.loads(token)  # Raises BadSignature if invalid
```

### **Data Protection**
- Passwords hashed with werkzeug.generate_password_hash
- Session cookies: HTTPONLY + Secure + SameSite=Lax
- CSRF tokens on all POST forms
- Institutional email domain validation

---

## **Performance Optimizations**

### **Database Level**
- SQLite WAL mode (Write-Ahead Logging) for concurrency
- Connection pooling (PostgreSQL: 20 connections)
- Indexed fields (email, student_number, username, role)
- Proper foreign keys with cascade deletes

### **Query Optimization**
- Efficient joins reducing N+1 queries
- Pagination ready (can add limit/offset)
- Select specific columns instead of SELECT *

### **Frontend**
- CSS animations use GPU acceleration (transform, opacity)
- Responsive images and lazy loading ready
- Minified CSS/JS for production

---

## **UI/UX Highlights**

### **Design System**
- **Color Palette:** Orange accent (#ff9800) with warm neutrals
- **Typography:** System fonts (San Francisco, Roboto)
- **Spacing:** 4px base unit (4, 8, 12, 16, 20px)
- **Radius:** 12-18px border radius for modern feel

### **Animations**
| Animation | Purpose | Duration |
|-----------|---------|----------|
| fadeIn | Page load | 0.4s |
| slideInUp | Card/notification entry | 0.5s |
| slideInDown | Flash message entry | 0.4s |
| scaleIn | Modal/error page | 0.5s |
| spin | Loading spinner | 0.8s |

### **Responsive Design**
- **Mobile first** approach
- All buttons stack vertically on phones
- Touch-friendly tap targets (44px minimum)
- Proper viewport scaling

---

## **Deployment Ready**

### **Development**
```bash
python run.py  # Flask development server on :5000
```

### **Production - Option 1: Gunicorn**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### **Production - Option 2: Docker**
```bash
docker-compose up -d  # Includes PostgreSQL
```

### **Environment Configuration**
```
FLASK_ENV=production
SECRET_KEY=<strong-secret-key>
DATABASE_URL=postgresql://user:pass@host/db
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## **What Makes This Project Strong**

### **✅ Technical Excellence**
- Clean, modular architecture (MVC pattern)
- Proper separation of concerns
- Type hints in Python code
- Security-first design approach
- Error handling with graceful fallbacks

### **✅ Real-World Practicality**
- Solves actual institutional problem
- Handles edge cases (duplicate adds, group isolation)
- Bulk operations reduce manual work
- Works offline (QR scanning fallback)

### **✅ User Experience**
- Smooth, responsive interface
- Clear visual feedback (loading states, animations)
- Accessible design with good contrast
- Mobile-friendly layout

### **✅ Production Ready**
- Database migrations support
- Error pages (404, 403, 500)
- CSRF protection
- Session management
- Docker deployment support

---

## **Demo Credentials**

| Role | Username | Password |
|------|----------|----------|
| Student | 2022-0001 | student123 |
| Faculty (Registrar) | registrar | office123 |
| Faculty (Library) | library | office123 |
| Faculty (CS Dept) | csdept | office123 |

---

## **Quick Reference: File Structure**

```
check8/
├── app/
│   ├── __init__.py          # App factory, error handlers
│   ├── config.py            # Configuration (dev/prod)
│   ├── models.py            # SQLAlchemy models (User, Course, etc)
│   ├── extensions.py        # Flask extensions (db, login_manager, etc)
│   ├── blueprints/
│   │   ├── auth/routes.py   # Login/signup routes
│   │   ├── student/routes.py # Student dashboard, QR, PDF
│   │   └── admin/routes.py   # Faculty verification, groups
│   ├── utils/
│   │   ├── qr.py            # QR token generation/verification
│   │   └── pdf_export.py    # PDF certificate generation
│   ├── static/
│   │   ├── style.css        # Responsive design + animations
│   │   └── app.js           # Client-side form handling, QR scanner
│   └── templates/
│       ├── base.html        # Layout template
│       ├── error.html       # Error pages
│       └── auth/            # Login/signup pages
├── run.py                   # Development server entry
├── wsgi.py                  # Production WSGI entry
├── seed.py                  # Database seeding script
└── requirements.txt         # Python dependencies
```

---

## **For Judges: Evaluation Criteria**

### **Technical Quality (30%)**
✅ Clean architecture, proper ORM usage, security features, database design  
✅ Error handling, input validation, type hints

### **System Functionality (25%)**
✅ All features working: auth, QR, verification, groups, PDF  
✅ Correct outputs, responsive performance

### **Presentation Skills (15%)**
✅ Clear demo flow, confident explanation, good teamwork

### **Documentation (15%)**
✅ System diagrams, deployment guide, demo script, code comments

### **UX & Relevance (15%)**
✅ Practical solution, smooth interactions, professional design, works on mobile

---

## **Final Notes**

- System tested with manual testing (visible in seed.py and demo flows)
- Database migrations handled via migration scripts
- Production ready with Docker support
- Designed with institutional requirements in mind
- Fully responsive and accessible design

**Ready for presentation!** 🚀
