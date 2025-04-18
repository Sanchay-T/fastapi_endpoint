from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("api-keys/", views.APIKeyListCreateView.as_view(), name="api_keys"),
    path(
        "api-keys/<int:pk>/regenerate/",
        views.RegenerateKeyView.as_view(),
        name="regenerate_key",
    ),
    path("api-keys/<int:pk>/toggle/", views.ToggleKeyView.as_view(), name="toggle_key"),
    path("docs/", views.APIDocsView.as_view(), name="docs"),
]
