import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column, JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=new_uuid, primary_key=True)
    company_name: str
    website: str
    objective: str
    status: str = Field(default="pending")  # pending | running | complete | error
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_runs"

    id: str = Field(default_factory=new_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    status: str = Field(default="pending")  # pending | running | complete | error
    current_node: Optional[str] = None
    graph_state: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=new_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    role: str  # user | assistant
    content: str
    created_at: datetime = Field(default_factory=utcnow)


# --- Pydantic schemas (request/response) ---

class SessionCreate(SQLModel):
    company_name: str
    website: str
    objective: str


class SessionRead(SQLModel):
    id: str
    company_name: str
    website: str
    objective: str
    status: str
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionRead):
    final_report: Optional[dict] = None


class MessageCreate(SQLModel):
    content: str


class MessageRead(SQLModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
