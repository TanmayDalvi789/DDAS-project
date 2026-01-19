# DDAS Local Agent (Phase-2)

Local system service for DDAS (Data Download Duplication Alert System).

## Responsibilities

- **Permission Validation**: Check system permissions at startup (FAIL-CLOSED)
- **Feature Extraction**: Extract local file/process features (stubs only, Phase-2)
- **Decision Making**: ALLOW / WARN / BLOCK decisions based on backend scores
- **Backend Communication**: Lookup similarity scores, sync configuration
- **User Notifications**: Display alerts and prompts to user

## Architecture

```
Agent (Local Service)
  ├─ Lifecycle: startup, heartbeat, shutdown
  ├─ Permissions: validate OS permissions (Windows/Linux/macOS)
  ├─ Proxy Events: consume metadata from MITM proxy
  ├─ Features: extract local file/network/system features
  ├─ Decision Engine: make ALLOW/WARN/BLOCK decisions
  ├─ Cache: local SQLite cache for fast lookup
  ├─ Backend Client: communicate with backend API
  └─ UI: notify user via system notifications
```

## NOT Included

- Detection algorithms (Phase-3)
- Proxy interception logic (handled by proxy component)
- Web server / API (agent is standalone service)
- Dashboard (separate component)

## Installation

```bash
pip install -e .
ddas-agent
```

## Configuration

Copy `.env.example` to `.env` and update:
- `BACKEND_URL`: Backend API endpoint
- `BACKEND_API_KEY`: Authentication token
- `AGENT_ID`: Unique agent identifier

## Documentation

- [AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - Design overview
- [PERMISSIONS.md](docs/PERMISSIONS.md) - Permission requirements
- [AGENT_FLOW.md](docs/AGENT_FLOW.md) - Request/response flow
