"""
WSGI entry point for production deployments.
Use with: gunicorn wsgi:app
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
