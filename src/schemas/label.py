import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, example="Bug")
    color: str = Field(default="#EF4444", max_length=50, example="#EF4444")


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    color: str
    created_at: datetime
