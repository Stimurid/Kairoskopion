# Staging Deployment Plan — Kairoskopion UI Cockpit v0

**Version:** v0.2.0-alpha-rc15
**Date:** 2026-06-13
**Status:** PLAN (not yet deployed)

> **This is an operator/staging preview, NOT a public product.**
> Access MUST be restricted. No public-facing deployment.

---

## Architecture

```
Internet
  │
  ├─ (blocked by IP allowlist / basic auth)
  │
  ▼
Caddy (reverse proxy, HTTPS via Let's Encrypt)
  │
  ├── /api/*  →  localhost:8000  (uvicorn + FastAPI)
  ├── /       →  localhost:5173  (Vite dev) OR static files (production build)
  │
  ▼
Server (single VPS, e.g. kairon-staging.shchuk.in)
```

---

## 1. Prerequisites

| Item | Requirement |
|------|-------------|
| Server | VPS with ≥1 GB RAM, Ubuntu 22.04+ or Debian 12+ |
| Python | ≥3.11 |
| Node.js | ≥18 (for UI build) |
| Caddy | v2.x (auto HTTPS) |
| Domain | Subdomain pointing to VPS IP (e.g. `kairon-staging.shchuk.in`) |
| DNS | A record → VPS IP |
| Git | Repository cloned at `/opt/kairoskopion` |

---

## 2. Server Setup

### 2.1 Clone and install

```bash
# Clone
cd /opt
git clone https://github.com/Stimurid/Kairoskopion.git kairoskopion
cd kairoskopion
git checkout v0.2.0-alpha-rc15

# Python backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# UI build (production)
cd ui
npm ci
npx vite build   # → ui/dist/
cd ..
```

### 2.2 Environment file

Create `/opt/kairoskopion/.env`:

```bash
# API
KAIROSKOPION_STORAGE_ROOT=/opt/kairoskopion/.kairoskopion
HOST=127.0.0.1
PORT=8000

# LLM (optional, leave empty for deterministic-only)
# KAIROSKOPION_LLM_BASE_URL=
# KAIROSKOPION_LLM_API_KEY=
# KAIROSKOPION_LLM_MODEL=

# UI (only needed if running Vite dev server, not for production build)
# VITE_API_URL=https://kairon-staging.shchuk.in/api
```

### 2.3 Verify local

```bash
source .venv/bin/activate
pytest                                    # 1275 tests pass
uvicorn kairoskopion.api.app:app --host 127.0.0.1 --port 8000 &
curl http://localhost:8000/health          # {"status":"ok","version":"0.2.0-alpha"}
kill %1
```

---

## 3. Systemd Services

### 3.1 Backend: `/etc/systemd/system/kairon-api.service`

```ini
[Unit]
Description=Kairoskopion API (staging)
After=network.target

[Service]
Type=simple
User=kairon
Group=kairon
WorkingDirectory=/opt/kairoskopion
EnvironmentFile=/opt/kairoskopion/.env
ExecStart=/opt/kairoskopion/.venv/bin/uvicorn kairoskopion.api.app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --log-level info
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.2 Enable and start

```bash
sudo useradd -r -s /bin/false kairon
sudo chown -R kairon:kairon /opt/kairoskopion

