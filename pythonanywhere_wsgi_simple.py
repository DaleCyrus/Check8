"""
Simplified PythonAnywhere WSGI Configuration for Check8
========================================================

This is the recommended approach - let PythonAnywhere handle the virtualenv.

Instructions:
1. Copy this entire file
2. Go to Web tab → WSGI configuration file
3. Replace the contents with this code
4. In Web tab, set Virtualenv to: /home/Nykt/Check8/venv
5. Save and reload
"""

import os
import sys

# Add project to Python path
project_dir = os.path.expanduser('~/Check8')
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

# Create Flask app
from app import create_app
app = create_app()
