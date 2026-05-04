#!/bin/bash
# Production startup script for Check8

set -e

echo "Starting Check8 Production Server..."

# Check required environment variables
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY not set. Using default (not secure for production)."
    export SECRET_KEY="dev-secret-change-me"
fi

if [ -z "$FLASK_ENV" ]; then
    export FLASK_ENV="production"
fi

# Create instance directory
mkdir -p instance

# Get number of CPU cores
WORKERS=$((2 * $(nproc) + 1))

echo "Environment: $FLASK_ENV"
echo "Workers: $WORKERS"
echo "Database: $DATABASE_URL"

# Start Gunicorn
exec gunicorn \
    --workers "$WORKERS" \
    --bind 0.0.0.0:${PORT:-5000} \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    wsgi:app
