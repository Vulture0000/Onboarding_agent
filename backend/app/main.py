"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agents, auth, calendar, employees, leave, me, policy, resumes, tasks
from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.seed import seed_if_empty, seed_users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("onboarding")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if seed_if_empty(db):
            logger.info("Seeded demo data.")
        if seed_users(db):
            logger.info("Seeded demo login accounts.")
    finally:
        db.close()
    # Warm the FAISS index in the background (needs GEMINI_API_KEY; safe no-op otherwise)
    import threading

    from app.rag.retriever import get_vector_store

    threading.Thread(target=get_vector_store, daemon=True).start()
    logger.info("Startup complete. LLM enabled: %s", settings.llm_enabled)
    yield


app = FastAPI(
    title="Agentic AI Employee Onboarding System",
    description="LangGraph-orchestrated multi-agent onboarding prototype.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, me, employees, resumes, tasks, calendar, leave, policy, agents):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": settings.llm_enabled}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never expose Python stack traces to API clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again or check agent activity."},
    )
