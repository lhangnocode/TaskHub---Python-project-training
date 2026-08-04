import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.label import Label, TaskLabel
from src.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Label, session)

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> Sequence[Label]:
        stmt = select(Label).where(Label.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_task_label(
        self, task_id: uuid.UUID, label_id: uuid.UUID
    ) -> TaskLabel | None:
        stmt = select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def attach_label_to_task(
        self, task_id: uuid.UUID, label_id: uuid.UUID
    ) -> TaskLabel:
        task_label = TaskLabel(task_id=task_id, label_id=label_id)
        self.session.add(task_label)
        await self.session.flush()
        return task_label

    async def detach_label_from_task(
        self, task_id: uuid.UUID, label_id: uuid.UUID
    ) -> bool:
        task_label = await self.get_task_label(task_id, label_id)
        if task_label is not None:
            await self.session.delete(task_label)
            await self.session.flush()
            return True
        return False
