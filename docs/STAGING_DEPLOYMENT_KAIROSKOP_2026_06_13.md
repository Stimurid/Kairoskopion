# Staging Deployment Note — kairoskop.mindkampf.ru

**Date:** 2026-06-13
**Deployed by:** Claude Code (operator: Timur Shchukin)
**Status:** LIVE (staging, password-protected)

---

## Infrastructure

| Item | Value |
|------|-------|
| Domain | `kairoskop.mindkampf.ru` |
| Server | `81.26.176.248` (`moderbober-prod-01`) |
| SSH user | `deploy` |
| App directory | `/opt/kairoskopion/app` |
| Venv | `/opt/kairoskopion/app/.venv` |
| Env file | `/opt/kairoskopion/secrets/kairoskopion.env` |
| Systemd service | `kairoskopion-api.service` |
| Backend port | 8088 (uvicorn, `0.0.0.0`) |
| Reverse proxy | Caddy in Docker (`moderbober-caddy`) |
| TLS | Auto (Let's Encrypt, via Caddy) |
| Access control | Basic auth (`timur` / bcrypt hash) |

## Deployed Version

| Item | Value |
|------|-------|
| Git ref | `458e1ff` (main) |
| Tag | `v0.2.0-alpha-rc16` (deployed commit) |
| Prior tag | `v0.2.0-alpha-rc15` at `1bcc2c9` (superseded; SPA serving added after it) |
| Backend version | `0.2.0-alpha` |
| pyproject.toml | `0.2.0a15` |

## Browser Smoke Test

Status: **pending** — to be performed by operator (Timur).
Basic auth password is not known to the deployment agent.

See checklist below:

1. Open `https://kairoskop.mindkampf.ru`
2. Enter basic auth credentials for user `timur`
3. Confirm app loads (not blank page)
4. Create a new case
5. Submit a short article/abstract
6. Confirm ArticleCard renders
7. Click an evidence badge → confirm EvidenceDrawer opens
8. Press Escape → confirm EvidenceDrawer closes
9. Open Scenario stage → confirm ScenarioBuilder renders
10. Open Pathways stage → confirm PathwayMap renders
11. Open Venue Pool stage → confirm VenuePoolBoard renders
12. Open Adaptation stage → confirm AdaptationStudio renders
13. Open Dossier stage → confirm DossierView renders
14. Open browser console (F12) → confirm no red errors

## Architecture

```
Internet → Caddy (Docker, HTTPS + basic_auth)
         → host.docker.internal:8088
         → uvicorn (systemd, FastAPI)
           ├── /health, /cases, /cases/{id}/... (API)
           └── /* (SPA static files from ui/dist/)
```

Single-port deployment: FastAPI serves both API endpoints and the built React SPA.
No separate static file server or Caddy file_server needed.

## Files on Server

- `/etc/systemd/system/kairoskopion-api.service` — systemd unit
- `/opt/kairoskopion/secrets/kairoskopion.env` — env (CORS origins)
- `/opt/moderbober/Caddyfile` — kairoskop.mindkampf.ru block appended
- `/opt/kairoskopion/app/` — git clone of Kairoskopion repo

## UFW Rule

```
8088/tcp ALLOW IN 172.18.0.0/16  # kairoskopion: caddy->host
```

Docker Caddy container is on `moderbober_default` network (`172.18.0.0/16`).
`host.docker.internal` resolves to `172.17.0.1` (default bridge gateway).
Traffic from `172.18.0.x` → `172.17.0.1:8088` traverses host routing — UFW must allow it.

## Smoke Test Results (2026-06-13)

| Test | Result |
|------|--------|
| DNS resolves to 81.26.176.248 | PASS |
| HTTPS + valid TLS | PASS |
| Unauthenticated → 401 | PASS |
| `/health` → `{"status":"ok","version":"0.2.0-alpha"}` | PASS |
| SPA serves `index.html` | PASS |
| `GET /cases` → `[]` | PASS |
| `POST /cases` creates case | PASS |
| `DELETE /cases/{id}` removes case | PASS |
| systemd service active | PASS |
| Frontend build present | PASS |
| Caddy container running | PASS |

## Known Limitations / Public-Prod Blockers

- **In-memory storage** — all cases lost on service restart.
- **Basic auth only** — no production authentication.
- **No database** — not production-ready.
- **No job queue** — synchronous only.
- **LLM integration off** — deterministic fallbacks active by default.
- **Single-worker uvicorn** — no horizontal scaling.
- **Staging/operator preview only** — not a public product.

## Update Procedure

```bash
ssh deploy@81.26.176.248
cd /opt/kairoskopion/app
git fetch origin
git checkout <new-tag-or-commit>
source .venv/bin/activate
pip install -e ".[api]"
cd ui && npm ci && npx vite build && cd ..
sudo systemctl restart kairoskopion-api
curl http://127.0.0.1:8088/health
```

## Rollback

```bash
ssh deploy@81.26.176.248
cd /opt/kairoskopion/app
sudo systemctl stop kairoskopion-api
git checkout 458e1ff   # current known-good
source .venv/bin/activate
pip install -e ".[api]"
sudo systemctl start kairoskopion-api
```
