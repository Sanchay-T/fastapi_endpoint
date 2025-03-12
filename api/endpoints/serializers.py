from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ApiKey, ScheduledTask


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("date_joined",)


class ApiKeySerializer(serializers.ModelSerializer):
    """Serializer for the ApiKey model."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApiKey
        fields = (
            "id",
            "name",
            "key",
            "user",
            "is_active",
            "is_expired",
            "expires_at",
            "last_used_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("key", "created_at", "updated_at", "last_used_at")

    def create(self, validated_data):
        # Key will be generated in the model's save method
        return super().create(validated_data)


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """Serializer for the ScheduledTask model."""

    class Meta:
        model = ScheduledTask
        fields = (
            "id",
            "name",
            "task_id",
            "status",
            "scheduled_at",
            "started_at",
            "completed_at",
            "result",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "task_id",
            "status",
            "started_at",
            "completed_at",
            "result",
            "error_message",
            "created_at",
            "updated_at",
        )


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for the health check endpoint."""

    status = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    components = serializers.DictField(child=serializers.BooleanField(read_only=True))
    info = serializers.DictField(child=serializers.CharField(read_only=True))
