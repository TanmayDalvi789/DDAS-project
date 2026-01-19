# DDAS Backend - Complete Architecture & Workflow Guide

## **TABLE OF CONTENTS**
1. Project Structure Explained
2. Data Flow Architecture
3. Component Interactions
4. Key Concepts
5. Build Sequence
6. How Everything Works Together

---

# **1. PROJECT STRUCTURE EXPLAINED**

## **Folder Organization**

```
backend/
├── pyproject.toml              # Project metadata & dependencies list
├── .env.example                # Sample environment variables
├── .gitignore                  # Files to exclude from git
├── README.md                   # This project overview
│
├── app/                        # Main application code
│   ├── __init__.py             # Makes 'app' a Python package
│   ├── main.py                 # Entry point - FastAPI app factory (START HERE)
│   ├── config.py               # Settings loader (DATABASE_URL, JWT_SECRET, etc)
│   ├── logging_config.py       # Structured logging setup
│   ├── constants.py            # Global constants (thresholds, error messages)
│   │
│   ├── middleware/             # HTTP middleware (intercepts requests)
│   │   ├── __init__.py
│   │   ├── tenant_middleware.py    # Extracts JWT token → knows who user is
│   │   ├── request_logging.py      # Logs all requests/responses
│   │   ├── rate_limit.py           # Prevents spam (100 req/sec limit)
│   │   └── request_validator.py    # Checks payload size/format
│   │
│   ├── db/                     # Database layer
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy engine setup (connects to PostgreSQL)
│   │   ├── models.py           # ORM models (Python classes = database tables)
│   │   │                        # Models:
│   │   │                        # - Organization (org data)
│   │   │                        # - User (email, password, role)
│   │   │                        # - APIKey (for agent authentication)
│   │   │                        # - Device (agent devices)
│   │   │                        # - Fingerprint (file hashes: SHA256, fuzzy sig)
│   │   │                        # - Download (download history/logs)
│   │   │                        # - Feedback (user overrides: ALLOW/BLOCK)
│   │   │                        # - VectorMetadata (embedding metadata)
│   │   │                        # - AuditLog (who did what when)
│   │   │
│   │   ├── repositories/       # Data Access Objects (CRUD for each table)
│   │   │   ├── __init__.py
│   │   │   ├── user_repo.py         # get_user(), create_user(), etc
│   │   │   ├── org_repo.py          # get_org(), create_org(), etc
│   │   │   ├── fingerprint_repo.py  # get_fingerprint(), add_fingerprint(), etc
│   │   │   ├── download_repo.py     # log_download(), get_downloads(), etc
│   │   │   └── feedback_repo.py     # add_feedback(), get_feedback(), etc
│   │   │
│   │   └── migrations/         # Alembic - version control for database schema
│   │       ├── versions/       # Migration files (changes to schema)
│   │       ├── env.py          # Alembic configuration
│   │       └── script.py.mako  # Migration template
│   │
│   ├── api/                    # API Routes (endpoints that agents/users call)
│   │   ├── __init__.py
│   │   ├── auth_api.py         # /auth/token, /auth/register, /auth/api-key/create
│   │   ├── search_api.py       # /v1/search (find similar fingerprints)
│   │   ├── upload_api.py       # /v1/ingest (store new fingerprint)
│   │   ├── feedback_api.py     # /v1/feedback (user override)
│   │   ├── health_api.py       # /health, /ready, /metrics
│   │   └── admin_api.py        # /admin/org/create, /admin/user/create
│   │
│   ├── services/               # Business Logic (core functionality)
│   │   ├── __init__.py
│   │   ├── fingerprint_service.py   # Ingest & deduplication logic
│   │   ├── embedding_service.py     # Generate AI embeddings
│   │   ├── faiss_manager.py         # FAISS index operations (search/add vectors)
│   │   ├── match_pipeline.py        # Orchestrate search (exact+fuzzy+semantic)
│   │   ├── decision_engine.py       # Score matches → ALLOW/WARN/BLOCK
│   │   ├── feedback_engine.py       # Process user feedback
│   │   ├── audit_manager.py         # Log all important events
│   │   └── sync_service.py          # Sync data with agents
│   │
│   ├── security/               # Authentication & Authorization
│   │   ├── __init__.py
│   │   ├── password_hash.py    # Bcrypt password hashing
│   │   ├── jwt_utils.py        # Create/verify JWT tokens
│   │   ├── api_key_manager.py  # Create/verify API keys
│   │   └── rbac.py             # Role-based access control
│   │
│   ├── storage/                # File Storage
│   │   ├── __init__.py
│   │   ├── file_store.py       # S3/MinIO wrapper
│   │   └── lifecycle_manager.py # Retention policies
│   │
│   └── tests/                  # Test Suite
│       ├── __init__.py
│       ├── unit/               # Test individual functions
│       ├── integration/        # Test API endpoints
│       ├── conftest.py         # Shared test fixtures
│       └── fixtures/           # Test data
│
├── docker/                     # Docker configuration
│   ├── backend.Dockerfile      # Container for backend API
│   └── worker.Dockerfile       # (Optional) Container for background jobs
│
├── ci/                         # Continuous Integration
│   └── github-actions/
│       ├── lint.yml            # Code quality checks (black, flake8, mypy)
│       ├── unit-tests.yml      # Run unit tests
│       ├── integration.yml     # Run integration tests
│       └── release.yml         # Build & push Docker image
│
└── docs/                       # Documentation
    ├── ARCHITECTURE.md         # This file - system design
    ├── API_REFERENCE.md        # API endpoint specs
    └── DB_SCHEMA.md            # Database diagram & table descriptions
```

