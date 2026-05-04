"""
PythonAnywhere WSGI Configuration
=================================

This file is used by PythonAnywhere's WSGI handler to run your Flask app.
Copy this to your WSGI configuration file in PythonAnywhere:
  /home/YOUR_USERNAME/YOURAPP.pythonanywhere.com_wsgi.py

Instructions:
1. Replace YOUR_USERNAME with your PythonAnywhere username
2. Replace YOURAPP with your web app name
3. Update the path below to match your project directory
"""

import os
import sys
import logging

# ============================================================================
# CONFIGURATION - Update these paths for your PythonAnywhere setup
# ============================================================================

# Path to your project directory
PROJECT_DIR = os.path.expanduser('~/Check8')

# Username (used for logging)
PYTHONANYWHERE_USERNAME = os.getenv('PYTHONANYWHERE_USERNAME', 'unknown')

# ============================================================================
# SETUP PYTHON PATH
# ============================================================================

# Add project to path so imports work
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ============================================================================
# ACTIVATE VIRTUAL ENVIRONMENT
# ============================================================================

VENV_PATH = os.path.join(PROJECT_DIR, 'venv', 'bin', 'activate_this.py')

try:
    with open(VENV_PATH) as f:
        exec(f.read(), {'__file__': VENV_PATH})
except FileNotFoundError:
    print(f"ERROR: Virtual environment not found at {VENV_PATH}")
    print("Please create it with: python3.10 -m venv ~/Check8/venv")
    raise

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================

from dotenv import load_dotenv
env_file = os.path.join(PROJECT_DIR, '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    # Set defaults if .env doesn't exist
    print(f"WARNING: .env file not found at {env_file}")
    print("Using default configuration...")
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('SECRET_KEY', 'change-me-in-production')

# ============================================================================
# SETUP LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"Initializing Check8 WSGI for {PYTHONANYWHERE_USERNAME}")
logger.info(f"Project directory: {PROJECT_DIR}")
logger.info(f"Flask environment: {os.environ.get('FLASK_ENV', 'unknown')}")

# ============================================================================
# CREATE FLASK APP
# ============================================================================

try:
    from app import create_app
    
    logger.info("Creating Flask application...")
    app = create_app()
    logger.info("Flask application created successfully!")
    
    # Additional logging for debugging
    logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    logger.info(f"Debug mode: {app.debug}")
    
except ImportError as e:
    logger.error(f"Failed to import app: {e}")
    raise
except Exception as e:
    logger.error(f"Failed to create Flask app: {e}")
    raise

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
# The 'app' object below is what PythonAnywhere uses to serve your website

if __name__ == '__main__':
    logger.info("Running in direct mode (not recommended for production)")
    app.run()
