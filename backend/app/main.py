from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import run_migrations
from app.routers import auth, dashboard, doubt, practice
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Cognify] Starting up...")
    try:
        run_migrations()
    except Exception as e:
        print(f"[DB] Migration warning: {e}")
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    print("[Cognify] Shutting down.")


app = FastAPI(
    title="Cognify — Adaptive JEE Maths Engine",
    version="0.1.0",
    description="Adaptive cognitive learning system for JEE Mathematics",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/auth",      tags=["Auth"])
app.include_router(practice.router,  prefix="/practice",  tags=["Practice"])
app.include_router(doubt.router,     prefix="/doubt",     tags=["Doubt"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "Cognify API v0.1.0"}
