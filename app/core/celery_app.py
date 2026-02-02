"""Celery application configuration."""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.sync_tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    # Enable task events for Flower monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Schedule: Run sync_data_folder_changes every 2 minutes
celery_app.conf.beat_schedule = {
    "sync-data-folder-every-2-minutes": {
        "task": "app.tasks.sync_tasks.sync_data_folder_changes_task",
        "schedule": 120.0,  # 2 minutes in seconds
    },
}
