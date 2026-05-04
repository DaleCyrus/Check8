@echo off
REM Windows batch script to run production server with Gunicorn

setlocal enabledelayedexpansion

echo Starting Check8 Production Server on Windows...

REM Check if FLASK_ENV is set
if not defined FLASK_ENV (
    set FLASK_ENV=production
    echo FLASK_ENV set to production
)

REM Check if SECRET_KEY is set
if not defined SECRET_KEY (
    echo WARNING: SECRET_KEY not set. Using default (not secure for production^).
    set SECRET_KEY=dev-secret-change-me
)

REM Create instance directory
if not exist "instance" mkdir instance

echo Environment: %FLASK_ENV%
echo Database: %DATABASE_URL%

REM Run Gunicorn (typically works via Python module on Windows)
python -m gunicorn -w 4 -b 0.0.0.0:%PORT:5000% --timeout 30 --access-logfile - --error-logfile - wsgi:app

endlocal
