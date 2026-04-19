# CHECK8 (Flask Starter)

CHECK8 is a web-based, QR-enabled clearance management system for BS Computer Science student clearance.

## Features in this starter

- Student + Office (admin) login
- Student dashboard showing clearance per office
- QR code generation per student (signed token)
- Office verification page (scan QR or paste token)
- Mark a student as Cleared / Blocked per office
- SQLite database (easy local setup)

## Tech

- Backend: Python + Flask
- Frontend: HTML/CSS + JavaScript
- DB: SQLite (via SQLAlchemy)
- QR: `qrcode` (server-side) + optional camera scanning via `html5-qrcode` (CDN)

## Setup (Windows / PowerShell)

From the `check8` folder:

```bash
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```bash
copy .env.example .env
```

Seed the database (creates sample users and offices):

```bash
python seed.py
```

Run:

```bash
python run.py
```

Open the app at `http://127.0.0.1:5000`.

## Sample accounts (from seed)

- Student: `2022-0001` / `student123`
- Student: `2022-0002` / `student123`
- Office (Registrar): `registrar` / `office123`
- Office (Library): `library` / `office123`
- Office (CS Dept): `csdept` / `office123`

## Notes

- This is a starter scaffold you can extend (roles, audit logs, notifications, approvals, reports, etc.).
- If camera scanning doesn’t work offline, you can still paste the token string into the verify form.

