# MagnetarStudio Production Deployment Guide

## 🚀 Quick Start (30 Minutes to Production)

This guide walks you through deploying MagnetarStudio to production with enterprise-grade security.

---

## Prerequisites

- Git repository access
- Server with Python 3.10+ and Node.js 18+
- Domain name with SSL certificate
- 4GB+ RAM, 20GB+ storage

---

## Step 1: Git History Cleanup (10 minutes)

**CRITICAL:** Remove exposed credentials from git history before deployment.

```bash
# 1. Backup repository
git clone --mirror https://github.com/yourorg/magnetarstudio.git backup-repo

# 2. Run automated purge script
cd magnetarstudio
./scripts/purge_credentials_from_history.sh

# 3. Force push cleaned history
git push --force --all
git push --force --tags

# 4. Verify cleanup
git log -S "8ae2ec5497cff953d881ac5b9f948ecacbb02e165396fdcd1ce9ac26b1ab7d00" --all
# Should return: no results

# 5. Team re-clones
git clone https://github.com/yourorg/magnetarstudio.git fresh-clone
```

**Status:** ⏸️ Manual step required (one-time only)

---

## Step 2: Production Environment Setup (10 minutes)

### 2.1 Generate Secure Secrets

```bash
# Generate JWT secret (256-bit)
openssl rand -hex 32
# Example output: a1b2c3d4e5f6...

# Generate audit encryption key (256-bit)
openssl rand -hex 32
# Example output: f6e5d4c3b2a1...

# Generate founder password (strong)
openssl rand -base64 24
# Example output: Xy9Kp2Lm...
```

### 2.2 Create Production `.env`

Create `/path/to/magnetarstudio/.env`:

```bash
# ===== Environment =====
ELOHIM_ENV=production
NODE_ENV=production

# ===== Security - JWT Authentication =====
ELOHIMOS_JWT_SECRET_KEY=<your-jwt-secret-from-step-2.1>
JWT_ALGORITHM=HS256

# ===== Security - Audit Log Encryption =====
ELOHIMOS_AUDIT_ENCRYPTION_KEY=<your-audit-key-from-step-2.1>

# ===== Founder Account =====
ELOHIM_FOUNDER_PASSWORD=<your-founder-password-from-step-2.1>

# ===== CORS - Production Origins =====
# Whitelist your production domain(s)
ELOHIM_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ===== Database =====
ELOHIM_DATA_DIR=/var/lib/magnetarstudio
ELOHIM_CONFIG_DIR=/etc/magnetarstudio

# ===== Session Security (MED-03) =====
# Max concurrent sessions per user
MAX_CONCURRENT_SESSIONS=3

# ===== Rate Limiting =====
# Redis connection (optional, improves performance)
REDIS_URL=redis://localhost:6379/0

# ===== HTTPS Enforcement =====
# Required for HSTS (Strict-Transport-Security header)
FORCE_HTTPS=true

# ===== Optional: External Services =====
# HaveIBeenPwned API (password breach detection)
# No API key needed - uses public API

# ===== Optional: Monitoring =====
PROMETHEUS_ENABLED=true
METRICS_PORT=9090

# ===== Optional: Emergency Features =====
# Only enable if you need emergency wipe capability
ELOHIM_ALLOW_EMERGENCY_WIPE=false
```

### 2.3 Secure File Permissions

```bash
# Set restrictive permissions on .env
chmod 600 /path/to/magnetarstudio/.env
chown appuser:appuser /path/to/magnetarstudio/.env

# Create data directories
sudo mkdir -p /var/lib/magnetarstudio
sudo mkdir -p /etc/magnetarstudio
sudo chown -R appuser:appuser /var/lib/magnetarstudio
sudo chown -R appuser:appuser /etc/magnetarstudio
```

---

## Step 3: Application Deployment (10 minutes)

### 3.1 Install Dependencies

```bash
# Backend (Python)
cd apps/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install additional security dependencies
pip install aiohttp  # For password breach checker

# Frontend (Node.js)
cd apps/native
npm ci --production

# Swift build
xcodebuild -scheme MagnetarStudio -configuration Release
```

### 3.2 Database Initialization

