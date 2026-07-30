import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
    error_response_schema,
)
from src.core.rbac import ResourceRole
from src.models.project import Project
from src.models.task import Task
from src.models.user import User
from src.models.workspace import WorkspaceMember
from src.repositories.comment_repository import CommentRepository
from src.repositories.label_repository import LabelRepository
from src.repositories.task_repository import TaskRepository
from src.repositories.user_repository import UserRepository
from src.repositories.workspace_repository import WorkspaceMemberRepository
from src.schemas.comment import CommentCreate, CommentRead
from src.schemas.common import MessageResponse
from src.schemas.task import TaskRead, TaskUpdate
from src.services.cache_service import invalidate_project_tasks_cache
from src.services.notification_service import send_task_assignment_email

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def get_task_and_check_access(
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    required_role: ResourceRole = ResourceRole.VIEWER,
) -> tuple[Task, Project, WorkspaceMember]:
    task_repo = TaskRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    task = await task_repo.get_by_id_with_relations(task_id)
    if task is None:
        raise NotFoundException(detail="Task not found")

    project = task.project
    member = await member_repo.get_member(project.workspace_id, user_id)
    if member is None:
        raise PermissionDeniedException(detail="You are not a member of this workspace")

    return task, project, member


@router.patch(
    "/{id}",
    response_model=TaskRead,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Task Not Found"),
    },
)
async def update_task(
    id: uuid.UUID,
    task_update: TaskUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> TaskRead:
    task, project, _ = await get_task_and_check_access(
        id, current_user.id, db, ResourceRole.EDITOR
    )

    task_repo = TaskRepository(db)
    user_repo = UserRepository(db)

    old_assignee_id = task.assignee_id
    new_assignee: User | None = None

    if task_update.assignee_id is not None and task_update.assignee_id != old_assignee_id:
        new_assignee = await user_repo.get_by_id(task_update.assignee_id)
        if new_assignee is None:
            raise NotFoundException(detail="New assignee user not found")

    update_attrs = task_update.model_dump(exclude_unset=True)
    await task_repo.update(task, update_attrs)
    await db.commit()

    # Invalidate Redis Cache
    await invalidate_project_tasks_cache(project.id)

    # Queue email notification if assignee changed
    if new_assignee:
        send_task_assignment_email(
            background_tasks=background_tasks,
            recipient_email=new_assignee.email,
            recipient_name=new_assignee.full_name,
            task_title=task.title,
            project_name=project.name,
        )

    # Re-query updated task
    updated_task = await task_repo.get_by_id_with_relations(id)
    if updated_task is None:
        raise NotFoundException(detail="Task not found")

    return TaskRead.model_validate(updated_task)


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Task Not Found"),
    },
)
async def delete_task(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    task, project, member = await get_task_and_check_access(
        id, current_user.id, db, ResourceRole.VIEWER
    )
    task_repo = TaskRepository(db)

    # Allow delete if user is reporter/assignee or holds ADMIN/OWNER role
    is_owner_or_admin = member.role in (ResourceRole.OWNER, ResourceRole.ADMIN)
    is_author = task.reporter_id == current_user.id or task.assignee_id == current_user.id

    if not (is_owner_or_admin or is_author):
        raise PermissionDeniedException(
            detail="You do not have permission to delete this task"
        )

    await task_repo.delete(task)
    await db.commit()

    # Invalidate Redis Cache
    await invalidate_project_tasks_cache(project.id)

    return MessageResponse(message="Task successfully deleted")


@router.post(
    "/{id}/labels/{label_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Task or Label Not Found"),
        409: error_response_schema(409, "Label already attached"),
    },
)
async def attach_label_to_task(
    id: uuid.UUID,
    label_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    task, project, _ = await get_task_and_check_access(
        id, current_user.id, db, ResourceRole.EDITOR
    )
    label_repo = LabelRepository(db)

    # Verify label exists under workspace
    label = await label_repo.get_by_id(label_id)
    if label is None or label.workspace_id != project.workspace_id:
        raise NotFoundException(detail="Label not found in workspace")

    # Check existing association
    existing_task_label = await label_repo.get_task_label(id, label_id)
    if existing_task_label is not None:
        raise ConflictException(detail="Label is already attached to task")

    await label_repo.attach_label_to_task(id, label_id)
    await db.commit()

    await invalidate_project_tasks_cache(project.id)

    return MessageResponse(message="Label attached to task successfully")


@router.post(
    "/{id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Task Not Found"),
    },
)
async def create_task_comment(
    id: uuid.UUID,
    comment_in: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CommentRead:
    task, project, _ = await get_task_and_check_access(
        id, current_user.id, db, ResourceRole.VIEWER
    )
    comment_repo = CommentRepository(db)

    comment = await comment_repo.create(
        {
            "task_id": id,
            "author_id": current_user.id,
            "content": comment_in.content,
        }
    )
    await db.commit()

    created_comment = await comment_repo.get_by_id(comment.id)
    if created_comment is None:
        raise NotFoundException(detail="Comment not found")

    return CommentRead.model_validate(created_comment)
