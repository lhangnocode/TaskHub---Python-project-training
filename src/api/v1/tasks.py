import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user, get_db
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
    error_response_schema,
)
from src.core.rbac import ResourceRole
from src.models.comment import Comment
from src.models.label import Label, TaskLabel
from src.models.project import Project
from src.models.task import Task
from src.models.user import User
from src.models.workspace import WorkspaceMember
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
    stmt = (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.assignee),
            selectinload(Task.reporter),
        )
        .where(Task.id == task_id)
    )
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()

    if task is None:
        raise NotFoundException(detail="Task not found")

    project = task.project
    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == project.workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    member_res = await db.execute(member_stmt)
    member = member_res.scalar_one_or_none()

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

    old_assignee_id = task.assignee_id
    new_assignee: User | None = None

    if task_update.assignee_id is not None and task_update.assignee_id != old_assignee_id:
        user_stmt = select(User).where(User.id == task_update.assignee_id)
        user_res = await db.execute(user_stmt)
        new_assignee = user_res.scalar_one_or_none()
        if new_assignee is None:
            raise NotFoundException(detail="New assignee user not found")
        task.assignee_id = task_update.assignee_id

    if task_update.title is not None:
        task.title = task_update.title
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.status is not None:
        task.status = task_update.status
    if task_update.priority is not None:
        task.priority = task_update.priority
    if task_update.due_date is not None:
        task.due_date = task_update.due_date

    db.add(task)
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
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.reporter),
        )
        .where(Task.id == id)
    )
    res = await db.execute(stmt)
    updated_task = res.scalar_one()

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

    # Allow delete if user is reporter/assignee or holds ADMIN/OWNER role
    is_owner_or_admin = member.role in (ResourceRole.OWNER, ResourceRole.ADMIN)
    is_author = task.reporter_id == current_user.id or task.assignee_id == current_user.id

    if not (is_owner_or_admin or is_author):
        raise PermissionDeniedException(
            detail="You do not have permission to delete this task"
        )

    await db.delete(task)
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

    # Verify label exists under workspace
    label_stmt = select(Label).where(
        Label.id == label_id,
        Label.workspace_id == project.workspace_id,
    )
    label_res = await db.execute(label_stmt)
    label = label_res.scalar_one_or_none()

    if label is None:
        raise NotFoundException(detail="Label not found in workspace")

    # Check existing association
    existing_stmt = select(TaskLabel).where(
        TaskLabel.task_id == id,
        TaskLabel.label_id == label_id,
    )
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none() is not None:
        raise ConflictException(detail="Label is already attached to task")

    task_label = TaskLabel(task_id=id, label_id=label_id)
    db.add(task_label)
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

    comment = Comment(
        task_id=id,
        author_id=current_user.id,
        content=comment_in.content,
    )
    db.add(comment)
    await db.commit()

    stmt = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment.id)
    )
    res = await db.execute(stmt)
    created_comment = res.scalar_one()

    return CommentRead.model_validate(created_comment)
