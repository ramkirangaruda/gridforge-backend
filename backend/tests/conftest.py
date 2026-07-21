"""Test env vars MUST be set before anything imports backend.core.config,
since Settings() is instantiated once at module import time. This file is
guaranteed to run before any test module in this directory, so it's the
right place to do it - don't move this env setup into a fixture.
"""
import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="gridforge_test_")
os.environ.setdefault("UPLOADS_DIR", _tmp_dir)
os.environ.setdefault("DB_PATH", os.path.join(_tmp_dir, "test_tasks.db"))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only-do-not-use-in-prod")
os.environ.setdefault("WORKER_API_KEY", "test-worker-key-for-ci-only")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.db.database import SessionLocal  # noqa: E402
from backend.db.models import TaskORM, UserORM  # noqa: E402
from backend.core.rate_limit import limiter  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


# Shared across test modules (test_auth.py, test_tasks.py, ...) rather
# than each redefining its own copy - plain functions, not fixtures,
# since they take arguments (username/password) that vary per call.

def register(client, username="alice", password="password123"):
    return client.post("/api/v1/auth/register", json={"username": username, "password": password})


def login(client, username="alice", password="password123"):
    return client.post("/api/v1/auth/login", data={"username": username, "password": password})


def register_and_login(client, username="alice", password="password123"):
    register(client, username, password)
    r = login(client, username, password)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def submit_fake_task(client, headers, filename="test.zip"):
    """submit-project's real path pushes the new task ID onto Redis
    (redis_service.queue_task) - mocked out here so these tests exercise
    the backend's own routing/DB/ownership logic without needing a live
    Redis in every environment that runs `pytest` (a contributor's
    laptop, not just CI, which does provision one as a service
    container - see .github/workflows/ci.yml)."""
    with patch("backend.services.redis_service.queue_task"):
        return client.post(
            "/api/v1/submit-project",
            files={"file": (filename, b"PK\x03\x04fake", "application/zip")},
            headers=headers,
        )


@pytest.fixture(autouse=True)
def _clean_db():
    """The SQLite engine/session is bound once at import time (see the
    note above), so every test in the session shares one DB file. Wipe it
    after each test rather than trying to re-init a fresh DB per test."""
    yield
    with SessionLocal() as session:
        session.query(TaskORM).delete()
        session.query(UserORM).delete()
        session.commit()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The slowapi Limiter's counters live in an in-memory store on the
    single shared `limiter` object (registered once on app.state at import
    time), not per-TestClient - without this, tests that call
    /auth/register or /auth/login more than a couple of times start
    tripping the 5/minute limit purely from earlier tests' calls sharing
    the same bucket (TestClient always presents as the same "testclient"
    pseudo-IP), not from anything the test itself is doing wrong."""
    limiter.reset()
    yield
