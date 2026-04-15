from fastapi import FastAPI

app = FastAPI(title="PokéRanker API")

@app.get("/health")
async def health():
    return {"status": "ok"}