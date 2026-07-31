# Aegis AI

**Enterprise-Grade Runtime Action Interception & AI-Assisted Governance Platform**

Aegis AI (backend service named *Guardrail AI*) is a high-performance FastAPI and React platform designed to secure, monitor, and audit tool operations (such as database deletions, email deliveries, or file operations) performed by AI agents or human operators. By evaluating actions against declarative policies, the system provides automated policy enforcement, AI-powered natural language explanations, human-in-the-loop (HITL) approvals, and a cryptographically chained audit trail.

---

## 🏗️ Platform Architecture

The platform sits as an interceptor proxy between clients (AI agents or human operators) and downstream systems/tools. It orchestrates the evaluation of parameters, state management for approvals, dynamic execution, and tamper-evident audit logging.

```mermaid
flowchart TD
    Client[Client / AI Agent] -->|POST /execute| FastAPI[FastAPI REST Gateway]
    FastAPI -->|1. Intercept & Evaluate| Guardrail[Guardrail Orchestrator]
    Guardrail -->|2. Query Rules| PolicyEngine[Policy Engine]
    PolicyEngine -->|Parse YAML & DB| PolicyRepository[Policy Repository]
    Guardrail -->|3. Evaluate Conditions| PolicyEvaluator[Policy Evaluator]
    PolicyEvaluator -->|Coerce Types & Compare| Operators[Comparison Operators]
    
    Guardrail -->|4. Decision Routing| Decision{Decision Outcome}
    
    Decision -->|allow / log_and_allow| Executor[Tool Executor]
    Decision -->|block| Block[Return 403 Blocked]
    Decision -->|require_hitl| HITLQueue[PgApprovalQueue]
    
    HITLQueue -->|Suspend Action & Wait| AuditorUI[React Auditor Console]
    AuditorUI -->|Approve & Release| FastAPI
    
    Executor -->|Run Action| Plugins[Tool Plugins Registry]
    Plugins -->|SQLite sandbox| DBTool[Database Tool]
    Plugins -->|smtplib| EmailTool[Email Tool]
    Plugins -->|os.read| FileTool[File Tool]
    Plugins -->|Dynamic Plugins| ExternalPlugins[External Log Tool]
    
    FastAPI -->|5. Record Decision| AuditLogger[Postgres Audit Logger]
    AuditLogger -->|Cryptographic Chaining| AuditRepo[Audit Log Repository]
    AuditRepo -->|SHA-256 Chained Blocks| PostgreSQL[(PostgreSQL / SQLite)]
    
    FastAPI -->|Prometheus Registry| Metrics[Observability Middleware]
```

---

## 🛠️ Platform Core Capabilities

