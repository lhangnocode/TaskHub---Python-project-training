from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestException, ConflictException, CredentialsException
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.auth import Token
from src.schemas.user import UserCreate


async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by_email(user_in.email)

    if existing_user is not None:
        raise ConflictException(detail="Email already registered")

    user = await user_repo.create(
        {
            "email": user_in.email,
            "hashed_password": get_password_hash(user_in.password),
            "full_name": user_in.full_name,
            "is_active": True,
        }
    )
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Token:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)

    if user is None or not verify_password(password, user.hashed_password):
        raise CredentialsException(detail="Incorrect email or password")

    if not user.is_active:
        raise BadRequestException(detail="Inactive user account")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
