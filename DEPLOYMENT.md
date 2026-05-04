# Deployment Guide

## Local Development
```bash
pip install -r requirements.txt
python run.py
```

---

## Production Deployment

### Option 1: Gunicorn (Recommended for VPS)

**Install:**
```bash
pip install -r requirements.txt
```

**Run:**
```bash
FLASK_ENV=production SECRET_KEY="your-strong-secret-key" gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

**With Systemd Service** (`/etc/systemd/system/check8.service`):
```ini
[Unit]
Description=Check8 Student Clearance System
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/check8
Environment="PATH=/home/check8/venv/bin"
Environment="FLASK_ENV=production"
Environment="SECRET_KEY=your-secret-key"
Environment="DATABASE_URL=postgresql://user:pass@localhost/check8_db"
ExecStart=/home/check8/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable check8
sudo systemctl start check8
sudo systemctl status check8
```

---

### Option 2: Docker (Containerized)

**Build:**
```bash
docker build -t check8:latest .
```

**Run with PostgreSQL:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f web
```

---

### Option 3: Railway/Heroku (PaaS)

1. Connect repository to Railway/Heroku
2. Set environment variables:
   - `FLASK_ENV=production`
   - `SECRET_KEY=your-secret-key`
   - `DATABASE_URL=postgresql://...`
3. Deploy automatically from Git

---

### Option 4: Nginx Reverse Proxy

**Setup** (`/etc/nginx/sites-available/check8`):
```nginx
upstream gunicorn {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static {
        alias /home/check8/static;
        expires 30d;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/check8 /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## Security Checklist

- [ ] Change `SECRET_KEY` to a strong random string
- [ ] Set `FLASK_ENV=production`
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Enable HTTPS/SSL (Let's Encrypt free)
- [ ] Set strong database password
- [ ] Enable rate limiting on endpoints
- [ ] Set secure cookie flags in config
- [ ] Regular backups of database
- [ ] Monitor logs and errors
- [ ] Keep dependencies updated

---

## Database Setup (PostgreSQL)

```sql
CREATE USER check8_user WITH PASSWORD 'strong_password';
CREATE DATABASE check8_db OWNER check8_user;
GRANT ALL PRIVILEGES ON DATABASE check8_db TO check8_user;
```

Then set `DATABASE_URL`:
```
postgresql://check8_user:strong_password@localhost:5432/check8_db
```

---

## Performance Tuning

**Gunicorn workers:** Use `2 * CPU_CORES + 1`
```bash
gunicorn -w 9 -b 0.0.0.0:5000 wsgi:app
```

**Database connection pooling** (update `config.py`):
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
```

---

## Monitoring & Logs

**View real-time logs:**
```bash
journalctl -u check8 -f
```

**Check service status:**
```bash
systemctl status check8
```
