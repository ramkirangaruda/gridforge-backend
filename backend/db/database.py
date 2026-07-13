import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# `check_same_thread=False`: FastAPI runs sync `def` route handlers in a
# threadpool, so different requests may use the engine from different
# threads. Safe here because each request opens its own short-lived Session
# (see get_session below) rather than sharing one connection across threads.
# `timeout=30`: how long a connection waits on SQLite's file lock before
# raising "database is locked", instead of failing immediately - this is
# the main defense against the backend and worker (or multiple backend
# request threads) writing at the same moment.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    future=True,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        # WAL lets readers proceed concurrently with a single writer instead
        # of blocking the whole file, which is the main throughput problem
        # with SQLite's default rollback-journal mode under concurrent access.
        cursor.execute("PRAGMA journal_mode=WAL")
        # NORMAL is safe under WAL (only durability of the last few commits
        # after an OS crash is at risk, not corruption) and notably faster
        # than the FULL default.
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Belt-and-suspenders alongside connect_args timeout above - both
        # configure the same underlying busy-wait behavior.
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    # Keep ORM attributes readable after commit() without an extra SELECT -
    # task_service converts ORM rows to Task pydantic models right after
    # committing, so the objects must not expire on commit.
    expire_on_commit=False,
)


def init_db() -> None:
    """Creates all tables that don't already exist. Safe to call repeatedly
    (e.g. on every app startup) - it's a no-op once the schema exists."""
    from backend.db import models  # noqa: F401  (registers models with Base)

    if _is_sqlite:
        settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    logger.info(f"Database schema ready at {settings.DATABASE_URL}")
