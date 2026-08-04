import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(..., example="john@example.com")
    password: str = Field(..., min_length=6, example="strongpassword123")
    full_name: str = Field(..., min_length=1, max_length=255, example="John Doe")


class UserUpdate(BaseModel):
    full_name: str | None = Field(
        None, min_length=1, max_length=255, example="John Smith"
    )
    email: EmailStr | None = Field(None, example="johnsmith@example.com")
    password: str | None = Field(None, min_length=6, example="newpassword123")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
