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