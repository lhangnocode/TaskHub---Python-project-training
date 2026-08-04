import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.workspace import Workspace, WorkspaceMember
from src.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Workspace, session)

    async def get_user_workspaces(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Workspace]:
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkspaceMember, session)

    async def get_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_workspace_members(
        self, workspace_id: uuid.UUID
    ) -> Sequence[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
