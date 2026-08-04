import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.task import Task
    from src.models.workspace import Workspace


class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_label_name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(50), default="#3B82F6", nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="labels")
    task_labels: Mapped[list["TaskLabel"]] = relationship(
        "TaskLabel", back_populates="label", cascade="all, delete-orphan"
    )


class TaskLabel(Base):
    __tablename__ = "task_labels"
    __table_args__ = (UniqueConstraint("task_id", "label_id", name="uq_task_label"),)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    task: Mapped["Task"] = relationship("Task", back_populates="task_labels")
    label: Mapped["Label"] = relationship("Label", back_populates="task_labels")