```bash
# Initialize database with WAL mode (concurrency)
cd apps/backend
python3 -c "
from api.auth_middleware import AuthService
auth = AuthService()
print('✅ Database initialized')
"

# Verify connection pooling
python3 -c "
from api.db_pool import get_connection_pool
pool = get_connection_pool()
print(f'✅ Connection pool initialized: {pool.min_connections}-{pool.max_connections} connections')
"
```

### 3.3 Start Application

#### Option A: systemd Service (Recommended)

Create `/etc/systemd/system/magnetarstudio.service`:

```ini
[Unit]
Description=MagnetarStudio API Server
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/path/to/magnetarstudio/apps/backend
Environment="PATH=/path/to/magnetarstudio/apps/backend/venv/bin"
EnvironmentFile=/path/to/magnetarstudio/.env
ExecStart=/path/to/magnetarstudio/apps/backend/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/magnetarstudio /etc/magnetarstudio

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable magnetarstudio
sudo systemctl start magnetarstudio
sudo systemctl status magnetarstudio
```

#### Option B: Docker (Alternative)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/backend /app
COPY .env /app/.env

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Build and run:

```bash
docker build -t magnetarstudio .
docker run -d -p 8000:8000 --name magnetarstudio magnetarstudio
```

---

## Step 4: Reverse Proxy & SSL (Nginx)

### 4.1 Install Nginx + Certbot

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### 4.2 Configure Nginx

Create `/etc/nginx/sites-available/magnetarstudio`:

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL security (Mozilla intermediate configuration)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS (already set by MagnetarStudio, but Nginx adds preload)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security headers (MagnetarStudio sets these, Nginx adds defense in depth)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to MagnetarStudio backend
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Preserve client information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Rate limiting (defense in depth - MagnetarStudio has its own)
        limit_req zone=api burst=20 nodelay;
    }

    # Metrics endpoint (optional, restrict access)
    location /metrics {
        proxy_pass http://127.0.0.1:9090;

        # Restrict to internal networks only
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
    }
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/magnetarstudio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4.3 Obtain SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (certbot creates this automatically)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Step 5: Verification & Testing (10 minutes)

### 5.1 Health Check

```bash
# Check application is running
curl -k https://yourdomain.com/api/health
# Expected: {"status": "healthy"}

# Check security headers
curl -I https://yourdomain.com | grep -E "Strict-Transport|X-Content-Type|X-Frame"
# Expected: All OWASP headers present

# Check authentication (should be rejected)
curl -X POST https://yourdomain.com/api/v1/vault/files
# Expected: 401 Unauthorized
```

### 5.2 Security Scan

```bash
# OWASP ZAP baseline scan (optional, 2 hours)
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://yourdomain.com

# SSL Labs scan
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
# Expected: A+ rating

# Security headers check
# Visit: https://securityheaders.com/?q=yourdomain.com
# Expected: A rating
```

### 5.3 Functional Testing

```bash
# Login test
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "founder",
    "password": "<your-founder-password>",
    "device_fingerprint": "test-device"
  }'
# Expected: JWT token + refresh token

# Token refresh test (use token from above)
curl -X POST https://yourdomain.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh-token-from-login>"}'
# Expected: New JWT token
```

---

## Step 6: Monitoring & Maintenance

### 6.1 Database Maintenance

MagnetarStudio automatically runs weekly VACUUM maintenance. Verify:

```bash
# Check logs for VACUUM operations
sudo journalctl -u magnetarstudio | grep VACUUM
# Expected: "VACUUMed auth database" weekly
```

### 6.2 Connection Pool Monitoring

```bash
# Check connection pool stats (via logs)
sudo journalctl -u magnetarstudio | grep "connection pool"
# Expected: Healthy pool with 2-10 connections
```

### 6.3 Security Monitoring

```bash
# Check for anomaly detections
sudo journalctl -u magnetarstudio | grep "anomaly detected"

# Check for breach detection attempts
sudo journalctl -u magnetarstudio | grep "breach"

# Check for input sanitization triggers
sudo journalctl -u magnetarstudio | grep "Dangerous.*pattern"
```

### 6.4 Prometheus Metrics (Optional)

Access metrics at `http://localhost:9090/metrics`:

```
# Key metrics to monitor:
magnetar_http_requests_total
magnetar_http_request_duration_seconds
magnetar_db_connections_active
magnetar_auth_sessions_active
magnetar_breach_checks_total
```

---

## Troubleshooting

### Issue: CORS Errors

