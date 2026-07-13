from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Integer, Float

from backend.db.database import Base


class TaskORM(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    logs = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    execution_time = Column(Float, nullable=True)
