# Engineering Decisions

## Decision 1: SQLite + SQLModel over PostgreSQL

**Choice:** SQLite with SQLModel (a thin SQLAlchemy + Pydantic wrapper), auto-created file at `backend/demo_zylabs.db`.

**Alternatives considered:**
- PostgreSQL + SQLAlchemy core (production-grade, async-native with `asyncpg`)
- PostgreSQL + asyncpg directly (lowest latency, most control)
- Firebase Firestore (no-infra NoSQL, but poor fit for relational session/run/message structure)

**Rationale:**
SQLite eliminates all infrastructure overhead — no Docker Compose, no connection pooling, no migration server. The DB file is created by `SQLModel.metadata.create_all(engine)` on startup: zero manual steps. SQLModel shares Pydantic model definitions between the ORM layer and FastAPI request/response schemas, cutting boilerplate significantly. The `graph_state` column stores the full `GraphState` TypedDict as JSON natively in SQLite.

**Tradeoffs:**
- SQLite has a single-writer lock. Concurrent workflow executions on the same file serialise at the DB layer. For a single-user demo this is invisible; at 10+ concurrent users it becomes a bottleneck.
- SQLModel uses synchronous sessions. We avoid blocking the asyncio event loop by running DB writes inside `asyncio.create_task()` callbacks. This works for our traffic level but is not equivalent to a true async ORM.

**What I'd change with 2 extra weeks:**
Switch to PostgreSQL with `asyncpg` + `SQLAlchemy async sessions` + Alembic migrations. The SQLModel schema is already portable — changing `DATABASE_URL` and adding async session handling is the full migration path. PostgreSQL also enables full-text search over `report_sections` without a separate search index.

**Tech debt:**
- No Alembic migration files — schema is auto-created with `create_all()`. A production deployment would require versioned migrations to support rolling updates.
- `check_same_thread=False` on the SQLite engine is safe for a single-process server but will silently corrupt data under `uvicorn --workers N`. Any multi-worker deployment must switch to PostgreSQL first.

---

## Decision 2: SSE over WebSockets for workflow progress

**Choice:** Server-Sent Events via `sse-starlette`, consumed by the browser's native `EventSource` API.

**Alternatives considered:**
- WebSockets — bidirectional, lower overhead at scale, but requires upgrade handshake + ping/pong management
- Long-polling — simple but chatty (a new request every N seconds regardless of events)
- Webhook + client polling hybrid — works behind NAT but doubles DB reads

**Rationale:**
Workflow progress is inherently one-way: the server pushes node events; the browser never sends data on the same connection. SSE is the correct tool for this use case. It uses a plain HTTP/1.1 connection — works through every reverse proxy without special config — has built-in browser reconnect, and requires zero client libraries (native `EventSource`). `sse-starlette` integrates as a FastAPI `StreamingResponse` in ~10 lines.

Each session gets its own `asyncio.Queue`. The LangGraph execution task puts events onto the queue; the SSE endpoint drains it. This decouples graph execution from HTTP transport completely.

**Tradeoffs:**
- SSE is unidirectional — if the client needs to cancel a running workflow mid-stream, it can't signal that over the same connection. We'd need a separate `DELETE /sessions/:id/run` endpoint.
- Max 6 concurrent SSE connections per origin in HTTP/1.1 browsers. Not a concern for this app (one SSE stream per tab), but would be a problem on a multi-session dashboard page.
- No `Last-Event-ID` support — if the browser disconnects mid-workflow and reconnects, missed events are not replayed. The client re-renders from the latest DB state instead.

**What I'd change with 2 extra weeks:**
Add WebSocket support alongside SSE (same event payload format, different transport) so mobile clients connect via WebSocket. Also implement `Last-Event-ID` resumption by persisting SSE events to a `workflow_events` table keyed by `(session_id, sequence_number)`.

**Tech debt:**
- No event replay on reconnect. If the browser loses connection mid-workflow, the SSE stream is silently dropped and the stepper freezes. The client currently polls `GET /sessions/:id` as a fallback.
- The per-session `asyncio.Queue` lives in process memory (`_sse_queues` dict in `sessions.py`). It is not shared across multiple server processes, so SSE only works in single-worker mode.

---

## Decision 3: LangGraph over raw `asyncio` chaining

**Choice:** LangGraph `StateGraph` with typed `GraphState` TypedDict.

**Alternatives considered:**
- Raw `asyncio` pipeline — `await planner(); await researcher(); ...` — simple but no formal state contract between steps
- LangChain `SequentialChain` — higher-level but limited conditional routing support
- Prefect / Celery — production-grade workflow orchestration with retries and a UI, but requires a broker (Redis/RabbitMQ) and adds significant infra overhead
- Temporal — best-in-class durable execution, but far beyond scope for a 2-day sprint

**Rationale:**
LangGraph enforces a formal graph structure with explicit node boundaries, a single typed shared state object (`GraphState`), and a declarative conditional routing API (`add_conditional_edges`). This matches exactly what the evaluation rubric requires (5 nodes, typed state, conditional routing, intermediate outputs, error handling). Every node receives the full `GraphState` and returns a partial update — making intermediate outputs inspectable and debuggable without any extra instrumentation.

