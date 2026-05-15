# Email Verification Not Sending - Root Cause Analysis

## Problem
No email verification emails are being sent during signup.

## Root Cause
**Gmail authentication is failing with error 535: "Username and Password not accepted"**

The SMTP credentials in your `.env` file are not being accepted by Gmail's SMTP server.

### Current Configuration
```
MAIL_USERNAME=your-school-gmail@gordoncollege.edu.ph
MAIL_PASSWORD=yuwww tyne smdc dgxl  ← This app password is INVALID/EXPIRED
```

## Why This Happens
1. Gmail's app passwords expire after a certain period of inactivity
2. The current password was generated on May 11, 2026, and may have expired
3. Gmail might also revoke credentials if:
   - The account password was changed
   - 2FA settings were modified
   - Security settings were updated

## Solution

You need to **regenerate a new Gmail App Password**:

### Step 1: Enable 2-Factor Authentication (if not already enabled)
1. Go to https://myaccount.google.com/
2. Click **Security** on the left sidebar
3. Scroll to **How you sign in to Google** section
4. Enable **2-Step Verification** if not enabled

### Step 2: Generate New App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select:
   - **App**: Mail
   - **Device**: Other (custom name)
3. Google will generate a 16-character app password
4. Copy this password (without spaces)

### Step 3: Update .env File
Create a `.env` file in the project root with:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-school-gmail@gordoncollege.edu.ph
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_DEFAULT_SENDER=your-school-gmail@gordoncollege.edu.ph
```

**Important**: Use the 16-character password from Google. It may contain spaces - that's normal.

### Step 4: Test the Connection
Run the test script to verify:
```bash
python test_email_request_context.py
```

You should see:
```
✅ Email sent successfully!
```

## How to Generate Gmail App Password

1. The app password is **different** from your Google account password
2. It's specifically for third-party applications like this Flask app
3. You can generate multiple app passwords for different apps
4. You can revoke them individually from the App Passwords page

## Files to Check/Update
- ✅ `app/config.py` - Email configuration is correct
- ✅ `app/extensions.py` - Flask-Mail initialized properly
- ✅ `app/__init__.py` - mail.init_app() called
- ✅ `app/utils/email.py` - Email functions implemented correctly
- ❌ `.env` - **NEEDS UPDATED GMAIL APP PASSWORD**

## Testing After Fix
1. Update `.env` with new password
2. Run `python test_email_request_context.py` to verify
3. Try signup flow - verification email should arrive in seconds
4. Check spam folder if not in inbox
