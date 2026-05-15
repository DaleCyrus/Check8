# CHECK8 Live Demo Script
**Presentation Time: 5-10 minutes**

---

## **PRE-DEMO CHECKLIST** ✓
- [ ] Database seeded: `python seed.py --reset`
- [ ] App running: `python run.py` → http://127.0.0.1:5000
- [ ] Browser DevTools closed (for clean demo)
- [ ] Network stable
- [ ] Test account credentials copied/accessible:
  - Student: `2022-0001` / `student123`
  - Faculty: `registrar` / `office123`

---

## **DEMO FLOW (5-10 min)**

### **PART 1: System Introduction (1 min)**
**What to say:**
> "CHECK8 is a QR-enabled student clearance management system built for academic institutions. It streamlines the clearance process by allowing students to generate secure QR codes and faculty to verify them instantly."

**Show:**
- Point to header with logo
- Mention the three main roles: Students, Faculty, Admins

---

### **PART 2: Student Perspective (2-3 min)**

#### **2a. Student Login & Dashboard**
1. Click "Sign up" → select "Sign up as Student"
2. **OR** go directly to login, enter: `2022-0001` / `student123`
3. **Show dashboard:**
   - "View Clearance Dashboard" - shows all courses with clearance status (Pending/Cleared/Blocked)
   - Point out **three clearance states with badges:**
     - ⏳ **Pending** (yellow) - not yet verified
     - ✅ **Cleared** (green) - approved by faculty
     - ❌ **Blocked** (red) - denied clearance
   - Mention: "All data tied to institutional email + secure password hash"

#### **2b. QR Code Generation**
1. Click "View Student QR Token"
2. **Show QR code** - explain:
   - "This QR is signed with app secret + student salt"
   - "Token is verified on scan - can't be forged"
3. Click "Copy token" button - show smooth loading animation
4. **Bonus:** Click "Download Clearance PDF" to show PDF certificate generation

**Key technical point to mention:**
> "QR tokens use cryptographic signing (URLSafeSerializer) to prevent forgery. Each student has a unique salt stored in the database."

---

### **PART 3: Faculty Perspective (3-4 min)**

#### **3a. Faculty Login**
1. Logout (click Logout button - smooth transition animation)
2. Login as: `registrar` / `office123`
3. **Show Faculty Dashboard:**
   - Table of students with clearance status
   - Search/filter capabilities
   - Multiple course support

#### **3b. Student Verification (QR Scan)**
1. Click "Verify Student" tab
2. **Show two options:**
   - **Option 1: Live Camera** - click "Start Camera" (explain: uses html5-qrcode library)
   - **Option 2: Paste Token** - paste the token you copied earlier
3. Hit submit - **observe smooth loading animation on button**
4. **Show verification result:**
   - Student name, ID, current status
   - Action buttons to update clearance (Cleared/Blocked)
5. **Update status:** Click "Mark as Cleared" → smooth notification appears at top
   - Point out: "Status updates instantly"

**Technical highlight:**
> "Verification validates the token signature. If salt doesn't match or signature is invalid, it shows error. This prevents unauthorized access."

#### **3c. Bulk Student Operations**
1. Click "Add Students" button
2. **Show bulk add form:**
   - Paste multiple student IDs (comma or newline separated)
   - Click "Add Students to Clearance List"
   - **Point out:** "Handles duplicates gracefully, prevents duplicate enrollments"

#### **3d. Student Groups Feature**
1. Click "Student Groups" 
2. **Show existing group** OR **create new group:**
   - Select Faculty/Department
   - Enter group name (e.g., "3rd Year Batch")
   - Click "Create Group"
3. **Add students to group:**
   - Click "Manage" on group card
   - Bulk paste student IDs
   - Click "Add Students to Group"
4. **Point out:**
   - Isolation constraint: "Each student can only be in 1 group per course per instructor"
   - Shows smooth animations as group updates

**Technical highlight:**
> "Groups enforce a unique constraint: UNIQUE(created_by_user_id, course_id, name). This prevents naming conflicts and ensures data integrity."

---

### **PART 4: Technical Architecture (1-2 min)**

