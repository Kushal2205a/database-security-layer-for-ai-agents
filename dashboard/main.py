"""
dashboard/main.py — Weir local edition
No auth, no Supabase. Open localhost:8000 and it just works.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes import intercepts, api
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)

app.include_router(intercepts.router)
app.include_router(api.router)