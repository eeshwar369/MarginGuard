import json
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal

import duckdb

LEDGER_SQL = """SELECT o.line_id,o.order_id,o.date,o.sku,o.product_name,o.quantity,
  strftime(o.date,'%Y-%m') AS period,
  o.quantity*o.unit_price AS gross,o.discount,
  COALESCE(r.refunds,0) AS refunds,c.product_cost-COALESCE(r.recovered,0) AS product_cost,
  c.shipping_cost AS shipping,
  o.quantity*o.unit_price-o.discount-COALESCE(r.refunds,0) AS revenue,
  o.quantity*o.unit_price-o.discount-COALESCE(r.refunds,0)-c.product_cost+
    COALESCE(r.recovered,0)-c.shipping_cost AS margin,
  o.source_row AS order_source_row,c.source_row AS cost_source_row
FROM orders o JOIN costs c USING(line_id)
LEFT JOIN (SELECT line_id,SUM(amount) AS refunds,SUM(recovered_cost) AS recovered
           FROM refunds GROUP BY line_id) r USING(line_id)"""

PERIOD_SQL = """SELECT period,COUNT(DISTINCT order_id) AS orders,COUNT(*) AS lines,SUM(quantity) AS units,
SUM(gross) AS gross,SUM(discount) AS discount,SUM(refunds) AS refunds,SUM(product_cost) AS product_cost,
SUM(shipping) AS shipping,SUM(revenue) AS revenue,SUM(margin) AS margin,
COUNT(DISTINCT CASE WHEN refunds>0 THEN order_id END) AS refunded_orders
FROM ledger GROUP BY period ORDER BY period"""


