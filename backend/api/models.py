from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid
from datetime import datetime

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskBase(BaseModel):
    filename: str
    status: TaskStatus = TaskStatus.QUEUED
    
class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    logs: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None

class Task(TaskBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None

    class Config:
        from_attributes = True