---

# **2. DATA FLOW ARCHITECTURE**

## **Request Journey Through Backend**

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCOMING REQUEST                              │
│              (From Agent or Admin Dashboard)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER                              │
│                   (Receives HTTP request)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MIDDLEWARE PIPELINE                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Request Validator                                     │   │
│  │    - Check payload size (<10MB)                          │   │
│  │    - Validate JSON format                                │   │
│  │    - Return 400 if invalid                               │   │
│  └──────────┬───────────────────────────────────────────────┘   │
│             │                                                    │
│  ┌──────────▼───────────────────────────────────────────────┐   │
│  │ 2. Tenant Middleware                                     │   │
│  │    - Extract JWT token from Authorization header         │   │
│  │    - Verify token signature (secret_key)                 │   │
│  │    - Extract: user_id, org_id, role                      │   │
│  │    - Return 401 if invalid                               │   │
│  │    - Attach to request.state (available in endpoint)     │   │
│  └──────────┬───────────────────────────────────────────────┘   │
│             │                                                    │
│  ┌──────────▼───────────────────────────────────────────────┐   │
│  │ 3. Rate Limit Middleware                                 │   │
│  │    - Check Redis: current_requests this second           │   │
│  │    - If > 100: Return 429 (Too Many Requests)            │   │
│  │    - Else: Increment counter, allow                      │   │
│  └──────────┬───────────────────────────────────────────────┘   │
│             │                                                    │
│  ┌──────────▼───────────────────────────────────────────────┐   │
│  │ 4. Request Logging Middleware                            │   │
│  │    - Log: method, path, user_id, org_id                  │   │
│  │    - Log to JSON file/console                            │   │
│  └──────────┬───────────────────────────────────────────────┘   │
│             │                                                    │
└─────────────┼────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ROUTE HANDLER (Endpoint)                      │
│        (e.g., @app.post("/v1/search"))                          │
│                                                                  │
│  Parameters from middleware:                                    │
│  - request.state.user_id                                        │
│  - request.state.org_id                                         │
│  - request.state.role                                           │
│                                                                  │
│  Check permissions using RBAC:                                  │
│  - Is role VIEWER/ANALYST/ADMIN?                                │
│  - Does role have "search" permission?                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SERVICE LAYER (Business Logic)                  │
│                                                                  │
│  Example: /v1/search endpoint calls:                            │
│  1. match_pipeline.search(query)                                │
│     │                                                           │
│     ├─→ fingerprint_repo.exact_match(sha256)  [PostgreSQL]     │
│     │                                                           │
│     ├─→ fingerprint_repo.fuzzy_match(sig)  [PostgreSQL]        │
│     │                                                           │
│     └─→ faiss_manager.semantic_search(embedding)  [FAISS]      │
│                                                                  │
│  2. decision_engine.score(matches)                              │
│     → Returns: decision (ALLOW/WARN/BLOCK)                      │
│                confidence score                                 │
│                reason codes                                     │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATA ACCESS LAYER (Repositories)                    │
│                                                                  │
│  Services call repositories to:                                 │
│  - Query PostgreSQL (fingerprints, users, orgs)                 │
│  - Query Redis (cache, rate limiting)                           │
│  - Query FAISS (vector similarity)                              │
│  - Query S3/MinIO (file storage)                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                ┌──────────┼──────────┬──────────┐
                │          │          │          │
                ▼          ▼          ▼          ▼
        ┌─────────────┐┌──────────┐┌────────┐┌──────────┐
        │ PostgreSQL  ││  FAISS   ││ Redis  ││ MinIO/S3 │
        │             ││ (Vector) ││(Cache) ││ (Files)  │
        │ Tables:     ││          ││        ││          │
        │ - Users     ││ Index:   ││ Keys:  ││ Bucket:  │
        │ - Orgs      ││ embeddings││ user:1 ││ samples/ │
        │ - Fingerps  ││          ││ rate:2 ││ payloads/│
        │ - Downloads ││          ││        ││          │
        │ - Feedback  ││          ││        ││          │
        │ - Audit     ││          ││        ││          │
        └─────────────┘└──────────┘└────────┘└──────────┘

                           │
                ┌──────────┴──────────┬──────────┬──────────┐
                │                     │          │          │
                ▼                     ▼          ▼          ▼
        [Data Retrieved] ────────────→ [Service Processes] → [Response Created]
