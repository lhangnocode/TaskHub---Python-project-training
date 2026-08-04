import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.task import TaskPriority, TaskStatus
from src.schemas.user import UserRead


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, example="Implement JWT auth")
    description: str | None = Field(
        None, max_length=5000, example="Add login/register endpoints with JWT tokens"
    )
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    assignee_id: uuid.UUID | None = Field(None)
    due_date: datetime | None = Field(None)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    status: TaskStatus | None = Field(None)
    priority: TaskPriority | None = Field(None)
    assignee_id: uuid.UUID | None = Field(None)
    due_date: datetime | None = Field(None)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: uuid.UUID | None
    reporter_id: uuid.UUID
    due_date: datetime | None
    created_at: datetime
    assignee: UserRead | None = None
    reporter: UserRead | None = None


class TaskFilterParams(BaseModel):
    status: TaskStatus | None = Field(None, description="Filter task by status")
    priority: TaskPriority | None = Field(None, description="Filter task by priority")
    assignee_id: uuid.UUID | None = Field(
        None, description="Filter task by assignee UUID"
    )
    page: int = Field(1, ge=1, description="Page number starting from 1")
    limit: int = Field(10, ge=1, le=100, description="Items per page (max 100)")
