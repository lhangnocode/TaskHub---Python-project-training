from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import error_response_schema
from src.core.security import get_password_hash
from src.models.user import User
from src.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
    },
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        422: error_response_schema(422, "Validation Error"),
    },
)
async def update_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return UserRead.model_validate(current_user)
