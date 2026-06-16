from fastapi import APIRouter
from sqlmodel import Session, select
from app.core.database import engine
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    db_ok = False
    try:
        with Session(engine) as s:
            s.exec(select(1))
            db_ok = True
    except Exception:
        pass

    gemini_ok = bool(settings.gemini_api_key)
    tavily_ok = bool(settings.tavily_api_key)

    return {
        "status": "ok" if (db_ok and gemini_ok and tavily_ok) else "degraded",
        "database": "ok" if db_ok else "error",
        "gemini_api_key": "configured" if gemini_ok else "missing",
        "tavily_api_key": "configured" if tavily_ok else "missing",
    }
