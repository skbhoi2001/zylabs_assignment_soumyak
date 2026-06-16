# Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Browser  (React 18 SPA)                      │
│                                                                  │
│  Dashboard (/)  ·  NewSession (/sessions/new)                    │
│  SessionDetail (/sessions/:id)                                   │
│                                                                  │
│  TanStack Query v5  ·  React Hook Form + Zod  ·  Tailwind CSS    │
│  EventSource API (SSE)  ·  Axios HTTP client                     │
└──────────────────────┬───────────────────────────────────────────┘
                       │  REST + SSE  (HTTP/1.1)
┌──────────────────────▼───────────────────────────────────────────┐
│                  FastAPI Backend  (Python 3.11)                   │
│                                                                  │
│  POST /sessions          GET  /sessions                          │
│  GET  /sessions/:id      POST /sessions/:id/run                  │
│  GET  /sessions/:id/run  (SSE stream)                            │
│  POST /sessions/:id/chat GET  /sessions/:id/chat                 │
│  GET  /health                                                    │
│                                                                  │
│  Middleware: request-ID logging · CORS · global exception handler│
└──────────┬─────────────────────────────┬─────────────────────────┘
           │ asyncio.create_task()       │ SQLModel ORM
┌──────────▼──────────────────┐  ┌──────▼──────────────────────────┐
│   LangGraph Workflow         │  │   SQLite  (demo_zylabs.db)       │
│                              │  │                                  │
│  Planner                     │  │  sessions                        │
│    ↓                         │  │  workflow_runs  (graph_state JSON│
│  Researcher                  │  │  messages                        │
│    ↓                         │  └──────────────────────────────────┘
│  Analyst                     │
│    ↓                         │
│  QualityCheck ──(retry loop)─┘
│    ↓
│  ReportGenerator
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────┐
│                      External APIs                               │
│                                                                  │
│  Google Gemini  (gemini-2.5-flash, free tier)                    │
│    · Planner node   · Analyst node                               │
│    · QualityCheck   · Chat replies                               │
│                                                                  │
│  Tavily Search API  (free tier, 1,000 req/mo)                    │
│    · Researcher node  (one search per sub-task)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Table

| Layer | Component | Tech | Responsibility |
|-------|-----------|------|----------------|
| Frontend | React SPA | Vite + React 18 + TanStack Query v5 + Tailwind CSS | Session creation, live SSE progress, report display, follow-up chat |
| Backend | FastAPI | Python 3.11 + FastAPI + SQLModel + Pydantic v2 | REST APIs, SSE streaming, async workflow orchestration |
| AI Workflow | LangGraph Graph | LangGraph 0.2 + `google-genai` | 5-node directed graph: plan → research → analyse → QA → report |
| LLM Client | `workflow/gemini.py` | `google-genai` SDK (`gemini-2.5-flash`) | Shared client with 3× retry + 30s backoff on 429 rate limits |
| Persistence | SQLite | SQLModel + SQLAlchemy + aiosqlite | Sessions, workflow runs (full GraphState as JSON), chat messages |
| External — LLM | Google Gemini | `gemini-2.5-flash` free tier | All LLM completions across all nodes and chat |
| External — Search | Tavily | Tavily Search API free tier | Web search in Researcher node (one query per sub-task) |

---

## LangGraph Node Diagram

```
START
  │
  ▼
┌──────────┐
│ Planner  │  gemini-2.5-flash
│          │  Input:  company_name, website, objective
│          │  Output: research_plan (list of 4–6 sub-task strings)
└────┬─────┘
     │
     ▼
┌─────────────┐
│ Researcher  │  Tavily Search API + httpx website scrape
│             │  Input:  research_plan (or gaps on retry)
│             │  Output: raw_findings (dict per sub-task), sources (URLs)
└──────┬──────┘
       │
       ▼
┌──────────┐
│ Analyst  │  gemini-2.5-flash
│          │  Input:  raw_findings (condensed to 15k chars)
│          │  Output: report_sections (9-key dict)
└────┬─────┘
     │
     ▼
┌───────────────┐
│ QualityCheck  │  gemini-2.5-flash
│               │  Input:  report_sections
│               │  Output: quality_score (0–100), gaps (list of strings)
└───────┬───────┘
        │
        │  quality_score >= 70  ─────────────────────────────┐
        │                                                     │
        │  quality_score < 70 AND retry_count < 2             │
        │    → increment_retry node (retry_count += 1)        │
        │    → back to Researcher                             │
        │                                                     │
        │  quality_score < 70 AND retry_count >= 2 ───────────┤
        │                                                     │
        ▼                                                     ▼
 (retry path)                                   ┌────────────────────┐
                                                │  ReportGenerator   │
                                                │                    │
                                                │  Input:  sections  │
                                                │          sources   │
                                                │  Output: final_    │
                                                │          report    │
                                                │          (JSON)    │
                                                └─────────┬──────────┘
                                                          │
                                                         END
```

### Conditional Routing Logic (`quality_router`)

| Condition | Route to | Notes |
|-----------|----------|-------|
| `quality_score >= 70` | `report_generator` | Finalize |
| `quality_score < 70` AND `retry_count < 2` | `increment_retry` → `researcher` | Re-research identified gaps |
| `quality_score < 70` AND `retry_count >= 2` | `report_generator` | Best-effort — prevent infinite loop |

---

## GraphState Schema

All nodes read from and write to a single `TypedDict`. No global variables, no ad-hoc dicts.

```python
class GraphState(TypedDict):
    session_id: str                   # links graph execution to DB session
    company_name: str
    website: str
    objective: str
    research_plan: List[str]          # Planner output — 4–6 sub-task strings
    raw_findings: Dict[str, Any]      # Researcher output — keyed by sub-task
    report_sections: Dict[str, str]   # Analyst output — 9 section keys
    quality_score: int                # QualityCheck output — 0 to 100
    gaps: List[str]                   # QualityCheck output — gap descriptions
    retry_count: int                  # incremented by increment_retry node
    final_report: Dict[str, Any]      # ReportGenerator output — full JSON
    error: Optional[str]              # set on any node failure
    sources: List[str]                # URLs collected by Researcher
```

The full `GraphState` dict is serialised to JSON and stored in `workflow_runs.graph_state` after every node completion, enabling partial result recovery on failure.

---

## Gemini Client (`workflow/gemini.py`)

A shared module wrapping all Gemini calls. Every node imports from here — no direct SDK calls in node files.

```python
MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3

def generate(prompt: str, system: Optional[str] = None) -> str:
    # Calls client.models.generate_content() with automatic 429 retry
    # Sleeps 30s × attempt on RESOURCE_EXHAUSTED before retrying

def chat_with_history(system: str, history: list, user_message: str) -> str:
    # Builds Gemini Content history (role: "user" | "model")
    # Strips leading "model" turns (Gemini requires history to start with "user")
    # Sends via client.chats.create(...).send_message(...)

def strip_fences(raw: str) -> str:
    # Removes ```json ... ``` fences the model occasionally adds
```

---

## Database Schema

File location: `backend/demo_zylabs.db` (auto-created on first server start)

### sessions

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT PK | UUID v4 |
| `company_name` | TEXT | |
| `website` | TEXT | |
| `objective` | TEXT | |
| `status` | TEXT | `pending` / `running` / `complete` / `error` |
| `created_at` | DATETIME | UTC |
| `updated_at` | DATETIME | UTC — updated on status change |

### workflow_runs

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT PK | UUID v4 |
| `session_id` | TEXT FK | → `sessions.id` |
| `status` | TEXT | `pending` / `running` / `complete` / `error` |
| `current_node` | TEXT | Last node that completed |
| `graph_state` | JSON | Full `GraphState` snapshot — updated after each node |
| `started_at` | DATETIME | Set when run is triggered |
| `completed_at` | DATETIME | Set on terminal status (`complete` / `error`) |

### messages

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT PK | UUID v4 |
| `session_id` | TEXT FK | → `sessions.id` |
| `role` | TEXT | `user` / `assistant` |
| `content` | TEXT | Message body |
| `created_at` | DATETIME | UTC |

---

## API Endpoint Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions` | Create a new research session — body: `{company_name, website, objective}` |
| `GET` | `/sessions` | List all sessions — params: `skip` (default 0), `limit` (default 50) |
| `GET` | `/sessions/:id` | Session detail + `final_report` JSON |
| `POST` | `/sessions/:id/run` | Trigger async LangGraph workflow — returns `{run_id, status: "started"}` |
| `GET` | `/sessions/:id/run` | **SSE stream** — emits node lifecycle events |
| `POST` | `/sessions/:id/chat` | Send a user message — returns assistant `Message` object |
| `GET` | `/sessions/:id/chat` | Full message history for the session |
| `GET` | `/health` | `{status, database, gemini_api_key, tavily_api_key}` |

### SSE Event Schema

Every event is a JSON object on the `data:` field.

| `type` | Payload fields | Description |
|--------|---------------|-------------|
| `started` | `node`, `timestamp` | Workflow execution began |
| `node_start` | `node`, `timestamp` | A specific node has started running |
| `node_complete` | `node`, `quality_score?`, `retry_count?`, `error?`, `timestamp` | Node finished |
| `complete` | `node`, `final_report`, `timestamp` | Full workflow succeeded |
| `error` | `message`, `timestamp` | Workflow failed — partial state saved to DB |
| `ping` | `timestamp` | Keep-alive heartbeat every 30s |

---

## Frontend Page & Component Map

| Route | Page | Key components |
|-------|------|----------------|
| `/` | `Dashboard.jsx` | `SessionCard` × N, skeleton loaders, new session button |
| `/sessions/new` | `NewSession.jsx` | React Hook Form + Zod, POST /sessions then POST /run |
| `/sessions/:id` | `SessionDetail.jsx` | `WorkflowStepper`, `ReportViewer`, `ChatPanel` |

| Component | Responsibility |
|-----------|---------------|
| `WorkflowStepper` | Opens `EventSource`, maps SSE events to 5-step progress bar |
| `ReportViewer` | Renders 9 collapsible section cards, copy-to-clipboard, source links |
| `ChatPanel` | Message thread, typing indicator, auto-scroll, sends POST /chat |
| `SessionCard` | Status badge (`pending`/`running`/`complete`/`error`), click to navigate |
| `ErrorBoundary` | Catches React render errors, shows retry button |
