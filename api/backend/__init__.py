"""
Backend package initialization.
"""

# Import Celery app instance for Django integration
from .celery import app as celery_app

__all__ = ("celery_app",)
