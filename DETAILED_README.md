# Django REST Framework API with Redis and Celery

## Project Overview

This project is a Django REST Framework (DRF) API that implements:

- **JWT Authentication**: Secure token-based authentication
- **API Key Management**: Create, regenerate, and delete API keys for external services
- **Scheduled Tasks**: Create and manage background tasks with Celery
- **Health Monitoring**: Endpoint to check system health (database, Redis)
- **Swagger Documentation**: Auto-generated API documentation

## System Architecture

```
┌─────────────┐     HTTP     ┌─────────────┐
│             │◄────────────►│             │
│   Client    │              │   Django    │
│             │              │    REST     │
└─────────────┘              │  Framework  │
                             │             │
                             └──────┬──────┘
                                    │
                                    │ ORM
                                    ▼
┌─────────────┐              ┌─────────────┐
│             │◄─────────────┤             │
│    Redis    │              │  Database   │
│             │              │             │
└──────┬──────┘              └─────────────┘
       │
       │ Message Broker
       ▼
┌─────────────┐
│             │
│   Celery    │
│   Workers   │
│             │
└─────────────┘
```

## Key Components

### 1. Django REST Framework
- **ViewSets**: Handle CRUD operations for models
- **Serializers**: Convert between Python objects and JSON
- **Authentication**: JWT token-based authentication
- **Permissions**: Control access to API endpoints

### 2. Redis
- **Caching**: Store cached data for faster access
- **Message Broker**: Queue for Celery tasks

### 3. Celery
- **Task Queue**: Process background tasks asynchronously
- **Scheduled Tasks**: Run tasks at specific times

## Project Structure

### Key Files

- **`backend/settings.py`**: Django configuration including database, Redis, and Celery settings
- **`backend/celery.py`**: Celery configuration and integration with Django
- **`endpoints/models.py`**: Data models including ApiKey and ScheduledTask
- **`endpoints/views.py`**: API endpoints and business logic
- **`endpoints/serializers.py`**: JSON serialization/deserialization
- **`endpoints/tasks.py`**: Celery task definitions

## Setup and Running

### Prerequisites

- Python 3.8+
- Redis server
- PostgreSQL (optional, falls back to SQLite)

### Environment Variables

```
# Database
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0

# Security
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Running the Services

#### 1. Start Redis Server

```bash
# Terminal 1
redis-server
```

#### 2. Start Celery Worker

```bash
# Terminal 2
source env/bin/activate
cd api
celery -A backend worker -l INFO
```

#### 3. Start Django Server with SSL

```bash
# Terminal 3
source env/bin/activate
cd api
python manage.py runserver_plus --cert-file local-cert.crt --key-file local-cert.key
```

## API Usage Guide

### 1. Authentication

Obtain a JWT token:

```bash
curl -k -X POST -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  https://127.0.0.1:8000/api/v1/auth/token/
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. Health Check

```bash
curl -k https://127.0.0.1:8000/api/v1/health/
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2025-03-29T12:00:00.000000",
  "components": {
    "database": true,
    "redis": true
  },
  "info": {
    "version": "1.0.0",
    "environment": "production"
  }
}
```

### 3. API Key Management

#### List API Keys

```bash
curl -k -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://127.0.0.1:8000/api/v1/api-keys/
```

#### Create API Key

```bash
curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My API Key"}' \
  https://127.0.0.1:8000/api/v1/api-keys/
```

#### Regenerate API Key

```bash
curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://127.0.0.1:8000/api/v1/api-keys/KEY_ID/regenerate/
```

#### Delete API Key

```bash
curl -k -X DELETE -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://127.0.0.1:8000/api/v1/api-keys/KEY_ID/
```

### 4. Scheduled Tasks

#### Create Task

```bash
curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Task","scheduled_at":"2025-03-30T12:00:00Z"}' \
  https://127.0.0.1:8000/api/v1/tasks/
```

#### Check Task Status

```bash
curl -k -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://127.0.0.1:8000/api/v1/tasks/TASK_ID/status/
```

#### Cancel Task

```bash
curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://127.0.0.1:8000/api/v1/tasks/TASK_ID/cancel/
```

## Data Flow Examples

### Example 1: Creating and Processing a Scheduled Task

1. **Client creates a task**:
   - POST request to `/api/v1/tasks/`
   - Task is saved to database with status "pending"

2. **Django schedules the task with Celery**:
   - `process_scheduled_task.apply_async(args=[task.id], eta=task.scheduled_at)`
   - Task information is serialized and sent to Redis

