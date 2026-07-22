from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "referat_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Crucial for GPU/ML stability: only run ONE task at a time per worker to prevent VRAM allocation collisions!
    worker_concurrency=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Auto-discover tasks in app.tasks.meeting_pipeline
celery_app.autodiscover_tasks(["app.tasks.meeting_pipeline"], force=True)
