"""Reproducible local timing; does not claim deployment throughput or model latency."""

import json
import platform
import statistics
import time
from pathlib import Path

from app.analytics import analyze
from app.data import csv_bytes, import_exports
from app.sample import sample_exports


def main():
    base, _ = import_exports(sample_exports())
    costs = {r["line_id"]: r for r in base["costs"]}
    measurements = []
    for count in [616, 10000, 50000]:
        snapshot = {"orders": [], "costs": [], "refunds": []}
        for i in range(count):
            order = base["orders"][i % len(base["orders"])]
            ident = "BENCH-" + str(i)
            snapshot["orders"].append({**order, "line_id": ident, "order_id": ident})
            snapshot["costs"].append({**costs[order["line_id"]], "line_id": ident})
        files = {k: csv_bytes(k, rows) for k, rows in snapshot.items()}
        timings = []
        for _ in range(3):
            started = time.perf_counter()
            valid, issues = import_exports(files)
            result = analyze(valid)
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            assert not issues and result["reconciliation_residual"] == 0
            assert sum(p["orders"] for p in result["periods"]) == count
            timings.append(elapsed)
        measurements.append(
            {
                "order_lines": count,
                "cost_lines": count,
                "refund_lines": 0,
                "import_and_analysis_ms": timings,
                "median_ms": statistics.median(timings),
                "input_bytes": sum(len(v) for v in files.values()),
                "reconciliation_residual": 0,
            }
        )
    output = {
        "environment": platform.platform(),
        "python": platform.python_version(),
        "method": "Three sequential parse + validation + DuckDB analysis runs, synthetic records, no HTTP/model call.",
        "measurements": measurements,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/benchmark.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
