# ZyLabs AI Research Copilot

An AI-powered company research automation tool built with **React**, **FastAPI**, **LangGraph**, and **SQLite**. Enter a company name and research objective — a 5-node LangGraph workflow plans, researches, analyses, quality-checks, and generates a structured 9-section report, with live SSE progress streaming and a follow-up chat interface powered by Gemini.

> **Fully free to run.** Uses Google Gemini free tier + Tavily free tier + local SQLite. No credit card required.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| `GEMINI_API_KEY` | Free | [aistudio.google.com](https://aistudio.google.com) → **Get API key** |
| `TAVILY_API_KEY` | Free (1,000 req/mo) | [app.tavily.com](https://app.tavily.com) → Dashboard |

---

## Quick Start

Open **two terminal windows** and run each block in its own terminal.

### Terminal 1 — Backend

```bash
cd backend

# First time only
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your GEMINI_API_KEY and TAVILY_API_KEY

# Every subsequent session
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

> **Tip:** always run `source .venv/bin/activate` first in each new terminal session.  
> Your prompt will show `(.venv)` when the environment is active — only then do `pip`, `python`, and `uvicorn` resolve correctly.

Backend is ready at → **http://localhost:8000**  
Interactive API docs → **http://localhost:8000/docs**

### Terminal 2 — Frontend

```bash
cd frontend

# First time only
npm install
cp .env.example .env

# Every subsequent session
npm run dev
```

App is ready at → **http://localhost:5173**

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
| `GEMINI_API_KEY` | **Yes** | Google AI Studio key — powers all LLM calls via `gemini-2.5-flash` |
| `TAVILY_API_KEY` | **Yes** | Tavily search API — used by the Researcher node (web search per sub-task) |
| `DATABASE_URL` | No | SQLite file path. Default: `sqlite:///./demo_zylabs.db` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins. Default: `http://localhost:5173,http://localhost:3000` |
| `LOG_LEVEL` | No | `INFO` / `DEBUG` / `WARNING`. Default: `INFO` |

### Frontend — `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | No | Backend base URL. Default: `http://localhost:8000` |

---

## Database

Zero setup required. SQLite creates `backend/demo_zylabs.db` automatically on first server start.

To create it manually before starting the server:

```bash
cd backend
source .venv/bin/activate
python -c "from app.core.database import create_db_and_tables; create_db_and_tables(); print('Done')"
```

Three tables are auto-created: `sessions`, `workflow_runs`, `messages`.

If port 8000 is already in use:
```bash
lsof -ti :8000 | xargs kill -9   # macOS / Linux
uvicorn app.main:app --reload --port 8000
```

---

## How It Works

```
User submits company name + website + objective
              │
              ▼
      POST /sessions  →  POST /sessions/:id/run
              │
              ▼
      LangGraph Workflow (5 nodes, async)
  ┌───────────────────────────────────────────────────────────┐
  │                                                           │
  │  Planner ──► Researcher ──► Analyst ──► QualityCheck     │
  │                  ▲                           │            │
  │                  │         score < 70        │            │
  │                  └──── re-research (max 2×) ─┘            │
  │                                    │                      │
  │                         score ≥ 70 ▼                      │
  │                         ReportGenerator                   │
  └───────────────────────────────────────────────────────────┘
              │
              ▼
      GET /sessions/:id/run  (SSE stream)
      → live node events → WorkflowStepper UI updates
              │
              ▼
      9-section report stored in DB
      + follow-up chat (Gemini with full report as system context)
```

### LangGraph Nodes

| Node | What it does | Model |
|------|-------------|-------|
| **Planner** | Breaks objective into 4–6 targeted research sub-tasks | `gemini-2.5-flash` |
| **Researcher** | Tavily web search per sub-task + website scrape via HTTP | Tavily API |
| **Analyst** | Synthesises all findings into 9 structured report sections | `gemini-2.5-flash` |
| **QualityCheck** | Scores completeness 0–100; routes back to Researcher if score < 70 | `gemini-2.5-flash` |
| **ReportGenerator** | Formats and enriches final JSON report with metadata + sources | — |

### Conditional Routing

| Condition | Next node |
|-----------|-----------|
| `quality_score >= 70` | ReportGenerator (finalize) |
| `quality_score < 70` AND `retry_count < 2` | Researcher (re-research gaps) |
| `quality_score < 70` AND `retry_count >= 2` | ReportGenerator (best-effort) |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — DB + API key status |
| `POST` | `/sessions` | Create a new research session |
| `GET` | `/sessions` | List all sessions (supports `skip` / `limit`) |
| `GET` | `/sessions/:id` | Fetch session detail + final report |
| `POST` | `/sessions/:id/run` | Trigger async LangGraph workflow |
| `GET` | `/sessions/:id/run` | **SSE stream** — live node progress events |
| `POST` | `/sessions/:id/chat` | Send a follow-up message |
| `GET` | `/sessions/:id/chat` | Fetch full chat history |

Full interactive docs at **http://localhost:8000/docs**

---

## Project Structure

```
zylabs_assignment_soumyak/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic Settings — loads .env, fails fast on missing keys
│   │   │   ├── database.py         # SQLModel engine + session factory
│   │   │   └── logging.py          # Structured JSON logging (request ID, session ID, node name)
│   │   ├── models/
│   │   │   └── models.py           # Session, WorkflowRun, Message ORM models + Pydantic schemas
│   │   ├── routers/
│   │   │   ├── sessions.py         # All session, run, and chat endpoints + SSE queue
│   │   │   └── health.py           # GET /health — DB + API key liveness
│   │   └── workflow/
│   │       ├── gemini.py           # Shared Gemini client: gemini-2.5-flash + 3× retry on 429
│   │       ├── state.py            # GraphState TypedDict (13 fields)
│   │       ├── graph.py            # LangGraph StateGraph wiring + async astream execution
│   │       ├── chat.py             # Follow-up chat: report injected as Gemini system instruction
│   │       └── nodes/
│   │           ├── planner.py          # Node 1 — breaks objective into sub-tasks
│   │           ├── researcher.py       # Node 2 — Tavily search + HTTP website scrape
│   │           ├── analyst.py          # Node 3 — synthesises 9 report sections
│   │           ├── quality_check.py    # Node 4 — scores + conditional router
│   │           └── report_generator.py # Node 5 — formats final JSON report
│   ├── requirements.txt
│   ├── .env.example
│   └── demo_zylabs.db              # Auto-created SQLite DB (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js           # Axios API client (all endpoints)
│   │   ├── components/
│   │   │   ├── WorkflowStepper.jsx # Live SSE consumer — 5-step progress bar
│   │   │   ├── ReportViewer.jsx    # 9 collapsible sections + copy-to-clipboard + source links
│   │   │   ├── ChatPanel.jsx       # Follow-up chat thread with typing indicator
│   │   │   ├── SessionCard.jsx     # Dashboard card with status badge
│   │   │   └── ErrorBoundary.jsx   # React error boundary with retry button
│   │   └── pages/
│   │       ├── Dashboard.jsx       # / — session list, new session button
│   │       ├── NewSession.jsx      # /sessions/new — form with Zod validation
│   │       └── SessionDetail.jsx   # /sessions/:id — stepper + report + chat
│   ├── .env.example
│   └── package.json
└── docs/
    ├── architecture.md             # System diagram, LangGraph flow, DB schema, API reference
    ├── engineering-decisions.md    # 3 key decisions with alternatives, tradeoffs, tech debt
    └── product-improvements.md     # Weaknesses, roadmap, buyer/user analysis, 90-day plan
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React 18 + Vite + TanStack Query v5 + Tailwind CSS 3 | Fast HMR, no-config, utility-first styling, smart server-state caching |
| Forms | React Hook Form + Zod | Inline validation, zero re-renders on change |
| Backend | FastAPI + Pydantic v2 + SQLModel | Async-native, auto OpenAPI docs, shared Pydantic models for DB + API |
| AI Workflow | LangGraph 0.2 — 5-node `StateGraph` | Typed shared state, conditional routing, native `astream()` |
| LLM | Google `gemini-2.5-flash` (free tier) | Strong reasoning, generous free quota, stable JSON output |
| Web Search | Tavily Search API (free tier) | Purpose-built for LLM agents, structured results, 1,000 free req/mo |
| Database | SQLite via SQLModel + aiosqlite | Zero infra — auto-created file, easy swap to Postgres for production |
| Streaming | Server-Sent Events via `sse-starlette` | Correct tool for one-way server push; native browser `EventSource` support |

---

## Rate Limit Handling

Gemini free tier enforces per-minute request limits. The shared `workflow/gemini.py` module handles this automatically:

- **3 automatic retries** with 30s backoff on `429 RESOURCE_EXHAUSTED`
- Model is set to `gemini-2.5-flash` which has the highest available quota on this key
- Tavily failures per sub-task are caught individually — the workflow continues with partial findings rather than aborting

---

## Further Reading

| Document | Contents |
|----------|----------|
| [docs/architecture.md](docs/architecture.md) | Full system diagram, LangGraph node flow, GraphState schema, DB schema, SSE event types |
| [docs/engineering-decisions.md](docs/engineering-decisions.md) | SQLite vs Postgres, SSE vs WebSockets, LangGraph vs raw asyncio — with alternatives, tradeoffs, tech debt |
| [docs/product-improvements.md](docs/product-improvements.md) | 5 weaknesses, top 3 improvements, buyer/user analysis, success metrics, 4-week AI roadmap, 90-day plan |

---

## Demo

> Add Loom demo link here (3–5 min: create session → watch graph → read report → chat).

---

## Deployment

> Add Railway / Render hosted deployment link here.
