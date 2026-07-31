# Aegis AI

**Enterprise-Grade Runtime Action Interception & AI-Assisted Governance Platform**

Aegis AI is a FastAPI and React platform designed to secure, monitor, and audit tool operations (such as database deletions, email deliveries, or file operations) performed by AI agents or human operators. By evaluating actions against declarative policies, the system provides **automated enforcement, AI-powered explanations, human-in-the-loop (HITL) approvals, and a comprehensive audit trail**.

```
                     ┌─────────────────────────────────┐
  Agent / Client ───>│  FastAPI REST API                 │
                     │  - POST /evaluate               │
                     │  - POST /execute                │
                     │  - POST /ai/chat                │
                     └───────┬──────────────┬──────────┘
                             │              │
                     ┌───────▼──────┐ ┌─────▼──────────┐
                     │ Guardrail    │ │ Groq Service   │
                     │ Orchestrator │ │ (Llama Agent)  │
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
                     ┌───────▼───────┐     ┌──────────────────────┐
                     │ Tool Executor │────>│ SQLite Database      │
                     │  (Plugins)    │────>│ Gmail SMTP Service   │
                     │               │────>│ File System          │
                     └───────┬───────┘     └──────────────────────┘
                             │
                     ┌───────▼───────┐
                     │ File & DB     │
                     │  Audit Loggers│
                     └───────────────┘
```

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| **Backend Core** | Python 3.12+, FastAPI, Uvicorn ASGI |
| **Persistence** | PostgreSQL (Alembic Migrations), SQLAlchemy ORM |
| **Sandbox DB** | SQLite (`./data/dummy.db` pre-populated with 10k rows) |
| **Email Transport** | `smtplib` + `EmailMessage` templates |
| **LLM Orchestration** | Groq SDK (`llama-3.3-70b-versatile` model) |
| **Frontend Web** | React 18, Vite 5, Tailwind CSS, TanStack React Query, Lucide icons |
| **Testing** | `pytest` unit test suite (475 test cases) |

---

## 📁 Project Directory Structure

```
guardrail-ai/
│
├── app/                          # Core backend package
│   ├── main.py                   # FastAPI initialization & startup routines
│   │
│   ├── api/                      # REST API routing layer
│   │   ├── routes.py             # Core endpoints (/evaluate, /execute, /simulate, /audit)
│   │   ├── ai_routes.py          # AI analysis & chatbot routes (/ai/chat, /ai/explain)
│   │   └── approval_routes.py    # Approval workflow (/approvals/{id}/approve, /reject)
│   │
│   ├── core/                     # Guardrail policy engine
│   │   ├── guardrail.py          # Guardrail orchestrator
│   │   ├── evaluator.py          # Rule condition matcher (AND/OR logic)
│   │   ├── operators.py          # Type-coercing value comparison module
│   │   └── executor.py           # Tool plugin resolver and executor
│   │
│   ├── services/                 # AI & LLM components
│   │   ├── prompts.py            # Chatbot and explainer prompt templates
│   │   └── groq_service.py       # Groq API integration client
│   │
│   ├── database/                 # Persistence layer
│   │   ├── models/               # SQLAlchemy models (ExecutionHistory, HITLRequest)
│   │   └── repositories/         # Repository patterns for cleaner queries
│   │
│   └── tools/                    # Core system plugins
│       ├── database_tool.py      # SQLite table simulator
│       ├── email_tool.py         # SMTP transmission with templates
│       └── file_tool.py          # Local file reader tool
│
├── configs/
│   └── default.yaml              # Declarative policy definition
│
├── frontend/                     # React web console (Aegis AI)
│   ├── src/
│   │   ├── pages/                # Dashboard, Policies, Approvals, Chatbot, Analytics, Simulation
│   │   └── components/           # Navigation, status badges, UI layouts
│   └── package.json
│
├── tests/                        # 475 pytest integration and unit cases
│   ├── api/                      # Endpoint integration tests
│   └── unit/                     # Business logic and plugin tests
│
├── .env.example                  # Environment file template
├── requirements.txt              # Production dependency file
└── pyproject.toml                # Project configurations & dependency bounds
```

---

## 💡 Guardrail Concept & Lifecycles

Every request submitted to `POST /execute` undergoes the following lifecycle:

1. **Evaluation:** The **Policy Engine** evaluates the request arguments against configured rules in `configs/default.yaml` using standard comparator operators.
2. **Decision Classifications:**
   * `allow` — Request is secure; executes immediately.
   * `log_and_allow` — Permitted, but logged in detail to the audit trail.
   * `block` — Request violates policy rules; rejected immediately.
   * `require_hitl` — Suspended. Captured as an approval ticket in the `hitl_requests` table with status `pending`.
3. **Automatic HITL Action Execution:** When a security analyst approves the pending request via `POST /approvals/{id}/approve`, the backend:
   * Triggers the **Tool Executor** to run the suspended tool.
   * Sends the real SMTP email or updates the SQLite database.
   * Propagates results back to the **Execution History** log, updating status to `executed`.

---

## ⚙️ Setup & Installation

### 1. Prerequisites
Ensure you have the following installed:
* Python 3.12+
* Node.js 18+ & npm
* PostgreSQL (for production database backend)

### 2. Backend Setup
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repo-url> guardrail-ai
   cd guardrail-ai
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and configure secrets in `.env`:
   ```bash
   cp .env.example .env
   ```
   **Key `.env` values to set:**
   ```env
   # Database connection (PostgreSQL)
   DATABASE_URL=postgresql://guardrail:password@localhost:5432/guardrail
   
   # Groq API access
   GROQ_API_KEY=gsk_your_groq_api_key
   
   # SMTP credentials for real email sending
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_address@gmail.com
   SMTP_PASSWORD=your_app_specific_password
   ```

5. Seed the default database users:
   ```bash
   uv run python seed_db.py
   ```
6. Run the FastAPI application:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *Interactive Swagger documentation is available at `http://localhost:8000/docs`.*

### 3. Frontend Web Console Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   *The console is served at `http://localhost:5173`. Proxies `/api` calls to the backend on `http://localhost:8000`.*

---

## 🧪 Testing and Verification

To run the complete test suite (475 test cases) cleanly:

```bash
# Force fallback to the deterministic mock Groq client to bypass rate limits
GROQ_API_KEY="" uv run pytest
```

---

## 🏢 Features Deep-Dive

### ✉️ Gmail SMTP Integration
The email plugin in [email_tool.py](file:///home/jslxh/PROJETCS/guardrail-ai/app/tools/email_tool.py) triggers real emails using SMTP with the template:
> **Subject:** Join the AI Avalon Tech Team Assessment Meeting
> 
> **Body:**
> Dear [Name],
> 
> We are pleased to invite you to the next stage of our selection process: the AI Avalon Technical Team Assessment Meeting.
> 
> Please confirm your availability by accessing the following link:
> https://avalon.ai/assessments/test-link
> 
> Best regards,
> The AI Avalon Team

### 🗄️ SQLite Database Sandbox
The database tool operates on a sandbox SQLite database (`./data/dummy.db`). On application startup, it populates a table `records` with 10,000 mock data rows, executing real SQL deletion queries whenever database tool actions are allowed.

### 🤖 Robust Operator Type-Coercion
Comparison evaluations automatically support type conversion. If a user submits strings via forms (e.g. `record_count="500"`), the engine matches this against numeric rules (e.g. `100`), coercing types safely to prevent unhandled comparison tracebacks.

---

## 📄 License
Proprietary. Aivar Innovations. All rights reserved.
