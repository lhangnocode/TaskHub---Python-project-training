import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="TaskHub Backend")
    description: str | None = Field(None, max_length=1000, example="FastAPI REST API project")


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
