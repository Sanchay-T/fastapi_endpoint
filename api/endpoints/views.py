from django.shortcuts import render
from django.db import connection
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status, viewsets, filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import datetime
import redis
import json
from celery.result import AsyncResult

from .models import ApiKey, ScheduledTask
from .serializers import (
    UserSerializer,
    ApiKeySerializer,
    ScheduledTaskSerializer,
    HealthCheckSerializer,
)
from backend.celery import app as celery_app

# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint that verifies the system components are operational.
    This endpoint is exempt from authentication to allow for monitoring tools.
    """
    health_data = {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {
            "database": False,
            "redis": False,
        },
        "info": {
            "version": "1.0.0",
            "environment": settings.DEBUG and "development" or "production",
        },
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_data["components"]["database"] = True
    except Exception as e:
        health_data["components"]["database"] = False
        health_data["status"] = "error"
        health_data["errors"] = {"database": str(e)}

    # Check Redis if configured
    try:
        if (
            hasattr(settings, "CACHES")
            and settings.CACHES.get("default", {}).get("BACKEND")
            == "django_redis.cache.RedisCache"
        ):
            redis_url = settings.CACHES["default"]["LOCATION"]
            r = redis.from_url(redis_url)
            r.ping()
            health_data["components"]["redis"] = True
    except Exception as e:
        health_data["components"]["redis"] = False
        health_data["status"] = "error"
        if not health_data.get("errors"):
            health_data["errors"] = {}
        health_data["errors"]["redis"] = str(e)

    # Return appropriate HTTP status code based on health
    response_status = (
        status.HTTP_200_OK
        if health_data["status"] == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(health_data, status=response_status)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing and retrieving users.
    Only accessible to admins.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined"]


class ApiKeyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing API keys.
    """

    serializer_class = ApiKeySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at", "expires_at"]

    def get_queryset(self):
        """Filter API keys to show only those belonging to the current user or all keys for admins."""
        user = self.request.user
        if user.is_staff:
            return ApiKey.objects.all()
        return ApiKey.objects.filter(user=user)

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Regenerate the API key."""
        api_key = self.get_object()
        api_key.key = api_key.generate_key()
        api_key.save(update_fields=["key"])
        return Response(
            {"message": "API key regenerated successfully", "key": api_key.key}
        )


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing scheduled tasks.
    """

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["name"]
    ordering_fields = ["name", "scheduled_at", "status"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel the task if it hasn't started yet."""
        task = self.get_object()
        if task.status == "pending":
            if task.task_id:
                celery_app.control.revoke(task.task_id, terminate=True)
            task.status = "cancelled"
            task.save(update_fields=["status"])
            return Response({"message": "Task cancelled successfully"})
        return Response(
            {"message": f"Cannot cancel task with status {task.status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get the current status of a task."""
        task = self.get_object()
        result = None

        if task.task_id:
            # Get the task result from Celery
            async_result = AsyncResult(task.task_id)

            if async_result.state == "PENDING":
                task.status = "pending"
            elif async_result.state == "STARTED":
                task.status = "running"
                if not task.started_at:
                    task.started_at = timezone.now()
            elif async_result.state == "SUCCESS":
                task.status = "completed"
                task.result = async_result.result
                if not task.completed_at:
                    task.completed_at = timezone.now()
            elif async_result.state == "FAILURE":
                task.status = "failed"
                task.error_message = str(async_result.result)
                if not task.completed_at:
                    task.completed_at = timezone.now()

            task.save()

        return Response(
            {
                "task_id": task.task_id,
                "status": task.status,
                "scheduled_at": task.scheduled_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "error_message": task.error_message,
            }
        )
