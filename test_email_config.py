#!/usr/bin/env python
"""Test script to verify email configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

print("Email Configuration Status:")
print("-" * 50)
print(f"MAIL_SERVER: {os.getenv('MAIL_SERVER', 'NOT SET')}")
print(f"MAIL_PORT: {os.getenv('MAIL_PORT', 'NOT SET')}")
print(f"MAIL_USE_TLS: {os.getenv('MAIL_USE_TLS', 'NOT SET')}")
print(f"MAIL_USERNAME: {os.getenv('MAIL_USERNAME', 'NOT SET')}")
print(f"MAIL_PASSWORD: {'SET' if os.getenv('MAIL_PASSWORD') else 'NOT SET'}")
print(f"MAIL_DEFAULT_SENDER: {os.getenv('MAIL_DEFAULT_SENDER', 'NOT SET')}")
print("-" * 50)

# Check if all required vars are set
required = ['MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
missing = [var for var in required if not os.getenv(var)]

if missing:
    print(f"\n❌ Missing required environment variables: {', '.join(missing)}")
    print("\nCreate a .env file in the project root with:")
    print("""
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gordoncollege.edu.ph
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gordoncollege.edu.ph
""")
else:
    print("\n✅ All email configuration variables are set!")
