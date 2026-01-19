# DDAS Backend API

Distributed Duplicate Asset Scanner - Backend service for centralized fingerprint indexing, search, and policy management.

## Architecture Overview

- **FastAPI**: High-performance Python web framework
- **PostgreSQL**: Primary data store (fingerprints, users, organizations, audit logs)
- **FAISS**: Vector similarity search for semantic fingerprinting
- **Redis**: Caching, rate limiting, job queue
- **MinIO/S3**: Object storage for sample payloads

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone and setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt  # or: poetry install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with local database credentials
   ```

3. **Initialize database**
   ```bash
   alembic upgrade head
   ```

4. **Start development server**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

   API available at http://localhost:8001
   Swagger docs at http://localhost:8001/docs

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000)
- Backend API (port 8001)

## Project Structure

```
app/
├── __init__.py
├── main.py                    # FastAPI app factory
├── config.py                  # Settings (pydantic)
├── logging_config.py          # Structured logging
├── constants.py               # Feature toggles, thresholds
│
├── middleware/                # HTTP middleware
│   ├── tenant_middleware.py   # JWT/API-key extraction
│   ├── request_logging.py     # Request/response logging
│   ├── rate_limit.py          # Rate limiting
│   └── request_validator.py   # Payload validation
│
├── db/                        # Database layer
│   ├── database.py            # SQLAlchemy engine & session
│   ├── models.py              # ORM models
│   └── repositories/          # Data access objects
│       ├── user_repo.py
│       ├── org_repo.py
│       ├── fingerprint_repo.py
│       ├── download_repo.py
│       └── feedback_repo.py
│
├── api/                       # API routes
│   ├── auth_api.py            # Authentication endpoints
│   ├── search_api.py          # Search endpoints
│   ├── upload_api.py          # Ingest endpoints
│   ├── feedback_api.py        # Feedback endpoints
│   ├── health_api.py          # Health checks
│   └── admin_api.py           # Admin endpoints
│
├── services/                  # Business logic
│   ├── fingerprint_service.py
│   ├── embedding_service.py
│   ├── faiss_manager.py
│   ├── match_pipeline.py
│   ├── decision_engine.py
│   ├── feedback_engine.py
│   ├── audit_manager.py
│   └── sync_service.py
│
├── security/                  # Auth & security
│   ├── password_hash.py
│   ├── jwt_utils.py
│   ├── api_key_manager.py
│   └── rbac.py
│
├── storage/                   # File storage
│   ├── file_store.py
│   └── lifecycle_manager.py
│
└── tests/                     # Test suite
    ├── unit/
    ├── integration/
    └── conftest.py
```

## API Endpoints

### Authentication
- `POST /auth/token` - Login with email/password
- `POST /auth/refresh` - Refresh JWT token
- `POST /auth/register` - Register new user (admin only)
- `POST /auth/api-key/create` - Generate API key
- `POST /auth/api-key/revoke` - Revoke API key

### Search & Ingest
- `POST /v1/search` - Query fingerprints (exact + fuzzy + semantic)
- `POST /v1/ingest` - Upload and index new fingerprint
- `POST /v1/feedback` - Record user decision override

### Health & Ops
- `GET /health` - Service health check
- `GET /ready` - Readiness probe (DB, Redis, FAISS)
- `GET /metrics` - Service metrics (counts, performance)

### Admin
- `POST /admin/org/create` - Create new organization
- `POST /admin/user/create` - Create new user
- `GET /admin/org/{org_id}/stats` - Organization statistics

## Example Requests

### Login
```bash
curl -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

### Ingest Fingerprint
```bash
curl -X POST http://localhost:8001/v1/ingest \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "document.pdf",
    "sha256": "abcd1234...",
    "size": 1024000,
    "fuzzy_sig": "ssdeep_sig_here"
  }'
```

### Search
```bash
curl -X POST http://localhost:8001/v1/search \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "document.pdf",
    "url": "https://example.com/file.pdf",
    "size": 1024000,
    "sample_bytes": "base64_encoded_sample"
  }'
```

## Testing

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app
```

### Run specific test file
```bash
pytest app/tests/unit/test_jwt_utils.py
```

## Development

### Code style
```bash
black app/
flake8 app/
mypy app/
```

### Format code
```bash
black app/
```

## Database Migrations

### Create new migration
```bash
alembic revision --autogenerate -m "Add new column"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## Deployment

### Build Docker image
```bash
docker build -t ddas-backend:latest -f docker/backend.Dockerfile .
```

### Push to registry
```bash
docker tag ddas-backend:latest your-registry/ddas-backend:latest
docker push your-registry/ddas-backend:latest
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and data flow
- [API_REFERENCE.md](docs/API_REFERENCE.md) - Detailed API specification
- [DB_SCHEMA.md](docs/DB_SCHEMA.md) - Database schema and relationships

## Security

- All endpoints require authentication (JWT or API key)
- Role-based access control (RBAC)
- Rate limiting per tenant
- Structured audit logging
- TLS/HTTPS recommended for production

## License

[Add your license]

## Support

For issues and questions, please open a GitHub issue.
