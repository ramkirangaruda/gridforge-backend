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
    owner: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None

    class Config:
        from_attributes = True


class PaginatedTasks(BaseModel):
    items: list[Task]
    total: int
    limit: int
    offset: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    # bcrypt (backend/core/auth.py) silently truncates anything past 72
    # bytes, so without a cap here two different long passwords sharing a
    # 72-byte prefix would hash identically - and hashing an
    # attacker-supplied megabyte-long string is a cheap way to burn CPU on
    # every request. 72 matches bcrypt's own limit exactly, not a random
    # round number.
    password: str = Field(min_length=8, max_length=72)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
