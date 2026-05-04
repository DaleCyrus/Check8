# PythonAnywhere Quick Deployment Checklist

## Pre-Deployment Checklist

### 1. Prepare Your Repository
- [ ] Commit all changes to GitHub: `git add . && git commit -m "Ready for deployment"`
- [ ] Push to main branch: `git push origin main`
- [ ] Verify `.env.example` is in repo (but NOT `.env`)
- [ ] Verify `wsgi.py` exists and is correct

### 2. PythonAnywhere Account Setup
- [ ] Create account at https://www.pythonanywhere.com
- [ ] For free tier: You can only have one web app
- [ ] For paid: More flexibility and better performance

---

## Deployment Steps

### Step 1: SSH/Bash Console
```bash
cd ~
git clone https://github.com/DaleCyrus/Check8.git
cd Check8
```

### Step 2: Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
```

**Checklist:**
- [ ] Virtual environment created
- [ ] All packages installed successfully

### Step 3: Environment Configuration
```bash
nano .env
```

**Add:**
```
FLASK_ENV=production
SECRET_KEY=<generate-strong-key>
DATABASE_URL=sqlite:///check8.db
```

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Checklist:**
- [ ] `.env` file created with SECRET_KEY
- [ ] SECRET_KEY is strong (32+ characters)
- [ ] Database path is correct

### Step 4: Database Initialization
```bash
source venv/bin/activate
python << 'EOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("✓ Database initialized successfully!")
EOF
```

**Checklist:**
- [ ] Database initialized without errors
- [ ] `instance/check8_fixed.db` or similar file created

### Step 5: Web App Configuration (PythonAnywhere Web Tab)

#### Basic Settings
- [ ] Click **Add a new web app**
- [ ] Choose **Manual configuration**
- [ ] Select **Python 3.10**
- [ ] Note the WSGI filename shown

#### Virtualenv
- [ ] Set to: `/home/YOUR_USERNAME/Check8/venv`
- [ ] Test by visiting your URL

#### WSGI File Configuration
- [ ] Copy contents from `pythonanywhere_wsgi_template.py`
- [ ] Paste into PythonAnywhere's WSGI file
- [ ] **Update these paths:**
  ```python
  PROJECT_DIR = os.path.expanduser('~/Check8')
  PYTHONANYWHERE_USERNAME = 'your_username'
  ```
- [ ] Save and reload

#### Static Files
- [ ] URL: `/static/`
- [ ] Directory: `/home/YOUR_USERNAME/Check8/app/static/`

**Checklist:**
- [ ] Virtualenv path set correctly
- [ ] WSGI file configured with correct paths
- [ ] Static files path configured
- [ ] Web app reloaded

### Step 6: Test Your Deployment
- [ ] Visit your app URL in browser
- [ ] Check for errors
- [ ] If 500 error, check error log in **Web** tab

---

## Troubleshooting

### Step 1: Check Error Logs
In PythonAnywhere **Web** tab → **Log files**:
- [ ] Check **Server log**
- [ ] Check **Error log**
- [ ] Check **Access log**

### Common Issues & Solutions

#### Issue: "ModuleNotFoundError"
```bash
source venv/bin/activate
pip list  # Verify packages are installed
pip install -r requirements.txt --force-reinstall
```

#### Issue: Static files not loading (404)
- [ ] Verify path in Web tab ends with `/`
- [ ] Check files actually exist in directory
- [ ] Try hard refresh (Ctrl+Shift+R)

#### Issue: Database errors
```bash
source venv/bin/activate
rm ~/Check8/instance/check8_fixed.db  # Delete old DB
python << 'EOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
EOF
```
Reload web app.

#### Issue: "Secret key" errors
- [ ] Check .env file exists: `cat .env`
- [ ] Verify SECRET_KEY line has no quotes
- [ ] Try setting it directly in WSGI file temporarily

#### Issue: Seeing old code
- [ ] Go to **Web** tab and click **Reload**
- [ ] Force browser cache clear: Ctrl+Shift+R
- [ ] Check git status: `git status`

---

## After Deployment

### Daily Maintenance
- [ ] Check error logs once daily
- [ ] Monitor performance in PythonAnywhere dashboard
- [ ] Keep dependencies updated

### Code Updates
```bash
cd ~/Check8
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # if changed
# Then reload in Web tab
```

### Backup Database
```bash
# Download your database file regularly
scp YOUR_USERNAME@ssh.pythonanywhere.com:~/Check8/instance/check8_fixed.db ./backup.db
```

### Optional: Setup Periodic Tasks
In PythonAnywhere **Tasks** tab:
- [ ] Set up daily backups
- [ ] Set up error monitoring

---

## Security Checklist

- [ ] SECRET_KEY is strong (32+ random characters)
- [ ] `.env` file contains sensitive data (never commit)
- [ ] FLASK_ENV is set to `production`
- [ ] DEBUG is False (automatic with FLASK_ENV=production)
- [ ] SESSION_COOKIE_SECURE is True
- [ ] Only allow HTTPS

---

## Performance Tips

### For SQLite (Free Tier)
- Suitable for small to medium apps
- Use WAL mode for better concurrency
- Regular backups recommended

### For PostgreSQL (Paid Tier)
```bash
pip install psycopg2-binary
# Update DATABASE_URL in .env
```

---

## Getting Help

1. **Error in logs?**
   - Read the full error message
   - Search PythonAnywhere docs: https://help.pythonanywhere.com
   - Search Flask docs: https://flask.palletsprojects.com

2. **Still stuck?**
   - Check SSH console history
   - Verify all files are present: `ls -la ~/Check8/`
   - Test app locally before uploading

3. **Useful Commands**
```bash
# Check Python version
python --version

# List installed packages
pip list

# Check if app imports correctly
python -c "from app import create_app; print('✓ App imports successfully')"

# View recent git changes
git log --oneline -5

# Check database exists
ls -lh ~/Check8/instance/
```

---

## Final Notes

- PythonAnywhere free tier has one web app limit
- 100 MB storage - check usage regularly
- 50+ web app reloads per day limit (usually not an issue)
- Bandwidth: 100 MB/day for free tier
- For production, consider upgrading to paid tier or other hosting

**Your app is now live!** 🚀
