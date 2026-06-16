import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session as DBSession, select
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_session
from app.core.logging import get_logger
from app.models.models import (
    Message,
    MessageCreate,
    MessageRead,
    Session,
    SessionCreate,
    SessionDetail,
    SessionRead,
    WorkflowRun,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory SSE queues: session_id -> asyncio.Queue
_sse_queues: dict[str, asyncio.Queue] = {}


def get_or_create_queue(session_id: str) -> asyncio.Queue:
    if session_id not in _sse_queues:
        _sse_queues[session_id] = asyncio.Queue()
    return _sse_queues[session_id]


# --- Session CRUD ---

@router.post("", response_model=SessionRead, status_code=201)
def create_session(payload: SessionCreate, db: DBSession = Depends(get_session)):
    session = Session(
        company_name=payload.company_name,
        website=payload.website,
        objective=payload.objective,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Session created", extra={"session_id": session.id})
    return session


@router.get("", response_model=List[SessionRead])
def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: DBSession = Depends(get_session),
):
    sessions = db.exec(
        select(Session).order_by(Session.created_at.desc()).offset(skip).limit(limit)
    ).all()
    return sessions


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: str, db: DBSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    run = db.exec(
        select(WorkflowRun)
        .where(WorkflowRun.session_id == session_id)
        .order_by(WorkflowRun.started_at.desc())
    ).first()

    final_report: Optional[dict] = None
    if run and run.graph_state:
        final_report = run.graph_state.get("final_report")

    return SessionDetail(
        id=session.id,
        company_name=session.company_name,
        website=session.website,
        objective=session.objective,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        final_report=final_report,
    )


# --- Workflow run ---

@router.post("/{session_id}/run", status_code=202)
async def trigger_run(session_id: str, db: DBSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "running":
        raise HTTPException(status_code=409, detail="Workflow already running")

    # Import here to avoid circular imports at module load
    from app.workflow.graph import run_graph

    run = WorkflowRun(session_id=session_id, started_at=datetime.now(timezone.utc))
    db.add(run)
    session.status = "running"
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)

    queue = get_or_create_queue(session_id)
    asyncio.create_task(run_graph(session, run.id, queue))

    return {"run_id": run.id, "status": "started"}


@router.get("/{session_id}/run")
async def stream_run(session_id: str, request: Request, db: DBSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    queue = get_or_create_queue(session_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"data": json.dumps(event)}
                if event.get("type") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "ping"})}

    return EventSourceResponse(event_generator())


# --- Chat ---

@router.post("/{session_id}/chat", response_model=MessageRead)
async def send_chat(
    session_id: str,
    payload: MessageCreate,
    db: DBSession = Depends(get_session),
):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    run = db.exec(
        select(WorkflowRun)
        .where(WorkflowRun.session_id == session_id)
        .order_by(WorkflowRun.started_at.desc())
    ).first()

    final_report: Optional[dict] = None
    if run and run.graph_state:
        final_report = run.graph_state.get("final_report")

    user_msg = Message(session_id=session_id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()

    history = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    ).all()

    from app.workflow.chat import generate_chat_reply

    reply_content = await generate_chat_reply(
        user_message=payload.content,
        history=history,
        final_report=final_report,
        session=session,
    )

    assistant_msg = Message(session_id=session_id, role="assistant", content=reply_content)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg


@router.get("/{session_id}/chat", response_model=List[MessageRead])
def get_chat_history(session_id: str, db: DBSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    ).all()
    return messages
