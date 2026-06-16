# Engineering Decisions

## Decision 1: SQLite + SQLModel over PostgreSQL + SQLAlchemy

**Choice:** SQLite with SQLModel (a thin SQLAlchemy + Pydantic wrapper)

**Alternatives considered:**
- PostgreSQL + SQLAlchemy core
- PostgreSQL + asyncpg (fully async)
- Firebase Firestore (no-infra NoSQL)

**Rationale:**
SQLite eliminates all infrastructure overhead for a 2-day sprint — no Docker Compose, no connection pooling config, no migration server. SQLModel provides an idiomatic SQLAlchemy-compatible ORM that shares Pydantic models with FastAPI request/response schemas, reducing boilerplate. The graph_state column stores the full `GraphState` dict as JSON, which SQLite handles natively.

**Tradeoffs:**
- SQLite has a single-writer lock; concurrent workflow executions on the same DB file can serialize. For a single-user demo this is invisible; at 10+ concurrent users it becomes a bottleneck.
- `asyncio` + SQLite requires the `aiosqlite` driver; SQLModel uses a synchronous session that we wrap with `asyncio.create_task()` to avoid blocking the event loop.

**What I'd change with 2 extra weeks:**
Switch to PostgreSQL with `asyncpg` + Alembic migrations. The SQLModel schema is already portable — just swap `DATABASE_URL` and add async session handling. PostgreSQL also enables full-text search over report sections without a separate vector store.

**Tech debt:** No Alembic migration files — schema is auto-created with `create_all()`. A production deployment would need versioned migrations.

---

## Decision 2: SSE over WebSockets for workflow progress

**Choice:** Server-Sent Events via `sse-starlette`

**Alternatives considered:**
- WebSockets (bidirectional, requires upgrade handshake + ping/pong)
- Long-polling (simple but chatty and introduces latency)
- Webhook + polling hybrid

**Rationale:**
Workflow progress is inherently one-way: the server pushes node status events to the browser; the browser never sends data on the same connection. SSE is the correct tool for this — it uses a plain HTTP/1.1 connection, works through all reverse proxies without special config, has built-in browser reconnect, and requires only `EventSource` on the client (no library). `sse-starlette` integrates cleanly with FastAPI's `StreamingResponse`.

**Tradeoffs:**
- SSE is HTTP/1.1 only; multiplexed HTTP/2 doesn't give SSE the same head-of-line unblocking. For high-throughput dashboards serving many simultaneous streams, WebSockets are more efficient.
- Max 6 concurrent SSE connections per origin in HTTP/1.1 browsers. Not a concern for this app (one stream per tab), but would matter for a multi-session dashboard.

**What I'd change with 2 extra weeks:**
Add WebSocket support alongside SSE so mobile clients (which handle WS better) can connect. The event payload format is identical — the channel mechanism just changes.

**Tech debt:** No SSE reconnect state — if the browser disconnects mid-workflow, it reopens the stream but missed events are not replayed. A proper implementation would persist events to DB and support `Last-Event-ID` resumption.

---

## Decision 3: LangGraph over raw `asyncio` chaining

**Choice:** LangGraph `StateGraph` with typed `GraphState`

**Alternatives considered:**
- Raw `asyncio` pipeline (chain of coroutines)
- LangChain `SequentialChain`
- Prefect / Celery workflow orchestration

**Rationale:**
LangGraph enforces a formal graph structure with explicit node boundaries, typed shared state, and conditional routing — all required by the evaluation rubric. The `StateGraph` + `TypedDict` pattern guarantees that every node receives and returns the full state dict, making intermediate outputs inspectable and debuggable. The `add_conditional_edges` API expresses the QualityCheck retry loop concisely. Compared to raw `asyncio`, LangGraph makes the control flow visible and auditable; compared to Celery, it requires no broker infrastructure.

**Tradeoffs:**
- LangGraph's `astream()` returns chunks per-node; the event shape is `{node_name: updated_state}`. This required a thin adapter in `graph.py` to translate into our SSE event format.
- LangGraph's checkpoint / persistence layer (`langgraph-checkpoint`) is not wired up — graph state is not automatically resumable after a server restart. We handle persistence manually by saving `graph_state` to the `WorkflowRun` row on each node completion.

**What I'd change with 2 extra weeks:**
Integrate `langgraph-checkpoint-sqlite` so the graph can resume from the last checkpoint if the server crashes mid-workflow. Also add a parallel research step where sub-tasks fan out concurrently (using `Send` API) rather than sequentially, cutting research time by ~60%.

**Tech debt items:**
1. **No test suite.** The backend has no unit or integration tests. The graph, nodes, and API endpoints should each have test coverage. Priority: high — AI node outputs are non-deterministic, so contract tests on the JSON schema returned by each node are critical.
2. **SQLite concurrency limits.** A single DB file with `check_same_thread=False` is safe for one process but will corrupt under multiple workers. Any production `uvicorn --workers N` deployment requires PostgreSQL.
3. **No authentication.** All API endpoints are unauthenticated. A production deployment would require at minimum JWT-based auth with session ownership checks.
