import base64
import hashlib
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .agent import execute_run
from .analytics import evidence
from .config import settings
from .data import SCHEMAS, ImportErrorDetail, csv_bytes, import_exports, validate_snapshot
from .db import (
    INTEGRITY_ERRORS,
    audit,
    begin_write,
    close_pool,
    connect,
    digest,
    encode,
    initialize,
    now,
    stale_memos,
    uid,
)
from .decisions import simulate
from .limits import BodyLimitMiddleware
from .models import (
    Approval,
    CostCorrection,
    Credentials,
    InvestigationRequest,
    Registration,
    Scenario,
    WorkspaceUpdate,
)
from .reports import memo_pdf
from .repository import dataset_row, public_dataset, require_ready, save_dataset
from .sample import sample_exports
from .security import COOKIE, create_session, current_user, hash_password, rate_limit, verify_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("marginguard")


@asynccontextmanager
async def lifespan(application):
    initialize()
    application.state.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="investigation")
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE expires_at<?", (time.time(),))
        c.execute(
            "DELETE FROM users WHERE is_demo=1 AND created_at<?",
            ((datetime.now(UTC) - timedelta(days=3)).isoformat(),),
        )
    try:
        yield
    finally:
        application.state.executor.shutdown(wait=True, cancel_futures=False)
        close_pool()


app = FastAPI(
    title="MarginGuard API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings().env != "production" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings().env != "production" else None,
)
app.add_middleware(BodyLimitMiddleware)


def csp():
    hashes = []
    index = settings().static_dir / "index.html"
    if index.exists():
        for code in re.findall(r"<script>(.*?)</script>", index.read_text(encoding="utf-8"), re.S):
            value = base64.b64encode(hashlib.sha256(code.encode()).digest()).decode()
            hashes.append(f"'sha256-{value}'")
    return (
        "default-src 'self'; script-src 'self' " + " ".join(hashes) + "; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'; object-src 'none'"
    )


@app.middleware("http")
async def boundaries(request: Request, call_next):
    request_id = uid()[:16]
    if request.url.path.startswith("/api/"):
        try:
            size = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid request size"}, status_code=400)
        if size > settings().max_upload_mb * 3 * 1024 * 1024 + 16384:
            return JSONResponse({"detail": "Upload exceeds the total request size limit"}, status_code=413)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin", "")
            allowed = {settings().app_origin.rstrip("/")}
            if settings().env == "development":
                allowed |= {"http://127.0.0.1:3000", "http://localhost:3000", "http://127.0.0.1:8000"}
            if origin.rstrip("/") not in allowed:
                return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error id=%s", request_id)
        response = JSONResponse(
            {"detail": "The request could not be completed. Please retry.", "request_id": request_id}, 500
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if settings().env == "production":
        response.headers["Content-Security-Policy"] = csp()
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    return JSONResponse(
        {"detail": "; ".join(f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in exc.errors())},
        status_code=422,
    )


@app.exception_handler(ImportErrorDetail)
async def import_error(_request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)


def identity(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "is_demo": bool(user["is_demo"]),
        "workspace_id": user["workspace_id"],
        "workspace_name": user["workspace_name"],
        "csrf_token": user["csrf"],
    }


@app.get("/api/health")
def health():
    with connect() as c:
        c.execute("SELECT 1")
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/config")
def config():
    return {
        "ai_available": bool(settings().gemini_api_key),
        "model": settings().gemini_model,
        "registration": settings().allow_registration,
        "demo": settings().allow_demo,
        "max_upload_mb": settings().max_upload_mb,
        "max_rows": settings().max_rows,
    }


@app.post("/api/auth/register")
def register(body: Registration, request: Request, response: Response):
    if not settings().allow_registration:
        raise HTTPException(403, "Registration is disabled on this deployment.")
    rate_limit("register:" + request.client.host, 8, 3600)
    user_id, workspace = uid(), uid()
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO users VALUES(?,?,?,?,0,?)",
                (user_id, body.email, body.name, hash_password(body.password), now()),
            )
            c.execute(
                "INSERT INTO workspaces(id,owner_id,name,created_at) VALUES(?,?,?,?)",
                (workspace, user_id, body.workspace_name, now()),
            )
            csrf = create_session(c, user_id, response)
            audit(c, workspace, "workspace.created", {"name": body.workspace_name})
    except INTEGRITY_ERRORS as e:
        raise HTTPException(409, "This account already exists. Please sign in.") from e
    return {
        "id": user_id,
        "name": body.name,
        "email": body.email,
        "is_demo": False,
        "workspace_id": workspace,
        "workspace_name": body.workspace_name,
        "csrf_token": csrf,
    }


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response):
    rate_limit("login-ip:" + request.client.host, 30, 900)
    rate_limit("login-email:" + hashlib.sha256(body.email.encode()).hexdigest(), 10, 900)
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
        if not verify_password(body.password, row["password_hash"] if row else None):
            raise HTTPException(401, "Email or password is incorrect.")
        csrf = create_session(c, row["id"], response)
        ws = c.execute("SELECT * FROM workspaces WHERE owner_id=?", (row["id"],)).fetchone()
    return identity({**dict(row), "workspace_id": ws["id"], "workspace_name": ws["name"], "csrf": csrf})


