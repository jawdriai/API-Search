from fastapi import FastAPI
from .routers import router as items_router

app = FastAPI(title="Practice App: External API Integration")
app.include_router(items_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

