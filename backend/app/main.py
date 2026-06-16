import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.logging import get_logger
from app.routers import health, sessions

logger = get_logger(__name__)

app = FastAPI(
    title="ZyLabs AI Research Copilot",
    description="AI-powered company research automation using LangGraph",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code}",
        extra={"request_id": request_id, "duration_ms": duration_ms},
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(str(exc), extra={"request_id": request_id}, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "request_id": request_id},
    )


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Database tables created / verified")


app.include_router(health.router)
app.include_router(sessions.router)
