# PythonAnywhere Deployment Guide for Check8

## Prerequisites
- PythonAnywhere account (https://www.pythonanywhere.com)
- Git repository access (GitHub)
- Environment variables ready

---

## Step 1: Initial Setup on PythonAnywhere

### 1.1 Open a Bash Console
- Log in to PythonAnywhere
- Go to **Consoles** → **Bash**
- This opens a terminal where you can run commands

### 1.2 Clone Your Repository
```bash
cd ~
git clone https://github.com/DaleCyrus/Check8.git
cd Check8
```

---

## Step 2: Create Virtual Environment

### 2.1 Create venv
```bash
python3.10 -m venv venv
source venv/bin/activate
```

### 2.2 Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3: Create Flask App (Web Tab)

### 3.1 Add New Web App
- Go to **Web** tab
- Click **Add a new web app**
- Choose **Manual configuration**
- Select **Python 3.10**

### 3.2 Configure WSGI File
The web app setup will create a WSGI file at:
```
/home/YOUR_USERNAME/YOURAPP.pythonanywhere.com_wsgi.py
```

**Replace its contents with:**
```python
import os
import sys

# Add your project directory to path
path = os.path.expanduser('~/Check8')
if path not in sys.path:
    sys.path.insert(0, path)

# Activate virtual environment
activate_this = os.path.expanduser('~/Check8/venv/bin/activate_this.py')
exec(open(activate_this).read(), {'__file__': activate_this})

# Import and create Flask app
from app import create_app
app = create_app()
```

---

## Step 4: Configure Environment Variables

### Option A: Via Web App Settings
1. Go to **Web** tab
2. Scroll to **Virtualenv**
3. Set path: `/home/YOUR_USERNAME/Check8/venv`

### Option B: Via .env File
Create `/home/YOUR_USERNAME/Check8/.env`:
```
FLASK_ENV=production
SECRET_KEY=your-very-strong-secret-key-here
DATABASE_URL=sqlite:///check8.db
```

### Option C: Via Web App Source Code Settings
Edit `app/config.py` to read from environment:
```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///check8.db'
    )
```

---

## Step 5: Configure Database

### 5.1 Initialize Database
In **Bash Console**:
```bash
cd ~/Check8
source venv/bin/activate
python
```

Then in Python shell:
```python
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("Database initialized!")
exit()
```

### 5.2 Run Migrations (if applicable)
```bash
flask db upgrade
```

---

## Step 6: Complete Web App Configuration

Go to **Web** tab and verify:

1. **Virtualenv path**: `/home/YOUR_USERNAME/Check8/venv`
2. **WSGI configuration file**: Points to your WSGI file
3. **Static files** mapping:
   - URL: `/static/`
   - Directory: `/home/YOUR_USERNAME/Check8/app/static/`
4. **Reload web app** after any changes

---

## Step 7: Troubleshooting

### Check Error Logs
- **Web** tab → **Log files**
- Check: Server log, Error log, Access log

### Common Issues

**Issue: Module not found**
```bash
# Ensure all dependencies installed
source venv/bin/activate
pip list
```

**Issue: Static files not loading**
- Verify path in Web tab matches exactly
- Ensure `/app/static/` contains your files

**Issue: Database errors**
```bash
# Reinitialize database
cd ~/Check8
rm instance/check8.db  # or wherever DB is stored
python -c "from app import create_app, db; app = create_app(); db.create_all()"
```

**Issue: 500 Internal Server Error**
1. Check error log in Web tab
2. Add debug mode to check error details
3. Verify WSGI file syntax

---

## Step 8: Update Code

After pushing changes to GitHub:
```bash
cd ~/Check8
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # if dependencies changed
```

Then in **Web** tab: Click **Reload YOUR_APP.pythonanywhere.com**

---

## Important Notes

- **PythonAnywhere uses SQLite by default** - Consider PostgreSQL for production
- **Keep `.env` file secure** - Don't commit to Git
- **Use strong SECRET_KEY** - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
- **Reload web app** after any changes to code or config
- **Check logs regularly** for errors and warnings
- **Set up automated backups** for your database file

---

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `FLASK_ENV` | Flask mode | `production` or `development` |
| `SECRET_KEY` | Session encryption | Long random string |
| `DATABASE_URL` | Database connection | `sqlite:///check8.db` |
| `DEBUG` | Debug mode | `False` for production |

---

## Advanced: PostgreSQL Database

For better production performance:

### 1. In Bash Console:
```bash
# Install PostgreSQL driver
source venv/bin/activate
pip install psycopg2-binary
```

### 2. Update DATABASE_URL environment variable:
```
postgresql://username:password@host:5432/dbname
```

### 3. Update app/config.py:
```python
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URL',
    'postgresql://user:pass@localhost/check8'
)
```

---

## Support
- PythonAnywhere Help: https://help.pythonanywhere.com
- Flask Documentation: https://flask.palletsprojects.com
- SQLAlchemy Docs: https://docs.sqlalchemy.org
