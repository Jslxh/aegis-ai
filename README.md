# Guardrail AI

**Runtime Action Guardrail & Policy Enforcement Platform**

Guardrail AI is a FastAPI-based REST API that intercepts tool actions (database deletes, email sends, file reads), evaluates them against declarative YAML policies, and enforces decisions. It provides **AI-powered explanations and risk analysis** via the Groq API, a **human-in-the-loop approval workflow**, and an **enterprise React web console** ("Aegis AI") for operators, auditors, and security analysts.

```
                     ┌─────────────────────────────────┐
  Client ──────────> │  API Routes (REST)              │
                     │  - POST /evaluate               │
                     │  - POST /execute                │
                     │  - POST /ai/explain             │
                     │  - POST /ai/risk-analysis       │
                     └───────┬──────────────┬──────────┘
                             │              │
                     ┌───────▼──────┐ ┌─────▼──────────┐
                     │ Guardrail    │ │ Groq Service   │
                     │ Orchestrator │ │ (AI Insights)  │
                     └───────┬──────┘ └────────────────┘
                             │
                     ┌───────▼───────┐
                     │ Policy Engine │
                     │  ┌─────────┐  │
                     │  │ Loader  │  │
                     │  │Evaluator│  │
                     │  │Operators│  │
                     │  └─────────┘  │
                     └───────┬───────┘
                             │
                     ┌───────▼───────┐     ┌──────────┐
                     │ Tool Executor │────>│ Database │
                     │               │────>│ Email    │
                     │               │────>│ File     │
                     └───────┬───────┘     └──────────┘
                             │
                     ┌───────▼───────┐
                     │ Audit Logger  │
                     │ (JSONL file)  │
                     └───────────────┘
```

---

## Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **Web Framework** | FastAPI 0.141.1 |
| **ASGI Server** | Uvicorn 0.52.0 |
| **Policy Format** | YAML (via PyYAML 6.0.3) |
| **LLM Integration** | Groq API (via groq 0.19.0) |
| **Secrets Management** | python-dotenv 1.1.0 |
| **Data Validation** | Pydantic (bundled with FastAPI) |
| **Testing** | Python unittest |
| **Web Console** | React 18 + Vite 5 + Tailwind 3 + React Query + Recharts + React Flow |

---

## Project Structure

```
guardrail-ai/
│
├── app/                          # Application package
│   ├── __init__.py               # Package marker
│   ├── main.py                   # FastAPI app factory, router registration
│   │
│   ├── api/                      # REST API layer
│   │   ├── __init__.py
│   │   ├── routes.py             # Core endpoints: /, /health, /policies, /evaluate, /execute, /simulate, /audit
│   │   └── ai_routes.py          # AI endpoints: /ai/explain, /ai/risk-analysis, /ai/hitl-summary, /ai/audit-summary, /ai/simulation-summary
│   │
│   ├── core/                     # Business logic / policy engine
│   │   ├── __init__.py
│   │   ├── loader.py             # PolicyLoader - reads YAML rules from file
│   │   ├── operators.py          # Comparison engine (>, <, ==, contains, etc.)
│   │   ├── evaluator.py          # PolicyEvaluator - evaluates requests against rules
│   │   ├── policy_engine.py      # PolicyEngine - manages loaded policies
│   │   ├── guardrail.py          # Guardrail - orchestrates policy evaluation
│   │   └── executor.py           # ToolExecutor - dispatches approved actions to tools
│   │
│   ├── services/                 # AI / LLM service layer
│   │   ├── __init__.py
│   │   ├── prompts.py            # Prompt templates for all AI use cases
│   │   └── groq_service.py       # GroqService client - handles API calls, errors, latency
│   │
│   ├── models/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── request.py            # ActionRequest, ExplainRequest, RiskAnalysisRequest, etc.
│   │   └── response.py           # EvaluationResult, ExecutionResult, SimulationResult, etc.
│   │
│   ├── tools/                    # Tool implementations (what actions act on)
│   │   ├── __init__.py
│   │   ├── database_tool.py      # DatabaseTool.delete()
│   │   ├── email_tool.py         # EmailTool.send()
│   │   └── file_tool.py          # FileTool.read()
│   │
│   ├── audit/                    # Audit logging subsystem
│   │   ├── __init__.py
│   │   └── logger.py             # BaseAuditLogger (ABC), FileAuditLogger (JSONL)
│   │
│   ├── hitl/                     # Human-in-the-loop abstraction
│   │   ├── __init__.py
│   │   └── approval.py           # BaseApprovalQueue (ABC), MockApprovalQueue (in-memory)
│   │
│   └── simulator/                # Simulation harness
│       ├── __init__.py
│       └── simulation.py         # Simulation - runs pre-defined test scenarios
│
├── configs/
│   └── default.yaml              # Declarative policy rules
│
├── tests/                        # Test suite
│   ├── test_guardrail.py         # Unit tests for Guardrail.evaluate()
│   ├── test_executor.py          # Unit tests for ToolExecutor
│   └── test_api.py               # Integration tests against live server
│
├── logs/                         # Runtime audit log output
│   └── audit.log                 # JSONL audit trail
│
├── docs/
│   ├── architecture.md           # Architecture documentation
│   └── api.md                    # API reference
│
├── .env                          # Environment configuration (not committed)
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Poetry project config
└── Dockerfile                    # Container build
```