def records(cursor) -> list[dict]:
    names = [x[0] for x in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


@contextmanager
def warehouse(snapshot: dict):
    c = duckdb.connect(":memory:")
    c.execute("SET threads=2")
    c.execute("SET memory_limit='256MB'")
    try:
        c.execute("""CREATE TABLE orders(line_id VARCHAR,order_id VARCHAR,date DATE,sku VARCHAR,
        product_name VARCHAR,quantity BIGINT,unit_price BIGINT,discount BIGINT,source_row INTEGER)""")
        c.execute(
            "CREATE TABLE costs(line_id VARCHAR,product_cost BIGINT,shipping_cost BIGINT,source_row INTEGER)"
        )
        c.execute(
            "CREATE TABLE refunds(refund_id VARCHAR,line_id VARCHAR,amount BIGINT,recovered_cost BIGINT)"
        )
        # One bound JSON parameter per relation avoids one insert round-trip per row.
        # Column names and casts are server constants; user data cannot become SQL.
        columns = {
            "orders": [
                ("line_id", "VARCHAR"),
                ("order_id", "VARCHAR"),
                ("date", "DATE"),
                ("sku", "VARCHAR"),
                ("product_name", "VARCHAR"),
                ("quantity", "BIGINT"),
                ("unit_price", "BIGINT"),
                ("discount", "BIGINT"),
                ("source_row", "INTEGER"),
            ],
            "costs": [
                ("line_id", "VARCHAR"),
                ("product_cost", "BIGINT"),
                ("shipping_cost", "BIGINT"),
                ("source_row", "INTEGER"),
            ],
            "refunds": [
                ("refund_id", "VARCHAR"),
                ("line_id", "VARCHAR"),
                ("amount", "BIGINT"),
                ("recovered_cost", "BIGINT"),
            ],
        }
        for table, fields in columns.items():
            projection = ",".join(
                f"CAST(json_extract_string(value,'$.{key}') AS {kind})" for key, kind in fields
            )
            c.execute(
                f"INSERT INTO {table} SELECT {projection} FROM json_each(?)", [json.dumps(snapshot[table])]
            )
        c.execute("CREATE VIEW ledger AS " + LEDGER_SQL)
        yield c
    finally:
        c.close()


def ratio(n: int, d: int) -> float:
    return float((Decimal(n) * 100 / Decimal(d)).quantize(Decimal("0.01"))) if d else 0.0


def analyze(snapshot: dict) -> dict:
    with warehouse(snapshot) as c:
        periods = records(c.execute(PERIOD_SQL))
        if not periods:
            raise ValueError("No reconcilable orders")
        for p in periods:
            p["margin_pct"] = ratio(p["margin"], p["revenue"])
            p["refund_rate"] = ratio(p["refunded_orders"], p["orders"])
        current = periods[-1]
        previous = periods[-2] if len(periods) > 1 else None
        daily = records(
            c.execute(
                """SELECT date::VARCHAR AS date,SUM(revenue) AS revenue,
            SUM(margin) AS margin,COUNT(DISTINCT order_id) AS orders FROM ledger WHERE period=?
            GROUP BY date ORDER BY date""",
                [current["period"]],
            )
        )
        products = records(
            c.execute(
                """SELECT sku,MIN(product_name) AS name,SUM(revenue) AS revenue,
            SUM(margin) AS margin,SUM(discount) AS discount,SUM(refunds) AS refunds,
            SUM(shipping) AS shipping,COUNT(DISTINCT order_id) AS orders
            FROM ledger WHERE period=? GROUP BY sku ORDER BY margin DESC""",
                [current["period"]],
            )
        )
        for p in products:
            p["margin_pct"] = ratio(p["margin"], p["revenue"])
        negative = c.execute(
            "SELECT COUNT(*) FROM ledger WHERE period=? AND margin<0", [current["period"]]
        ).fetchone()[0]
    bridge = []
    if previous:
        for key in ["gross", "discount", "refunds", "product_cost", "shipping"]:
            delta = current[key] - previous[key]
            bridge.append({"key": key, "value": delta if key == "gross" else -delta})
        if sum(p["value"] for p in bridge) != current["margin"] - previous["margin"]:
            raise ArithmeticError("The margin bridge did not reconcile")
    return {
        "current": current,
        "previous": previous,
        "periods": periods,
        "daily": daily,
        "products": products,
        "bridge": bridge,
        "negative_lines": negative,
        "reconciliation_residual": 0,
        "currency": "INR",
        "findings": findings(current, previous, products, negative),
    }


def findings(current: dict, previous: dict | None, products: list, negative: int) -> list[dict]:
    result = []
    labels = {
        "discount": "Discounts",
        "refunds": "Refunds",
        "product_cost": "Net product costs",
        "shipping": "Shipping",
    }
    if previous:
        for key, label in labels.items():
            delta = current[key] - previous[key]
            before = Decimal(previous[key]) / previous["orders"]
            after = Decimal(current[key]) / current["orders"]
            per_order = int((after - before).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            result.append(
                {
                    "id": "ev-" + key,
                    "key": key,
                    "title": f"{label} {'increased' if delta > 0 else 'decreased' if delta < 0 else 'unchanged'}",
                    "amount": -delta,
                    "severity": "high" if delta > 0 and per_order > 0 else "info",
                    "status": "supported",
                    "per_order_change": per_order,
                    "explanation": f"Comparing {previous['period']} with {current['period']}. "
                    "Total and per-order changes are calculated separately to account for volume. "
                    "This is an accounting contribution, not proof of customer behavior.",
                    "evidence": {
                        "query": PERIOD_SQL,
                        "params": [],
                        "formula": f"current.{key} - previous.{key}",
                        "before": previous[key],
                        "after": current[key],
                        "delta": delta,
                    },
                }
            )
        result.sort(key=lambda f: f["amount"])
    result.append(
        {
            "id": "ev-negative",
            "key": "negative",
            "title": "Order lines with negative contribution"
            if negative
            else "No order lines have negative contribution",
            "amount": 0,
            "count": negative,
            "severity": "high" if negative else "info",
            "status": "supported",
            "explanation": (
                "These lines cost more to fulfil than their retained revenue. Refunds may explain some losses."
                if negative
                else "All order lines in the current period have non-negative contribution under the imported cost model."
            ),
            "evidence": {
                "query": "SELECT * FROM ledger WHERE period=? AND margin<0 ORDER BY margin",
                "params": [current["period"]],
                "formula": "revenue - product_cost - shipping",
            },
        }
    )
    if not previous:
        result.append(
            {
                "id": "ev-baseline",
                "key": "baseline",
                "title": "A comparison period is missing",
                "amount": 0,
                "severity": "info",
                "status": "unresolved",
                "explanation": "Import a second calendar month to explain changes over time.",
                "evidence": None,
            }
        )
    return result


def evidence(snapshot: dict, summary: dict, evidence_id: str, offset=0, limit=50, search="") -> dict:
    finding = next((f for f in summary["findings"] if f["id"] == evidence_id), None)
    if not finding or not finding["evidence"]:
        raise KeyError("Evidence not found")
    periods = [summary["current"]["period"]]
    if summary["previous"]:
        periods.append(summary["previous"]["period"])
    with warehouse(snapshot) as c:
        conditions, params = ["period IN (" + ",".join("?" for _ in periods) + ")"], periods[:]
        if evidence_id == "ev-negative":
            conditions += ["margin<0", "period=?"]
            params.append(summary["current"]["period"])
        if search:
            conditions.append("(contains(lower(line_id),lower(?)) OR contains(lower(sku),lower(?)))")
            params.extend([search, search])
        where = " AND ".join(conditions)
        total = c.execute("SELECT COUNT(*) FROM ledger WHERE " + where, params).fetchone()[0]
        rows = records(
            c.execute(
                "SELECT * EXCLUDE(date),date::VARCHAR AS date FROM ledger WHERE "
                + where
                + " ORDER BY date DESC,line_id LIMIT ? OFFSET ?",
                params + [limit, offset],
            )
        )
    return {
        "finding": finding,
        "ledger_query": LEDGER_SQL,
        "rows": rows,
        "total": total,
        "offset": offset,
        "limit": limit,
        "source_hashes": snapshot["source_hashes"],
    }
