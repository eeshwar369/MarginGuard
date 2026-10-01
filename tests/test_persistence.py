import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.db import begin_write, close_pool, connect, initialize
from app.security import rate_limit


def test_commits_survive_reconnect_and_failed_transactions_roll_back(database):
    initialize()
    with connect() as c:
        c.execute("INSERT INTO rate_limits VALUES(?,?,?)", ("persistent", 3, time.time() + 60))
    close_pool()
    with connect() as c:
        assert c.execute("SELECT count FROM rate_limits WHERE bucket=?", ("persistent",)).fetchone()[0] == 3
    with pytest.raises(RuntimeError):
        with connect() as c:
            begin_write(c)
            c.execute("UPDATE rate_limits SET count=9 WHERE bucket=?", ("persistent",))
            raise RuntimeError("simulate failed operation")
    close_pool()
    with connect() as c:
        assert c.execute("SELECT count FROM rate_limits WHERE bucket=?", ("persistent",)).fetchone()[0] == 3


def test_concurrent_rate_limit_cannot_oversubscribe(database):
    initialize()

    def attempt(_):
        try:
            rate_limit("concurrent", 5, 60)
            return True
        except HTTPException as error:
            assert error.status_code == 429
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(attempt, range(16))) == 5


def test_parameters_quotes_percent_unicode_and_expiry_precision(database):
    initialize()
    value = "₹ ? 25% ' ; DROP TABLE users; --"
    expiry = 1791000000.125
    with connect() as c:
        c.execute("INSERT INTO rate_limits VALUES(?,?,?)", (value, 1, expiry))
        row = c.execute(
            "SELECT bucket, reset_at, '?' AS literal, '100%' AS percent FROM rate_limits WHERE bucket=?",
            (value,),
        ).fetchone()
        assert dict(row) == {"bucket": value, "reset_at": expiry, "literal": "?", "percent": "100%"}


def test_render_uses_assigned_origin_and_requires_durable_database(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://marginguard-test.onrender.com")
    monkeypatch.delenv("MG_APP_ORIGIN", raising=False)
    with pytest.raises(ValueError, match="so data survives"):
        Settings(_env_file=None, database_url="")
    config = Settings(
        _env_file=None,
        env="production",
        cookie_secure=True,
        database_url="postgresql://test:private@db.example.test/demo?sslmode=require",
    )
    assert config.app_origin == "https://marginguard-test.onrender.com"
    assert "private" not in repr(config)
    monkeypatch.setenv("MG_APP_ORIGIN", "https://custom.example.test")
    assert (
        Settings(_env_file=None, database_url=config.database_url).app_origin == "https://custom.example.test"
    )


def test_production_database_requires_tls(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    with pytest.raises(ValueError, match="requires sslmode") as failure:
        Settings(
            _env_file=None,
            env="production",
            cookie_secure=True,
            app_origin="https://example.test",
            database_url="postgresql://test:private@db.example.test/demo",
        )
    assert "private" not in str(failure.value)
