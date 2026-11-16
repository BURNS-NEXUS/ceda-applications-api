# API Features Structure

This document describes the feature-based architecture of the CEDA Applications API.

## Overview

The API is organized into self-contained features, each handling a specific domain. This modular approach makes it easy to:
- Develop and test features independently
- Reuse feature components across the application
- Scale features independently
- Maintain clear separation of concerns

## Features

### 1. Auth Feature (`api/features/auth/`)

Handles user authentication and authorization.

**Files:**
- `schemas.py` - Pydantic schemas for request/response validation
- `helpers.py` - Utility functions for email validation
- `router.py` - API endpoints

**Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auth/csrf` | None | Get CSRF token for protected requests |
| POST | `/auth/register` | None | Register a new user |
| POST | `/auth/login` | None | Login with email and password |
| POST | `/auth/logout` | Required | Logout current user |
| GET | `/auth/me` | Required | Get current user info |

**Schemas:**

```python
class LoginIn(Schema):
    email: str
    password: str

class RegisterIn(Schema):
    email: str
    password: str
    first_name: str
    last_name: str

class UserOut(Schema):
    id: str
    email: str
```

### 2. Applications Feature (`api/features/applications/`)

Manages user applications with project information.

**Files:**
- `schemas.py` - Pydantic schemas for request/response validation
- `router.py` - API endpoints

**Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/applications/` | Required | List all applications for current user |
| POST | `/applications/` | Required | Create a new application |
| GET | `/applications/{id}` | Required | Get specific application |
| PUT | `/applications/{id}` | Required | Update application |
| DELETE | `/applications/{id}` | Required | Delete application |

**Schemas:**

```python
class ApplicationIn(Schema):
    project_title: str

class ApplicationOut(Schema):
    id: str
    project_title: str
```

**Fields:**
- `project_title` (string) - The title of the application/project

## Health Check

A global health check endpoint is available:

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/health` | None | `{"status": "ok"}` |

## Directory Structure

```
api/
├── features/
│   ├── __init__.py              # Feature module initialization
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── schemas.py           # Auth request/response schemas
│   │   ├── helpers.py           # Auth utilities
│   │   └── router.py            # Auth endpoints
│   └── applications/
│       ├── __init__.py
│       ├── schemas.py           # Application request/response schemas
│       └── router.py            # Application endpoints
├── api.py                       # Main API initialization & routing
├── models.py                    # Django models
├── admin.py                     # Django admin
└── ...other files...
```

## Adding a New Feature

To add a new feature (e.g., `reports`):

1. Create feature directory:
   ```bash
   mkdir -p api/features/reports
   ```

2. Create required files:
   - `__init__.py` - Leave empty
   - `schemas.py` - Define Pydantic schemas
   - `router.py` - Define endpoints using `Router()`

3. Example `router.py`:
   ```python
   from ninja import Router
   
   router = Router()
   
   @router.get("/", response=list)
   def list_reports(request):
       return []
   ```

4. Update `api/features/__init__.py`:
   ```python
   from .reports.router import router as reports_router
   ```

5. Update `api/api.py`:
   ```python
   api.add_router("/reports", reports_router, tags=["reports"])
   ```

## Authentication

The API uses Django session-based authentication via cookies:
- Clients must include the `sessionid` cookie with requests
- Protected endpoints require the CSRF token in the `X-CSRFToken` header
- Get a CSRF token from the `/auth/csrf` endpoint

## Usage Examples

### Register a User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

### Create Application
```bash
curl -X POST http://localhost:8000/api/applications/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "project_title": "My First Project"
  }'
```

## Related Files

- Main API file: [api.py](/Users/raps/Documents/hackathons/botswana/ceda-applications-api/api/api.py)
- Django models: [models.py](/Users/raps/Documents/hackathons/botswana/ceda-applications-api/api/models.py)
- Django URL config: Check Django project settings for URL routing