@app.post("/api/auth/demo")
def demo(request: Request, response: Response):
    if not settings().allow_demo:
        raise HTTPException(403, "Demo workspaces are disabled.")
    rate_limit("demo:" + request.client.host, 12, 3600)
    user_id, workspace = uid(), uid()
    with connect() as c:
        c.execute("INSERT INTO users VALUES(?,NULL,?,NULL,1,?)", (user_id, "Demo reviewer", now()))
        c.execute(
            "INSERT INTO workspaces(id,owner_id,name,created_at) VALUES(?,?,?,?)",
            (workspace, user_id, "Northstar Studio", now()),
        )
        csrf = create_session(c, user_id, response, demo=True)
    snapshot, issues = import_exports(sample_exports())
    save_dataset(workspace, "Northstar Studio · Aug–Sep 2026", snapshot, issues, True)
    return {
        "id": user_id,
        "name": "Demo reviewer",
        "email": None,
        "is_demo": True,
        "workspace_id": workspace,
        "workspace_name": "Northstar Studio",
        "csrf_token": csrf,
    }


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return identity(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, user=Depends(current_user)):
    token = hashlib.sha256(request.cookies[COOKIE].encode()).hexdigest()
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token,))
        audit(c, user["workspace_id"], "session.signed_out", {})
    response.delete_cookie(COOKIE, path="/", secure=settings().cookie_secure, httponly=True, samesite="lax")
    return {"ok": True}


@app.get("/api/workspace")
def workspace(user=Depends(current_user)):
    with connect() as c:
        ws = c.execute("SELECT * FROM workspaces WHERE id=?", (user["workspace_id"],)).fetchone()
        active = c.execute(
            "SELECT * FROM datasets WHERE id=? AND workspace_id=?", (ws["active_dataset_id"], ws["id"])
        ).fetchone()
        versions = c.execute(
            """SELECT id,version,name,status,content_hash,synthetic,created_at
                            FROM datasets WHERE workspace_id=? ORDER BY version DESC""",
            (ws["id"],),
        ).fetchall()
    return {
        "id": ws["id"],
        "name": ws["name"],
        "dataset": public_dataset(active) if active else None,
        "versions": [dict(r) for r in versions],
        "scenario": json.loads(ws["scenario_json"]),
        "scenario_hash": ws["scenario_hash"],
    }


@app.patch("/api/workspace")
def rename_workspace(body: WorkspaceUpdate, user=Depends(current_user)):
    with connect() as c:
        c.execute("UPDATE workspaces SET name=? WHERE id=?", (body.name, user["workspace_id"]))
        audit(c, user["workspace_id"], "workspace.renamed", {"name": body.name})
    return {"name": body.name}


@app.post("/api/datasets/import")
async def upload_dataset(
    name: str = Form(..., min_length=2, max_length=80),
    orders: UploadFile = File(...),
    refunds: UploadFile = File(...),
    costs: UploadFile = File(...),
    user=Depends(current_user),
):
    rate_limit("import:" + user["workspace_id"], 10, 300)
    maximum = settings().max_upload_mb * 1024 * 1024 + 1
    files = {
        "orders": await orders.read(maximum),
        "refunds": await refunds.read(maximum),
        "costs": await costs.read(maximum),
    }
    snapshot, issues = await run_in_threadpool(import_exports, files)
    return await run_in_threadpool(save_dataset, user["workspace_id"], name, snapshot, issues, False)


@app.post("/api/datasets/sample")
def load_sample(quality_challenge: bool = False, user=Depends(current_user)):
    rate_limit("sample:" + user["workspace_id"], 10, 300)
    snapshot, issues = import_exports(sample_exports(duplicate=quality_challenge))
    return save_dataset(
        user["workspace_id"],
        "Northstar Studio · " + ("Quality challenge" if quality_challenge else "Sample data"),
        snapshot,
        issues,
        True,
    )


