# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                  │
│  Dashboard | NewSession | SessionDetail                     │
│  TanStack Query · React Hook Form · EventSource (SSE)       │
└────────────────────┬────────────────────────────────────────┘
                     │ REST + SSE
┌────────────────────▼────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.11)             │
│  POST /sessions  GET /sessions  GET /sessions/:id           │
│  POST /sessions/:id/run   GET /sessions/:id/run (SSE)       │
│  POST /sessions/:id/chat  GET /sessions/:id/chat            │
│  GET /health                                                │
└────────┬───────────────────────────────┬────────────────────┘
         │ asyncio.create_task           │ SQLModel
┌────────▼────────────────┐   ┌──────────▼─────────────────┐
│   LangGraph Workflow     │   │      SQLite Database         │
│  Planner → Researcher   │   │  sessions                    │
│  → Analyst → QCheck     │   │  workflow_runs               │
│  → ReportGenerator      │   │  messages                    │
└────────┬────────────────┘   └────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────┐
│                  External APIs                             │
│  Anthropic (claude-sonnet-4-6)  ·  Tavily Search          │
└───────────────────────────────────────────────────────────┘
```

---

## Component Table

| Layer | Component | Tech | Responsibility |
|-------|-----------|------|----------------|
| Frontend | React SPA | Vite + React + TanStack Query + Tailwind | Session creation, live progress, report display, follow-up chat |
| Backend | FastAPI | Python 3.11 + FastAPI + SQLModel | REST APIs, SSE streaming, async workflow orchestration |
| AI Workflow | LangGraph Graph | LangGraph 0.2 + Claude | 5-node directed graph: plan → research → analyse → QA → report |
| Persistence | SQLite | SQLModel + SQLAlchemy | Sessions, workflow runs (graph state JSON), chat messages |
| External | Claude / Tavily | Anthropic API + Tavily | LLM completions (all nodes) and web search (Researcher node) |

---

## LangGraph Node Diagram

```
START
  │
  ▼
┌─────────┐
│ Planner │  Claude: breaks objective into 4–6 research sub-tasks
└────┬────┘
     │
     ▼
┌────────────┐
│ Researcher │  Tavily search per sub-task + website scrape
└─────┬──────┘
      │
      ▼
┌─────────┐
│ Analyst │  Claude: synthesises 9 report sections
└────┬────┘
     │
     ▼
┌──────────────┐
│ QualityCheck │  Claude: scores completeness 0–100
└──────┬───────┘
       │
       ├─ score >= 70 ──────────────────────────┐
       │                                         │
       └─ score < 70 AND retry < 2 → increment → Researcher (loop)
       │
       └─ score < 70 AND retry >= 2 ────────────┐
                                                 │
                                                 ▼
                                    ┌────────────────────┐
                                    │  ReportGenerator   │  formats final JSON
                                    └─────────┬──────────┘
                                              │
                                             END
```

**Conditional routing logic** (`quality_router`):
- `quality_score >= 70` → `report_generator`
- `quality_score < 70 AND retry_count < 2` → `researcher` (with `retry_count + 1`)
- `quality_score < 70 AND retry_count >= 2` → `report_generator` (best-effort)

---

## GraphState Schema

```python
class GraphState(TypedDict):
    session_id: str
    company_name: str
    website: str
    objective: str
    research_plan: List[str]        # Planner output
    raw_findings: Dict[str, Any]    # Researcher output (per sub-task)
    report_sections: Dict[str, str] # Analyst output (9 sections)
    quality_score: int              # QualityCheck output
    gaps: List[str]                 # QualityCheck gaps
    retry_count: int                # incremented on re-research
    final_report: Dict[str, Any]    # ReportGenerator output
    error: Optional[str]            # set on any node failure
    sources: List[str]              # URLs collected by Researcher
```

---

## Database Schema

### sessions
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| company_name | TEXT | |
| website | TEXT | |
| objective | TEXT | |
| status | TEXT | pending / running / complete / error |
| created_at | DATETIME | UTC |
| updated_at | DATETIME | UTC |

### workflow_runs
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| session_id | TEXT FK | → sessions.id |
| status | TEXT | pending / running / complete / error |
| current_node | TEXT | last node executed |
| graph_state | JSON | full GraphState snapshot |
| started_at | DATETIME | |
| completed_at | DATETIME | |

### messages
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| session_id | TEXT FK | → sessions.id |
| role | TEXT | user / assistant |
| content | TEXT | |
| created_at | DATETIME | UTC |

---

## API Endpoint Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | Create a new research session |
| GET | `/sessions` | List all sessions (paginated: skip, limit) |
| GET | `/sessions/:id` | Fetch session detail + final report |
| POST | `/sessions/:id/run` | Trigger async LangGraph workflow |
| GET | `/sessions/:id/run` | SSE stream — live node progress events |
| POST | `/sessions/:id/chat` | Send a follow-up message |
| GET | `/sessions/:id/chat` | Fetch full chat history |
| GET | `/health` | Health check (DB + API key status) |

### SSE Event Types

| Type | Description |
|------|-------------|
| `started` | Workflow execution began |
| `node_start` | A node has started |
| `node_complete` | A node has finished (includes `quality_score`, `error`) |
| `complete` | Workflow finished successfully |
| `error` | Workflow failed |
| `ping` | Keep-alive heartbeat (every 30s) |