**Symptom:** Browser shows "CORS policy blocked"

**Solution:**
```bash
# Verify ELOHIM_CORS_ORIGINS in .env
echo $ELOHIM_CORS_ORIGINS
# Should include your domain: https://yourdomain.com

# Restart application
sudo systemctl restart magnetarstudio
```

### Issue: Database Locked Errors

**Symptom:** "database is locked" errors in logs

**Solution:**
```bash
# Verify connection pooling is enabled
python3 -c "from api.db_pool import get_connection_pool; print('Pool active')"

# Check WAL mode
sqlite3 /var/lib/magnetarstudio/auth.db "PRAGMA journal_mode"
# Should return: wal
```

### Issue: High Memory Usage

**Symptom:** Server using >2GB RAM

**Solution:**
```bash
# Reduce uvicorn workers
# Edit /etc/systemd/system/magnetarstudio.service
# Change: --workers 4 -> --workers 2

sudo systemctl daemon-reload
sudo systemctl restart magnetarstudio
```

### Issue: Token Expiration Errors

**Symptom:** Clients getting 401 after 1 hour

**Expected Behavior:** This is normal (MED-05 enhancement)

**Solution:** Frontend should implement auto-refresh:
```javascript
// When token expires, call /api/v1/auth/refresh
const response = await fetch('/api/v1/auth/refresh', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({refresh_token: storedRefreshToken})
});
```

---

## Security Checklist

Before going live, verify:

- [ ] Git history purged (no secrets in `git log -S`)
- [ ] Production `.env` with strong secrets (32+ char random)
- [ ] CORS origins whitelisted (not `*`)
- [ ] HTTPS enforced (no HTTP traffic)
- [ ] SSL certificate valid (A+ on SSL Labs)
- [ ] Firewall configured (only 80, 443 open)
- [ ] Database files owned by app user (not root)
- [ ] `.env` file permissions 600 (not readable by others)
- [ ] Systemd security hardening enabled
- [ ] Monitoring/alerting configured
- [ ] Backup strategy implemented (daily snapshots)
- [ ] Disaster recovery tested

---

## Performance Tuning

### Connection Pool Optimization

Adjust based on load:

```python
# apps/backend/api/db_pool.py (line 20-21)
DEFAULT_MIN_CONNECTIONS = 5  # Increase for high traffic
DEFAULT_MAX_CONNECTIONS = 20  # Increase for very high traffic
```

### Uvicorn Workers

Formula: `(2 × CPU cores) + 1`

```bash
# For 4-core server:
--workers 9

# For 8-core server:
--workers 17
```

### Rate Limiting

Adjust based on expected traffic:

```python
# Current: 100 requests/minute global
# For high-traffic sites, increase to 500-1000/min
```

---

## Backup Strategy

### Automated Daily Backups

Create `/etc/cron.daily/magnetar-backup`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/magnetarstudio"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup SQLite databases
cp /var/lib/magnetarstudio/auth.db $BACKUP_DIR/auth-$DATE.db
cp /var/lib/magnetarstudio/data.db $BACKUP_DIR/data-$DATE.db

# Backup encrypted audit logs
cp /var/lib/magnetarstudio/encrypted_audit.db $BACKUP_DIR/audit-$DATE.db

# Compress
tar -czf $BACKUP_DIR/magnetar-$DATE.tar.gz $BACKUP_DIR/*-$DATE.db
rm $BACKUP_DIR/*-$DATE.db

# Keep last 30 days
find $BACKUP_DIR -name "magnetar-*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: magnetar-$DATE.tar.gz"
```

Make executable:
```bash
sudo chmod +x /etc/cron.daily/magnetar-backup
```

---

## Production Deployment Complete! 🎉

Your MagnetarStudio instance is now:
- ✅ Secured with enterprise-grade authentication
- ✅ Protected with OWASP security headers
- ✅ Encrypted with SSL/TLS
- ✅ Monitored with comprehensive logging
- ✅ Backed up daily
- ✅ Ready for production traffic

**Next Steps:**
1. Monitor logs for first 24 hours
2. Set up alerting for anomalies
3. Create runbook for common operations
4. Train team on security features

---

**Questions?** Check documentation:
- SECURITY_FIXES.md - Security implementation details
- FINAL_STATUS_REPORT.md - Complete security assessment
- SESSION_SUMMARY.md - All features and changes