```

---

## **Example: POST /v1/search Flow**

```
REQUEST:
{
  "filename": "document.pdf",
  "url": "https://example.com/file.pdf",
  "size": 1024000,
  "sample_bytes": "base64_encoded_sample"
}

STEP 1: Middleware validates & extracts user info
STEP 2: Route handler receives request + user context
STEP 3: Check if user has "search" permission (RBAC)
STEP 4: Call match_pipeline.search()
STEP 5: match_pipeline orchestrates:
        - Exact match (SHA256 in PostgreSQL)
        - Fuzzy match (fuzzy_sig similar in PostgreSQL)
        - Semantic match (embedding in FAISS)
STEP 6: decision_engine scores results
STEP 7: audit_manager logs the search event
STEP 8: Return response:

RESPONSE:
{
  "decision": "WARN",
  "confidence": 0.75,
  "reason": "fuzzy_similar",
  "matches": [
    {
      "fingerprint_id": 123,
      "filename": "document_v1.pdf",
      "similarity": 0.92,
      "first_seen": "2025-11-20"
    }
  ]
}
```

---

# **3. COMPONENT INTERACTIONS**

## **How Components Talk to Each Other**

```
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI MAIN                              │
│              (entry point - app.main:app)                    │
└──────────────────┬───────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────────┐
│ Routers │  │Middleware│  │Dependencies  │
│ (API)   │  │(Security)│  │(DB, Services)│
└────┬────┘  └────┬─────┘  └──────┬───────┘
     │            │               │
     ├────────────┴───────────────┤
     │                            │
     ▼                            ▼
┌──────────────────┐    ┌──────────────────┐
│   API Routes     │    │    Dependency    │
│  - auth_api.py   │    │   Injection      │
│  - search_api.py │    │   Container      │
│  - upload_api.py │    │                  │
│  - etc.          │    │ Provides:        │
└────────┬─────────┘    │ - DB Session     │
         │              │ - Services       │
         │              │ - Config         │
         │              └────────┬─────────┘
         │                       │
         ├───────────────────────┤
         │                       │
         ▼                       ▼
    ┌─────────────────────────────────────┐
    │         SERVICE LAYER               │
    │  - fingerprint_service.py           │
    │  - embedding_service.py             │
    │  - faiss_manager.py                 │
    │  - match_pipeline.py                │
    │  - decision_engine.py               │
    │  - feedback_engine.py               │
    │  - audit_manager.py                 │
    └────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────────────┐  ┌──────────────────┐
