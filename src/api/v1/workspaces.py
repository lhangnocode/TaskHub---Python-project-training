import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user, get_db, require_workspace_role
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
    error_response_schema,
)
from src.core.rbac import ResourceRole
from src.models.project import Project
from src.models.user import User
from src.models.workspace import Workspace, WorkspaceMember
from src.schemas.common import MessageResponse
from src.schemas.project import ProjectCreate, ProjectRead
from src.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceRead,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        422: error_response_schema(422, "Validation Error"),
    },
)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    workspace = Workspace(
        name=workspace_in.name,
        description=workspace_in.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.flush()

    # Creator automatically becomes OWNER member
    owner_member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=ResourceRole.OWNER,
    )
    db.add(owner_member)
    await db.commit()
    await db.refresh(workspace)

    return WorkspaceRead.model_validate(workspace)


@router.get(
    "/{id}",
    response_model=WorkspaceRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Workspace Not Found"),
    },
)
async def get_workspace(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceRead:
    stmt = select(Workspace).where(Workspace.id == id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if workspace is None:
        raise NotFoundException(detail="Workspace not found")

    # Member check
    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == id,
        WorkspaceMember.user_id == current_user.id,
    )
    member_res = await db.execute(member_stmt)
    if member_res.scalar_one_or_none() is None:
        raise PermissionDeniedException(detail="You are not a member of this workspace")

    return WorkspaceRead.model_validate(workspace)


@router.post(
    "/{id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires ADMIN/OWNER)"),
        404: error_response_schema(404, "User or Workspace Not Found"),
        409: error_response_schema(409, "User already a member"),
    },
)
async def add_workspace_member(
    id: uuid.UUID,
    member_in: WorkspaceMemberAdd,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.ADMIN))],
) -> WorkspaceMemberRead:
    # Verify user exists
    user_stmt = select(User).where(User.id == member_in.user_id)
    user_res = await db.execute(user_stmt)
    target_user = user_res.scalar_one_or_none()
    if target_user is None:
        raise NotFoundException(detail="Target user not found")

    # Check existing membership
    existing_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == id,
        WorkspaceMember.user_id == member_in.user_id,
    )
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none() is not None:
        raise ConflictException(detail="User is already a member of this workspace")

    new_member = WorkspaceMember(
        workspace_id=id,
        user_id=member_in.user_id,
        role=member_in.role, # Defaults to VIEWER
    )
    db.add(new_member)
    await db.commit()

    # Query back with user relationship loaded
    stmt = (
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.id == new_member.id)
    )
    res = await db.execute(stmt)
    created_member = res.scalar_one()

    return WorkspaceMemberRead.model_validate(created_member)


@router.delete(
    "/{id}/members/{user_id}",
    response_model=MessageResponse,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Member Not Found"),
    },
)
async def remove_workspace_member(
    id: uuid.UUID,
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.ADMIN))],
) -> MessageResponse:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == id,
        WorkspaceMember.user_id == user_id,
    )
    res = await db.execute(stmt)
    member = res.scalar_one_or_none()

    if member is None:
        raise NotFoundException(detail="Workspace member not found")

    if member.role == ResourceRole.OWNER:
        raise PermissionDeniedException(detail="Cannot remove workspace owner")

    await db.delete(member)
    await db.commit()

    return MessageResponse(message="Workspace member successfully removed")


@router.post(
    "/{id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires EDITOR/ADMIN/OWNER)"),
        404: error_response_schema(404, "Workspace Not Found"),
    },
)
async def create_workspace_project(
    id: uuid.UUID,
    project_in: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.EDITOR))],
) -> ProjectRead:
    project = Project(
        workspace_id=id,
        name=project_in.name,
        description=project_in.description,
        created_by_id=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectRead.model_validate(project)
