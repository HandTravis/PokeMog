from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base
from app.routes import router
from sqlalchemy import text
from alembic.config import Config
from alembic import command
import os

def run_migrations():
    """Run Alembic migrations on startup."""
    alembic_cfg = Config("/app/migrations/alembic.ini")
    alembic_cfg.set_main_option("script_location", "/app/migrations")
    command.upgrade(alembic_cfg, "head")

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield

app = FastAPI(title="PokéRanker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}