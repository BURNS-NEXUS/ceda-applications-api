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
- `filters.py` - Query parameters for filtering and pagination
- `schemas.py` - Pydantic schemas for request/response validation
- `router.py` - API endpoints

**Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/applications/` | Required | List applications visible to the current user |
| POST | `/applications/` | Required | Create a new application |
| GET | `/applications/{id}` | Required | Get specific application |
| PUT | `/applications/{id}` | Required | Update application |
| DELETE | `/applications/{id}` | Required | Delete application |

The list endpoint accepts non-negative `skip` and `take` query parameters, for
example `/api/applications/?skip=10&take=10`. `skip` defaults to 0; omitting
`take` returns all remaining applications. `take=0` returns an empty page.
The response contains `total`, the number of visible applications before
pagination and after filtering, and `data`, the requested page. Applications
are ordered by creation time, then ID, both descending. Offset pagination
can shift when applications are added or removed between requests.

Search and filtering are optional and can be combined; all filters are ANDed.

- `search` matches a case-insensitive substring in project title, company
  number, or email (OR across those fields).
- `status_in` and `status_not_in` accept repeated parameters, for example
  `?status_in=draft&status_in=submitted`. Status refers to the application's
  `state`. Supplying both applies inclusion and exclusion together.
- `created_at`, `updated_at`, `incorporation_date`, and `loan_amount` support
  the suffixes `_eq`, `_gt`, `_gte`, `_lt`, and `_lte`. For an inclusive
  between filter, combine `_gte` and `_lte`, for example
  `?loan_amount_gte=100&loan_amount_lte=500`.
  Dates use `YYYY-MM-DD`; created and updated timestamps are compared by
  calendar date in the configured Django time zone. Loan amounts use decimals.

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

### 3. Audit Logs Feature (`api/features/audit_logs/`)

`GET /api/audit-logs/` lists audit entries for authenticated users in the
`admin` group. Other authenticated users receive 403.

The endpoint accepts non-negative `skip` and `take` query parameters. `skip`
defaults to 0; omitting `take` returns all remaining entries, and `take=0`
returns an empty page. The response has `total` (before pagination) and `data`,
ordered by creation time and ID, both descending. Offset pagination can shift
when entries are added or removed.

Each entry includes `id`, `actor_id` (nullable), `action`, `resource_type`,
`resource_id`, `details`, and `created_at`. Deleting an actor retains the entry
and clears `actor_id`. This feature provides storage and retrieval only;
application actions do not automatically create audit entries.

### 4. Single Types Feature (`api/features/single_types/`)

Stores application-wide configuration in a singleton `SystemSettings` model.
Exactly one row exists, always with `pk=1`; `SystemSettings.load()` creates it
with defaults on first use, `save()` forces `pk=1`, and `delete()` is a no-op.

| Field | Type | Default | Validation |
| --- | --- | --- | --- |
| `site_name` | string | `"My App"` | 1–100 characters |
| `maintenance_mode` | boolean | `false` | — |
| `evaluators_per_application` | integer | `2` | Minimum `1` |

**Endpoints:**

| Method | Path | Auth / permission | Description |
| --- | --- | --- | --- |
| GET | `/api/settings` | Authenticated | Return current settings, creating defaults on first call |
| PATCH | `/api/settings` | `api.change_systemsettings` | Partially update settings, returning the full object |

`PATCH` only changes the fields present in the body; omitted fields are
preserved. Invalid values return `422`, a missing permission returns `403`, and
unauthenticated requests return `401`. All fields carry OpenAPI descriptions,
examples, and constraints, so the generated schema documents them fully.

### 5. Absentees Feature (`api/features/absentees/`)

Tracks employees who are absent or on leave. Only `User` records can be
absentees; each user has at most one absence record. Adding replaces the
previous record; removing clears it. Each record exposes `is_on_leave`
computed from today's date and the leave period.

**Model:** `Absentee` — `user` (FK), `leave_type` (vacation/sick/personal/
unpaid/other), `start_date`, `end_date` (nullable, open-ended), `reason`,
timestamps. Unique constraint on `user`.

**Endpoints:**

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/absentees` | Authenticated | List absences with `is_on_leave` |
| POST | `/api/absentees` | `api.add_absentee` | Add or update an absence |
| DELETE | `/api/absentees/{absentee_id}` | `api.delete_absentee` | Remove an absence |

### 6. Scoring Feature (`scoring/`)

A separate Django app providing flexible application scoring: admins define
criteria (weights, max scores, types), multiple scorers score each application
independently, and reporting aggregates results.

**Models:** `ScoringCriterion`, `ApplicationScoring` (one per scorer per
application), `ApplicationScore` (one per criterion per session). Permissions
are declared in `Meta.permissions` and enforced per-endpoint.

**Endpoints:** see README "Application scoring" section for the full permission
map and endpoint list. Score math lives in `scoring/services.py` and is shared
by admin and API.

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
