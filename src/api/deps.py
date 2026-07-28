import uuid
from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import CredentialsException, PermissionDeniedException
from src.core.rbac import ResourceRole, has_role_permission
from src.core.security import decode_token
from src.database import get_db
from src.models.user import User
from src.models.workspace import WorkspaceMember

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise CredentialsException(detail="Could not validate access token")

    token_type = payload.get("type")
    if token_type != "access":
        raise CredentialsException(detail="Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise CredentialsException(detail="Invalid token subject")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise CredentialsException(detail="Invalid user ID format in token")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise CredentialsException(detail="User not found")
    if not user.is_active:
        raise CredentialsException(detail="Inactive user account")

    return user


def require_workspace_role(
    required_role: ResourceRole,
) -> Callable[..., AsyncSession]:
    """Dependency factory checking user membership role in a workspace."""

    async def dependency(
        workspace_id: uuid.UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> WorkspaceMember:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        result = await db.execute(stmt)
        member = result.scalar_one_or_none()

        if member is None:
            raise PermissionDeniedException(
                detail="User is not a member of this workspace"
            )

        if not has_role_permission(member.role, required_role):
            raise PermissionDeniedException(
                detail=f"Required role level: {required_role.value}, user role: {member.role.value}"
            )

        return member

    return dependency
