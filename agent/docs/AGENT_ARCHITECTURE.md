# DDAS Agent Architecture

## Overview

The DDAS Agent is a **local system service** (not a web server) that makes ALLOW/WARN/BLOCK decisions for file downloads.

## Core Responsibilities

1. **Permission Validation** (FAIL-CLOSED)
   - Validate OS permissions at startup
   - Block agent if permissions missing
   - Platform-specific: Windows (admin), Linux (root), macOS (Full Disk Access)

2. **Event Consumption**
   - Consume HTTP metadata from MITM proxy
   - Extract URL, headers, basic properties
   - Pass to decision engine

3. **Feature Extraction**
   - Extract local file features (Phase-3)
   - Hash-based identification
   - Fuzzy matching features
   - Semantic features (embeddings later)

4. **Decision Making**
   - Query backend for similarity scores
   - Decide based on thresholds:
     - score ≥ 0.95 → ALLOW (trusted)
     - 0.75 ≤ score < 0.95 → WARN (confirm)
     - score < 0.75 → BLOCK (unsafe)

5. **Backend Communication**
   - Lookup similarity scores (read-only)
   - Sync configuration updates
   - Report agent status (heartbeat)

6. **Local Caching**
   - SQLite cache for fast lookups
   - Avoid repeated backend calls
   - TTL-based expiration

7. **User Notifications**
   - System notifications for WARN/BLOCK
   - Request user confirmation
   - Platform-specific (Windows/Linux/macOS)

## Module Organization

```
app/
├── main.py                 # Bootstrap entry point
├── config.py              # Configuration from environment
├── constants.py           # Decision thresholds, timeouts
├── logging_config.py      # Logging setup
│
├── lifecycle/
│   ├── startup.py         # Agent initialization
│   ├── heartbeat.py       # Periodic status reporting
│   └── shutdown.py        # Graceful cleanup
│
├── permissions/
│   ├── checker.py         # FAIL-CLOSED validation
│   ├── guidance.py        # User-friendly instructions
│   ├── errors.py          # Permission exceptions
│   └── platform/
│       ├── windows.py     # Windows admin check
│       ├── linux.py       # Linux root check
│       └── macos.py       # macOS Full Disk Access check
│
├── proxy_events/
│   ├── event_listener.py  # Consume proxy metadata
│   └── adapters.py        # Normalize events
│
├── features/              # STUBS ONLY (Phase-2)
│   ├── exact.py           # Hash-based features
│   ├── fuzzy.py           # Content similarity features
│   └── semantic.py        # Embedding features
│
├── decision/
│   ├── engine.py          # ALLOW/WARN/BLOCK logic
│   └── explain.py         # Decision explanations
│
├── cache/
│   ├── database.py        # SQLite cache storage
│   ├── models.py          # Cache data structures
│   └── repository.py      # Cache data access layer
│
├── backend_client/
│   ├── auth.py            # API authentication
│   ├── lookup_client.py   # /detect endpoint client
│   ├── sync_client.py     # Config sync client
│   └── config_client.py   # Agent-specific config client
│
├── ui/
│   ├── notifier.py        # System notifications
│   └── prompts.py         # User prompts
│
└── tests/
    ├── unit/              # Unit tests (TODO)
    └── integration/       # Integration tests (TODO)
```

## Not Included (Yet)

- **Detection Algorithms** (Phase-3)
  - Exact matching
  - Fuzzy matching
  - Semantic matching
  All moved to backend

- **Proxy Interception**
  - Handled by separate proxy component
  - Agent only consumes events

- **Dashboard Logic**
  - Separate dashboard component

- **Web Server**
  - Agent is standalone service, not web backend

## Design Principles

1. **Fail-Closed**: Agent cannot start without valid permissions
2. **Stateless**: Decisions based on backend scores only
3. **Decoupled**: Minimal dependencies on proxy/dashboard
4. **Extensible**: Clear separation for Phase-3 algorithms
5. **Observable**: Logging and decision explanations
6. **Efficient**: Local caching to reduce backend calls
