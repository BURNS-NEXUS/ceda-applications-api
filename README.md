## Prerequisites
- Windows,Mac OS or linux, preferably linux or MacOS
- Python ~3.13.15 

## Run with Docker

With Docker and Docker Compose installed, start the API from the project root:

```bash
docker compose up --build
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

See [FEATURES.md](./FEATURES.md) for detailed API documentation.