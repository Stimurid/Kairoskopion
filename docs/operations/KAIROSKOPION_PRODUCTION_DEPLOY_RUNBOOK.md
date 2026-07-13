# Kairoskopion Production Deploy Runbook

**Last updated:** 2026-06-24
**Status:** LIVE (staging/operator preview)

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
| Access control | Basic auth (`timur` / bcrypt hash in Caddyfile) |
| Repo | `Stimurid/Kairoskopion` |
| Branch policy | prod follows `main` |

## Health Checks

| Check | Command |
|-------|---------|
| Local (on VM) | `curl http://127.0.0.1:8088/health` |
| External | `curl https://kairoskop.mindkampf.ru/health` (requires basic auth) |

**Note:** `/health` does not expose the git commit hash. To verify the deployed commit, check on the VM:

```bash
ssh deploy@81.26.176.248
cd /opt/kairoskopion/app && git log --oneline -1
```

## Deploy Procedure

```bash
ssh deploy@81.26.176.248
cd /opt/kairoskopion/app
git fetch origin
git pull origin main
source .venv/bin/activate
pip install -e '.[api]'
cd ui && npm ci && npx vite build && cd ..
sudo systemctl restart kairoskopion-api
curl http://127.0.0.1:8088/health
```

### SSH Access Status

> **Canonical policy:** `docs/operations/ACCESS_AND_TRANSPORT_POLICY.md`

`SSH_POLICY=DISABLED_BY_DEFAULT` · `SSH_AUTOMATIC_RETRY_LIMIT=0`

SSH, SCP, SFTP, port-22 are **disabled**. Do not probe, retry, or increase
timeout. The deploy and rollback procedures above are **historical references
only** — they require SSH and cannot be executed under current policy.

Status when deploy is blocked: `RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT`.
~~`DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR`~~ — deprecated.

## Rollback

```bash
ssh deploy@81.26.176.248
cd /opt/kairoskopion/app
sudo systemctl stop kairoskopion-api
git checkout <known-good-commit>
source .venv/bin/activate
pip install -e '.[api]'
cd ui && npm ci && npx vite build && cd ..
sudo systemctl start kairoskopion-api
curl http://127.0.0.1:8088/health
```

## Environment Variables

Env vars are loaded by systemd from `/opt/kairoskopion/secrets/kairoskopion.env`.

**Do not print, log, or commit secrets.** The env file contains LLM API keys (302.ai proxy) and CORS config. It is NOT in the git repo.

The FastAPI app also has a `.env` loader (`_load_dotenv_if_present()` in `app.py`) that reads `.env` in the working directory. On prod, systemd's `EnvironmentFile=` takes precedence.

Key env vars used on prod:
- `KAIROSKOPION_LLM_BASE_URL` — LLM proxy URL
- `KAIROSKOPION_LLM_API_KEY` — LLM API key
- `KAIROSKOPION_LLM_MODEL` — model identifier
- `KAIROSKOPION_DATA_DIR` — user data directory
- `KAIROSKOPION_LOG_DIR` — log file directory
- `KAIROSKOPION_CORS_ORIGINS` — allowed CORS origins

## Evidence Packs — Deployment Requirement

All venue evidence packs **must** live in `data/venue_evidence_packs/` (tracked by git). The runtime resolver scans only this directory.

`private_inputs/` is in `.gitignore` and does **not** exist on prod. Any evidence pack that lives only in `private_inputs/` will fail to resolve after deployment.

Current Top 5 packs (all tracked):
1. `logos_evidence_pack.md` — Логос (ISSN 0869-5377)
2. `voprosy_filosofii_evidence_pack.md` — Вопросы философии (ISSN 0042-8744)
3. `filosofskiy_zhurnal_evidence_pack.md` — Философский журнал (ISSN 2072-0726)
4. `epistemologiya_i_filosofiya_nauki_evidence_pack.md` — Эпистемология и ФН (ISSN 1811-833X)
5. `tsifrovoy_ucheny_evidence_pack.md` — Цифровой ученый (ISSN 2618-9267)

## Architecture (Single-Port)

```
Internet → Caddy (Docker, HTTPS + basic_auth)
         → host.docker.internal:8088
         → uvicorn (systemd, FastAPI)
           ├── /health, /auth/*, /cases/* (API)
           └── /* (SPA static files from ui/dist/)
```

Single-port deployment: FastAPI serves both API endpoints and the built React SPA.

## Recovery Checklist

If SSH config is lost or deploy path is forgotten:

1. Server: `81.26.176.248`
2. User: `deploy`
3. App: `/opt/kairoskopion/app`
4. Service: `kairoskopion-api.service`
5. This runbook: `docs/operations/KAIROSKOPION_PRODUCTION_DEPLOY_RUNBOOK.md`
6. Legacy deploy note: `docs/STAGING_DEPLOYMENT_KAIROSKOP_2026_06_13.md`

## Smoke Test Scripts

Temporary smoke scripts (untracked, not committed):

- `_smoke2.py` — case flow venue selection probe (direct Python)
- `_smoke3.py` — RiskOfficer direct probe (no env vars outside systemd)
- `_smoke3_http.py` — full API smoke via HTTP (auth, intake, venue, fit, risk, dossier)

To run HTTP smoke on prod:

> **⚠ DEPRECATED** — the `scp`/`ssh` commands below require SSH, which is
> disabled under current policy. Use the HTTP API directly from any machine
> that can reach `kairoskop.mindkampf.ru`.

```bash
# DEPRECATED — SSH disabled
# scp _smoke3_http.py deploy@81.26.176.248:/opt/kairoskopion/app/
# ssh deploy@81.26.176.248
# cd /opt/kairoskopion/app
# source .venv/bin/activate
# python _smoke3_http.py
```