3. **Celery worker processes the task at the scheduled time**:
   - Worker retrieves task from Redis
   - Updates task status to "running"
   - Performs the task work
   - Updates task status to "completed" or "failed"

4. **Client checks task status**:
   - GET request to `/api/v1/tasks/{id}/status/`
   - API returns current status from database

### Example 2: API Key Authentication Flow

1. **User creates an API key**:
   - POST request to `/api/v1/api-keys/`
   - System generates a random key and stores it in the database

2. **External service uses the API key**:
   - Includes API key in request header
   - API validates the key against the database
   - If valid, processes the request

## Testing

A comprehensive test script is available at `/Users/sanchaythalnerkar/fastapi_endpoint/comprehensive_test.py`. This script tests all major API endpoints and functionality.

To run the tests:

```bash
source env/bin/activate
python comprehensive_test.py
```

The test script will verify:
- Health check endpoint
- API documentation
- Authentication
- API key management
- Scheduled task management

## Troubleshooting

### Common Issues

1. **Health check fails with Redis error**:
   - Ensure Redis server is running
   - Check Redis connection settings in `settings.py`

2. **Celery tasks not processing**:
   - Verify Celery worker is running
   - Check Redis connection
   - Look for errors in Celery worker logs

3. **Authentication failures**:
   - Ensure JWT token is valid and not expired
   - Check that token is correctly included in Authorization header

## Technical Deep Dive

### JWT Authentication

The API uses `djangorestframework-simplejwt` for JWT authentication:

- **Token Issuance**: `/api/v1/auth/token/`
- **Token Refresh**: `/api/v1/auth/token/refresh/`
- **Token Verification**: Handled by `JWTAuthentication` class

JWT tokens contain encoded user information and are signed with a secret key to prevent tampering.

### Celery Task Processing

Celery tasks are defined in `tasks.py` and scheduled through the API. The flow is:

1. Task is created and stored in the database
2. Task is scheduled with Celery using `apply_async`
3. Redis stores the task until the scheduled time
4. Celery worker picks up the task when it's due
5. Task updates its status in the database as it progresses

### Redis Integration

Redis serves two main purposes:

1. **Caching**: Django uses Redis as a cache backend through `django-redis`
2. **Message Broker**: Celery uses Redis to store and retrieve tasks

The Redis connection is configured in `settings.py` with fallback to localhost if not specified in environment variables.

### SSL/HTTPS

The API uses SSL certificates for secure communication:

- **local-cert.crt**: SSL certificate
- **local-cert.key**: Private key

These are used by Django's development server to provide HTTPS support.

## Step-by-Step Guide to Verify Everything Works

1. **Start all required services**:
   - Redis server
   - Celery worker
   - Django server with SSL

2. **Verify health check**:
   ```bash
   curl -k https://127.0.0.1:8000/api/v1/health/
   ```
   Ensure both database and Redis components show as `true`

3. **Get authentication token**:
   ```bash
   curl -k -X POST -H "Content-Type: application/json" \
     -d '{"username":"your_username","password":"your_password"}' \
     https://127.0.0.1:8000/api/v1/auth/token/
   ```
   Save the access token for subsequent requests

4. **Create an API key**:
   ```bash
   curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test API Key"}' \
     https://127.0.0.1:8000/api/v1/api-keys/
   ```
   Note the returned API key ID and key value

5. **Create a scheduled task**:
   ```bash
   curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Task","scheduled_at":"2025-03-30T12:00:00Z"}' \
     https://127.0.0.1:8000/api/v1/tasks/
   ```
   Note the returned task ID

6. **Check task status**:
   ```bash
   curl -k -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://127.0.0.1:8000/api/v1/tasks/TASK_ID/status/
   ```
   Verify the task status is "pending"

7. **Cancel the task**:
   ```bash
   curl -k -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://127.0.0.1:8000/api/v1/tasks/TASK_ID/cancel/
   ```
   Verify the response indicates successful cancellation

8. **Check task status again**:
   ```bash
   curl -k -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://127.0.0.1:8000/api/v1/tasks/TASK_ID/status/
   ```
   Verify the task status is now "cancelled"

## Conclusion

This Django REST Framework API provides a robust foundation for building secure, scalable web services with background task processing capabilities. The integration of Redis and Celery enables efficient handling of asynchronous operations, while JWT authentication ensures secure access to API endpoints.
