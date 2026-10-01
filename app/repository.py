import json

from fastapi import HTTPException

from .analytics import analyze
from .db import audit, begin_write, connect, digest, encode, now, stale_memos, uid


def dataset_row(c, workspace: str, dataset_id: str | None = None):
    if dataset_id:
        row = c.execute(
            "SELECT * FROM datasets WHERE workspace_id=? AND id=?", (workspace, dataset_id)
        ).fetchone()
    else:
        row = c.execute(
            """SELECT d.* FROM datasets d JOIN workspaces w ON w.active_dataset_id=d.id
                           WHERE w.id=? AND d.workspace_id=w.id""",
            (workspace,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Import data or load a sample workspace first.")
    return row


def public_dataset(row) -> dict:
    data = dict(row)
    snapshot = json.loads(data.pop("snapshot"))
    for key in ["summary", "issues"]:
        data[key] = json.loads(data[key])
    data["files"] = [
        {"kind": kind, "rows": len(snapshot[kind]), "hash": snapshot["source_hashes"].get(kind, "")}
        for kind in ["orders", "refunds", "costs"]
    ]
    data["synthetic"] = bool(data["synthetic"])
    return data


def save_dataset(
    workspace: str,
    name: str,
    snapshot: dict,
    issues: list,
    synthetic: bool,
    expected_active_hash: str | None = None,
) -> dict:
    blocked = any(i["severity"] == "error" for i in issues)
    status = "blocked" if blocked else "needs_review" if issues else "ready"
    summary = {} if blocked else analyze(snapshot)
    dataset_id = uid()
    with connect() as c:
        begin_write(c)
        if expected_active_hash is not None:
            active = dataset_row(c, workspace)
            if active["content_hash"] != expected_active_hash:
                raise HTTPException(
                    409, "Data changed in another session. Refresh before saving this correction."
                )
        count = c.execute("SELECT COUNT(*) FROM datasets WHERE workspace_id=?", (workspace,)).fetchone()[0]
        if count >= 30:
            raise HTTPException(
                409,
                "This workspace has reached 30 data versions. Export records before starting a new workspace.",
            )
        version = count + 1
        c.execute(
            "INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                dataset_id,
                workspace,
                version,
                name,
                digest(snapshot),
                encode(snapshot),
                encode(summary),
                encode(issues),
                status,
                int(synthetic),
                now(),
            ),
        )
        c.execute(
            "UPDATE workspaces SET active_dataset_id=?,scenario_json='{}',scenario_hash='' WHERE id=?",
            (dataset_id, workspace),
        )
        stale_memos(c, workspace)
        audit(
            c,
            workspace,
            "dataset.created",
            {
                "dataset_id": dataset_id,
                "version": version,
                "status": status,
                "hash": digest(snapshot),
                "issues": len(issues),
            },
        )
        row = dataset_row(c, workspace, dataset_id)
        return public_dataset(row)


def require_ready(row):
    if row["status"] != "ready":
        raise HTTPException(409, "Resolve or acknowledge the data-quality issues before continuing.")
