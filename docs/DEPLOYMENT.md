# Deploying the complete product

The app is packaged as a single service. **Render Free + Neon Free PostgreSQL** keeps accounts, imported snapshots, investigations, memos, and audit history outside Render's temporary filesystem. Local development can still use SQLite. Keep one application instance/process because investigation execution and restart recovery are not a distributed job system.

## Local run

1. Install Python 3.12+, Node 22, and uv.
2. Run `uv sync --frozen` in the repository root.
3. In `web`, run `npm ci` then `npm run build`.
4. Copy `.env.example` to `.env` and set `MG_APP_ORIGIN=http://127.0.0.1:8000`.
5. Run `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` from the repository root.
6. Open `http://127.0.0.1:8000`. Use **Explore the live workspace** for an isolated sample, or register a private account.

For frontend development, run the API on port 8000 and `npm run dev` in `web`. Set the app origin to `http://127.0.0.1:3000`. The development proxy keeps cookies and API requests on the same browser origin.

## Free Render + Neon deployment

The included `render.yaml` selects **Render Free**, with no paid disk. A separate Neon PostgreSQL database supplies durable storage. Stay on each provider's Free plan. No paid resource is required by this blueprint. See [Render Free limitations](https://render.com/docs/free), [Neon plans](https://neon.com/pricing), and [the Blueprint specification](https://render.com/docs/blueprint-spec).

1. Sign in to [Neon](https://console.neon.tech/signup). Create a **Free** project named `marginguard`; select Singapore if offered to match the Render region. No extra auth or object-storage product is needed.
2. In Neon, click **Connect**, enable connection pooling, and copy the PostgreSQL connection string. Keep its password and `sslmode=require` (or stricter) query parameter intact. This string is a secret, not a public database URL to share in the submission.
3. Open [Deploy MarginGuard on Render](https://render.com/deploy?repo=https://github.com/eeshwar369/MarginGuard). Connect the supplied GitHub repository, use the root `render.yaml`, and confirm the service plan is **Free** with no disk or paid add-on.
4. Paste the Neon string into **`MG_DATABASE_URL`** and a Gemini key into **`MG_GEMINI_API_KEY`**, then deploy. If using deterministic mode initially, omit the Gemini variable and add it later in **Environment**. Never commit either secret or include them in the presentation.
5. The app reads Render's assigned HTTPS URL automatically from `RENDER_EXTERNAL_URL`. Do not copy the local `.env` file into Render. Only set `MG_APP_ORIGIN` yourself when using a custom domain; use its exact HTTPS origin without a path.
6. Keep `MG_ENV=production`, `MG_COOKIE_SECURE=true`, and one instance. Database tables initialize on startup. The free-service defaults cap each CSV at **4 MB / 10,000 rows** to reduce memory pressure.
7. Verify `/api/health`, then test demo creation, data import, evidence, an investigation, decision approval, and PDF download. Create a private account, save data, restart/redeploy the service, sign in again, and confirm its records remain available.
8. With a real AI key, consent to AI planning and verify that the run says **ai**, records model tokens, and does not silently fall back. Mocked provider tests do not verify a real provider call.

Render's Free service sleeps after inactivity and can take around a minute to wake. Neon also suspends idle compute while retaining data. Neon Free currently includes 0.5 GB storage and monthly compute/network quotas; reaching a quota can block access or writes until the quota resets or space is freed. This is a bounded free deployment, not a claim of unlimited capacity or always-on availability. Check current limits in both dashboards before judging. Do not use artificial keep-alive traffic to evade free-tier limits.

The local SQLite database is not automatically copied into Neon. A fresh cloud deployment starts with a fresh database; existing local records remain untouched. Sample demo accounts still expire and are cleaned up by the application's documented retention policy. Use a registered account when demonstrating long-term persistence.

## Gemini key

Open [Google AI Studio API keys](https://aistudio.google.com/apikey), sign in, and choose **Create API key** in a new or existing project. Set it as `MG_GEMINI_API_KEY` in Render's **Environment** page and deploy the environment change. The configured `gemini-2.5-flash` has a free usage tier with rate limits, not unlimited requests. Check [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing) and the project's tier before enabling billing. Free-tier content can be used to improve Google's products; use synthetic data for the public demo.

TLS termination and network perimeter are hosting responsibilities. Terminate HTTPS before the application and restrict direct backend exposure. If adding a CDN/reverse proxy, configure its body-size limit to 25 MB and rate limits for authentication and demo creation. Verify client-IP forwarding for the chosen platform.

## Docker

`docker compose up --build` starts a local-only service at port 8000 with a persistent named volume. For an internet deployment, use production environment values and HTTPS termination. The runtime runs as UID 10001. Ensure the mounted disk is writable by that UID. The Linux container builds successfully. PostgreSQL deployments do not need a mounted application disk; SQLite deployments still do.

## Backup and restore

For SQLite, run `uv run python scripts/backup.py --database /absolute/path/marginguard.sqlite3 --destination /secure/backup/path`. The script uses SQLite's backup API and integrity checks the result. For Neon/PostgreSQL use `pg_dump` with a **direct** connection and Neon-supported snapshot/restore features; the SQLite utility does not back up PostgreSQL. Protect and encrypt backups at the storage layer; they contain account and business data. The development filesystem is not encrypted by this application.

Schedule off-service backups, define retention, and test restoration. To restore, stop the service, retain the current database and its WAL/SHM files for rollback, place the verified backup at the configured database path with the correct owner, and start a single service process. Never overwrite a running SQLite database.

## Operational limits and remaining launch work

- Local defaults: 8 MB and 50,000 rows per CSV. Free Render blueprint: 4 MB and 10,000 rows per CSV. Three files per import; 30 retained versions per workspace.
- 20 investigation starts per workspace per hour; model timeout 35 seconds.
- Demo accounts expire after 48 hours; accounts older than three days are purged on application startup.
- No email verification, self-service password reset, team invitations, separate approver role, SSO, billing, ERP connectors, or automated store changes in this release.
- Configure monitoring, backup scheduling, a support/contact policy, data retention, and an independent security review before onboarding real businesses at scale.
- Local automated verification is not a substitute for load testing the deployed service and confirming hosting-specific proxy, disk, and recovery behavior.