---

## What This Project Does

Guardrail AI acts as a **security middleware** between users and sensitive tool operations. Every action is intercepted, evaluated against a YAML-based policy set, and then allowed, blocked, flagged for human approval, or logged-and-allowed.

### Example scenario

1. A user tries to delete 500 records from the database
2. The request is sent to `POST /execute`
3. Guardrail evaluates it against policies
4. Policy `block_large_delete` matches (`record_count > 100`)
5. The action is **blocked** with a descriptive message
6. The event is recorded in the audit log
7. The user receives a clear block response

---

## Core Concepts

### 1. Policies (YAML)

All policies are defined declaratively in `configs/default.yaml`. Each rule specifies:

- **tool / action** - which operation it applies to
- **conditions** - field comparisons with operators
- **decision** - what to do when matched
- **message** - human-readable explanation

Four decision types:

| Decision | Meaning | Action |
|---|---|---|
| `allow` | Match not found | Action permitted, tool executed |
| `block` | Policy violated | Action denied immediately |
| `require_hitl` | Needs human review | Returns pending status |
| `log_and_allow` | Permitted but monitored | Action executed + audit logged |

**Supported operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`, `contains`, `startswith`, `endswith`

### 2. Tools

The platform simulates three tool types. Each returns a structured success response:

- **DatabaseTool** - `delete(record_count)` → simulated deletion
- **EmailTool** - `send(recipient)` → simulated email send
- **FileTool** - `read(path)` → simulated file read

### 3. Audit Logging

Every evaluated request is timestamped and written as JSONL to `logs/audit.log`. The `AuditLogger` implements a `BaseAuditLogger` abstract class, making it swappable to a database or cloud logger.

### 4. Human-in-the-Loop (HITL)

The platform ships a full approval workflow. The abstract `BaseApprovalQueue` defines the contract, `MockApprovalQueue` provides in-memory tracking, and `PgApprovalQueue` persists requests in PostgreSQL (tables managed by Alembic migration `0008`).

- `POST /execute` returns `waiting_for_human` with an `approval_request_id` for `require_hitl` decisions; the queue entry expires after `HITL_EXPIRY_HOURS` (default 24).
- Operators review pending requests via the REST API: `GET /approvals`, `GET /approvals/stats`, `POST /approvals/{id}/approve|reject|expire` (security_analyst role required for mutations).
- Every approval decision is written to the audit trail with the reviewer identity and comments.

### 5. Simulation Harness

The `GET /simulate` endpoint runs 5 pre-configured scenarios that exercise all policy decisions:
- Large Delete → blocked
- Small Delete → allowed
- External Email → require_hitl
- Internal Email → allowed
- Confidential File → log_and_allow

---

## AI-Powered Insights (Groq Integration)

The platform integrates with the **Groq API** to provide intelligent analysis of policy decisions, risk, and audit events. All AI features are optional and gracefully degrade if no API key is configured.

### Use Cases

| Endpoint | Purpose | Input | Output |
|---|---|---|---|
| `POST /ai/explain` | Explain a policy decision | Matched rule, decision, reason, request context | Natural language explanation |
| `POST /ai/risk-analysis` | Assess risk of an action | Tool, action, parameters, decision | Risk level, impact, recommendations |
| `POST /ai/hitl-summary` | Help human operators decide | Request details, policy decision | Summary, risk, recommendation |
| `POST /ai/audit-summary` | Summarize audit events | Raw audit log record | Readable summary |
| `POST /ai/simulation-summary` | Analyze simulation results | Summary stats, individual results | Effectiveness analysis |

### Architecture

```
POST /ai/explain ──> ai_routes.py ──> GroqService ──> prompts.py ──> Groq API
                                            │
                                     Structured JSON
                                    (success/content or error)
