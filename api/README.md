# Django REST Framework API

A production-ready Django REST Framework API with comprehensive features for authentication, task scheduling, monitoring, and more.

## Features

- **Authentication & Authorization**
  - JWT Authentication with token refresh
  - OAuth2 support
  - API Key authentication for external services
  - Role-based permissions

- **API Documentation**
  - Swagger/OpenAPI documentation
  - ReDoc alternative view

- **Security**
  - CORS protection
  - Content Security Policy
  - Brute-force protection with Django Defender
  - Secure password validation

- **Performance**
  - Redis caching
  - Database connection pooling
  - Static file compression with Whitenoise

- **Background Processing**
  - Celery task queue
  - Scheduled tasks with Django Celery Beat
  - Task result tracking

- **Monitoring & Logging**
  - Health check endpoint
  - Prometheus metrics
  - Sentry error tracking
  - Comprehensive logging

- **Production Ready**
  - Environment-based configuration
  - PostgreSQL database support
  - Gunicorn/Uvicorn server
  - Docker support

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL (recommended for production)
- Redis (for caching and Celery)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the values as needed

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

### Running with Docker

1. Build the Docker image:
   ```
   docker-compose build
   ```

2. Start the services:
   ```
   docker-compose up
   ```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

## Development

### Running Tests

```
pytest
```

### Code Coverage

```
coverage run -m pytest
coverage report
```

## Deployment

### Preparing for Production

1. Set `DEBUG=False` in your `.env` file
2. Configure a proper `SECRET_KEY`
3. Set up a PostgreSQL database
4. Configure Redis for caching and Celery
5. Set up proper email settings

### Deployment Options

- **Heroku**: Ready to deploy with minimal configuration
- **Docker**: Use the provided Docker configuration
- **Traditional Hosting**: Use Gunicorn with Nginx

## License

This project is licensed under the MIT License - see the LICENSE file for details. 