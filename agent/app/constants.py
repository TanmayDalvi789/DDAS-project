"""Agent constants."""

# Decision outcomes
DECISION_ALLOW = "ALLOW"
DECISION_WARN = "WARN"
DECISION_BLOCK = "BLOCK"

DECISION_OUTCOMES = {DECISION_ALLOW, DECISION_WARN, DECISION_BLOCK}

# ============================================================================
# STEP-6: Decision Engine Thresholds
# ============================================================================
# These thresholds determine when files trigger WARN or BLOCK decisions.
# Configurable via environment variables (optional overrides).

# Exact Match
# Note: Exact match always blocks (score == 1.0), no threshold needed

# Fuzzy Match Thresholds
FUZZY_WARN_THRESHOLD = 0.75    # Trigger WARN if fuzzy score >= 0.75
FUZZY_BLOCK_THRESHOLD = 0.90   # Trigger BLOCK if fuzzy score >= 0.90

# Semantic Match Thresholds
SEMANTIC_WARN_THRESHOLD = 0.80   # Trigger WARN if semantic score >= 0.80
SEMANTIC_BLOCK_THRESHOLD = 0.92  # Trigger BLOCK if semantic score >= 0.92

# Fusion Rule: BLOCK > WARN > ALLOW (no averaging, deterministic precedence)
# Decision logic:
# 1. If any exact match (score == 1.0) → BLOCK
# 2. If any fuzzy score >= FUZZY_BLOCK_THRESHOLD → BLOCK
# 3. If any semantic score >= SEMANTIC_BLOCK_THRESHOLD → BLOCK
# 4. If any fuzzy score >= FUZZY_WARN_THRESHOLD → WARN
# 5. If any semantic score >= SEMANTIC_WARN_THRESHOLD → WARN
# 6. Else → ALLOW

# ============================================================================
# STEP-7: User Notification and Enforcement Configuration
# ============================================================================
# Settings for user alerts and enforcement behavior

# Notification timeouts (seconds)
NOTIFICATION_WARN_TIMEOUT = 5     # How long to show WARN notification
NOTIFICATION_BLOCK_TIMEOUT = 10   # How long to show BLOCK notification
NOTIFICATION_ALLOW_TIMEOUT = 3    # How long to show ALLOW notification

# User confirmation for WARN decisions
WARN_CONFIRMATION_TIMEOUT = 10    # Seconds to wait for user response
WARN_DEFAULT_ACTION = "CANCEL"    # Default if no response ("PROCEED" or "CANCEL")

# Enforcement behavior
ALLOW_ENFORCEMENT_ENABLED = False  # Show notification for ALLOW (optional)
WARN_ENFORCEMENT_ENABLED = True    # Show notification and wait for user response
BLOCK_ENFORCEMENT_ENABLED = True   # Show notification and block immediately (non-overridable)

# Backends
BACKEND_TIMEOUT_SECONDS = 10
BACKEND_RETRY_ATTEMPTS = 3

# Cache
CACHE_TTL_SECONDS = 3600  # 1 hour