```

- **prompts.py** - Contains all system/system-prompt templates separated from user content. Easy to modify without touching business logic.
- **groq_service.py** - Thin client wrapper. Handles authentication, timeouts, error logging, and latency tracking. Never crashes the application.

### Error Handling

| Scenario | HTTP Status | Response |
|---|---|---|
| No API key configured | 503 | `{"detail": "Groq service not initialized"}` |
| Groq API call fails | 502 | `{"detail": "Invalid API Key ..."}` |
| Successful response | 200 | `{"success": true, "content": "...", "model": "...", "latency": 0.5}` |

---

## API Endpoints

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Welcome message |
| `GET` | `/health` | Health check |
| `GET` | `/about` | Project information |
| `GET` | `/policies` | List all loaded policy rules |
| `POST` | `/evaluate` | Evaluate an action against policies (no execution) |
| `POST` | `/execute` | Evaluate and execute an action |
| `GET` | `/simulate` | Run simulation scenarios |
| `GET` | `/audit` | Return raw audit log entries |

### AI Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/ai/explain` | Explain a policy decision |
| `POST` | `/ai/risk-analysis` | Risk assessment for an action |
| `POST` | `/ai/hitl-summary` | Human-in-the-loop decision support |
| `POST` | `/ai/audit-summary` | Readable audit log summary |
| `POST` | `/ai/simulation-summary` | Simulation effectiveness analysis |

---

## Data Flow

```
                 ┌──────────┐
                 │  Client  │
                 └────┬─────┘
                      │ ActionRequest {tool, action, ...}
                      ▼
              ┌───────────────┐
              │  POST /execute│
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │ Guardrail     │
              │ .evaluate()   │
              └───────┬───────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Policy   │ │ Policy   │ │ Policy   │
   │ Loader   │ │Evaluator │ │Operators │
   └──────────┘ └──────────┘ └──────────┘
         │
         ▼ {decision, matched_rule, reason}
         │
    ┌────┴────┐
    │  audit  │
    │ .log()  │
    └────┬────┘
         │
    ┌────┴────┐
    │ decision│
    └────┬────┘
         │
    ┌────┴──────────┬──────────┬──────────┐
    ▼               ▼          ▼          ▼
  block        require_hitl  allow   log_and_allow
    │               │          │          │
    ▼               ▼          ▼          ▼
 Return         Return     ToolExec   ToolExec
 blocked       waiting    .execute() .execute()
 response    for_human       │          │
                          Return     Return
                          executed   executed_
                                     with_logging
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip (or Poetry)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd guardrail-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `.env` to set your Groq API key (required for AI features, AI endpoints return 503 without it):

```env
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile  # or any Groq-supported model
```

### Running the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Interactive API docs at `http://localhost:8000/docs`.

### Running with Docker (development)

```bash
# 1. Create your environment file from the template
cp .env.example .env

# 2. Start the stack (PostgreSQL + API with hot reload)
docker compose up --build
```

- `db` — PostgreSQL 16 (data persisted in the `db_data` volume).
- `api` — FastAPI served by uvicorn with `--reload`; the repo is bind-mounted
  so edits to `./app` are picked up without rebuilding.
- Health checks: `docker compose ps` shows both services `healthy` when ready.
- Interactive API docs at `http://localhost:8000/docs`.

### Running with Docker (production)

```bash
# Set strong secrets before deploying
cp .env.example .env
#   -> POSTGRES_PASSWORD=change-me-to-a-strong-password
#   -> GROQ_API_KEY=gsk_...   (optional, enables /ai/* endpoints)

docker compose -f docker-compose.prod.yml up -d --build

docker compose -f docker-compose.prod.yml ps      # all healthy?
docker compose -f docker-compose.prod.yml logs -f api
```

The production stack runs four services:

