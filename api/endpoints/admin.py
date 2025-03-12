from django.contrib import admin
from .models import ApiKey, ScheduledTask


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "is_active",
        "is_expired",
        "created_at",
        "expires_at",
        "last_used_at",
    )
    list_filter = ("is_active", "created_at", "expires_at")
    search_fields = ("name", "user__username", "user__email")
    readonly_fields = ("key", "created_at", "updated_at", "last_used_at")
    fieldsets = (
        (None, {"fields": ("name", "key", "user")}),
        ("Status", {"fields": ("is_active", "expires_at")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "last_used_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "scheduled_at", "started_at", "completed_at")
    list_filter = ("status", "scheduled_at", "created_at")
    search_fields = ("name", "task_id")
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    )
    fieldsets = (
        (None, {"fields": ("name", "task_id", "status")}),
        ("Timing", {"fields": ("scheduled_at", "started_at", "completed_at")}),
        ("Results", {"fields": ("result", "error_message"), "classes": ("collapse",)}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
