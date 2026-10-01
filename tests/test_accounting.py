import copy
from decimal import Decimal

import pytest

from app.analytics import analyze, evidence
from app.data import ImportErrorDetail, csv_bytes, import_exports, money, validate_snapshot
from app.decisions import simulate
from app.models import Scenario


def test_multi_refund_join_does_not_multiply_costs(exports):
    snapshot, issues = import_exports(exports)
    assert issues == []
    result = analyze(snapshot)
    assert result["previous"]["margin"] == 10000
    # 20000 gross - 2000 discount - 5000 refunds - 8000 cost + 1500 recovery - 1500 shipping.
    assert result["current"]["margin"] == 5000
    assert result["current"]["product_cost"] == 6500
    assert result["current"]["revenue"] == 13000
    assert sum(x["value"] for x in result["bridge"]) == -5000
    assert result["current"]["orders"] == 1
    negative = next(f for f in result["findings"] if f["id"] == "ev-negative")
    assert negative["count"] == 0 and negative["status"] == "supported"


def test_evidence_matches_source_rows_and_params(exports):
    snapshot, _ = import_exports(exports)
    result = evidence(snapshot, analyze(snapshot), "ev-refunds", limit=1, search="L1")
    assert result["total"] == 1
    assert result["rows"][0]["margin"] == 5000
    assert result["rows"][0]["order_source_row"] == 3
    assert result["finding"]["evidence"]["delta"] == 5000
    injected = evidence(snapshot, analyze(snapshot), "ev-refunds", search="' OR 1=1 --")
    assert injected["total"] == 0


def test_row_order_does_not_change_accounting(exports):
    snapshot, _ = import_exports(exports)
    baseline = analyze(snapshot)
    for k in ["orders", "refunds", "costs"]:
        snapshot[k].reverse()
    assert analyze(snapshot) == baseline


def test_duplicate_refund_quarantined_and_excluded(exports):
    snapshot, _ = import_exports(exports)
    baseline = analyze(snapshot)
    snapshot["refunds"].append({**snapshot["refunds"][0], "source_row": 5})
    clean, issues = validate_snapshot(snapshot)
    assert issues[0]["severity"] == "warning"
    assert issues[0]["resolution"] == "quarantined"
    assert len(clean["refunds"]) == 2
    assert analyze(clean) == baseline


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda s: s["costs"].pop(), "missing_cost"),
        (lambda s: s["refunds"][0].update(amount=999999), "refund_exceeds_order"),
        (lambda s: s["refunds"][0].update(recovered_cost=999999), "refund_exceeds_order"),
        (lambda s: s["refunds"][0].update(line_id="missing"), "orphan_record"),
        (lambda s: s["refunds"][0].update(date="2020-01-01"), "refund_before_order"),
        (lambda s: s["orders"][1].update(order_id="O0"), "order_date_conflict"),
        (lambda s: s["orders"].append(copy.deepcopy(s["orders"][0])), "duplicate_key"),
    ],
)
def test_bad_joins_and_contradictory_records_block(exports, change, code):
    snapshot, _ = import_exports(exports)
    change(snapshot)
    _, issues = validate_snapshot(snapshot)
    assert any(x["code"] == code and x["severity"] == "error" for x in issues)


@pytest.mark.parametrize("invalid", ["1.234", "-1", "NaN", "Infinity", "1e3", "₹100", "1,000", "=1+1"])
def test_invalid_money_is_rejected(invalid):
    with pytest.raises(ValueError):
        money(invalid)


def test_decimal_money_is_exact():
    assert money("0.29") == 29
    assert money("19.99") * 3 == 5997


def test_unsupported_currency_and_missing_header_rejected(exports):
    for bad in [exports["orders"].replace(b"INR", b"USD"), b"garbage\n1\n", b"\x00binary"]:
        with pytest.raises(ImportErrorDetail):
            import_exports({**exports, "orders": bad})


def test_exact_integer_overflow_is_rejected(exports):
    snapshot, _ = import_exports(exports)
    snapshot["orders"][0].update(quantity=9999, unit_price=999999999999)
    with pytest.raises(ImportErrorDetail, match="exact-integer"):
        validate_snapshot(snapshot)


def test_csv_formula_cells_are_escaped(exports):
    snapshot, _ = import_exports(exports)
    snapshot["orders"][0]["product_name"] = "=HYPERLINK(1)"
    content = csv_bytes("orders", snapshot["orders"])
    assert b"'=HYPERLINK(1)" in content


def test_single_month_is_not_a_fabricated_comparison(exports):
    snapshot, _ = import_exports(exports)
    snapshot["orders"] = snapshot["orders"][1:]
    snapshot["costs"] = snapshot["costs"][1:]
    result = analyze(snapshot)
    assert result["previous"] is None
    assert result["bridge"] == []
    assert result["findings"][-1]["status"] == "unresolved"


def baseline():
    return {"orders": 1000, "margin": 14000000, "discount": 2000000, "shipping": 1000000}


def test_reference_scenario_and_break_even():
    result = simulate(baseline(), Scenario())
    options = {a["id"]: a for a in result["alternatives"]}
    assert options["discount"]["selected"] == 13800000
    assert options["discount"]["worst"] == 13200000
    assert options["shipping"]["worst"] == 14100000
    assert options["shipping"]["best"] == 14500000
    assert result["recommended"] == "shipping"
    assert result["break_even_pct"] == pytest.approx(6.6666666667)


def test_recommendation_flips_under_return_cost():
    result = simulate(baseline(), Scenario(extra_return_cost=20))
    assert result["recommended"] == "status_quo"


def test_zero_change_tie_prefers_current_policy():
    result = simulate(baseline(), Scenario(discount_reduction=0, shipping_saving=0, extra_return_cost=0))
    assert result["recommended"] == "status_quo"


def test_negative_unit_margin_bounds_are_sorted():
    result = simulate({**baseline(), "margin": -14000000}, Scenario())
    for a in result["alternatives"]:
        assert a["worst"] <= a["selected"] <= a["best"]
    assert result["break_even_pct"] is None


@pytest.mark.parametrize(
    "params", [Scenario(demand_drop=20), Scenario(discount_reduction=1000), Scenario(shipping_saving=1000)]
)
def test_impossible_scenario_rejected(params):
    with pytest.raises(ValueError):
        simulate(baseline(), params)


def test_implementation_cost_and_whole_orders():
    current = {**baseline(), "orders": 7}
    result = simulate(current, Scenario(implementation_cost=Decimal("123.45")))
    a = next(a for a in result["alternatives"] if a["id"] == "discount")
    assert a["orders"] == 6
    assert a["selected"] == 12006000 - 12345