| Service   | Role                                                                 |
|-----------|----------------------------------------------------------------------|
| `db`      | PostgreSQL 16, data in the `db_data` named volume                     |
| `migrate` | One-shot `alembic upgrade head` run on startup (fails loudly)        |
| `api`     | Multi-stage production image, 4 uvicorn workers, non-root user       |
| `web`     | React frontend served by nginx; `/api` is reverse-proxied to `api`  |

The API container only starts after `migrate` completes successfully, and the
image ships an `alembic` migration path plus a database-wait entrypoint
(`docker-entrypoint.sh`), so a fresh EC2 host can be brought up in one command.

**Backing up the database:**

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U guardrail guardrail > guardrail-$(date +%F).sql
```

### Web console (React)

The `frontend/` directory contains the Aegis AI management console — a React 18 SPA
covering the full governance lifecycle: dashboard, policy management, HITL
approvals, runtime monitoring, audit center, simulation harness, analytics, an
architecture viewer (React Flow), and AI explainability.

```bash
cd frontend
npm install

# Dev server on http://localhost:5173 (proxies /api -> http://localhost:8000)
npm run dev

# Production build + lint
npm run build
npm run lint
```

The dev proxy forwards `/api/*` to the backend (override with `VITE_PROXY_TARGET`),
stripping the `/api` prefix — matching the nginx proxy used in the Docker images,
so the built app and the dev server call the same endpoints.

Default login: create an admin user via `POST /auth/register` (requires an existing
admin), or seed one directly in the database.

---

## Deploying to AWS EC2

### 1. Launch an instance

- **AMI:** Ubuntu 22.04/24.04 LTS (64-bit x86)
- **Type:** `t3.medium` (2 vCPU / 4 GiB) or larger
- **Storage:** 20 GiB gp3 (tune to your audit-log volume)
- **Security group inbound rules:**
  - `80` (TCP) — web console (nginx), restrict to your IPs or a load balancer
  - `8000` (TCP) — Guardrail AI API, restrict to your IPs or a load balancer
  - `22` (TCP, SSH) — from your IP only
  - Postgres port `5432` **must not** be open to the internet

### 2. Install Docker Engine

```bash
# SSH into the instance, then:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 3. Deploy the application

```bash
git clone <repo-url> guardrail-ai
cd guardrail-ai

# Secrets
cp .env.example .env
# set POSTGRES_PASSWORD, GROQ_API_KEY, etc. (or export them as env vars)

# Build and start
sudo docker compose -f docker-compose.prod.yml up -d --build

# Verify
sudo docker compose -f docker-compose.prod.yml ps   # all "healthy"
curl http://localhost:8000/health/live               # {"status":"ok"}
curl http://localhost:8000/health/ready              # DB + engine checks
# open the web console at http://<instance-ip>/  (proxies /api to the API)
```

### 4. Keep it running and updated

```bash
# Logs
sudo docker compose -f docker-compose.prod.yml logs -f

# Apply new releases
git pull
sudo docker compose -f docker-compose.prod.yml up -d --build
```

Container `restart: unless-stopped` policies bring the API and DB back after
reboots. For a hardened setup, front the API with a TLS-terminating reverse
proxy (nginx/ALB) and restrict the security group to it.

---

## Testing

```bash
# Full test suite with coverage (uses an in-memory SQLite database; no server or Postgres needed)
pytest --cov=app --cov-branch

# Or inside the dev container
docker compose exec api pytest
```

Coverage threshold is configured in `pyproject.toml` (`fail_under = 90`).
CI runs the same command on push/PR (see `.github/workflows/ci.yml`).

---

## Design Principles

- **SOLID**: Single-responsibility modules. Policy evaluation is decoupled from tool execution. The AI service layer is independent of the core engine.
- **Extensibility**: Add new tools by creating a class in `app/tools/` and registering it in `ToolExecutor`. Add new policies by editing the YAML file — no code changes needed.
- **Graceful Degradation**: All AI features are optional. If Groq is unavailable or not configured, the platform continues to function normally.
- **Auditability**: Every decision is logged with timestamp, matched rule, and full request context.
- **Separation of Concerns**: LLM prompt templates live in `prompts.py`, not in API routes. Business logic stays in services, not in routes.

---

## License

Proprietary. Aivar Innovations.
