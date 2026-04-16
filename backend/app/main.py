from fastapi import FastAPI
from app.database import engine
from app.models import Base

app = FastAPI(title="PokéRanker API")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)