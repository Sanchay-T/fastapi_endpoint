from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Register viewsets
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"api-keys", views.ApiKeyViewSet, basename="apikey")
router.register(r"tasks", views.ScheduledTaskViewSet, basename="scheduledtask")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Add any non-viewset API endpoints here
    path("health/", views.health_check, name="health_check"),
]