@app.get("/api/templates/{kind}")
def template(kind: str):
    if kind not in SCHEMAS:
        raise HTTPException(404, "Template not found")
    content = sample_exports()[kind]
    return Response(
        content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'}
    )


@app.post("/api/datasets/{dataset_id}/acknowledge")
def acknowledge(dataset_id: str, user=Depends(current_user)):
    with connect() as c:
        begin_write(c)
        row = dataset_row(c, user["workspace_id"], dataset_id)
        if row["status"] == "blocked":
            raise HTTPException(409, "Errors require a corrected export; they cannot be acknowledged away.")
        c.execute("UPDATE datasets SET status='ready' WHERE id=?", (dataset_id,))
        audit(
            c,
            user["workspace_id"],
            "quality.acknowledged",
            {"dataset_id": dataset_id, "hash": row["content_hash"]},
        )
    return {"status": "ready"}


@app.post("/api/datasets/{dataset_id}/activate")
def activate(dataset_id: str, user=Depends(current_user)):
    with connect() as c:
        begin_write(c)
        row = dataset_row(c, user["workspace_id"], dataset_id)
        require_ready(row)
        c.execute(
            "UPDATE workspaces SET active_dataset_id=?,scenario_json='{}',scenario_hash='' WHERE id=?",
            (dataset_id, user["workspace_id"]),
        )
        stale_memos(c, user["workspace_id"])
        audit(c, user["workspace_id"], "dataset.activated", {"dataset_id": dataset_id})
    return {"ok": True}


@app.post("/api/datasets/correct-cost")
def correct_cost(body: CostCorrection, user=Depends(current_user)):
    with connect() as c:
        row = dataset_row(c, user["workspace_id"])
        require_ready(row)
    snapshot = json.loads(row["snapshot"])
    target = next((r for r in snapshot["costs"] if r["line_id"] == body.line_id), None)
    if not target:
        raise HTTPException(404, "Order line not found in this data version.")
    before = dict(target)
    target["product_cost"], target["shipping_cost"] = (
        int(body.product_cost * 100),
        int(body.shipping_cost * 100),
    )
    snapshot.setdefault("corrections", []).append(
        {"line_id": body.line_id, "before": before, "after": dict(target), "reason": body.reason, "at": now()}
    )
    snapshot, issues = validate_snapshot(snapshot)
    return save_dataset(
        user["workspace_id"],
        row["name"] + " · revised",
        snapshot,
        issues,
        bool(row["synthetic"]),
        expected_active_hash=body.expected_hash,
    )


@app.get("/api/evidence/{evidence_id}")
def get_evidence(
    evidence_id: str,
    dataset_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str = Query("", max_length=100),
    user=Depends(current_user),
):
    with connect() as c:
        row = dataset_row(c, user["workspace_id"], dataset_id)
        require_ready(row)
    try:
        result = evidence(
            json.loads(row["snapshot"]), json.loads(row["summary"]), evidence_id, offset, limit, search
        )
    except KeyError as e:
        raise HTTPException(404, "No numerical evidence exists for this finding.") from e
    return {**result, "content_hash": row["content_hash"], "version": row["version"], "dataset_id": row["id"]}


@app.get("/api/datasets/{dataset_id}/export/{kind}")
def export_data(dataset_id: str, kind: str, user=Depends(current_user)):
    if kind not in SCHEMAS:
        raise HTTPException(404, "Export not found")
    with connect() as c:
        row = dataset_row(c, user["workspace_id"], dataset_id)
    return Response(
        csv_bytes(kind, json.loads(row["snapshot"])[kind]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{kind}-v{row["version"]}.csv"'},
    )


def public_run(row):
    data = dict(row)
    data.pop("state", None)
    for field in ["events", "result"]:
        data[field] = json.loads(data[field]) if data[field] else None
    return data


@app.get("/api/investigations")
def investigations(user=Depends(current_user)):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM runs WHERE workspace_id=? ORDER BY created_at DESC LIMIT 30",
            (user["workspace_id"],),
        ).fetchall()
    return [public_run(r) for r in rows]


