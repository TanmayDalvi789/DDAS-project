"""Application constants and configuration values."""

# Decision Types
DECISION_ALLOW = "ALLOW"
DECISION_WARN = "WARN"
DECISION_BLOCK = "BLOCK"

DECISIONS = [DECISION_ALLOW, DECISION_WARN, DECISION_BLOCK]

# User Roles
ROLE_ADMIN = "ADMIN"
ROLE_ANALYST = "ANALYST"
ROLE_VIEWER = "VIEWER"

ROLES = [ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER]

# Role Permissions Mapping
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "create_org",
        "create_user",
        "manage_users",
        "manage_policies",
        "view_all_orgs",
        "view_all_downloads",
        "view_all_feedback",
        "manage_settings",
        "manage_api_keys",
    ],
    ROLE_ANALYST: [
        "ingest_fingerprints",
        "search_fingerprints",
        "view_feedback",
        "manage_feedback",
        "view_org_downloads",
        "export_logs",
    ],
    ROLE_VIEWER: [
        "search_fingerprints",
        "view_feedback",
        "view_org_downloads",
    ],
}

# Limits
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_SAMPLE_SIZE = 64 * 1024  # 64KB
MAX_FILENAME_LENGTH = 500
MAX_URL_LENGTH = 2000

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Search Configuration
FAISS_SEARCH_K = 10  # Default top-K results
FAISS_BATCH_SIZE = 1024  # Batch size for embedding

# Cache TTL (in seconds)
EMBEDDING_CACHE_TTL = 3600  # 1 hour
ORGANIZATION_CACHE_TTL = 1800  # 30 minutes
POLICY_CACHE_TTL = 300  # 5 minutes

# Timeout (in seconds)
EMBEDDING_TIMEOUT = 30
FAISS_SEARCH_TIMEOUT = 10
DB_QUERY_TIMEOUT = 30

# Retention Policies
AUDIT_LOG_RETENTION_DAYS = 90
FEEDBACK_RETENTION_DAYS = 365
DOWNLOAD_RECORD_RETENTION_DAYS = 180

# Error Messages
ERROR_INVALID_CREDENTIALS = "Invalid email or password"
ERROR_INVALID_TOKEN = "Invalid or expired token"
ERROR_INSUFFICIENT_PERMISSIONS = "Insufficient permissions for this action"
ERROR_ORGANIZATION_NOT_FOUND = "Organization not found"
ERROR_USER_NOT_FOUND = "User not found"
ERROR_FINGERPRINT_NOT_FOUND = "Fingerprint not found"
ERROR_DOWNLOAD_NOT_FOUND = "Download record not found"
ERROR_INVALID_API_KEY = "Invalid API key"
ERROR_API_KEY_EXPIRED = "API key has expired"
ERROR_MAINTENANCE_MODE = "Service is in maintenance mode"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"

# Status Codes
STATUS_INDEXED = "indexed"
STATUS_SYNCING = "syncing"
STATUS_ERROR = "error"

# Feature Flags
FEATURE_FLAGS = {
    "semantic_search": True,
    "fuzzy_matching": True,
    "exact_matching": True,
    "feedback_collection": True,
    "user_overrides": True,
}
