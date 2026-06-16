# ZyLabs AI Research Copilot

An AI-powered company research automation tool built with **React**, **FastAPI**, **LangGraph**, and **SQLite**. Submit a company name and research objective; a 5-node LangGraph workflow plans, researches, analyses, quality-checks, and generates a 9-section report — with live SSE progress streaming and a follow-up chat interface.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| `GEMINI_API_KEY` | Free | [aistudio.google.com](https://aistudio.google.com) → Get API key |
| `TAVILY_API_KEY` | Free (1,000/mo) | [app.tavily.com](https://app.tavily.com) → Dashboard |

> **No paid API needed.** Both keys have generous free tiers sufficient for development and demos.

---

## Quick Start

Open **two terminal windows** and run:

### Terminal 1 — Backend

```bash
cd backend

# First time only — create virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in your API keys

# Every subsequent time — just activate then start
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

> **Important:** always run `source .venv/bin/activate` first in each new terminal.
> Your prompt will show `(.venv)` when the environment is active.
> Only then will `pip`, `uvicorn`, and `python` resolve to the correct versions.

### Terminal 2 — Frontend

```bash
cd frontend

# First time only
npm install
cp .env.example .env

# Every time
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## Environment Variables

### Backend — `backend/.env`

```env
GEMINI_API_KEY=your_key_from_aistudio_google_com
TAVILY_API_KEY=your_key_from_app_tavily_com
DATABASE_URL=sqlite:///./demo_zylabs.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google AI Studio key — used for all LLM calls (`gemini-2.5-flash`) |
| `TAVILY_API_KEY` | Yes | Tavily web search — used by the Researcher node |
| `DATABASE_URL` | No | SQLite file path (default: `sqlite:///./demo_zylabs.db`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins for CORS |
| `LOG_LEVEL` | No | `INFO` / `DEBUG` / `WARNING` (default: `INFO`) |

### Frontend — `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | No | Backend base URL (default: `http://localhost:8000`) |

---

## Database

SQLite — **zero setup required**. The database file (`demo_zylabs.db`) is created automatically on first server start inside the `backend/` directory.

To create it manually before starting the server:

```bash
cd backend
source .venv/bin/activate
python -c "from app.core.database import create_db_and_tables; create_db_and_tables(); print('Done')"
```

Three tables are created: `sessions`, `workflow_runs`, `messages`.

---

## How It Works

```
User submits company + objective
        │
        ▼
POST /sessions  →  POST /sessions/:id/run
        │
        ▼
  LangGraph Workflow (5 nodes)
  ┌─────────────────────────────────────────────────────────┐
  │  Planner  →  Researcher  →  Analyst  →  QualityCheck   │
  │                                  ↓              ↓       │
  │                         score ≥ 70 → ReportGenerator   │
  │                         score < 70 → re-research (×2)  │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  SSE stream → live progress in WorkflowStepper UI
        │
        ▼
  9-section report + follow-up chat (Gemini with report as context)
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — DB + API key status |
| `POST` | `/sessions` | Create a new research session |
| `GET` | `/sessions` | List all sessions |
| `GET` | `/sessions/:id` | Fetch session detail + report |
| `POST` | `/sessions/:id/run` | Trigger async LangGraph workflow |
| `GET` | `/sessions/:id/run` | SSE stream — live node progress events |
| `POST` | `/sessions/:id/chat` | Send a follow-up chat message |
| `GET` | `/sessions/:id/chat` | Fetch full chat history |

Interactive API docs: **http://localhost:8000/docs**

---

## Project Structure

```
zylabs_assignment_soumyak/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings — loads .env, fails fast on missing keys
│   │   │   ├── database.py     # SQLModel engine + session factory
│   │   │   └── logging.py      # Structured JSON logging with request/session IDs
│   │   ├── models/
│   │   │   └── models.py       # Session, WorkflowRun, Message + Pydantic schemas
│   │   ├── routers/
│   │   │   ├── sessions.py     # All session, run, and chat endpoints + SSE
│   │   │   └── health.py       # GET /health
│   │   └── workflow/
│   │       ├── gemini.py       # Shared Gemini client (gemini-2.5-flash + retry logic)
│   │       ├── state.py        # GraphState TypedDict (13 fields)
│   │       ├── graph.py        # LangGraph StateGraph wiring + async execution
│   │       ├── chat.py         # Follow-up chat with report injected as system prompt
│   │       └── nodes/
│   │           ├── planner.py          # Node 1: break objective into sub-tasks
│   │           ├── researcher.py       # Node 2: Tavily search + website scrape
│   │           ├── analyst.py          # Node 3: synthesise 9 report sections
│   │           ├── quality_check.py    # Node 4: score + conditional routing
│   │           └── report_generator.py # Node 5: format final JSON report
│   ├── requirements.txt
│   ├── .env.example
│   └── demo_zylabs.db          # Auto-created SQLite file (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js       # Axios API client
│   │   ├── components/
│   │   │   ├── WorkflowStepper.jsx   # Live SSE progress — 5-step bar
│   │   │   ├── ReportViewer.jsx      # 9 collapsible sections + source links
│   │   │   ├── ChatPanel.jsx         # Follow-up chat thread
│   │   │   ├── SessionCard.jsx       # Dashboard session card
│   │   │   └── ErrorBoundary.jsx     # React error boundary with retry
│   │   └── pages/
│   │       ├── Dashboard.jsx         # Session list (/)
│   │       ├── NewSession.jsx        # Session creation form (/sessions/new)
│   │       └── SessionDetail.jsx     # Workflow + report + chat (/sessions/:id)
│   ├── .env.example
│   └── package.json
└── docs/
    ├── architecture.md
    ├── engineering-decisions.md
    └── product-improvements.md
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React + Vite + TanStack Query + Tailwind CSS | Fast HMR, zero-config, utility-first styling |
| Backend | FastAPI + Pydantic v2 + SQLModel | Async-native, auto OpenAPI docs, shared Pydantic models |
| AI Workflow | LangGraph 0.2 — 5-node DAG | Typed state, conditional routing, native async |
| LLM | Google `gemini-2.5-flash` (free tier) | Strong reasoning, generous free quota |
| Web Search | Tavily Search API (free tier) | Purpose-built for LLM agents, structured JSON results |
| Database | SQLite via SQLModel | Zero infra — single file, auto-created, swap to Postgres for scale |
| Streaming | Server-Sent Events via `sse-starlette` | Simpler than WebSockets for one-way server push |

---

## LangGraph Workflow Detail

| Node | Input | Output | Model |
|------|-------|--------|-------|
| **Planner** | company, website, objective | 4–6 research sub-tasks | `gemini-2.5-flash` |
| **Researcher** | research plan | raw findings per task | Tavily API + HTTP scrape |
| **Analyst** | raw findings | 9 report sections | `gemini-2.5-flash` |
| **QualityCheck** | report sections | score (0–100) + gaps | `gemini-2.5-flash` |
| **ReportGenerator** | sections + sources | formatted final report JSON | — |

**Conditional routing:** score ≥ 70 → finalize · score < 70 + retries < 2 → re-research · max retries → best-effort finalize.

---

## Rate Limit Handling

The Gemini free tier enforces per-minute request limits. The app handles this automatically:

- Shared `workflow/gemini.py` wraps every call with **3 retries + 30s backoff** on `429 RESOURCE_EXHAUSTED`
- If `gemini-2.0-flash` is rate-limited, switch to `gemini-2.5-flash` in `gemini.py` (already set as default)
- Tavily failures are caught per sub-task; the workflow continues with partial findings

---

## Docs

| Document | Contents |
|----------|----------|
| [docs/architecture.md](docs/architecture.md) | System diagram, LangGraph node flow, DB schema, API reference |
| [docs/engineering-decisions.md](docs/engineering-decisions.md) | 3 key decisions with alternatives, tradeoffs, and tech debt |
| [docs/product-improvements.md](docs/product-improvements.md) | Weaknesses, roadmap, buyer/user analysis, metrics, 90-day plan |

---

## Demo

> Add Loom demo link here after recording.

---

## Deployment

> Add Railway / Render deployment link here.
