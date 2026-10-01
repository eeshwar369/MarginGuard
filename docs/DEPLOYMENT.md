# Deploying the complete product

The app is packaged as a single service. A persistent disk is required. Do not deploy its SQLite database on an ephemeral/serverless filesystem or run multiple replicas.

## Local run

1. Install Python 3.12+, Node 22, and uv.
2. Run `uv sync --frozen` in the repository root.
3. In `web`, run `npm ci` then `npm run build`.
4. Copy `.env.example` to `.env` and set `MG_APP_ORIGIN=http://127.0.0.1:8000`.
5. Run `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` from the repository root.
6. Open `http://127.0.0.1:8000`. Use **Explore the live workspace** for an isolated sample, or register a private account.

For frontend development, run the API on port 8000 and `npm run dev` in `web`. Set the app origin to `http://127.0.0.1:3000`. The development proxy keeps cookies and API requests on the same browser origin.

## Render blueprint (prepared; not deployed)

The included `render.yaml` uses a paid `1c-2g` service and a 1 GB persistent disk. Review current hosting charges in your account before deploying. No hosting purchase has been made by this project. Configuration references: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [persistent disks](https://render.com/docs/disks), and [Docker deployment](https://render.com/docs/docker).

1. Publish this repository to your GitHub account, then create a Render Blueprint from it.
2. Set `MG_APP_ORIGIN` to the **exact final HTTPS origin**, without a trailing path. This is required for CSRF protection. If the assigned hostname is unknown, set it after Render assigns the service URL and before opening it to users.
3. Set `MG_GEMINI_API_KEY` in the hosting secret environment, or leave it empty for verified deterministic mode. Do not commit it. The configured model is `gemini-2.5-flash`.
4. Keep `MG_ENV=production`, `MG_COOKIE_SECURE=true`, one instance, and the disk mount `/var/lib/marginguard`.
5. Verify `/api/health`, then test demo creation, data import, evidence, an investigation, decision approval, and PDF download from the public URL.
6. With a real AI key, consent to AI planning and verify that the run says **ai**, records model tokens, and does not silently fall back. Local tests cover a mocked provider and failure injection, not a real provider call.

TLS termination and network perimeter are hosting responsibilities. Terminate HTTPS before the application and restrict direct backend exposure. If adding a CDN/reverse proxy, configure its body-size limit to 25 MB and rate limits for authentication and demo creation. Verify client-IP forwarding for the chosen platform.

## Docker

`docker compose up --build` starts a local-only service at port 8000 with a persistent named volume. For an internet deployment, use production environment values and HTTPS termination. The runtime runs as UID 10001. Ensure the mounted disk is writable by that UID. The container definition is provided; a local container build was not run because the Docker daemon was stopped on the build machine.

## Backup and restore

Run `uv run python scripts/backup.py --database /absolute/path/marginguard.sqlite3 --destination /secure/backup/path`. The script uses SQLite's backup API and integrity checks the result. Protect and encrypt backups at the storage layer; they contain account and business data. The development filesystem is not encrypted by this application.

Schedule off-service backups, define retention, and test restoration. To restore, stop the service, retain the current database and its WAL/SHM files for rollback, place the verified backup at the configured database path with the correct owner, and start a single service process. Never overwrite a running SQLite database.

## Operational limits and remaining launch work

- 8 MB and 50,000 rows per CSV, three files per import; 30 retained versions per workspace.
- 20 investigation starts per workspace per hour; model timeout 35 seconds.
- Demo accounts expire after 48 hours; accounts older than three days are purged on application startup.
- No email verification, self-service password reset, team invitations, separate approver role, SSO, billing, ERP connectors, or automated store changes in this release.
- Configure monitoring, backup scheduling, a support/contact policy, data retention, and an independent security review before onboarding real businesses at scale.
- Local automated verification is not a substitute for load testing the deployed service and confirming hosting-specific proxy, disk, and recovery behavior.