sudo systemctl daemon-reload
sudo systemctl enable kairon-api
sudo systemctl start kairon-api
sudo systemctl status kairon-api
```

---

## 4. Caddy Configuration

### 4.1 Caddyfile: `/etc/caddy/Caddyfile`

```caddyfile
kairon-staging.shchuk.in {
    # --- Access restriction (choose ONE) ---

    # Option A: IP allowlist (recommended for single-operator staging)
    @blocked not remote_ip <YOUR_IP>/32
    respond @blocked 403

    # Option B: Basic auth (if multiple operators need access)
    # basicauth /* {
    #     operator $2a$14$HASHED_PASSWORD_HERE
    # }

    # --- API proxy ---
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy localhost:8000
    }

    # --- Health check (no auth) ---
    handle /health {
        reverse_proxy localhost:8000
    }

    # --- Static frontend ---
    handle {
        root * /opt/kairoskopion/ui/dist
        try_files {path} /index.html
        file_server
    }

    # --- Headers ---
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    # --- Logging ---
    log {
        output file /var/log/caddy/kairon-staging.log
        format console
    }
}
```

### 4.2 CORS note

The FastAPI app currently allows all origins (`allow_origins=["*"]`). Behind Caddy with IP restriction, this is acceptable for staging. For any broader access, tighten CORS to the staging domain only:

```python
# In src/kairoskopion/api/app.py
allow_origins=["https://kairon-staging.shchuk.in"]
```

### 4.3 Enable Caddy

```bash
sudo systemctl enable caddy
sudo systemctl restart caddy
```

Caddy auto-provisions HTTPS via Let's Encrypt.

---

## 5. DNS

| Record | Type | Value |
|--------|------|-------|
| `kairon-staging.shchuk.in` | A | `<VPS_IP>` |

---

## 6. Deployment Checklist

```
[ ] VPS provisioned, SSH access confirmed
[ ] DNS A record pointing to VPS IP
[ ] Python 3.11+ installed
[ ] Node.js 18+ installed
[ ] Caddy v2 installed
[ ] Repository cloned at /opt/kairoskopion
[ ] Checked out v0.2.0-alpha-rc15
[ ] .env created (no secrets in git)
[ ] Python venv created, pip install -e ".[dev]"
[ ] pytest passes (1275 tests)
[ ] UI built (npm ci && npx vite build)
[ ] kairon user created
[ ] kairon-api.service installed and running
[ ] Caddyfile configured with IP restriction
[ ] HTTPS certificate provisioned (automatic)
[ ] curl https://kairon-staging.shchuk.in/health returns ok
[ ] Browser: UI loads, can create case, intake text, walk pipeline
```

---

## 7. Update / Rollback

### Update to new tag

```bash
cd /opt/kairoskopion
sudo systemctl stop kairon-api
git fetch origin
git checkout <new-tag>
source .venv/bin/activate
pip install -e ".[dev]"
cd ui && npm ci && npx vite build && cd ..
pytest
sudo systemctl start kairon-api
sudo systemctl restart caddy
```

### Rollback

```bash
cd /opt/kairoskopion
sudo systemctl stop kairon-api
git checkout v0.2.0-alpha-rc15   # or previous known-good tag
source .venv/bin/activate
pip install -e ".[dev]"
cd ui && npm ci && npx vite build && cd ..
sudo systemctl start kairon-api
```

---

## 8. Monitoring

| What | How |
|------|-----|
| API health | `curl https://kairon-staging.shchuk.in/health` |
| API logs | `journalctl -u kairon-api -f` |
| Caddy logs | `tail -f /var/log/caddy/kairon-staging.log` |
| Disk | `df -h /opt/kairoskopion` |

---

## 9. Security Summary

| Concern | Status |
|---------|--------|
| HTTPS | Caddy auto-TLS via Let's Encrypt |
| Access restriction | IP allowlist or basic auth in Caddyfile |
| No secrets in git | .env in .gitignore, .env.example has placeholders only |
| No node_modules in git | .gitignore covers ui/node_modules/ |
| No dist in git | .gitignore covers ui/dist/ |
| No .claude/ in git | .gitignore covers .claude/ |
| CORS | Allow all (acceptable behind IP restriction); tighten for broader access |
| Auth | None in app — relies on reverse proxy restriction |
| Persistence | In-memory only — restarts lose state |
| Database | None — not production-ready |
| Job queue | None — synchronous only |

---

## 10. What This Is NOT

- **Not a production deployment.** No database, no auth, no job queue.
- **Not public-facing.** Must be IP-restricted or auth-gated.
- **Not a public product claim.** UI Cockpit v0 is an operator staging preview.
- **Deterministic fallbacks still active.** LLM integration is optional and off by default.
- **State is ephemeral.** Restarting the API loses all in-memory cases.
