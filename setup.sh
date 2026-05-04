#!/bin/bash
# Quick deployment setup script

echo "=== Check8 Deployment Setup ==="
echo ""

# Check Python version
python_version=$(python3 --version)
echo "Python: $python_version"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Activate venv
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your SECRET_KEY and DATABASE_URL"
fi

# Create instance directory
mkdir -p instance

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run in development:"
echo "  python run.py"
echo ""
echo "To run in production:"
echo "  source venv/bin/activate"
echo "  bash start_production.sh"
echo ""
echo "To use Docker:"
echo "  docker-compose up -d"
echo ""
