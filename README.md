## Decision tree (evolution)

Design decisions are recorded as they are made in the frontend repository's
README under **"Decision tree (evolution)"** — that is the system-wide log and
covers both repositories. Backend-specific entries currently include: the
Vercel-hosted Django API as the single source of truth, idempotent demo seeding
(`seed_demo_portal`), step-aware date validation on the wizard, and the
**hybrid evaluator assignment** model (expertise-ranked auto-assignment plus a
claim/decline pool). Read that section before changing workflow behaviour.

## Prerequisites
- Windows,Mac OS or linux, preferably linux or MacOS
- Python ~3.13.15 

## Run with Docker

With Docker and Docker Compose installed, start the API from the project root:

```bash
docker compose up --build -d
```


```bash
docker compose up -d
docker compose exec api python manage.py seed
```

The API will be available at http://localhost:8000. Migrations run automatically
when the container starts, and the SQLite database is kept in a Docker volume
when the container is stopped or recreated.

Stop the API with `Ctrl+C`, or run `docker compose down`. To remove the database
volume as well, run `docker compose down --volumes`.

## Commands
```bash
 uv run python manage.py seed
 #creates an admin and customer@ceda.local with password, don't run in production
```
```bash
 uv run python manage.py makemigrations
```
```bash
 uv run python manage.py migrate
```
## Project Structure

This API uses a **feature-based architecture** where each feature is a self-contained module handling a specific domain.

### Features

- **Auth** (`api/features/auth/`) - User registration, login, and authentication
- **Applications** (`api/features/applications/`) - Project applications with field `project_title`
- **Documents** (`api/features/documents/`) - Admin-managed document types and applicant uploads with review decisions
- **Absentees** (`api/features/absentees/`) - Tracks employees on leave / absent from work
- **Scoring** (`scoring/`) - Flexible application scoring with criteria, multiple scorers, and reporting
- **Single types** (`api/features/single_types/`) - Singleton application settings such as site name and maintenance mode

See [FEATURES.md](./FEATURES.md) for detailed API documentation.

## Current user permissions

`GET /api/me/permissions` returns the authenticated user's resolved Django
permissions, including permissions granted directly or through groups:

```json
{
  "user_id": "abc123",
  "username": "reviewer",
  "is_superuser": false,
  "permissions": [
    "api.review_application_document",
    "api.view_all_application_documents"
  ]
}
```

Use this endpoint to decide which management actions to show in a client.

## System settings (single types)

Application-wide configuration is stored as a **singleton**: exactly one
`SystemSettings` row, always with primary key `1`. `SystemSettings.load()`
creates the row with defaults the first time it is requested and always returns
that same record. Saving forces `pk=1`, and deleting the singleton is a no-op.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `site_name` | string | `"My App"` | Public name of the application, 1–100 characters |
| `maintenance_mode` | boolean | `false` | When true, clients show a maintenance notice |
| `evaluators_per_application` | integer | `2` | Evaluators assigned per application, minimum `1` |

Future settings can be added as model fields; the two endpoints keep working.

### API endpoints

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/settings` | Any authenticated user | Return the current settings (creating defaults on first call) |
| PATCH | `/api/settings` | `api.change_systemsettings` | Partially update settings and return the full object |

`PATCH` is a partial update: only the fields present in the request body change.
Omitted fields keep their current values. An empty body (`{}`) is valid and
returns the current settings unchanged.

Only the Django permission `api.change_systemsettings` is required to update
settings. No staff status, group, or role is needed — assign the permission
directly to a user in **Admin → Users → User permissions** (or through a group).
Superusers have it automatically. Reading settings only requires
authentication, so any signed-in client can display the site name and respect
maintenance mode.

Request and response example:

```bash
# Read the current settings
curl http://localhost:8000/api/settings -b cookies.txt

# Update only maintenance mode (other fields are preserved)
curl -X PATCH http://localhost:8000/api/settings \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"maintenance_mode": true}'
```

```json
{
  "site_name": "My App",
  "maintenance_mode": true,
  "evaluators_per_application": 2
}
```

`PATCH` returns `422` when a value is invalid, for example
`"evaluators_per_application": 0`, a blank `site_name`, or a non-boolean
`maintenance_mode`. A user without `api.change_systemsettings` receives `403`.
Unauthenticated requests receive `401`.

## Absentees (on leave)

Tracks employees who are absent from work or on leave. Only `User` records can be
absentees. Adding an absence for a user replaces any previous absence; removing
the record clears it. Each record exposes an `is_on_leave` flag computed from
today's date and the leave period.

### API endpoints

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/absentees` | Any authenticated user | List all absences with `is_on_leave` |
| POST | `/api/absentees` | `api.add_absentee` | Add or update an employee's absence |
| DELETE | `/api/absentees/{absentee_id}` | `api.delete_absentee` | Remove an absence record |

POST body:

```json
{
  "user_id": "abc123",
  "leave_type": "sick",
  "start_date": "2026-12-01",
  "end_date": "2026-12-14",
  "reason": "Medical appointment"
}
```

