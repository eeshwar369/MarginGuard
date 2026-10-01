import csv
import hashlib
import io
import re
from datetime import date
from decimal import Decimal

from .config import settings

SCHEMAS = {
    "orders": [
        "line_id",
        "order_id",
        "date",
        "sku",
        "product_name",
        "quantity",
        "unit_price",
        "discount",
        "currency",
    ],
    "refunds": ["refund_id", "line_id", "date", "amount", "recovered_cost"],
    "costs": ["line_id", "product_cost", "shipping_cost"],
}
MONEY = {"unit_price", "discount", "amount", "recovered_cost", "product_cost", "shipping_cost"}


class ImportErrorDetail(ValueError):
    pass


def money(value: str) -> int:
    value = value.strip()
    if not re.fullmatch(r"\d{1,10}(\.\d{1,2})?", value):
        raise ValueError(
            "Use a positive amount with up to two decimal places, without currency symbols or commas"
        )
    return int(Decimal(value) * 100)


def parse_csv(kind: str, content: bytes) -> list[dict]:
    if len(content) > settings().max_upload_mb * 1024 * 1024:
        raise ImportErrorDetail(f"{kind}: file exceeds {settings().max_upload_mb} MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ImportErrorDetail(f"{kind}: save the file as UTF-8 CSV") from e
    if "\x00" in text:
        raise ImportErrorDetail(f"{kind}: binary content is not a CSV file")
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ImportErrorDetail(f"{kind}: missing or duplicate column headings")
        missing = set(SCHEMAS[kind]) - set(reader.fieldnames)
        if missing:
            raise ImportErrorDetail(f"{kind}: missing columns: {', '.join(sorted(missing))}")
        rows = []
        for number, raw in enumerate(reader, start=2):
            if len(rows) >= settings().max_rows:
                raise ImportErrorDetail(f"{kind}: maximum {settings().max_rows:,} rows per file")
            if None in raw or any(raw.get(k) is None for k in SCHEMAS[kind]):
                raise ImportErrorDetail(f"{kind}, row {number}: column count does not match the header")
            row = {k: raw[k].strip() for k in SCHEMAS[kind]}
            try:
                for key, value in list(row.items()):
                    if key in MONEY:
                        row[key] = money(value)
                    elif key == "quantity":
                        if not re.fullmatch(r"[1-9]\d{0,3}", value):
                            raise ValueError("quantity must be an integer between 1 and 9999")
                        row[key] = int(value)
                    elif key == "date":
                        row[key] = date.fromisoformat(value).isoformat()
                    elif key == "currency":
                        if value != "INR":
                            raise ValueError("Only INR is supported; mixed currencies cannot be reconciled")
                    elif not value or len(value) > 120:
                        raise ValueError(f"{key} must contain 1–120 characters")
                if kind == "orders" and row["discount"] > row["quantity"] * row["unit_price"]:
                    raise ValueError("discount exceeds the line's gross amount")
            except ValueError as e:
                raise ImportErrorDetail(f"{kind}, row {number}: {e}") from e
            row["source_row"] = number
            rows.append(row)
        if kind in {"orders", "costs"} and not rows:
            raise ImportErrorDetail(f"{kind}: at least one data row is required")
        return rows
    except csv.Error as e:
        raise ImportErrorDetail(f"{kind}: malformed CSV: {e}") from e


def validate_snapshot(snapshot: dict) -> tuple[dict, list[dict]]:
    issues = []
    result = {**snapshot}
    for kind, key in [("orders", "line_id"), ("costs", "line_id"), ("refunds", "refund_id")]:
        seen, kept = {}, []
        for row in snapshot[kind]:
            ident = row[key]
            if ident in seen:
                same = {k: v for k, v in row.items() if k != "source_row"} == {
                    k: v for k, v in seen[ident].items() if k != "source_row"
                }
                recoverable = same and kind == "refunds"
                issues.append(
                    {
                        "code": "duplicate_refund" if recoverable else "duplicate_key",
                        "severity": "warning" if recoverable else "error",
                        "file": kind,
                        "row": row["source_row"],
                        "record_id": ident,
                        "message": f"Duplicate {key} {ident}. "
                        + (
                            "Identical refund quarantined; review before analysis."
                            if recoverable
                            else "Conflicting or repeated key. Correct the export and re-import."
                        ),
                        "resolution": "quarantined" if recoverable else "correction_required",
                    }
                )
                continue
            seen[ident] = row
            kept.append(row)
        result[kind] = kept
    orders = {r["line_id"]: r for r in result["orders"]}
    costs = {r["line_id"]: r for r in result["costs"]}
    for line_id, row in orders.items():
        if line_id not in costs:
            issues.append(
                {
                    "code": "missing_cost",
                    "severity": "error",
                    "file": "orders",
                    "row": row["source_row"],
                    "record_id": line_id,
                    "message": f"No fulfilment cost for {line_id}. Margin calculation is blocked.",
                    "resolution": "correction_required",
                }
            )
    for row in result["costs"] + result["refunds"]:
        if row["line_id"] not in orders:
            issues.append(
                {
                    "code": "orphan_record",
                    "severity": "error",
                    "file": "refunds" if "refund_id" in row else "costs",
                    "row": row["source_row"],
                    "record_id": row["line_id"],
                    "message": "This record does not reference an imported order line.",
                    "resolution": "correction_required",
                }
            )
    totals = {}
    # Browser JSON numbers and downstream arithmetic must retain every paise.
    magnitude = sum(r["quantity"] * r["unit_price"] + r["discount"] for r in result["orders"])
    magnitude += sum(r["product_cost"] + r["shipping_cost"] for r in result["costs"])
    magnitude += sum(r["amount"] + r["recovered_cost"] for r in result["refunds"])
    if magnitude > 2**52:
        raise ImportErrorDetail(
            "Combined monetary values exceed the supported exact-integer range. Split this export."
        )
    order_dates = {}
    for row in result["orders"]:
        prior = order_dates.setdefault(row["order_id"], row["date"])
        if prior != row["date"]:
            issues.append(
                {
                    "code": "order_date_conflict",
                    "severity": "error",
                    "file": "orders",
                    "row": row["source_row"],
                    "record_id": row["order_id"],
                    "message": "All lines of the same order must have the same order date.",
                    "resolution": "correction_required",
                }
            )
    for row in result["refunds"]:
        order = orders.get(row["line_id"])
        if order and row["date"] < order["date"]:
            issues.append(
                {
                    "code": "refund_before_order",
                    "severity": "error",
                    "file": "refunds",
                    "row": row["source_row"],
                    "record_id": row["refund_id"],
                    "message": "Refund date precedes its order date.",
                    "resolution": "correction_required",
                }
            )
        item = totals.setdefault(row["line_id"], {"amount": 0, "recovered_cost": 0})
        for key in item:
            item[key] += row[key]
    for ident, total in totals.items():
        order, cost = orders.get(ident), costs.get(ident)
        if (
            order
            and cost
            and (
                total["amount"] > order["quantity"] * order["unit_price"] - order["discount"]
                or total["recovered_cost"] > cost["product_cost"]
            )
        ):
            issues.append(
                {
                    "code": "refund_exceeds_order",
                    "severity": "error",
                    "file": "refunds",
                    "row": 0,
                    "record_id": ident,
                    "message": "Cumulative refunds or recovered costs exceed this order line's value.",
                    "resolution": "correction_required",
                }
            )
    return result, issues


def import_exports(files: dict[str, bytes]) -> tuple[dict, list[dict]]:
    snapshot = {kind: parse_csv(kind, files[kind]) for kind in SCHEMAS}
    snapshot["source_hashes"] = {kind: hashlib.sha256(content).hexdigest() for kind, content in files.items()}
    return validate_snapshot(snapshot)


def csv_bytes(kind: str, rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SCHEMAS[kind], extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for raw in rows:
        row = dict(raw)
        for key in MONEY & set(row):
            row[key] = f"{Decimal(row[key]) / 100:.2f}"
        # Avoid spreadsheet formula interpretation in exported string fields.
        for key, value in row.items():
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                row[key] = "'" + value
        writer.writerow(row)
    return output.getvalue().encode("utf-8")
