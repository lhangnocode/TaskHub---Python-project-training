import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.task import Task, TaskPriority, TaskStatus
from src.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def get_by_id_with_relations(self, task_id: uuid.UUID) -> Task | None:
        stmt = (
            select(Task)
            .options(
                selectinload(Task.project),
                selectinload(Task.assignee),
                selectinload(Task.reporter),
            )
            .where(Task.id == task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_tasks_filtered(
        self,
        project_id: uuid.UUID,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[Sequence[Task], int]:
        query = select(Task).where(Task.project_id == project_id)
        count_query = (
            select(func.count()).select_from(Task).where(Task.project_id == project_id)
        )

        if status is not None:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)
        if priority is not None:
            query = query.where(Task.priority == priority)
            count_query = count_query.where(Task.priority == priority)
        if assignee_id is not None:
            query = query.where(Task.assignee_id == assignee_id)
            count_query = count_query.where(Task.assignee_id == assignee_id)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        query = (
            query.options(
                selectinload(Task.assignee),
                selectinload(Task.reporter),
            )
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        res = await self.session.execute(query)
        tasks = res.scalars().all()

        return tasks, total
