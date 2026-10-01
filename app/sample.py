import random

from .data import csv_bytes


def sample_exports(seed=26, duplicate=False) -> dict[str, bytes]:
    rng = random.Random(seed)
    products = [
        ("TEE-01", "Studio Tee", 89900, 34500),
        ("TOTE-02", "Everyday Tote", 69900, 26000),
        ("PACK-03", "Weekend Pack", 149900, 61000),
    ]
    data = {"orders": [], "refunds": [], "costs": []}
    for month, per_day in [(8, 10), (9, 12)]:
        for day in range(1, 29):
            for j in range(per_day):
                sku, name, price, cost = products[rng.randrange(3)]
                ident = f"MG-{month:02}{day:02}-{j:03}"
                qty = 2 if rng.random() < 0.15 else 1
                discount = (6000 if month == 8 else 15000) * qty
                shipping = 4500 + (1800 if month == 9 else 0)
                product_cost = (cost + (4000 if month == 9 else 0)) * qty
                data["orders"].append(
                    {
                        "line_id": ident,
                        "order_id": ident,
                        "date": f"2026-{month:02}-{day:02}",
                        "sku": sku,
                        "product_name": name,
                        "quantity": qty,
                        "unit_price": price,
                        "discount": discount,
                        "currency": "INR",
                    }
                )
                data["costs"].append(
                    {"line_id": ident, "product_cost": product_cost, "shipping_cost": shipping}
                )
                if rng.random() < (0.035 if month == 8 else 0.075):
                    data["refunds"].append(
                        {
                            "refund_id": "REF-" + ident,
                            "line_id": ident,
                            "date": f"2026-{month:02}-{day:02}",
                            "amount": price * qty - discount,
                            "recovered_cost": int(product_cost * 0.8),
                        }
                    )
    if duplicate and data["refunds"]:
        data["refunds"].append(dict(data["refunds"][-1]))
    return {kind: csv_bytes(kind, rows) for kind, rows in data.items()}
