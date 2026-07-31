import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, require_workspace_role
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
    error_response_schema,
)
from src.core.rbac import ResourceRole
from src.models.user import User
from src.models.workspace import WorkspaceMember
from src.repositories.project_repository import ProjectRepository
from src.repositories.user_repository import UserRepository
from src.repositories.workspace_repository import WorkspaceMemberRepository, WorkspaceRepository
from src.schemas.common import MessageResponse
from src.schemas.project import ProjectCreate, ProjectRead
from src.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceMemberRoleUpdate,
    WorkspaceRead,
    WorkspaceUpdate,
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
    workspace_repo = WorkspaceRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    workspace = await workspace_repo.create(
        {
            "name": workspace_in.name,
            "description": workspace_in.description,
            "owner_id": current_user.id,
        }
    )

    # Creator automatically becomes OWNER member
    await member_repo.create(
        {
            "workspace_id": workspace.id,
            "user_id": current_user.id,
            "role": ResourceRole.OWNER,
        }
    )
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
    workspace_repo = WorkspaceRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    workspace = await workspace_repo.get_by_id(id)
    if workspace is None:
        raise NotFoundException(detail="Workspace not found")

    member = await member_repo.get_member(id, current_user.id)
    if member is None:
        raise PermissionDeniedException(detail="You are not a member of this workspace")

    return WorkspaceRead.model_validate(workspace)


@router.patch(
    "/{id}",
    response_model=WorkspaceRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires ADMIN/OWNER)"),
        404: error_response_schema(404, "Workspace Not Found"),
    },
)
async def update_workspace(
    id: uuid.UUID,
    workspace_update: WorkspaceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.ADMIN))],
) -> WorkspaceRead:
    workspace_repo = WorkspaceRepository(db)

    workspace = await workspace_repo.get_by_id(id)
    if workspace is None:
        raise NotFoundException(detail="Workspace not found")

    update_attrs = workspace_update.model_dump(exclude_unset=True)
    updated_workspace = await workspace_repo.update(workspace, update_attrs)
    await db.commit()
    await db.refresh(updated_workspace)

    return WorkspaceRead.model_validate(updated_workspace)


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires OWNER)"),
        404: error_response_schema(404, "Workspace Not Found"),
    },
)
async def delete_workspace(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.OWNER))],
) -> MessageResponse:
    workspace_repo = WorkspaceRepository(db)

    workspace = await workspace_repo.get_by_id(id)
    if workspace is None:
        raise NotFoundException(detail="Workspace not found")

    await workspace_repo.delete(workspace)
    await db.commit()

    return MessageResponse(message="Workspace successfully deleted")


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
    user_repo = UserRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    target_user = await user_repo.get_by_id(member_in.user_id)
    if target_user is None:
        raise NotFoundException(detail="Target user not found")

    existing_member = await member_repo.get_member(id, member_in.user_id)
    if existing_member is not None:
        raise ConflictException(detail="User is already a member of this workspace")

    new_member = await member_repo.create(
        {
            "workspace_id": id,
            "user_id": member_in.user_id,
            "role": member_in.role,  # Defaults to VIEWER
        }
    )
    await db.commit()

    created_member = await member_repo.get_by_id(new_member.id)

    return WorkspaceMemberRead.model_validate(created_member)


@router.patch(
    "/{id}/members/{user_id}",
    response_model=WorkspaceMemberRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires ADMIN/OWNER)"),
        404: error_response_schema(404, "Member Not Found"),
    },
)
async def update_workspace_member_role(
    id: uuid.UUID,
    user_id: uuid.UUID,
    role_update: WorkspaceMemberRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[WorkspaceMember, Depends(require_workspace_role(ResourceRole.ADMIN))],
) -> WorkspaceMemberRead:
    member_repo = WorkspaceMemberRepository(db)

    member = await member_repo.get_member(id, user_id)
    if member is None:
        raise NotFoundException(detail="Workspace member not found")

    if member.role == ResourceRole.OWNER:
        raise PermissionDeniedException(detail="Cannot modify workspace owner role")

    updated_member = await member_repo.update(member, {"role": role_update.role})
    await db.commit()

    reloaded_member = await member_repo.get_by_id(updated_member.id)
    return WorkspaceMemberRead.model_validate(reloaded_member)


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
    member_repo = WorkspaceMemberRepository(db)

    member = await member_repo.get_member(id, user_id)
    if member is None:
        raise NotFoundException(detail="Workspace member not found")

    if member.role == ResourceRole.OWNER:
        raise PermissionDeniedException(detail="Cannot remove workspace owner")

    await member_repo.delete(member)
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
    project_repo = ProjectRepository(db)

    project = await project_repo.create(
        {
            "workspace_id": id,
            "name": project_in.name,
            "description": project_in.description,
            "created_by_id": current_user.id,
        }
    )
    await db.commit()
    await db.refresh(project)

    return ProjectRead.model_validate(project)
