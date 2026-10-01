from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from .models import Scenario


def cents(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def simulate(current: dict, params: Scenario) -> dict:
    n = current["orders"]
    if not n:
        raise ValueError("No orders available for a scenario")
    if params.demand_drop > params.max_demand_drop:
        raise ValueError("The selected demand drop cannot exceed its maximum bound")
    discount = params.discount_reduction * 100
    shipping = params.shipping_saving * 100
    if discount * n > current["discount"]:
        raise ValueError("Discount reduction exceeds the current average discount per order")
    if shipping * n > current["shipping"]:
        raise ValueError("Shipping saving exceeds the current average shipping cost per order")
    baseline = current["margin"]
    unit = Decimal(baseline) / n
    fee = params.implementation_cost * 100

    def discount_total(drop):
        retained = int((Decimal(n) * (1 - Decimal(drop) / 100)).to_integral_value(rounding=ROUND_FLOOR))
        return cents(retained * (unit + discount) - fee), retained

    selected, selected_orders = discount_total(params.demand_drop)
    best, _ = discount_total(0)
    worst, _ = discount_total(params.max_demand_drop)
    # For negative unit contribution, fewer orders can improve total contribution.
    low, high = min(best, worst), max(best, worst)
    ship_best = cents(Decimal(baseline) + n * shipping - fee)
    ship_worst = cents(Decimal(baseline) + n * (shipping - params.extra_return_cost * 100) - fee)
    alternatives = [
        {
            "id": "discount",
            "label": "Tighten discounts",
            "best": high,
            "worst": low,
            "selected": selected,
            "delta": selected - baseline,
            "orders": selected_orders,
        },
        {
            "id": "shipping",
            "label": "Reduce shipping cost",
            "best": ship_best,
            "worst": ship_worst,
            "selected": ship_worst,
            "delta": ship_worst - baseline,
            "orders": n,
        },
        {
            "id": "status_quo",
            "label": "Keep current policy",
            "best": baseline,
            "worst": baseline,
            "selected": baseline,
            "delta": 0,
            "orders": n,
        },
    ]
    alternatives.sort(key=lambda a: (a["worst"], a["id"] == "status_quo"), reverse=True)
    boundary = None
    if unit + discount > 0 and baseline >= 0:
        boundary = float((1 - (Decimal(baseline) + fee) / (n * (unit + discount))) * 100)
    curve = []
    for step in range(21):
        drop = params.max_demand_drop * step / 20
        total, retained = discount_total(drop)
        curve.append(
            {
                "demand_drop": float(drop),
                "discount": total,
                "shipping": ship_worst,
                "baseline": baseline,
                "orders": retained,
            }
        )
    return {
        "baseline": baseline,
        "orders": n,
        "unit_margin": cents(unit),
        "break_even_pct": boundary,
        "alternatives": alternatives,
        "recommended": alternatives[0]["id"],
        "curve": curve,
        "params": params.model_dump(mode="json"),
        "assumptions": [
            "Scenario estimates, not forecasts or guaranteed savings.",
            "The current mix and all per-order variable costs scale with order volume.",
            "Shipping changes hold volume constant; extra return cost varies over the selected range.",
            "Fixed overhead and tax are excluded. The entered implementation cost applies to either change.",
            "Ranking maximizes the worst contribution margin within your explicit bounds.",
            "Break-even uses a continuous volume approximation; scenario totals use whole orders.",
        ],
    }
