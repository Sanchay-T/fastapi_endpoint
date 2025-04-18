import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import TemplateView, View
from endpoints.models import ApiKey

logger = logging.getLogger(__name__)

# Create your views here.


class LandingView(TemplateView):
    template_name = "portal/landing.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the user's API keys for quick access
        context["api_keys"] = ApiKey.objects.filter(user=self.request.user)
        return context


class APIKeyListCreateView(LoginRequiredMixin, View):
    template_name = "portal/api_keys.html"

    def get(self, request):
        # Get all API keys for the current user
        logger.info(f"Fetching API keys for user: {request.user.username}")
        api_keys = ApiKey.objects.filter(user=request.user)
        return render(request, self.template_name, {"api_keys": api_keys})

    def post(self, request):
        logger.info("--- Hitting APIKeyListCreateView POST ---")
        logger.debug(f"POST data: {request.POST}")

        name = request.POST.get("name", f"Key {timezone.now().strftime('%Y-%m-%d')}")
        expires_days_str = request.POST.get("expires_days", "365")

        logger.info(
            f"Attempting to create key with name: '{name}', expires in: {expires_days_str} days"
        )

        try:
            expires_days = int(expires_days_str)
            if expires_days <= 0:
                raise ValueError("Expiration days must be positive.")

            expires_at = timezone.now() + timezone.timedelta(days=expires_days)

            # Create the API key
            logger.info(f"Creating ApiKey for user {request.user.username}...")
            new_key = ApiKey.objects.create(
                name=name, user=request.user, expires_at=expires_at
            )
            logger.info(f"Successfully created ApiKey with ID: {new_key.id}")
            messages.success(request, f"API key '{name}' created successfully.")

        except ValueError as ve:
            logger.warning(
                f"Invalid input for expires_days: {expires_days_str}. Error: {ve}"
            )
            messages.error(request, f"Invalid value provided for expiration: {ve}")
        except Exception as e:
            logger.error(
                f"--- ERROR creating ApiKey for user {request.user.username}: {e} ---",
                exc_info=True,
            )
            messages.error(
                request, f"An unexpected error occurred while creating the API key: {e}"
            )

        logger.info("Redirecting back to portal:api_keys")
        return redirect("portal:api_keys")


class RegenerateKeyView(LoginRequiredMixin, View):
    def post(self, request, pk):
        logger.info(f"Regenerating key ID {pk} for user {request.user.username}")
        api_key = get_object_or_404(ApiKey, id=pk, user=request.user)
        try:
            api_key.key = api_key.generate_key()
            api_key.save(update_fields=["key", "updated_at"])
            logger.info(f"Successfully regenerated key ID {pk}")
            messages.success(request, f"API key '{api_key.name}' has been regenerated.")
        except Exception as e:
            logger.error(f"Error regenerating key ID {pk}: {e}", exc_info=True)
            messages.error(request, "Failed to regenerate the key.")
        return redirect("portal:api_keys")


class ToggleKeyView(LoginRequiredMixin, View):
    def post(self, request, pk):
        logger.info(f"Toggling key ID {pk} for user {request.user.username}")
        api_key = get_object_or_404(ApiKey, id=pk, user=request.user)
        try:
            api_key.is_active = not api_key.is_active
            api_key.save(update_fields=["is_active", "updated_at"])
            status_text = "activated" if api_key.is_active else "deactivated"
            logger.info(f"Successfully {status_text} key ID {pk}")
            messages.success(
                request, f"API key '{api_key.name}' has been {status_text}."
            )
        except Exception as e:
            logger.error(f"Error toggling key ID {pk}: {e}", exc_info=True)
            messages.error(request, "Failed to update the key status.")
        return redirect("portal:api_keys")


class APIDocsView(LoginRequiredMixin, View):
    template_name = "portal/docs.html"

    def get(self, request):
        logger.info(
            f"Fetching active API keys for docs view for user {request.user.username}"
        )
        api_keys = ApiKey.objects.filter(user=request.user, is_active=True)

        if not api_keys.exists():
            logger.warning(
                f"User {request.user.username} has no active API keys. Redirecting to create one."
            )
            messages.warning(
                request,
                "You don't have any active API keys. Create one to use the API.",
            )
            return redirect("portal:api_keys")

        return render(
            request,
            self.template_name,
            {
                "api_keys": api_keys,
                "swagger_url": "/api/docs/",  # Link to Swagger UI
            },
        )
