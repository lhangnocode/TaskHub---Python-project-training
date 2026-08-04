import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.comment import Comment
    from src.models.label import TaskLabel
    from src.models.project import Project
    from src.models.user import User


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Task(Base):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, native_enum=False),
        default=TaskStatus.TODO,
        nullable=False,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, native_enum=False),
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_tasks"
    )
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[reporter_id], back_populates="reported_tasks"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )
    task_labels: Mapped[list["TaskLabel"]] = relationship(
        "TaskLabel", back_populates="task", cascade="all, delete-orphan"
    )
