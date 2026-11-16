# Quick Reference - Feature-Based API Organization

## 📁 New Directory Structure

```
api/
├── features/                    ← NEW: Feature modules container
│   ├── __init__.py              ← Exports routers
│   ├── auth/                    ← Auth feature
│   │   ├── __init__.py
│   │   ├── schemas.py           ← LoginIn, RegisterIn, UserOut
│   │   ├── helpers.py           ← Email validation
│   │   └── router.py            ← Auth endpoints (register, login, logout, me, csrf)
│   └── applications/            ← Applications feature
│       ├── __init__.py
│       ├── schemas.py           ← ApplicationIn, ApplicationOut
│       └── router.py            ← Application endpoints (CRUD)
│
├── api.py                       ← REFACTORED: Main API (registers features)
├── models.py                    ← User model (unchanged)
├── schemas.py                   ← DEPRECATED: Moved to features/auth/schemas.py
├── helpers.py                   ← DEPRECATED: Moved to features/auth/helpers.py
└── ...other files...
```

## 🎯 Key Changes

### ✅ What Changed
1. **Created `features/` directory** - Organizes code by domain/feature
2. **Split auth logic** into `features/auth/`:
   - `schemas.py` - Request/response validation
   - `helpers.py` - Utility functions
   - `router.py` - Endpoints

3. **Created `features/applications/`** - New feature for project applications
   - `schemas.py` - ApplicationIn/Out schemas
   - `router.py` - CRUD endpoints (ready for implementation)

4. **Refactored `api.py`** - Now cleanly registers feature routers

### ⚠️ Deprecation Notice
The following old files in `api/` can now be removed:
- `schemas.py` (moved to `features/auth/schemas.py`)
- `helpers.py` (moved to `features/auth/helpers.py`)

## 🚀 API Endpoints

### Auth Feature
```
GET    /api/auth/csrf              (no auth)
POST   /api/auth/register          (no auth)
POST   /api/auth/login             (no auth)
POST   /api/auth/logout            (auth required)
GET    /api/auth/me                (auth required)
```

### Applications Feature
```
GET    /api/applications/          (auth required) - List all
POST   /api/applications/          (auth required) - Create
GET    /api/applications/{id}      (auth required) - Get one
PUT    /api/applications/{id}      (auth required) - Update
DELETE /api/applications/{id}      (auth required) - Delete
```

### Health
```
GET    /api/health                 (no auth)
```

## 📋 Application Model Fields

The `ApplicationOut` and `ApplicationIn` schemas currently define:
- **project_title** (string) - The title of the application/project

## 🔧 Adding a New Feature

1. Create folder: `api/features/my_feature/`
2. Create files:
   - `__init__.py`
   - `schemas.py` (Pydantic schemas)
   - `router.py` (Endpoints with Router())
   - `helpers.py` (optional, for utilities)

3. Export in `api/features/__init__.py`:
   ```python
   from .my_feature.router import router as my_feature_router
   ```

4. Register in `api/api.py`:
   ```python
   api.add_router("/my-feature", my_feature_router, tags=["my_feature"])
   ```

## ✨ Benefits of This Structure

- **Modularity**: Each feature is independent
- **Scalability**: Easy to add new features
- **Testability**: Can test features in isolation
- **Maintainability**: Clear separation of concerns
- **Reusability**: Feature components can be shared

## 📚 Documentation

Full API documentation: See [FEATURES.md](./FEATURES.md)
