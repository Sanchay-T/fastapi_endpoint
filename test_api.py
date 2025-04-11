#!/usr/bin/env python
"""
Test script for the Django REST Framework API.
This script tests various endpoints and functionality of the API.
"""
import requests
import json
import sys
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Base URL for the API
BASE_URL = "https://127.0.0.1:8000/api/v1"
DOCS_URL = "https://127.0.0.1:8000/api/docs/"


# Test the health check endpoint (doesn't require authentication)
def test_health_check():
    print("\n=== Testing Health Check Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/health/", verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


# Test authentication with JWT
def test_authentication(username, password):
    print("\n=== Testing Authentication ===")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/token/",
            data={"username": username, "password": password},
            verify=False,
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            print("Authentication successful!")
            print(f"Access Token: {token_data.get('access')[:20]}...")
            print(f"Refresh Token: {token_data.get('refresh')[:20]}...")
            return token_data
        else:
            print(f"Authentication failed: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# Test API key management
def test_api_keys(access_token):
    print("\n=== Testing API Keys Endpoint ===")
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        # Get list of API keys
        response = requests.get(f"{BASE_URL}/api-keys/", headers=headers, verify=False)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            api_keys = response.json()
            print(f"API Keys: {json.dumps(api_keys, indent=2)}")
            return True
        else:
            print(f"Failed to get API keys: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


# Test scheduled tasks
def test_scheduled_tasks(access_token):
    print("\n=== Testing Scheduled Tasks Endpoint ===")
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        # Get list of tasks
        response = requests.get(f"{BASE_URL}/tasks/", headers=headers, verify=False)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            tasks = response.json()
            print(f"Tasks: {json.dumps(tasks, indent=2)}")
            return True
        else:
            print(f"Failed to get tasks: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


# Test API documentation
def test_api_docs():
    print("\n=== Testing API Documentation ===")
    try:
        response = requests.get(DOCS_URL, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Documentation available: {response.status_code == 200}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    print("=== Django REST Framework API Testing ===")

    # Test health check (no auth required)
    health_ok = test_health_check()

    # Test API docs
    docs_ok = test_api_docs()

    # Ask for credentials
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        username = input("Enter username: ")
        password = input("Enter password: ")

    # Test authentication
    token_data = test_authentication(username, password)

    if token_data:
        access_token = token_data.get("access")

        # Test API keys endpoint
        api_keys_ok = test_api_keys(access_token)

        # Test scheduled tasks endpoint
        tasks_ok = test_scheduled_tasks(access_token)

        print("\n=== Test Summary ===")
        print(f"Health Check: {'✅' if health_ok else '❌'}")
        print(f"API Documentation: {'✅' if docs_ok else '❌'}")
        print(f"Authentication: ✅")
        print(f"API Keys: {'✅' if api_keys_ok else '❌'}")
        print(f"Scheduled Tasks: {'✅' if tasks_ok else '❌'}")
    else:
        print("\n=== Test Summary ===")
        print(f"Health Check: {'✅' if health_ok else '❌'}")
        print(f"API Documentation: {'✅' if docs_ok else '❌'}")
        print(f"Authentication: ❌")
        print("API Keys: Not tested (authentication required)")
        print("Scheduled Tasks: Not tested (authentication required)")


if __name__ == "__main__":
    main()
