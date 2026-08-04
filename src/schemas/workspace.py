import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.core.rbac import ResourceRole
from src.schemas.user import UserRead


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="Engineering Hub")
    description: str | None = Field(
        None, max_length=1000, example="Main workspace for dev team"
    )


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=255, example="Updated Engineering Hub"
    )
    description: str | None = Field(
        None, max_length=1000, example="Updated description"
    )


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceMemberAdd(BaseModel):
    user_id: uuid.UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    role: ResourceRole = Field(default=ResourceRole.VIEWER, example=ResourceRole.VIEWER)


class WorkspaceMemberRoleUpdate(BaseModel):
    role: ResourceRole = Field(..., example=ResourceRole.ADMIN)


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: ResourceRole
    created_at: datetime
    user: UserRead | None = None