The `quality_router` conditional edge — the core of the retry loop — is expressed in 8 lines of pure Python. Replicating this cleanly in raw `asyncio` would require manual state management, loop guards, and retry counters threaded through every function.

**Key implementation detail — `astream()` adapter:**
LangGraph's `astream()` returns chunks of the form `{node_name: updated_state_slice}`. We wrap this in `graph.py` with a thin adapter that translates each chunk into our SSE event format (`node_start`, `node_complete`, etc.) and simultaneously writes the full state to `WorkflowRun.graph_state` in the DB.

**Tradeoffs:**
- LangGraph's checkpoint/persistence layer (`langgraph-checkpoint`) is not wired up. Graph state is not automatically resumable after a server restart. We handle persistence manually by saving `graph_state` to `WorkflowRun` after each node.
- The `increment_retry` node is an internal implementation detail (bumps `retry_count`) that we filter out of SSE events to keep the frontend stepper clean.
- `astream()` is asynchronous; each node call is still synchronous (blocking on Gemini API calls). True parallelism within a node (e.g. fan-out research sub-tasks) requires LangGraph's `Send` API, which is not yet implemented.

**What I'd change with 2 extra weeks:**
1. Integrate `langgraph-checkpoint-sqlite` so the graph resumes from the last checkpoint on server restart.
2. Use LangGraph's `Send` API to fan out Researcher sub-tasks concurrently (`asyncio.gather` inside the node), cutting research wall-clock time by ~60%.
3. Add a dedicated `ErrorRecovery` node that rewrites failed sections using only website content when Tavily is unavailable.

---

## Decision 4: Google Gemini (`gemini-2.5-flash`) over Anthropic Claude

**Choice:** `google-genai` SDK, model `gemini-2.5-flash`, via a shared `workflow/gemini.py` client module.

**Background:**
The original design used `claude-sonnet-4-6` (Anthropic). During implementation the project was switched to Gemini to enable a fully free-tier setup — no credit card required for development or demos.

**Alternatives considered:**
- Anthropic `claude-sonnet-4-6` — stronger reasoning, more reliable JSON output, but paid-only
- OpenAI `gpt-4o-mini` — free tier available, but smaller context window for the Analyst prompt
- Ollama (local LLama 3) — zero API cost, but unpredictable JSON adherence and slow on CPU

**Rationale:**
`gemini-2.5-flash` is available on Google AI Studio's free tier with sufficient quota for development and demos. It handles the structured JSON prompts reliably when given explicit instructions to avoid markdown fences. The `google-genai` SDK (`google-genai >= 1.0.0`) is the current maintained package — the older `google-generativeai` is deprecated.

**Shared client pattern:**
All four LLM-calling files (planner, analyst, quality_check, chat) import from `workflow/gemini.py` rather than calling the SDK directly. This centralises the model name, retry logic, and fence-stripping in one place — changing the model or adding streaming requires a single-file edit.

```python
# workflow/gemini.py
MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3

def generate(prompt, system=None):   # single-turn with optional system instruction
def chat_with_history(system, history, user_message):  # multi-turn chat
def strip_fences(raw):               # remove ```json ... ``` if model adds them
```

**Tradeoffs:**
- Gemini free tier rate limits (`gemini-2.0-flash` had `limit: 0` — daily quota exhausted). Solution: use `gemini-2.5-flash`, which has a separate and larger quota pool on this key.
- Gemini's chat history format uses `role: "model"` (not `"assistant"`), and history must start with a `"user"` turn. `chat_with_history()` handles both normalisation steps.
- JSON output is less consistent than Claude — the model occasionally wraps output in ` ```json ``` ` despite explicit instructions. `strip_fences()` handles this defensively.

**Tech debt:**
- `time.sleep()` blocks the asyncio event loop during 429 retries (30s per attempt). Should be replaced with `asyncio.sleep()` in an async wrapper.
- No fallback model — if `gemini-2.5-flash` quota is exhausted, the workflow fails. A fallback chain (e.g. try `gemini-2.0-flash-lite` first) would improve resilience.

---

## Top 3 Tech Debt Items

1. **No test suite.** The backend has zero unit or integration tests. AI node outputs are non-deterministic — contract tests on the JSON schema returned by each node (e.g. "does Planner always return a list of strings?") are the highest-value tests to write first. Without them, prompt changes can silently break the parsing logic.

2. **SQLite + single-writer lock.** Safe for single-process development, but `uvicorn --workers N > 1` will cause DB corruption. Any production deployment must migrate to PostgreSQL before adding workers. The schema is already portable.

3. **No authentication.** All API endpoints are publicly accessible. A production deployment needs at minimum: JWT-based auth (Auth0 or Clerk), session ownership checks (`session.user_id == current_user.id`), and per-user rate limits on workflow runs to prevent API cost abuse.
