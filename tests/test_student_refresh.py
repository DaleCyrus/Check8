import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import ClearanceStatus, Course, Faculty, Role, User


class StudentRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        database = Path(cls.directory.name, "refresh-test.db").as_posix()
        with patch.object(Config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{database}"):
            cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        with cls.app.app_context():
            student = User(role=Role.STUDENT.value, full_name="REFRESH TEST",
                           email="refresh@gordoncollege.edu.ph", student_number="REFRESH-001")
            student.set_password("test-password")
            db.session.add(student)
            db.session.commit()
            cls.student_id = student.id

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        cls.directory.cleanup()

    def setUp(self):
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.student_id)
            session["_fresh"] = True

    def test_empty_dashboard_has_refresh_targets(self):
        response = self.client.get("/student/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for marker in ("data-clearance-rows", "data-clearance-count", "data-clearance-summary",
                       "data-clearance-percent", "data-clearance-empty", "data-clearance-notice"):
            self.assertIn(marker, html)
        self.assertIn('data-status-url="/student/clearance-status-json"', html)
        self.assertIn('max="1"', html)

    def test_json_reflects_updates_and_is_not_cached(self):
        with self.app.app_context():
            faculty = Faculty(name="Refresh Test Faculty")
            db.session.add(faculty)
            db.session.flush()
            course = Course(code="REFRESH-101", name="Refresh Test", faculty_id=faculty.id)
            db.session.add(course)
            db.session.flush()
            clearance = ClearanceStatus(student_id=self.student_id, course_id=course.id, state="pending")
            db.session.add(clearance)
            db.session.commit()
            clearance_id = clearance.id
        response = self.client.get("/student/clearance-status-json")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.json[0]["state"], "pending")
        with self.app.app_context():
            clearance = db.session.get(ClearanceStatus, clearance_id)
            clearance.state = "cleared"
            clearance.note = "Approved in test"
            db.session.commit()
        response = self.client.get("/student/clearance-status-json")
        self.assertEqual(response.json[0]["state"], "cleared")
        self.assertEqual(response.json[0]["note"], "Approved in test")
        html = self.client.get("/student/dashboard").get_data(as_text=True)
        self.assertIn(f'data-clearance-id="{clearance_id}" data-state="cleared"', html)
        self.assertIn("1 of 1 courses approved", html)

    def test_requires_student_access(self):
        self.assertEqual(self.app.test_client().get("/student/clearance-status-json").status_code, 302)
        with self.app.app_context():
            admin_id = db.session.execute(db.select(User.id).where(User.role == Role.ADMIN.value)).scalar_one()
        with self.client.session_transaction() as session:
            session["_user_id"] = str(admin_id)
        self.assertEqual(self.client.get("/student/clearance-status-json").status_code, 403)
