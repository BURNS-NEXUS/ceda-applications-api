# API Architecture Diagram

## Request Flow

```
HTTP Request
    ↓
Django Middleware (Sessions, CSRF)
    ↓
api/api.py (NinjaAPI)
    ↓
Feature Routers
    ├─→ /auth → features/auth/router.py
    │   ├─ POST /register → RegisterIn → UserOut
    │   ├─ POST /login → LoginIn → UserOut
    │   ├─ POST /logout
    │   ├─ GET /me → UserOut
    │   └─ GET /csrf
    │
    ├─→ /applications → features/applications/router.py
    │   ├─ POST / → ApplicationIn → ApplicationOut
    │   ├─ GET / → ApplicationOut[]
    │   ├─ GET /{id} → ApplicationOut
    │   ├─ PUT /{id} → ApplicationIn → ApplicationOut
    │   └─ DELETE /{id}
    │
    └─→ /health (global) → {"status": "ok"}
    ↓
Response (JSON)
```

## Module Dependency Graph

```
api/
├── api.py (main entry point)
│   └── imports from features/__init__.py
│
└── features/
    ├── __init__.py (exports all routers)
    │   ├── auth/
    │   │   ├── router.py (uses schemas, helpers)
    │   │   ├── schemas.py (Pydantic models)
    │   │   └── helpers.py (utilities)
    │   │
    │   └── applications/
    │       ├── router.py (uses schemas)
    │       └── schemas.py (Pydantic models)
```

## Feature Isolation

```
┌─────────────────────────────────────────────┐
│          CEDA Applications API              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐    ┌──────────────────┐  │
│  │   Auth       │    │  Applications    │  │
│  │  Feature     │    │  Feature         │  │
│  │              │    │                  │  │
│  │ • schemas.py │    │ • schemas.py     │  │
│  │ • router.py  │    │ • router.py      │  │
│  │ • helpers.py │    │ • (models TBD)   │  │
│  │              │    │                  │  │
│  │ Endpoints:   │    │ Endpoints:       │  │
│  │ • /register  │    │ • / (LIST)       │  │
│  │ • /login     │    │ • / (CREATE)     │  │
│  │ • /logout    │    │ • /{id} (READ)   │  │
│  │ • /me        │    │ • /{id} (UPDATE) │  │
│  │ • /csrf      │    │ • /{id} (DELETE) │  │
│  │              │    │                  │  │
│  └──────────────┘    └──────────────────┘  │
│         ↑                      ↑            │
│         └──────────────────────┘            │
│           Registered via                    │
│         features/__init__.py                │
└─────────────────────────────────────────────┘
```

## Adding a New Feature

```
                         Create Feature
                              ↓
                    mkdir features/new_feature
                              ↓
                    Create __init__.py ✓
                              ↓
                    Create schemas.py
                      (Pydantic models)
                              ↓
                    Create router.py
                      (Endpoints with Router())
                              ↓
                    Create helpers.py (optional)
                      (Utilities)
                              ↓
                    Update features/__init__.py
                      (export router)
                              ↓
                    Update api/api.py
                      (register router)
                              ↓
                    Feature Ready! 🎉
```

## Example: Creating Reports Feature

```python
# Step 1: Create api/features/reports/schemas.py
from ninja import Schema

class ReportOut(Schema):
    id: str
    title: str
    created_at: str

class ReportIn(Schema):
    title: str


# Step 2: Create api/features/reports/router.py
from ninja import Router
from .schemas import ReportOut, ReportIn

router = Router()

@router.get("/", response=list[ReportOut])
def list_reports(request):
    return []

@router.post("/", response={201: ReportOut})
def create_report(request, payload: ReportIn):
    pass


# Step 3: Update api/features/__init__.py
from .reports.router import router as reports_router

# Step 4: Update api/api.py
api.add_router("/reports", reports_router, tags=["reports"])

# Result: New endpoints!
# GET  /api/reports/
# POST /api/reports/
```

## Authentication Flow

```
Client Request
    ↓
Has sessionid cookie? 
    ├─ No → Django Auth returns None
    │       └─ Endpoint requires auth? → 401 Unauthorized
    │
    └─ Yes → Django loads User from session
            └─ Available as request.auth
               ├─ For protected endpoints: ✓ Access granted
               └─ For public endpoints: ✓ Available but optional
```

## Data Flow Example: Creating Application

```
Client: POST /applications/
├─ Headers: 
│  ├─ Content-Type: application/json
│  ├─ X-CSRFToken: <token>
│  ├─ Cookie: sessionid=<session>
│
└─ Body: { "project_title": "My Project" }
        ↓
Django validates CSRF + loads user
        ↓
router.create_application(request, payload)
        ↓
ApplicationIn schema validates: project_title is string
        ↓
(TBD) Save to database
        ↓
Return 201 + ApplicationOut schema
        ↓
Client receives:
{
  "id": "cuid123...",
  "project_title": "My Project"
}
```
