#!/usr/bin/env python
"""Test email sending functionality."""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import User, Role
from app.utils.email import send_email_verification
from app.extensions import db
import uuid

# Create app context
app = create_app()

with app.app_context():
    print("Testing email sending functionality...")
    print("-" * 60)
    
    # Check Flask-Mail configuration
    print(f"Flask-Mail configured: {bool(app.config.get('MAIL_SERVER'))}")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
    print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
    print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
    print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
    print("-" * 60)
    
    # Try to create a test user and send email
    try:
        # Create a temporary test user (not committing to DB)
        test_user = User(
            role=Role.STUDENT.value,
            student_number="test_9999",
            full_name="Test User",
            email="test@gordoncollege.edu.ph",
            department="IT",
            program="BSCS",
            username=None,
            qr_salt=str(uuid.uuid4()),
        )
        test_user.set_password("testpass123")
        
        print("\n🔄 Attempting to send test verification email...")
        result = send_email_verification(test_user)
        
        if result:
            print("✅ Email sent successfully!")
            print(f"   Token generated: {test_user.email_verification_token[:20]}...")
            print(f"   Token expires: {test_user.email_verification_token_expires}")
        else:
            print("❌ Email sending failed (check app logs)")
            
    except Exception as e:
        print(f"❌ Error during test: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
