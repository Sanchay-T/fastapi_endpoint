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


class BankStatementAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for bank statement analysis request."""

    bank_names = serializers.ListField(child=serializers.CharField(), required=True)
    pdf_paths = serializers.ListField(child=serializers.CharField(), required=True)
    passwords = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    start_date = serializers.ListField(
        child=serializers.CharField(), required=True
    )  # Ideally DateField, but keeping as Char for simplicity matching FastAPI
    end_date = serializers.ListField(
        child=serializers.CharField(), required=True
    )  # Ideally DateField
    ca_id = serializers.CharField(required=True)
    # whole_transaction_sheet = serializers.ListField(child=serializers.DictField(), required=False, allow_null=True)
    # aiyazs_array_of_array = serializers.ListField(child=serializers.ListField(child=serializers.DictField()), required=False, allow_null=True)

    def validate(self, data):
        """Check that number of passwords matches number of pdfs if passwords are provided."""
        if data.get("passwords") and len(data.get("passwords")) != len(
            data.get("pdf_paths")
        ):
            raise serializers.ValidationError(
                f"Number of passwords ({len(data.get('passwords'))}) must match number of PDFs ({len(data.get('pdf_paths'))})"
            )
        if len(data.get("start_date")) != len(data.get("pdf_paths")):
            raise serializers.ValidationError(
                "Number of start dates must match number of PDFs."
            )
        if len(data.get("end_date")) != len(data.get("pdf_paths")):
            raise serializers.ValidationError(
                "Number of end dates must match number of PDFs."
            )
        if len(data.get("bank_names")) != len(data.get("pdf_paths")):
            raise serializers.ValidationError(
                "Number of bank names must match number of PDFs."
            )

        return data


class ExcelDownloadRequestSerializer(serializers.Serializer):
    """Serializer for Excel download request."""

    transaction_data = serializers.ListField(
        child=serializers.DictField(), required=True
    )
    name_n_num = serializers.ListField(child=serializers.DictField(), required=True)
    case_name = serializers.CharField(required=True)
