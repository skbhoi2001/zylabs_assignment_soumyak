import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.workflow.state import GraphState
from app.workflow.nodes.planner import planner_node
from app.workflow.nodes.researcher import researcher_node
from app.workflow.nodes.analyst import analyst_node
from app.workflow.nodes.quality_check import quality_check_node, quality_router
from app.workflow.nodes.report_generator import report_generator_node

logger = get_logger(__name__)


def _increment_retry(state: GraphState) -> GraphState:
    """Thin wrapper inserted before researcher on retry paths to bump the counter."""
    return {**state, "retry_count": state.get("retry_count", 0) + 1}


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("quality_check", quality_check_node)
    builder.add_node("report_generator", report_generator_node)
    builder.add_node("increment_retry", _increment_retry)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst", "quality_check")
    builder.add_conditional_edges(
        "quality_check",
        quality_router,
        {
            "researcher": "increment_retry",
            "report_generator": "report_generator",
        },
    )
    builder.add_edge("increment_retry", "researcher")
    builder.add_edge("report_generator", END)

    return builder.compile()


graph = build_graph()

NODE_ORDER = ["planner", "researcher", "analyst", "quality_check", "report_generator"]


async def run_graph(
    session: Any,
    run_id: str,
    queue: asyncio.Queue,
) -> None:
    """Execute the LangGraph workflow asynchronously and emit SSE events."""
    from app.core.database import engine
    from app.models.models import WorkflowRun, Session as DBSession
    from sqlmodel import Session as SqlSession

    session_id = session.id

    async def emit(event_type: str, node: str = "", data: dict | None = None):
        payload = {"type": event_type, "node": node, "timestamp": datetime.now(timezone.utc).isoformat()}
        if data:
            payload.update(data)
        await queue.put(payload)

    def _update_run(run_id: str, status: str, current_node: str, graph_state: dict):
        with SqlSession(engine) as db:
            run = db.get(WorkflowRun, run_id)
            if run:
                run.status = status
                run.current_node = current_node
                run.graph_state = graph_state
                if status in ("complete", "error"):
                    run.completed_at = datetime.now(timezone.utc)
                db.add(run)
                db.commit()

    def _update_session_status(session_id: str, status: str):
        with SqlSession(engine) as db:
            s = db.get(DBSession, session_id)
            if s:
                s.status = status
                s.updated_at = datetime.now(timezone.utc)
                db.add(s)
                db.commit()

    initial_state: GraphState = {
        "session_id": session_id,
        "company_name": session.company_name,
        "website": session.website,
        "objective": session.objective,
        "research_plan": [],
        "raw_findings": {},
        "report_sections": {},
        "quality_score": 0,
        "gaps": [],
        "retry_count": 0,
        "final_report": {},
        "error": None,
        "sources": [],
    }

    try:
        await emit("started", "planner")

        current_state = initial_state
        seen_nodes: set[str] = set()

        async for chunk in graph.astream(initial_state):
            for node_name, node_state in chunk.items():
                if node_name in ("increment_retry",):
                    continue  # internal — don't surface to frontend

                display_node = node_name
                event_state = {**current_state, **node_state}
                current_state = event_state

                if display_node not in seen_nodes:
                    await emit("node_start", display_node)
                    seen_nodes.add(display_node)

                await emit(
                    "node_complete",
                    display_node,
                    {
                        "quality_score": event_state.get("quality_score"),
                        "retry_count": event_state.get("retry_count"),
                        "error": event_state.get("error"),
                    },
                )
                _update_run(run_id, "running", display_node, dict(event_state))

        # Workflow finished
        error = current_state.get("error")
        if error and not current_state.get("final_report"):
            _update_run(run_id, "error", "failed", dict(current_state))
            _update_session_status(session_id, "error")
            await emit("error", "", {"message": error})
        else:
            _update_run(run_id, "complete", "report_generator", dict(current_state))
            _update_session_status(session_id, "complete")
            await emit("complete", "report_generator", {"final_report": current_state.get("final_report")})

    except Exception as exc:
        logger.error(f"Graph execution failed: {exc}", extra={"session_id": session_id}, exc_info=True)
        _update_run(run_id, "error", "failed", {"error": str(exc)})
        _update_session_status(session_id, "error")
        await emit("error", "", {"message": str(exc)})
