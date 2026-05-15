#!/usr/bin/env python
"""Test email sending within request context (simulating actual signup)."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import User, Role
from app.utils.email import send_email_verification
from app.extensions import db
import uuid

app = create_app()

# Configure app for external URL generation
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'

with app.app_context():
    # Create request context to enable url_for
    with app.test_request_context():
        print("Testing email sending within request context...")
        print("-" * 60)
        
        try:
            # Create a temporary test user
            test_user = User(
                role=Role.STUDENT.value,
                student_number="test_9999",
                full_name="Test User",
                email="giankarlo.deleon@gordoncollege.edu.ph",
                department="IT",
                program="BSCS",
                username=None,
                qr_salt=str(uuid.uuid4()),
            )
            test_user.set_password("testpass123")
            
            print("🔄 Attempting to send test verification email...")
            result = send_email_verification(test_user)
            
            if result:
                print("✅ Email sent successfully!")
                print(f"   To: {test_user.email}")
                print(f"   Token: {test_user.email_verification_token[:20]}...")
                print(f"   Expires: {test_user.email_verification_token_expires}")
            else:
                print("❌ Email sending returned False (check Flask logs)")
                
        except Exception as e:
            print(f"❌ Exception occurred: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