│  Repositories   │  │  External Clients│
│  (Data Access)  │  │  - FAISS Index   │
│                 │  │  - Redis         │
│ - user_repo.py  │  │  - S3/MinIO      │
│ - org_repo.py   │  │                  │
│ - fp_repo.py    │  └──────────────────┘
│ - etc.          │
└────────┬────────┘
         │
    ┌────┴────────────────────┐
    │                         │
    ▼                         ▼
┌────────────┐        ┌─────────────────┐
│ PostgreSQL │        │ Other Storage   │
│  Database  │        │ - FAISS index   │
│            │        │ - Redis cache   │
│ Tables:    │        │ - MinIO files   │
│ - users    │        │                 │
│ - orgs     │        └─────────────────┘
│ - fingerps │
│ - etc.     │
└────────────┘
```

---

# **4. KEY ARCHITECTURAL CONCEPTS**

## **A. LAYERED ARCHITECTURE**

Your backend is organized in **layers** (like a cake):

```
┌─────────────────────────────┐
│  API Layer                  │  👤 User sees this
│  (Endpoints)                │
├─────────────────────────────┤
│  Service Layer              │  🧠 Business logic
│  (Business Logic)           │
├─────────────────────────────┤
│  Repository Layer           │  💾 Data access
│  (Data Access)              │
├─────────────────────────────┤
│  Data Layer                 │  🗄️ Storage
│  (Databases)                │
└─────────────────────────────┘
```

**Benefits:**
- Each layer has one responsibility
- Easy to test (replace layer with fake)
- Easy to change (replace lower layer)

---

## **B. REQUEST FLOW PATTERN**

```
Request → Middleware → Endpoint → Service → Repository → Database → Response
```

**Each component:**
1. **Middleware** - Validates & authenticates
2. **Endpoint** - Catches request, calls service
3. **Service** - Contains logic, calls repo
4. **Repository** - Executes database query
5. **Database** - Returns data

---

## **C. SEPARATION OF CONCERNS**

| Layer | Responsibility | Example |
|-------|---|---|
| **Middleware** | Auth, logging, rate limiting | Check JWT token |
| **API Endpoints** | Receive request, validate input, return response | `@app.post("/v1/search")` |
| **Services** | Business logic, orchestration | Combine exact + fuzzy + semantic search |
| **Repositories** | Database queries only | `get_user(user_id)` |
| **Models** | Database schema | `class User(Base)` |

---

## **D. DEPENDENCY INJECTION**

Instead of importing dependencies at top:

```python
# ❌ BAD - Tightly coupled
def search(query):
    db = Database()  # Created inside
    user_repo = UserRepository(db)
    result = user_repo.get_user(123)
    return result

# ✅ GOOD - Loosely coupled
def search(query, db: Database = Depends(get_db)):
    user_repo = UserRepository(db)  # Passed in
    result = user_repo.get_user(123)
    return result
```

**FastAPI `Depends()`** automatically:
- Creates database session
- Passes it to endpoint
- Closes connection when done

---

# **5. BUILD SEQUENCE**

## **Why This Order?**

```
1. Database (Models, Migrations)
   ↓ (depends on database schema)
2. Repositories (CRUD operations)
   ↓ (depends on repositories)
3. Services (Business logic)
   ↓ (depends on services)
4. API Endpoints (Route handlers)
   ↓ (depends on complete API)
5. Tests (Validate everything)
   ↓ (depends on tested code)
