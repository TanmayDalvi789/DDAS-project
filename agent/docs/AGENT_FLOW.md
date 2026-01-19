# DDAS Agent Flow

## Request-Response Flow

```
File Download
    ↓
Proxy MITM Intercept
    ↓
Proxy → Agent (Metadata Event)
    ├── URL, headers, method, status
    └── File hash (if available)
    ↓
Agent: Feature Extraction (Local)
    ├── Extract MD5/SHA256 hash
    ├── Read file properties
    └── Prepare for lookup
    ↓
Agent: Backend Lookup
    └── POST /api/v1/detection/detect
        ├── Input: file_hash, file_size
        └── Output: similarity scores
    ↓
Agent: Decision Engine
    ├── Get best_score from backend
    ├── Apply thresholds
    └── Decide: ALLOW / WARN / BLOCK
    ↓
Decision → Proxy (Action)
    ├── ALLOW: Let download continue
    ├── WARN: Show notification + confirm
    └── BLOCK: Block download immediately
    ↓
Cache Result (SQLite)
    └── Fast lookup next time
```

## Decision Thresholds

| Score Range | Decision | Action |
|---|---|---|
| ≥ 0.95 | ALLOW | Download continues silently |
| 0.75-0.95 | WARN | Notification + user confirmation |
| < 0.75 | BLOCK | Download blocked immediately |

## Response Flow Example

### Backend Response (Lookup)

```json
{
  "matched": true,
  "best_score": 0.89,
  "best_algorithm": "fuzzy",
  "scores": [
    {"algorithm": "exact", "score": 0.0},
    {"algorithm": "fuzzy", "score": 0.89},
    {"algorithm": "semantic", "score": 0.75}
  ],
  "decision": "ALLOW",
  "confidence": 0.89,
  "reason": "File matched with known safe file"
}
```

### Agent Decision

```json
{
  "decision": "WARN",
  "confidence": 0.89,
  "reason": "Medium confidence match, manual review recommended",
  "require_user_confirmation": true
}
```

### Proxy Action

- Display notification: "File download requires confirmation"
- Wait for user response
- Allow/block based on user input

## Cache Behavior

When agent sees same file hash again:

1. Check local SQLite cache
2. If found and not expired (TTL 1 hour):
   - Return cached decision immediately
   - Skip backend call
3. If not found or expired:
   - Query backend
   - Update cache
   - Return decision

## Error Handling

If backend is unreachable:

1. Check cache (might have old entry)
2. If no cache: Default to BLOCK (safe fail-closed)
3. Log error and retry with backoff
4. Eventually notify user if backend still down

## Components Interaction

```
┌─────────────────┐
│   MITM Proxy    │
│   (separate)    │
└────────┬────────┘
         │ Event: URL, headers
         ↓
    ┌────────────────┐
    │  Agent App     │
    │ ┌────────────┐ │
    │ │Permissions │ (FAIL-CLOSED validation)
    │ │  Checker   │ │
    │ └────────────┘ │
    │ ┌────────────┐ │
    │ │   Cache    │ (SQLite local lookup)
    │ │ Repository │ │
    │ └────────────┘ │
    │ ┌────────────┐ │
    │ │  Decision  │ (ALLOW/WARN/BLOCK)
    │ │  Engine    │ │
    │ └────────────┘ │
    │ ┌────────────┐ │
    │ │ Backend    │ (Similarity scores)
    │ │ Lookup     │ │
    │ └────────────┘ │
    │ ┌────────────┐ │
    │ │    UI      │ (Notifications)
    │ │ Notifier   │ │
    │ └────────────┘ │
    └─────┬──────────┘
          │ Action: ALLOW / WARN / BLOCK
          ↓
    ┌─────────────────┐
    │   MITM Proxy    │
    │   (allow/block) │
    └─────────────────┘
```
