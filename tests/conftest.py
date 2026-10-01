import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.data import csv_bytes


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MG_GEMINI_API_KEY", "")
    monkeypatch.setenv("MG_COOKIE_SECURE", "false")
    monkeypatch.setenv("MG_ENV", "development")
    settings.cache_clear()
    from app.main import app

    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as c:
        yield c
    settings.cache_clear()


def sign_in(client, email="test@example.com"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test owner",
            "email": email,
            "password": "correct-horse-26",
            "workspace_name": "Test business",
        },
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


@pytest.fixture
def owner(client):
    return sign_in(client)


@pytest.fixture
def exports():
    orders, costs = [], []
    for i, month in enumerate(["08", "09"]):
        orders.append(
            {
                "line_id": f"L{i}",
                "order_id": f"O{i}",
                "date": f"2026-{month}-01",
                "sku": "TEE",
                "product_name": "Test shirt",
                "quantity": 2,
                "unit_price": 10000,
                "discount": 1000 + i * 1000,
                "currency": "INR",
            }
        )
        costs.append({"line_id": f"L{i}", "product_cost": 8000, "shipping_cost": 1000 + i * 500})
    refunds = [
        {"refund_id": "R1", "line_id": "L1", "date": "2026-09-02", "amount": 3000, "recovered_cost": 1000},
        {"refund_id": "R2", "line_id": "L1", "date": "2026-09-03", "amount": 2000, "recovered_cost": 500},
    ]
    return {
        k: csv_bytes(k, rows) for k, rows in {"orders": orders, "costs": costs, "refunds": refunds}.items()
    }


def upload(client, exports, name="Test data"):
    return client.post(
        "/api/datasets/import",
        data={"name": name},
        files={k: (k + ".csv", content, "text/csv") for k, content in exports.items()},
    )