6. Docker & CI/CD
```

**Why this order?**
- Data layer must exist before accessing it
- Repositories need models to work
- Services need repositories to function
- Endpoints need services to do work
- Tests validate everything is working
- Docker packages everything

---

# **6. HOW EVERYTHING WORKS TOGETHER - COMPLETE EXAMPLE**

## **Scenario: Agent Searches for Similar File**

```
┌────────────────────────────────────────────────────────────────┐
│ AGENT sends: POST /v1/search                                   │
│ Headers: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...         │
│ Body: {                                                         │
│   "filename": "report.pdf",                                     │
│   "size": 5000000,                                              │
│   "sample_bytes": "JVBERi0xLjQ..."  (base64)                    │
│ }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [1] REQUEST VALIDATOR MIDDLEWARE                               │
│ ├─ Check: Is payload < 10MB?  ✓                                │
│ ├─ Check: Is JSON valid?  ✓                                    │
│ └─ Continue to next middleware                                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [2] TENANT MIDDLEWARE                                          │
│ ├─ Extract JWT: eyJhbGciOiJIUzI1NiIs...                       │
│ ├─ Verify signature with JWT_SECRET_KEY                        │
│ ├─ Decode token → {"user_id": 5, "org_id": 2, "role": ...}   │
│ ├─ Attach to request.state                                     │
│ └─ User authenticated ✓                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [3] RATE LIMIT MIDDLEWARE                                      │
│ ├─ Query Redis: GET rate_limit:org:2                          │
│ ├─ Current count: 45 requests this second                       │
│ ├─ Limit: 100 requests/sec  ✓                                  │
│ ├─ Increment: SET rate_limit:org:2 = 46                        │
│ └─ Continue                                                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [4] REQUEST LOGGING MIDDLEWARE                                 │
│ └─ Log to JSON file:                                           │
│   {                                                             │
│     "timestamp": "2025-11-25T15:30:45Z",                        │
│     "method": "POST",                                           │
│     "path": "/v1/search",                                       │
│     "user_id": 5,                                               │
│     "org_id": 2,                                                │
│     "status": "in_progress"                                     │
│   }                                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [ENDPOINT] @app.post("/v1/search")                             │
│ async def search(request: SearchRequest, user_id: int = ...):  │
│                                                                 │
│ ├─ Get user_id, org_id from request.state (from middleware)   │
│ ├─ Check RBAC: Does ANALYST role have "search" permission?    │
│ │  └─ ANALYST permissions: [search, ingest, feedback]  ✓      │
│ │                                                              │
│ ├─ Call service layer:                                         │
│ │  await match_pipeline.search(                               │
│ │    filename="report.pdf",                                    │
│ │    size=5000000,                                             │
│ │    sample_bytes=decoded,                                     │
│ │    org_id=2                                                  │
│ │  )                                                           │
│ └─ Continue to service                                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [SERVICE] match_pipeline.search()                              │
│                                                                 │
│ Step 1: Exact Match                                            │
│ ├─ Compute SHA256(sample_bytes)                                │
│ ├─ → "a1b2c3d4e5f6..."                                         │
│ ├─ Call: fingerprint_repo.get_by_sha256("a1b2...", org_id=2)  │
│ └─ Result: None (no exact match)                               │
│                                                                 │
│ Step 2: Fuzzy Match                                            │
│ ├─ Compute fuzzy hash (ssdeep) of sample_bytes                │
│ ├─ → "12288:2d3/4d5e..."                                       │
│ ├─ Call: fingerprint_repo.fuzzy_search("12288:...", org_id=2) │
│ └─ Result: [                                                    │
│     {id: 42, filename: "report_v1.pdf", score: 0.88},          │
│     {id: 78, filename: "annual_report.pdf", score: 0.76}       │
│   ]                                                             │
│                                                                 │
│ Step 3: Semantic Search                                        │
│ ├─ Call: embedding_service.embed("report.pdf")                 │
│ │  (Uses sentence-transformers model)                          │
│ │  → [0.23, -0.15, 0.67, ..., 0.34]  (384 dimensions)        │
│ │                                                               │
│ ├─ Cache in Redis (TTL: 1 hour)                                │
│ │                                                               │
│ ├─ Call: faiss_manager.search(                                 │
│ │    query_vector=[0.23, -0.15, ...],                          │
│ │    k=10  (top 10 results)                                    │
│ │  )                                                            │
│ │                                                               │
│ └─ Result: [                                                    │
│     {vector_id: 101, distance: 0.12, org_id: 2},                │
│     {vector_id: 202, distance: 0.18, org_id: 2}                 │
│   ]                                                             │
│    (Lower distance = more similar)                              │
│                                                                 │
│ Step 4: Combine Results                                        │
│ └─ Merge exact + fuzzy + semantic matches                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [SERVICE] decision_engine.score()                              │
│                                                                 │
│ For each match, calculate confidence score:                    │
│ ├─ Match 1: {id: 42, fuzzy: 0.88}                              │
│ │  ├─ exact_match: 0.0  (no exact match)                       │
│ │  ├─ fuzzy_score: 0.88  (88% similar)                         │
│ │  ├─ semantic_score: 0.15  (15% semantic similar)             │
│ │  ├─ size_similarity: 0.95  (95% same size)                   │
│ │  └─ COMBINED: (0.0 + 0.88*0.3 + 0.15*0.2 + 0.95*0.1) = 0.42 │
│ │                                                               │
│ ├─ Match 2: {id: 78, fuzzy: 0.76}                              │
│ │  └─ COMBINED: 0.35                                           │
│ │                                                               │
│ └─ Highest confidence: 0.42                                    │
│    Map to decision:                                             │
│    if confidence < 0.4: ALLOW ✓ (probably different)            │
│    if 0.4 <= confidence < 0.85: WARN (might be duplicate)       │
│    if confidence >= 0.85: BLOCK (very likely duplicate)         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [SERVICE] audit_manager.log_search()                           │
│ └─ Log to AuditLog table:                                      │
│   {                                                             │
│     "user_id": 5,                                               │
│     "org_id": 2,                                                │
│     "action": "search",                                         │
│     "query_filename": "report.pdf",                             │
│     "decision": "WARN",                                         │
│     "confidence": 0.42,                                         │
│     "matches_found": 2,                                         │
│     "timestamp": "2025-11-25T15:30:45Z"                        │
│   }                                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [ENDPOINT] Return Response                                     │
│ {                                                               │
│   "decision": "WARN",                                           │
│   "confidence": 0.42,                                           │
│   "reason": "fuzzy_similar",                                    │
│   "matches": [                                                  │
│     {                                                           │
│       "fingerprint_id": 42,                                     │
│       "filename": "report_v1.pdf",                              │
│       "similarity": 0.88,                                       │
│       "first_seen": "2025-11-20"                                │
│     },                                                          │
│     {                                                           │
│       "fingerprint_id": 78,                                     │
│       "filename": "annual_report.pdf",                          │
│       "similarity": 0.76,                                       │
│       "first_seen": "2025-11-18"                                │
│     }                                                           │
│   ]                                                             │
│ }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ [RESPONSE] 200 OK - Agent receives decision                    │
│                                                                 │
│ Agent now knows: This file is SIMILAR to 2 other files         │
│ Agent decides: Show warning to user before download            │
└────────────────────────────────────────────────────────────────┘
```

---

# **SUMMARY: Keep These In Mind**

## **The Backend is Like a Postal Service**

```
1. MAIL SORTING (Middleware)
   - Check stamp is valid (JWT token)
   - Check weight limit (payload size)
   - Sort by destination (org_id)

2. DELIVERY ROUTING (Endpoint)
   - Read address (route matching)
   - Decide which department (service)
   - Get delivery person (service)

3. CHECKING ARCHIVES (Service)
   - Search exact matches (PostgreSQL)
   - Search similar (FAISS)
   - Check historical records (Repositories)

4. FILE MANAGEMENT (Repository)
   - Pull from filing cabinet (PostgreSQL query)
   - Get from index (FAISS)
   - Cross reference (multiple tables)

5. DELIVERY (Response)
   - Package result
   - Send back to sender (agent)
```

---

## **Key Points to Remember**

✅ **Middleware** - Security guard (authenticates)
✅ **Endpoints** - Reception desk (receives requests)
✅ **Services** - Workers (do the work)
✅ **Repositories** - File managers (access data)
✅ **Models** - Database schema (structure)
✅ **Config** - Settings (environment variables)
✅ **Constants** - Rules (thresholds, limits)

---

**When you're ready, we'll start building WEEK 1 - DAY 3-5: DATABASE SCHEMA & ORM MODELS**

Any questions about this architecture? 🎓
