import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Create the Celery app
app = Celery("backend")

# Use settings from Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load tasks from all registered Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task for testing Celery functionality."""
    print(f"Request: {self.request!r}")