`leave_type` is one of `vacation`, `sick`, `personal`, `unpaid`, `other`.
`end_date` is optional (omit for open-ended leave). `start_date` must not be
after `end_date`.

## Application scoring

A flexible scoring system: admins define scoring criteria (weights, max scores,
types), multiple scorers score each application independently, and reporting
aggregates per-scorer and per-criterion results.

### Permissions

| Permission | Grants |
| --- | --- |
| `scoring.manage_scoring_criteria` | Create/update/delete scoring criteria |
| `scoring.view_scoringcriterion` | View scoring criteria |
| `scoring.score_application` | Submit scores for an application |
| `scoring.view_all_scores` | View scores of all scorers on any application |
| `scoring.finalize_scoring` | Override/edit submitted scores or mark scoring complete |
| `scoring.add/change/delete/view_applicationscoring` | Admin CRUD for scoring sessions |
| `scoring.add/change/delete/view_applicationscore` | Admin CRUD for scores |

### API endpoints

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET | `/api/scoring-criteria` | `scoring.view_scoringcriterion` | List active criteria (`?include_inactive=true` with manage) |
| POST | `/api/scoring-criteria` | `scoring.manage_scoring_criteria` | Create a criterion |
| GET | `/api/scoring-criteria/{id}` | `scoring.view_scoringcriterion` | Retrieve a criterion |
| PATCH | `/api/scoring-criteria/{id}` | `scoring.manage_scoring_criteria` | Update a criterion |
| DELETE | `/api/scoring-criteria/{id}` | `scoring.manage_scoring_criteria` | Delete (blocked if scores reference it) |
| GET | `/api/applications/{id}/scorings` | `score_application` or `view_all_scores` | List sessions (own unless view_all_scores) |
| GET | `/api/applications/{id}/scorings/me` | `score_application` | Get caller's session |
| PUT | `/api/applications/{id}/scorings/me` | `score_application` | Create/update caller's draft session (batch scores) |
| POST | `/api/applications/{id}/scorings/me/submit` | `score_application` | Submit (all required criteria must be scored) |
| GET | `/api/applications/{id}/scorings/{scoring_id}` | owner or `view_all_scores` | Retrieve a session |
| PATCH | `/api/applications/{id}/scorings/{scoring_id}` | owner or `finalize_scoring` | Edit a session |
| DELETE | `/api/applications/{id}/scorings/{scoring_id}` | own draft or `finalize_scoring` | Delete a session |
| GET | `/api/applications/{id}/scoring-summary` | `view_all_scores` | Per-scorer totals, per-criterion means, overall weighted mean |

Scoring criteria support `numeric` and `boolean` score types; boolean scores must
be `0` or the criterion maximum. Submitted sessions are immutable unless the
user has `finalize_scoring`.

## Application documents

Document type access is controlled with Django permissions. They can be
assigned to individual users in **Admin → Users → User permissions**; no group
or staff role is required.

| Permission | Grants |
| --- | --- |
| `api.view_all_document_types` | View inactive document types |
| `api.manage_document_types` | Create, update, and delete document types |
| `api.view_all_application_documents` | View documents for any application |
| `api.manage_all_application_documents` | Upload, replace, and delete documents for any application |
| `api.review_application_document` | Accept or reject documents |

Applicants do not need these permissions to manage their own application's
documents; ownership is checked for every applicant request. Superusers have
all permissions automatically.

### Managing document types

Document types can be managed through the API (permission required) or Django
Admin. `is_required` is set on create or update, so no separate endpoint is
needed to mark a type as required.

API example:

```bash
curl -X POST http://localhost:8000/api/document-types \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"name":"Tax Clearance","description":"Valid tax clearance","allowed_file_types":["pdf"],"is_required":true,"is_active":true}'
```

Document types that already have uploads cannot be deleted because the foreign
key is protected; set `is_active=false` instead to hide them from applicants.

### API endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/document-types` | Active document types (`?include_inactive=true` with permission) |
| POST | `/api/document-types` | Create a document type |
| GET | `/api/document-types/{document_type_id}` | Retrieve a document type |
| PATCH | `/api/document-types/{document_type_id}` | Update a document type (including `is_required`/`is_active`) |
| DELETE | `/api/document-types/{document_type_id}` | Delete an unused document type |
| GET | `/api/applications/{id}/documents` | List an application's documents |
| POST | `/api/applications/{id}/documents` | Upload a document (multipart: `file`, `document_type_id`, `file_description`) |
| GET | `/api/applications/{id}/documents/{document_id}` | Retrieve a document |
| PATCH | `/api/applications/{id}/documents/{document_id}` | Update the description or replace the file (multipart, or JSON for description only) |
| DELETE | `/api/applications/{id}/documents/{document_id}` | Delete a document |
| GET | `/api/applications/{id}/documents/required` | Required document types with upload progress |
| POST | `/api/applications/{id}/documents/{document_id}/decision` | Accept/reject a document (`api.review_application_document`, body `{"status", "reason"}`) |

Uploads are limited to 10MB by default (override with
`MAX_DOCUMENT_FILE_SIZE` in settings). Each application can hold one document
per document type; replacing a file resets its status to `pending`.