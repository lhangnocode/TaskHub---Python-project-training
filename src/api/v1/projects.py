import math
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import NotFoundException, PermissionDeniedException, error_response_schema
from src.core.rbac import ResourceRole, has_role_permission
from src.models.project import Project
from src.models.task import TaskPriority, TaskStatus
from src.models.user import User
from src.models.workspace import WorkspaceMember
from src.repositories.project_repository import ProjectRepository
from src.repositories.task_repository import TaskRepository
from src.repositories.user_repository import UserRepository
from src.repositories.workspace_repository import WorkspaceMemberRepository
from src.schemas.common import PaginatedResponse
from src.schemas.task import TaskCreate, TaskRead
from src.services.cache_service import (
    build_project_tasks_cache_key,
    get_cached_project_tasks,
    invalidate_project_tasks_cache,
    set_cached_project_tasks,
)
from src.services.notification_service import send_task_assignment_email

router = APIRouter(prefix="/projects", tags=["Projects & Tasks"])


async def check_project_access(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    required_role: ResourceRole = ResourceRole.VIEWER,
) -> tuple[Project, WorkspaceMember]:
    project_repo = ProjectRepository(db)
    member_repo = WorkspaceMemberRepository(db)

    project = await project_repo.get_by_id(project_id)
    if project is None:
        raise NotFoundException(detail="Project not found")

    member = await member_repo.get_member(project.workspace_id, user_id)
    if member is None:
        raise PermissionDeniedException(detail="You are not a member of this workspace")

    if not has_role_permission(member.role, required_role):
        raise PermissionDeniedException(
            detail=f"Required role: {required_role.value}, user role: {member.role.value}"
        )

    return project, member


@router.get(
    "/{id}/tasks",
    response_model=PaginatedResponse[TaskRead],
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied"),
        404: error_response_schema(404, "Project Not Found"),
    },
)
async def get_project_tasks(
    id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: TaskStatus | None = Query(None, description="Filter by status"),
    priority: TaskPriority | None = Query(None, description="Filter by priority"),
    assignee_id: uuid.UUID | None = Query(None, description="Filter by assignee UUID"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[TaskRead]:
    # Check access permission
    _, _ = await check_project_access(id, current_user.id, db, ResourceRole.VIEWER)

    # Redis Caching Check
    cache_key = build_project_tasks_cache_key(
        project_id=id,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )

    cached_data = await get_cached_project_tasks(cache_key)
    if cached_data:
        return PaginatedResponse[TaskRead].model_validate(cached_data)

    task_repo = TaskRepository(db)
    offset = (page - 1) * limit
    tasks, total = await task_repo.get_project_tasks_filtered(
        project_id=id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        skip=offset,
        limit=limit,
    )

    items = [TaskRead.model_validate(task) for task in tasks]
    total_pages = math.ceil(total / limit) if limit > 0 else 0

    response_payload = PaginatedResponse[TaskRead](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=total_pages,
    )

    # Save to Redis Cache
    await set_cached_project_tasks(cache_key, response_payload.model_dump(mode="json"))

    return response_payload


@router.post(
    "/{id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: error_response_schema(401, "Unauthorized"),
        403: error_response_schema(403, "Permission Denied (Requires EDITOR/ADMIN/OWNER)"),
        404: error_response_schema(404, "Project or Assignee Not Found"),
    },
)
async def create_project_task(
    id: uuid.UUID,
    task_in: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> TaskRead:
    project, _ = await check_project_access(id, current_user.id, db, ResourceRole.EDITOR)

    user_repo = UserRepository(db)
    task_repo = TaskRepository(db)

    assignee: User | None = None
    if task_in.assignee_id:
        assignee = await user_repo.get_by_id(task_in.assignee_id)
        if assignee is None:
            raise NotFoundException(detail="Assignee user not found")

    new_task = await task_repo.create(
        {
            "project_id": id,
            "title": task_in.title,
            "description": task_in.description,
            "status": task_in.status,
            "priority": task_in.priority,
            "assignee_id": task_in.assignee_id,
            "reporter_id": current_user.id,
            "due_date": task_in.due_date,
        }
    )
    await db.commit()

    # Invalidate Redis cache for this project's task queries
    await invalidate_project_tasks_cache(id)

    # Queue Email Notification if assigned
    if assignee:
        send_task_assignment_email(
            background_tasks=background_tasks,
            recipient_email=assignee.email,
            recipient_name=assignee.full_name,
            task_title=new_task.title,
            project_name=project.name,
        )

    # Re-query task with relationships loaded
    created_task = await task_repo.get_by_id_with_relations(new_task.id)
    if created_task is None:
        raise NotFoundException(detail="Created task not found")

    return TaskRead.model_validate(created_task)
