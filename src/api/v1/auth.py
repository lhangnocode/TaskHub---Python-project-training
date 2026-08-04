from typing import Annotated

from fastapi import APIRouter, Depends, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, oauth2_scheme
from src.core.exceptions import CredentialsException, error_response_schema
from src.core.security import create_access_token, decode_token
from src.models.user import User
from src.schemas.auth import LoginRequest, LogoutRequest, RefreshTokenRequest, Token
from src.schemas.common import MessageResponse
from src.schemas.user import UserCreate, UserRead
from src.services.auth_service import (
    authenticate_user,
    is_token_blacklisted,
    register_user,
    revoke_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_optional_form_data(
    username: str | None = Form(default=None),
    password: str | None = Form(default=None),
) -> OAuth2PasswordRequestForm | None:
    if username and password:
        return OAuth2PasswordRequestForm(username=username, password=password)
    return None


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: error_response_schema(409, "Email already registered"),
        422: error_response_schema(422, "Validation Error"),
    },
)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await register_user(db, user_in)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    responses={
        401: error_response_schema(401, "Incorrect email or password"),
        422: error_response_schema(422, "Validation Error"),
    },
)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    login_data: LoginRequest | None = None,
    form_data: Annotated[
        OAuth2PasswordRequestForm | None, Depends(get_optional_form_data)
    ] = None,
) -> Token:
    email = ""
    password = ""

    if form_data and form_data.username:
        email = form_data.username
        password = form_data.password
    elif login_data:
        email = login_data.email
        password = login_data.password
    else:
        raise CredentialsException(detail="Email and password required")

    return await authenticate_user(db, email, password)


@router.post(
    "/refresh",
    response_model=Token,
    responses={
        401: error_response_schema(401, "Invalid refresh token"),
    },
)
async def refresh_token(
    refresh_in: RefreshTokenRequest,
) -> Token:
    if await is_token_blacklisted(refresh_in.refresh_token):
        raise CredentialsException(detail="Refresh token has been revoked")

    payload = decode_token(refresh_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise CredentialsException(detail="Invalid or expired refresh token")

    sub = payload.get("sub")
    if not sub:
        raise CredentialsException(detail="Invalid token subject")

    new_access_token = create_access_token(subject=sub)
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_in.refresh_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    responses={
        401: error_response_schema(401, "Unauthorized"),
    },
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    logout_in: LogoutRequest | None = None,
) -> MessageResponse:
    # Revoke access token
    await revoke_token(token)

    # Revoke optional refresh token
    if logout_in and logout_in.refresh_token:
        await revoke_token(logout_in.refresh_token)

    return MessageResponse(message="Successfully logged out")