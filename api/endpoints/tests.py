from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json
from .models import ApiKey, ScheduledTask


class HealthCheckTests(TestCase):
    """Tests for the health check endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("health_check")

    def test_health_check_returns_200(self):
        """Test that the health check endpoint returns a 200 status code."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the response contains the expected fields
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("components", data)
        self.assertIn("info", data)


class ApiKeyTests(TestCase):
    """Tests for the API key endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpassword",
            is_staff=True,
        )
        self.api_key = ApiKey.objects.create(name="Test API Key", user=self.user)
        self.url = reverse("apikey-list")
        self.detail_url = reverse("apikey-detail", args=[self.api_key.id])

    def test_list_api_keys_requires_authentication(self):
        """Test that listing API keys requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_own_api_keys(self):
        """Test that a user can list their own API keys."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_admin_can_list_all_api_keys(self):
        """Test that an admin can list all API keys."""
        # Create another API key for a different user
        ApiKey.objects.create(name="Another API Key", user=self.admin_user)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_regenerate_api_key(self):
        """Test that a user can regenerate their API key."""
        self.client.force_authenticate(user=self.user)
        original_key = self.api_key.key
        response = self.client.post(
            reverse("apikey-regenerate", args=[self.api_key.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from database
        self.api_key.refresh_from_db()
        self.assertNotEqual(original_key, self.api_key.key)


class ScheduledTaskTests(TestCase):
    """Tests for the scheduled task endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )
        self.task = ScheduledTask.objects.create(name="Test Task")
        self.url = reverse("scheduledtask-list")
        self.detail_url = reverse("scheduledtask-detail", args=[self.task.id])

    def test_list_tasks_requires_authentication(self):
        """Test that listing tasks requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_tasks(self):
        """Test that an authenticated user can list tasks."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_cancel_task(self):
        """Test that a task can be cancelled."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("scheduledtask-cancel", args=[self.task.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from database
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "cancelled")