@app.post("/api/investigations", status_code=202)
def start_investigation(body: InvestigationRequest, request: Request, user=Depends(current_user)):
    rate_limit("run:" + user["workspace_id"], 20, 3600)
    run_id = uid()
    use_ai = body.use_ai and bool(settings().gemini_api_key)
    if use_ai and not body.consent:
        raise HTTPException(
            400, "Confirm that the question and numerical summaries may be sent to the AI provider."
        )
    with connect() as c:
        begin_write(c)
        dataset = dataset_row(c, user["workspace_id"])
        require_ready(dataset)
        count = c.execute(
            "SELECT COUNT(*) FROM runs WHERE workspace_id=? AND status IN ('running','queued')",
            (user["workspace_id"],),
        ).fetchone()[0]
        global_count = c.execute("SELECT COUNT(*) FROM runs WHERE status IN ('running','queued')").fetchone()[
            0
        ]
        if count or global_count >= 12:
            raise HTTPException(
                429, "An investigation is already running or the service is busy. Please wait."
            )
        c.execute(
            """INSERT INTO runs(id,workspace_id,dataset_id,question,status,mode,stage,created_at)
                    VALUES(?,?,?,?,'queued',?,'Queued',?)""",
            (
                run_id,
                user["workspace_id"],
                dataset["id"],
                body.question,
                "ai" if use_ai else "verified",
                now(),
            ),
        )
        audit(
            c,
            user["workspace_id"],
            "investigation.started",
            {"run_id": run_id, "ai_consent": use_ai and body.consent},
        )
    request.app.state.executor.submit(execute_run, run_id)
    return {"id": run_id, "status": "queued"}


@app.get("/api/investigations/{run_id}")
def investigation(run_id: str, user=Depends(current_user)):
    with connect() as c:
        row = c.execute(
            "SELECT * FROM runs WHERE id=? AND workspace_id=?", (run_id, user["workspace_id"])
        ).fetchone()
    if not row:
        raise HTTPException(404, "Investigation not found")
    return public_run(row)


