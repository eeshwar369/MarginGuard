# MarginGuard

**Investigate margin changes. Stress-test the next move. Approve the exact evidence.**

Built by **Genztech** for **PS-04: AI Decision Engine for Business Data**. Team leader and member: **Baleeshwar Palavadi** · [LinkedIn](https://www.linkedin.com/in/eeshwar369/).

MarginGuard is a working single-instance product for a small retail operator who needs to explain contribution-margin erosion and compare possible actions. It turns orders, refunds, and fulfilment costs into an inspectable ledger, evidence-linked investigations, sensitivity analyses, and versioned decision memos.

**[Open the live product](https://marginguard-genztech.onrender.com)** · [Source repository](https://github.com/eeshwar369/MarginGuard)

The public service runs on Render Free with durable Neon PostgreSQL storage. It can take around a minute to wake after inactivity.

![MarginGuard workspace](docs/images/overview.png)

## Deploy with free persistent storage

[Deploy on Render](https://render.com/deploy?repo=https://github.com/eeshwar369/MarginGuard) using the included Free blueprint and a separate [Neon Free PostgreSQL](https://console.neon.tech/signup) database. Set the private Neon connection string as `MG_DATABASE_URL` and the optional Gemini key as `MG_GEMINI_API_KEY` in Render. The app automatically uses its assigned HTTPS origin.

Accounts, datasets, checkpoints, and decisions stay in PostgreSQL across Render restarts. Free services have cold starts and usage quotas; this is not unlimited or always-on hosting. Follow the [deployment guide](docs/DEPLOYMENT.md) for setup and the persistence check. Local development defaults to SQLite when no database URL is set.

## Try it locally

```sh
uv sync --frozen
cd web
npm ci
npm run build
cd ..
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** and choose **Explore the live workspace**. The default development configuration allows this origin. Every visitor receives a separate demo account with clearly labeled synthetic data. No external AI key is needed to inspect and test the deterministic product flows.

For AI planning, copy `.env.example` to `.env`, set `MG_GEMINI_API_KEY` locally, and restart the service. Consent is required before sending a question and numerical summaries to Gemini. Without a key, the interface explicitly identifies verified deterministic analysis. A real Gemini 3.5 Flash-Lite investigation completed on the public service, recorded 415 model tokens, and correctly contradicted the sample discount hypothesis. All three browser journeys also passed against the public deployment. See the [verification record](docs/VERIFICATION.md).

## What is implemented

- **Data reconciliation:** matched CSV imports, strict money/date/key validation, pre-aggregated refunds, duplicate quarantine, blocking errors, immutable dataset versions, and source hashes.
- **Investigations:** a four-stage LangGraph workflow, typed bounded Gemini tool selection when configured, supported/contradicted/unresolved results, deterministic verification, execution traces, and restart recovery from saved checkpoints.
- **Evidence explorer:** exact formulas and SQL, literal search, pagination, source-row references, raw normalized CSV exports, and cost corrections with a reason and optimistic concurrency checks.
- **Decision lab:** discount and shipping alternatives, explicit demand/return-cost bounds, implementation costs, a continuous break-even approximation, whole-order scenario totals, and recommendations based on downside contribution.
- **Decision records:** human acknowledgement and approval tied to data and scenario hashes; stale approvals after input changes; retained approval history; PDF and JSON exports.
- **Product controls:** private accounts, scrypt passwords, HTTP-only sessions, CSRF and origin protection, resource isolation, request/import limits, persistent rate limits, production CSP, audit events, and responsive layouts.

## Judge walkthrough

1. Open the sample. September revenue rises **4.3%** while contribution margin falls **18.1%**.
2. Inspect **Discounts increased**. Follow the formula and source rows instead of accepting a narrative on trust.
3. Ask **“Did discounts decrease?”**. The numerical evidence contradicts that hypothesis.
4. In Decision lab, change maximum extra return cost per order from **₹4 to ₹20**. The recommendation changes from shipping savings to keeping the current policy.
5. Restore ₹4, create a memo, review assumptions, approve, and download its PDF.
6. Correct a cost in Evidence explorer. The data version changes and the old memo becomes **stale**.
7. Load the quality challenge. An identical refund is quarantined; investigations and scenarios remain blocked until acknowledgement.

All sample business numbers are synthetic. No customer adoption, realized savings, causal demand estimate, or calibrated model confidence is claimed.

## Verification

```sh
uv run ruff check app tests scripts
uv run pytest -q
uv run python -m scripts.benchmark
cd web
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser tests expect a running app at port 8000. On Windows, `MG_BROWSER_PATH` may point to an installed Chrome executable. See [verification results](docs/VERIFICATION.md) for measured results and limits. The [CI workflow](.github/workflows/ci.yml) builds the frontend, tests the backend, starts the server, and exercises the browser journeys.

## Architecture and deployment

| Layer | Technology | Responsibility |
|---|---|---|
| Interface | Next.js, React, TypeScript, Recharts | Exported client served from the application |
| API | FastAPI, Pydantic | Authenticated contracts and transactional workflows |
| Analytics | DuckDB, integer paise | Reconciliation and exact accounting attribution |
| Investigation | LangGraph, optional Google Gemini | Bounded planning with durable stage checkpoints |
| Scenarios | Python Decimal | Whole-order sensitivity and downside comparisons |
| Persistence | PostgreSQL in the cloud; SQLite WAL locally | Accounts, snapshots, runs, memos, audit |
| Reports | ReportLab | Downloadable decision PDF |
| Verification | pytest, Playwright, Ruff, TypeScript | Financial, security, workflow, and browser checks |

Read the [architecture](docs/ARCHITECTURE.md), [deployment guide](docs/DEPLOYMENT.md), and [CSV contract](docs/CSV_CONTRACT.md). The Dockerfile, Compose file, Render blueprint, and backup utility are included. The public Render service is deployed with Neon PostgreSQL and private provider credentials. Use one application process; cloud state belongs in PostgreSQL, and local SQLite requires a persistent volume. Horizontal scaling, SSO, separate approver roles, password reset, and external store connectors are outside this release.

The final project presentation and demo materials are prepared separately in the workspace's `deliverables` directory. The submission must include this repository, the actual deployed Render URL, and an accessible demo-video URL after their access checks.
