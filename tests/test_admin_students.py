import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Role, User


class AdminStudentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        database = Path(cls.directory.name, "students-test.db").as_posix()
        with patch.object(Config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{database}"):
            cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        with cls.app.app_context():
            cls.admin_id = db.session.execute(
                db.select(User.id).where(User.role == Role.ADMIN.value)
            ).scalar_one()
            student = User(role=Role.STUDENT.value, full_name="TEST STUDENT",
                           email="test@gordoncollege.edu.ph", student_number="TEST-001")
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
            session["_user_id"] = str(self.admin_id)
            session["_fresh"] = True

    def assert_students_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/faculty/admin/students")

    def test_students_has_own_page_and_selected_sidebar(self):
        response = self.client.get("/faculty/admin/students")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-current="page" href="/faculty/admin/students"', html)
        self.assertEqual(html.count('aria-current="page"'), 1)
        self.assertIn('id="add-student"', html)
        self.assertIn('id="students"', html)
        self.assertIn('id="import"', html)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_dashboard_is_overview_only(self):
        response = self.client.get("/faculty/admin/dashboard")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-current="page" href="/faculty/admin/dashboard"', html)
        self.assertNotIn('id="students"', html)
        self.assertNotIn('id="add-student"', html)
        self.assertIn('/faculty/admin/students#import', html)

    def test_other_sidebar_pages_link_to_students(self):
        for path in ("/faculty/groups", "/faculty/admin/instructors"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn('href="/faculty/admin/students"', html)
                self.assertIn(f'aria-current="page" href="{path}"', html)
                self.assertEqual(html.count('aria-current="page"'), 1)

    def test_students_requires_admin(self):
        self.assertEqual(self.app.test_client().get("/faculty/admin/students").status_code, 302)
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.student_id)
        self.assertEqual(self.client.get("/faculty/admin/students").status_code, 403)

    def test_create_student_returns_to_students(self):
        response = self.client.post("/faculty/admin/students/create", data={
            "student_number": "TEST-002", "first_name": "New", "last_name": "Student",
            "email": "new@gordoncollege.edu.ph", "password": "chosen-password",
        })
        self.assert_students_redirect(response)
        with self.app.app_context():
            student = db.session.execute(db.select(User).where(User.student_number == "TEST-002")).scalar_one()
            self.assertTrue(student.check_password("chosen-password"))

    def test_invalid_create_returns_to_students(self):
        self.assert_students_redirect(self.client.post("/faculty/admin/students/create", data={
            "student_number": "INVALID", "first_name": "Test", "last_name": "Student",
        }))

    def test_update_and_toggle_return_to_students(self):
        self.assert_students_redirect(self.client.post(
            f"/faculty/admin/students/{self.student_id}/update", data={"department": "CCS"}))
        self.assert_students_redirect(self.client.post(
            f"/faculty/admin/students/{self.student_id}/toggle"))

    def test_import_returns_to_students(self):
        self.assert_students_redirect(self.client.post("/faculty/admin/import-students/preview"))
        response = self.client.post("/faculty/admin/import-students/preview", data={
            "file": (io.BytesIO(b"student_number,email,first_name,last_name\nTEST-003,import@gordoncollege.edu.ph,Import,Student\n"), "students.csv"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/faculty/admin/students">Cancel', response.get_data(as_text=True))
        self.assert_students_redirect(self.client.post("/faculty/admin/import-students/confirm"))


if __name__ == "__main__":
    unittest.main()