@app.post("/api/investigations/{run_id}/resume", status_code=202)
def resume(run_id: str, request: Request, user=Depends(current_user)):
    rate_limit("resume:" + user["workspace_id"], 5, 300)
    with connect() as c:
        begin_write(c)
        row = c.execute(
            "SELECT * FROM runs WHERE id=? AND workspace_id=?", (run_id, user["workspace_id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Investigation not found")
        if row["status"] != "interrupted":
            raise HTTPException(409, "Only interrupted runs can be resumed.")
        active = c.execute(
            "SELECT COUNT(*) FROM runs WHERE workspace_id=? AND status IN ('running','queued')",
            (user["workspace_id"],),
        ).fetchone()[0]
        total = c.execute("SELECT COUNT(*) FROM runs WHERE status IN ('running','queued')").fetchone()[0]
        if active or total >= 12:
            raise HTTPException(429, "An investigation is already running or the service is busy.")
        c.execute("UPDATE runs SET status='queued',stage='Resuming' WHERE id=?", (run_id,))
    request.app.state.executor.submit(execute_run, run_id)
    return {"id": run_id, "status": "queued"}


@app.post("/api/scenario/preview")
def preview_scenario(body: Scenario, user=Depends(current_user)):
    with connect() as c:
        row = dataset_row(c, user["workspace_id"])
        require_ready(row)
    try:
        result = simulate(json.loads(row["summary"])["current"], body)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {
        **result,
        "dataset_id": row["id"],
        "data_hash": row["content_hash"],
        "scenario_hash": digest(body.model_dump(mode="json")),
    }


@app.put("/api/scenario")
def save_scenario(body: Scenario, user=Depends(current_user)):
    result = preview_scenario(body, user)
    with connect() as c:
        begin_write(c)
        active = dataset_row(c, user["workspace_id"])
        if active["id"] != result["dataset_id"]:
            raise HTTPException(409, "Data changed. Recalculate the scenario before saving.")
        ws = c.execute("SELECT scenario_hash FROM workspaces WHERE id=?", (user["workspace_id"],)).fetchone()
        if ws["scenario_hash"] != result["scenario_hash"]:
            stale_memos(c, user["workspace_id"])
            c.execute(
                "UPDATE workspaces SET scenario_json=?,scenario_hash=? WHERE id=?",
                (encode(body.model_dump(mode="json")), result["scenario_hash"], user["workspace_id"]),
            )
            audit(
                c,
                user["workspace_id"],
                "scenario.saved",
                {"scenario_hash": result["scenario_hash"], "dataset_id": active["id"]},
            )
    return result


def public_memo(row):
    data = dict(row)
    data["content"] = json.loads(data["content"])
    return data


@app.get("/api/memos")
def memos(user=Depends(current_user)):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM memos WHERE workspace_id=? ORDER BY created_at DESC LIMIT 50",
            (user["workspace_id"],),
        ).fetchall()
    return [public_memo(row) for row in rows]


@app.post("/api/memos")
def create_memo(user=Depends(current_user)):
    with connect() as c:
        begin_write(c)
        row = dataset_row(c, user["workspace_id"])
        require_ready(row)
        ws = c.execute("SELECT * FROM workspaces WHERE id=?", (user["workspace_id"],)).fetchone()
        if not ws["scenario_hash"]:
            raise HTTPException(409, "Save a scenario in the decision lab first.")
        summary = json.loads(row["summary"])
        scenario = simulate(summary["current"], Scenario.model_validate_json(ws["scenario_json"]))
        existing = c.execute(
            "SELECT * FROM memos WHERE workspace_id=? AND dataset_id=? AND scenario_hash=? AND status!='stale'",
            (ws["id"], row["id"], ws["scenario_hash"]),
        ).fetchone()
        if existing:
            return public_memo(existing)
        content = {
            "scenario": scenario,
            "data_hash": row["content_hash"],
            "version": row["version"],
            "synthetic": bool(row["synthetic"]),
            "findings": summary["findings"],
            "source_hashes": json.loads(row["snapshot"])["source_hashes"],
        }
        memo_id = uid()
        c.execute(
            """INSERT INTO memos(id,workspace_id,dataset_id,scenario_hash,content,status,created_at)
                    VALUES(?,?,?,?,?,'draft',?)""",
            (memo_id, ws["id"], row["id"], ws["scenario_hash"], encode(content), now()),
        )
        audit(c, ws["id"], "memo.created", {"memo_id": memo_id})
        return public_memo(c.execute("SELECT * FROM memos WHERE id=?", (memo_id,)).fetchone())


@app.post("/api/memos/{memo_id}/approve")
def approve_memo(memo_id: str, body: Approval, user=Depends(current_user)):
    if not body.acknowledged:
        raise HTTPException(400, "Review and acknowledge the assumptions before approving.")
    with connect() as c:
        begin_write(c)
        memo = c.execute(
            "SELECT * FROM memos WHERE id=? AND workspace_id=?", (memo_id, user["workspace_id"])
        ).fetchone()
        if not memo:
            raise HTTPException(404, "Memo not found")
        ws = c.execute("SELECT * FROM workspaces WHERE id=?", (user["workspace_id"],)).fetchone()
        dataset = dataset_row(c, user["workspace_id"])
        if (
            memo["status"] == "stale"
            or ws["active_dataset_id"] != memo["dataset_id"]
            or dataset["content_hash"] != body.expected_dataset_hash
            or memo["scenario_hash"] != body.expected_scenario_hash
            or ws["scenario_hash"] != memo["scenario_hash"]
        ):
            raise HTTPException(409, "The data or assumptions changed. Create and review a fresh memo.")
        if memo["status"] != "approved":
            c.execute(
                "UPDATE memos SET status='approved',approved_by=?,approved_at=? WHERE id=?",
                (user["name"], now(), memo_id),
            )
            audit(c, user["workspace_id"], "memo.approved", {"memo_id": memo_id, "by": user["name"]})
        return public_memo(c.execute("SELECT * FROM memos WHERE id=?", (memo_id,)).fetchone())


@app.get("/api/memos/{memo_id}/export")
def export_memo(memo_id: str, format: str = "pdf", user=Depends(current_user)):
    with connect() as c:
        memo = c.execute(
            "SELECT * FROM memos WHERE id=? AND workspace_id=?", (memo_id, user["workspace_id"])
        ).fetchone()
        if not memo:
            raise HTTPException(404, "Memo not found")
        data = public_memo(memo)
        audit(
            c,
            user["workspace_id"],
            "memo.exported",
            {"memo_id": memo_id, "status": memo["status"], "format": format},
        )
    if format == "json":
        return Response(
            encode(data),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="memo-{memo_id[:8]}.json"'},
        )
    if format != "pdf":
        raise HTTPException(400, "Choose pdf or json")
    return Response(
        memo_pdf(data, user["workspace_name"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="memo-{memo_id[:8]}.pdf"'},
    )


@app.get("/api/audit")
def activity(offset: int = Query(0, ge=0), user=Depends(current_user)):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM audit WHERE workspace_id=? ORDER BY id DESC LIMIT 100 OFFSET ?",
            (user["workspace_id"], offset),
        ).fetchall()
    return [{**dict(row), "details": json.loads(row["details"])} for row in rows]


if Path(settings().static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings().static_dir, html=True), name="web")