#### **Show Code Quality:**
1. **Open VSCode / browser dev tools → Elements**
2. Point out smooth animations:
   - Card hover effects (translateY transform)
   - Button transitions (0.25s cubic-bezier)
   - Notification slide-in animations

3. **Mention database design:**
   - Foreign keys + cascade deletes
   - Unique constraints prevent duplicates
   - SQLAlchemy ORM with proper relationships

4. **Security features:**
   - HTTPONLY secure cookies (30-min timeout)
   - CSRF protection on all forms
   - Institutional email validation (@gordoncollege.edu.ph)
   - Password hashing with werkzeug.security

#### **Show Error Handling:**
1. Navigate to invalid URL (e.g., `/admin/nonexistent`)
2. **Show beautifully styled 404 error page:**
   - Large error code with gradient text
   - Clear message with action buttons
   - Point out: "Error pages use same design language as rest of app"

---

### **PART 5: UI/UX Highlights (30 sec)**

**Point out smooth interactions:**
- ✨ **Page animations** - fade-in on load
- ✨ **Button animations** - smooth hover, scale on active, loading spinner
- ✨ **Notifications** - icons (✓, ⚠️, ⚡), animations with slide-in
- ✨ **Form interactions** - input focus states, disabled states
- ✨ **Mobile responsive** - all buttons/forms stack on small screens
- ✨ **Color system** - orange accent theme consistent throughout

---

## **POTENTIAL Q&A**

**Q: "Why use QR codes?"**
> "QR codes are non-hackable if signed properly. The token is encrypted with app secret + student salt. Faculty can even scan offline."

**Q: "How do you prevent duplicate clearances?"**
> "Database has UNIQUE(student_id, course_id) constraint on ClearanceStatus table. Duplicate attempts fail at database level."

**Q: "What about security?"**
> "Sessions are HTTPONLY + Secure cookies, 30-min timeout. All forms have CSRF tokens. Passwords are hashed, never stored plaintext. Authentication checks every protected route."

**Q: "Scalability?"**
> "Built with SQLAlchemy + configurable database (SQLite for dev, PostgreSQL for production). Connection pooling, WAL mode for concurrency. Can handle hundreds of concurrent users."

**Q: "What's next?"**
> "Could add: Email notifications, audit logs, advanced reporting, API for mobile apps, two-factor authentication."

---

## **DEMO TALKING POINTS (for judges)**

### **Engineering Quality**
- ✅ Clean MVC architecture with Flask blueprints
- ✅ Proper database design with constraints & relationships
- ✅ Security-conscious (signed tokens, CSRF, password hashing)
- ✅ Error handling with user-friendly pages
- ✅ Responsive design that works on mobile/tablet/desktop

### **System Functionality**
- ✅ All core features working: auth, QR generation, verification, groups
- ✅ Bulk operations reduce manual work
- ✅ Data integrity maintained (constraints, unique keys)
- ✅ Smooth performance with optimized queries

### **UX/Design**
- ✅ Consistent design language (orange theme)
- ✅ Smooth animations make app feel polished
- ✅ Clear visual hierarchy with typography
- ✅ Accessible color scheme with good contrast
- ✅ Loading states + error messages prevent confusion

### **Code Quality**
- ✅ Type hints in Python code
- ✅ Proper separation of concerns (models, routes, utilities)
- ✅ Documented database models
- ✅ Clean commit history (if using git)

---

## **TIME MANAGEMENT**

| Section | Time | Notes |
|---------|------|-------|
| Intro | 1 min | What is CHECK8 |
| Student Demo | 2 min | Login, QR, PDF |
| Faculty Demo | 3 min | Verify, bulk add, groups |
| Architecture | 1.5 min | Code quality, security |
| UI/UX | 0.5 min | Animations, design |
| **TOTAL** | **~8 min** | Leave 2 min for questions |

---

## **TROUBLESHOOTING**

| Issue | Solution |
|-------|----------|
| Camera not working | Use "Paste token" option instead |
| Database locked | Restart app, run `seed.py --reset` |
| Form won't submit | Check network tab for errors, try refresh |
| Notification not showing | Check browser console for JS errors |
| QR code not generating | Verify student has qr_salt in DB |

---

**Good luck with your presentation! 🚀**