### 1. Declarative Security Policy Engine
- **Flexible Rules Schema:** Evaluates requests against declarative policies loaded dynamically from [default.yaml](file:///home/jslxh/PROJETCS/guardrail-ai/configs/default.yaml) and synchronized to the database.
- **Boolean Combinator Logic:** Evaluates conditions in [evaluator.py](file:///home/jslxh/PROJETCS/guardrail-ai/app/core/evaluator.py) supporting `AND` / `OR` logical operators.
- **Robust Type-Coercion:** Implemented in [operators.py](file:///home/jslxh/PROJETCS/guardrail-ai/app/core/operators.py), the `compare` module automatically coerces string-formatted parameters (e.g. `record_count: "150"`) to numbers before testing numeric boundary rules (e.g. `> 100`).

### 2. Tamper-Evident Cryptographic Audit Ledger
- **SHA-256 Block Chaining:** Built into [audit_log_repository.py](file:///home/jslxh/PROJETCS/guardrail-ai/app/database/repositories/audit_log_repository.py), all evaluations are hashed and chained (the `checksum` of each block hashes the canonical contents of the record appended to the `prev_checksum` of the previous block).
- **Concurrency Protection:** Uses PostgreSQL advisory locks (`pg_advisory_xact_lock`) to serialize concurrent writers, maintaining absolute block integrity without deadlocks.
- **Chain Verification:** The system includes a verification function `verify_integrity` to parse the log chain and detect any deleted, injected, or modified audit entries.

### 3. Human-in-the-Loop (HITL) Approvals
- **Stateful Suspend & Resume:** When policies mark an action as `require_hitl`, execution is suspended, and the transaction is placed into [PgApprovalQueue](file:///home/jslxh/PROJETCS/guardrail-ai/app/hitl/approval.py#L54-L123).
- **One-Click Release:** Once an auditor reviews and approves the request, the orchestrator retrieves the original parameters, executes the tool, logs the outcome, and marks the ticket as `executed`.

### 4. Dynamic Tool Plugin System (Open/Closed Principle)
- **Plugin Registry:** The [ToolExecutor](file:///home/jslxh/PROJETCS/guardrail-ai/app/core/executor.py#L7-L80) utilizes a dynamic [ToolRegistry](file:///home/jslxh/PROJETCS/guardrail-ai/app/plugins/registry.py) to automatically discover and register plugins.
- **Extensible:** New tools can be introduced without modifying the core executor codebase by subclassing [BaseToolPlugin](file:///home/jslxh/PROJETCS/guardrail-ai/app/plugins/interface.py) and saving them inside the [plugins](file:///home/jslxh/PROJETCS/guardrail-ai/plugins) directory.

### 5. Production-Ready Observability
- **Prometheus Telemetry:** Tracks HTTP request rates, tool execution latencies, database transaction counts, and security exception flags in [metrics.py](file:///home/jslxh/PROJETCS/guardrail-ai/app/observability/metrics.py) using the RED/USE framework.
- **Health Verification:** Provides structured subsystem checks (Database connection, Groq API availability, SMTP Server ping) under `/health`.

---

## 📁 Project Directory Structure

```
guardrail-ai/
│
├── alembic/                       # Database schema migration history
│
├── app/                           # Core FastAPI backend package
│   ├── main.py                    # Gateway entry point & lifecycle hooks
│   │
│   ├── api/                       # REST API layer (routers & dependencies)
│   │   ├── routes.py              # Primary evaluation & execution endpoints
│   │   ├── approval_routes.py     # Suspend/release HITL workflows
│   │   ├── audit_routes.py        # Audit logs search & cryptographic check
│   │   ├── ai_routes.py           # Conversational Agent & Explainer integration
│   │   ├── auth_routes.py         # JWT Token & user session endpoints
│   │   └── monitoring_routes.py   # System metrics, analytics, and health reports
│   │
│   ├── core/                      # Guardrail evaluation core engine
│   │   ├── guardrail.py           # Evaluation orchestrator
│   │   ├── policy_engine.py       # Configuration policy synchronizer
│   │   ├── evaluator.py           # AST condition validator
│   │   └── executor.py            # Unified execution pipeline
│   │
│   ├── audit/                     # Audit trail routing hooks
│   │   └── logger.py              # File fallback & Postgres logger interfaces
│   │
│   ├── database/                  # Persistence and Data Access layers
│   │   ├── session.py             # SQLAlchemy session factory
│   │   ├── models/                # SQLAlchemy database definitions
│   │   └── repositories/          # Encapsulated query logic (Repository pattern)
│   │
│   ├── hitl/                      # Human-in-the-loop components
│   │   └── approval.py            # In-memory and PostgreSQL-backed approval queues
│   │
│   ├── observability/             # Telemetry & Monitoring config
│   │   ├── metrics.py             # Prometheus metrics registry & counts
│   │   ├── middleware.py          # HTTP latency & status tracking middleware
│   │   └── health.py              # Service-specific health check routines
│   │
│   └── tools/                     # Core tool integrations (dynamic plugins)
│       ├── database_tool.py       # SQLite database simulator
│       ├── email_tool.py          # SMTP client supporting templates
│       └── file_tool.py           # File reader implementation
│
├── configs/
│   └── default.yaml               # System governance policy definition
│
├── frontend/                      # React SPA Web Dashboard
│   ├── src/
│   │   ├── pages/                 # Dashboard, Approvals, Chatbot Sandbox, Analytics
│   │   ├── components/            # Reusable dashboard cards, layouts, error-bounds
│   │   └── lib/                   # API Axios fetch clients
│   ├── package.json               # Frontend dependencies & Vite scripts
│   └── tailwind.config.js         # Styling configurations
│
├── plugins/                       # Target directory for hot-loaded external plugins
│   └── log_tool.py                # External logging plugin example
│
├── tests/                         # Pytest test suite (unit and integration tests)
├── Dockerfile                     # Multi-stage production backend build
├── Dockerfile.dev                 # Slim development backend build
├── docker-compose.yml             # Development orchestrator (FastAPI + React)
└── docker-compose.prod.yml        # Production orchestration (Postgres + Nginx + FastAPI)
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
Ensure you have the following installed:
- Python 3.12+ (or the `uv` toolchain)
- Node.js 18+ & npm
- PostgreSQL (Database backend)

### 2. Environment Configuration
Copy the environment template from the root directory:
```bash
cp .env.example .env
```
Key configuration parameters:
```env
# Persistence Setup
DATABASE_URL=postgresql://guardrail:password@localhost:5432/guardrail

# LLM Orchestrator Setup
GROQ_API_KEY=gsk_your_groq_api_key

# Email Server Setup (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_address@gmail.com
SMTP_PASSWORD=your_app_specific_password
```

### 3. Backend Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run Alembic migrations to construct the database schema:
   ```bash
   alembic upgrade head
   ```
4. Seed default database users, administrative accounts, and policy records:
   ```bash
   python seed_db.py
   ```
5. Run the FastAPI application server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *Swagger documentation is served at `http://localhost:8000/docs`.*

### 4. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   *The React console will run on `http://localhost:5173`. Outbound requests are routed to the FastAPI backend via Vite dev proxy.*

### 5. Running with Docker Compose
To boot up the entire development ecosystem (FastAPI, React client, PostgreSQL database, Adminer admin interface) in one command:
```bash
docker-compose up --build
```
For production deployment with production-ready builds (served through an Nginx proxy):
```bash
docker-compose -f docker-compose.prod.yml up --build
```

---

## 🔌 API Reference Cheat-Sheet

| Endpoint | Method | Role | Description |
|---|---|---|---|
| `/auth/login` | `POST` | *Anonymous* | Authenticates users and returns JWT access & refresh tokens |
| `/execute` | `POST` | `operator` | Evaluates parameters and runs the selected tool dynamically |
| `/evaluate` | `POST` | `viewer` | Runs policy checking logic dry-run without executing actions |
| `/approvals/pending` | `GET` | `auditor` | Fetches suspended actions waiting for human-in-the-loop release |
| `/approvals/{id}/approve`| `POST` | `auditor` | Releases suspended action, triggering execution downstream |
| `/audit/logs` | `GET` | `auditor` | Searches audit records with sorting and filters |
| `/audit/verify` | `GET` | `auditor` | Validates SHA-256 chaining to verify audit log integrity |
| `/ai/chat` | `POST` | `viewer` | Conversational interface translating natural language to tools |
| `/ai/explain` | `POST` | `auditor` | Compiles detailed reasoning for policy block/exception states |
| `/metrics` | `GET` | *System* | Promytheus endpoint tracking RED/USE system statistics |
| `/health` | `GET` | *System* | Verifies readiness of DB, Groq, and SMTP server integrations |

---

## 🧪 Testing & Verification

To run unit tests, database queries assertions, and validation endpoints:
```bash
# Execute pytest suite bypasssing external rate limits
GROQ_API_KEY="" pytest
```

To run cryptographic audit validation via cURL:
```bash
curl -X GET "http://localhost:8000/api/audit/verify" \
     -H "Authorization: Bearer <auditor_jwt_token>"
```
Expected output:
```json
{
  "valid": true,
  "checked": 1420,
  "errors": []
}
```

---

## 🔐 Security & Governance (RBAC Roles)

Aegis AI enforces role-based access controls to segregate operations, audits, and configuration tasks:

1. **viewer:** Permitted to query dashboard counters, evaluate hypothetical requests (`POST /evaluate`), and speak with the AI Chatbot helper.
2. **operator:** Authorized to execute permitted actions (`POST /execute`) and run pipeline tests.
3. **auditor:** Granted full access to review suspended actions (`PgApprovalQueue`), approve/reject execution tickets, query the Audit ledger, and run cryptographic verification checks.
4. **admin:** Allowed to directly configure, update, and deploy declarative policy YAML rules to the live policy engines.

---

## 📄 License

Proprietary. Jslxh. All rights reserved.

