"""Creates the SQLite schema on first run.

Run explicitly with `python -m backend.db.init_db` (from the repo root, so
absolute imports resolve) before first starting the backend, or as a
one-off container/CI step. task_service.py also calls init_db() on import
as a safety net, so this is optional for local dev - it exists mainly for
deployments that want schema creation as an explicit, auditable step
rather than an import-time side effect.
"""
from backend.db.database import init_db

if __name__ == "__main__":
    init_db()
    print("GridForge database schema initialized.")
