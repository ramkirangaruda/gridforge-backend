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

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.database import SessionLocal
from backend.db.models import TaskORM, UserORM


@pytest.fixture()
def client():
    return TestClient(app)


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
