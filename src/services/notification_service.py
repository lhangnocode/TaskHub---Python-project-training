import logging
from typing import Any

from fastapi import BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from src.config import settings

logger = logging.getLogger(__name__)

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
    SUPPRESS_SEND=settings.SUPPRESS_SEND,
)

fastmail = FastMail(mail_config)


def send_task_assignment_email(
    background_tasks: BackgroundTasks,
    recipient_email: str,
    recipient_name: str,
    task_title: str,
    project_name: str,
) -> None:
    """Queue background task email notification for task assignment using FastAPI-Mail."""
    html_content = f"""
    <h3>Hello {recipient_name},</h3>
    <p>You have been assigned a new task on <strong>TaskHub</strong>:</p>
    <ul>
        <li><strong>Task Title:</strong> {task_title}</li>
        <li><strong>Project:</strong> {project_name}</li>
    </ul>
    <p>Log in to TaskHub to review and manage your assigned task.</p>
    """

    message = MessageSchema(
        subject=f"[TaskHub] Assigned Task: {task_title}",
        recipients=[recipient_email],
        body=html_content,
        subtype=MessageType.html,
    )

    try:
        background_tasks.add_task(fastmail.send_message, message)
        logger.info("Queued task assignment email notification to %s", recipient_email)
    except Exception as exc:
        logger.error("Failed to queue task assignment email to %s: %s", recipient_email, exc)
