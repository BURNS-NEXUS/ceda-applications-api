## Prerequisites
- Windows or linux, preferably linux
- Python > 3.14 

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