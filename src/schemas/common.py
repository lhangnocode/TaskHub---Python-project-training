from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str = Field(..., example="Operation successful")


class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int = Field(..., example=42)
    page: int = Field(..., example=1)
    limit: int = Field(..., example=10)
    pages: int = Field(..., example=5)
