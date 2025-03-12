"""
Tasks module for Celery background jobs.
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
import time

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_scheduled_task(self, task_id):
    """
    Process a scheduled task by its ID.

    Args:
        task_id: The ID of the ScheduledTask record

    Returns:
        dict: Results of the processed task
    """
    from .models import ScheduledTask

    logger.info(f"Starting scheduled task with ID: {task_id}")

    try:
        with transaction.atomic():
            # Get the task and update its status
            task = ScheduledTask.objects.select_for_update().get(id=task_id)
            task.status = "running"
            task.started_at = timezone.now()
            task.task_id = self.request.id  # Store the Celery task ID
            task.save(update_fields=["status", "started_at", "task_id"])

        # Simulate task processing
        time.sleep(5)  # Replace with actual processing
        result = {"processed": True, "time": timezone.now().isoformat()}

        # Update task as completed
        with transaction.atomic():
            task = ScheduledTask.objects.select_for_update().get(id=task_id)
            task.status = "completed"
            task.completed_at = timezone.now()
            task.result = result
            task.save(update_fields=["status", "completed_at", "result"])

        logger.info(f"Completed scheduled task with ID: {task_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}")

        # Update task as failed
        try:
            with transaction.atomic():
                task = ScheduledTask.objects.select_for_update().get(id=task_id)
                task.status = "failed"
                task.completed_at = timezone.now()
                task.error_message = str(e)
                task.save(update_fields=["status", "completed_at", "error_message"])
        except Exception as inner_e:
            logger.error(f"Failed to update task status: {str(inner_e)}")

        # Re-raise the exception to mark the Celery task as failed
        raise
