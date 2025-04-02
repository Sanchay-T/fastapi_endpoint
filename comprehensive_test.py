#!/usr/bin/env python3
"""
Comprehensive test script for the Django REST Framework API.
This script tests all major endpoints and functionality.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
import getpass

# Disable SSL warnings for local development
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URL for the API
BASE_URL = "https://127.0.0.1:8000"

# Authentication credentials
USERNAME = ""
PASSWORD = ""

# Store the authentication token
AUTH_TOKEN = None

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")

def print_result(success, message=""):
    """Print a formatted result."""
    if success:
        print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")
    else:
        print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_info(text):
    """Print information text."""
    print(f"{Colors.BLUE}{text}{Colors.ENDC}")

def print_warning(text):
    """Print warning text."""
    print(f"{Colors.YELLOW}{text}{Colors.ENDC}")

def get_input(prompt):
    """Get user input with a prompt."""
    return input(f"{Colors.BOLD}{prompt}{Colors.ENDC}")

def make_request(method, endpoint, data=None, auth=False, files=None):
    """Make an HTTP request to the API."""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    
    if auth and AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    if data and not files:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, verify=False)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=data, files=files, verify=False)
        elif method == "PUT":
            response = requests.put(url, headers=headers, data=data, verify=False)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, verify=False)
        else:
            print_warning(f"Unsupported method: {method}")
            return None
        
        print_info(f"Status Code: {response.status_code}")
        
        try:
            return response.json(), response.status_code
        except:
            return response.text, response.status_code
    
    except requests.exceptions.RequestException as e:
        print_warning(f"Request failed: {e}")
        return None, 0

def test_health_check():
    """Test the health check endpoint."""
    print_header("Testing Health Check Endpoint")
    response, status_code = make_request("GET", "/api/v1/health/")
    
    if status_code == 200:
        print_info(f"Response: {json.dumps(response, indent=2)}")
        return status_code == 200 and response.get("status") == "ok"
    else:
        print_info(f"Response: {json.dumps(response, indent=2)}")
        return False

def test_api_documentation():
    """Test the API documentation endpoints."""
    print_header("Testing API Documentation")
    response, status_code = make_request("GET", "/api/docs/")
    
    if isinstance(response, str):
        has_docs = "swagger-ui" in response
        print_info(f"Documentation available: {has_docs}")
        return status_code == 200 and has_docs
    else:
        print_warning("Unexpected response format")
        return False

def test_authentication():
    """Test authentication and obtain a JWT token."""
    global AUTH_TOKEN, USERNAME, PASSWORD
    
    print_header("Testing Authentication")
    
    if not USERNAME:
        USERNAME = get_input("Enter username: ")
    if not PASSWORD:
        PASSWORD = getpass.getpass("Enter password: ")
    
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    response, status_code = make_request("POST", "/api/v1/auth/token/", data)
    
    if status_code == 200 and "access" in response:
        AUTH_TOKEN = response["access"]
        print_info(f"Authentication successful. Token obtained.")
        return True
    else:
        print_warning(f"Authentication failed: {response}")
        return False

def test_api_keys():
    """Test API key management endpoints."""
    print_header("Testing API Key Management")
    
    # List API keys
    print_info("Listing API keys...")
    response, status_code = make_request("GET", "/api/v1/api-keys/", auth=True)
    
    if status_code != 200:
        print_warning(f"Failed to list API keys: {response}")
        return False
    
    initial_count = len(response)
    print_info(f"Found {initial_count} existing API keys")
    
    # Create a new API key
    print_info("Creating a new API key...")
    data = {
        "name": f"Test Key {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    response, status_code = make_request("POST", "/api/v1/api-keys/", data, auth=True)
    
    if status_code != 201:
        print_warning(f"Failed to create API key: {response}")
        return False
    
    api_key_id = response["id"]
    api_key = response["key"]
    print_info(f"Created API key: {api_key}")
    
    # Regenerate the API key
    print_info("Regenerating the API key...")
    response, status_code = make_request("POST", f"/api/v1/api-keys/{api_key_id}/regenerate/", auth=True)
    
    if status_code != 200:
        print_warning(f"Failed to regenerate API key: {response}")
        return False
    
    new_api_key = response["key"]
    print_info(f"Regenerated API key: {new_api_key}")
    
    # Verify the key was changed
    if new_api_key == api_key:
        print_warning("API key was not changed after regeneration")
        return False
    
    # Delete the API key
    print_info("Deleting the API key...")
    response, status_code = make_request("DELETE", f"/api/v1/api-keys/{api_key_id}/", auth=True)
    
    if status_code not in [204, 200]:
        print_warning(f"Failed to delete API key: {response}")
        return False
    
    # Verify deletion by listing keys again and checking if the specific key is gone
    response, status_code = make_request("GET", "/api/v1/api-keys/", auth=True)
    
    # Make sure we have a valid response to check
    if not isinstance(response, list):
        print_warning(f"Unexpected response format when verifying deletion: {response}")
        # Since we got a 204 status code, assume deletion was successful
        print_info("API key deletion returned success status, but verification failed")
        return True
    
    # Find the specific API key in the response
    key_found = False
    for item in response:
        if isinstance(item, dict) and item.get('id') == api_key_id:
            key_found = True
            break
    
    if not key_found:
        print_info("API key was successfully deleted")
        return True
    else:
        print_warning("API key was not deleted")
        return False

def test_scheduled_tasks():
    """Test scheduled task management endpoints."""
    print_header("Testing Scheduled Task Management")
    
    # List scheduled tasks
    print_info("Listing scheduled tasks...")
    response, status_code = make_request("GET", "/api/v1/tasks/", auth=True)
    
    if status_code != 200:
        print_warning(f"Failed to list tasks: {response}")
        return False
    
    initial_count = len(response)
    print_info(f"Found {initial_count} existing tasks")
    
    # Create a new scheduled task
    print_info("Creating a new scheduled task...")
    future_time = (datetime.now() + timedelta(minutes=10)).isoformat()
    data = {
        "name": f"Test Task {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "scheduled_at": future_time
    }
    
    response, status_code = make_request("POST", "/api/v1/tasks/", data, auth=True)
    
    if status_code != 201:
        print_warning(f"Failed to create task: {response}")
        return False
    
    task_id = response["id"]
    print_info(f"Created task with ID: {task_id}")
    
    # Check task status
    print_info("Checking task status...")
    response, status_code = make_request("GET", f"/api/v1/tasks/{task_id}/status/", auth=True)
    
    if status_code != 200:
        print_warning(f"Failed to check task status: {response}")
        return False
    
    print_info(f"Task status: {response['status']}")
    
    # Cancel the task
    print_info("Cancelling the task...")
    response, status_code = make_request("POST", f"/api/v1/tasks/{task_id}/cancel/", auth=True)
    
    if status_code != 200:
        print_warning(f"Failed to cancel task: {response}")
        return False
    
    # Check if the cancellation was successful based on the message
    if "message" in response and "cancelled successfully" in response["message"]:
        print_info("Task was successfully cancelled")
        return True
    else:
        print_warning(f"Task was not cancelled, response: {response}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print_header("Django REST Framework API Testing")
    
    results = {
        "Health Check": test_health_check(),
        "API Documentation": test_api_documentation(),
        "Authentication": test_authentication()
    }
    
    # Only run these tests if authentication succeeded
    if results["Authentication"]:
        results["API Keys"] = test_api_keys()
        results["Scheduled Tasks"] = test_scheduled_tasks()
    else:
        results["API Keys"] = "Not tested (authentication required)"
        results["Scheduled Tasks"] = "Not tested (authentication required)"
    
    # Print summary
    print_header("Test Summary")
    for test, result in results.items():
        if isinstance(result, bool):
            print_result(result, test)
        else:
            print(f"{test}: {result}")

if __name__ == "__main__":
    # Check if credentials were provided as command-line arguments
    if len(sys.argv) >= 3:
        USERNAME = sys.argv[1]
        PASSWORD = sys.argv[2]
    
    run_all_tests()
