"""S.S. Blue Metal — JSON API for the mobile app.

Shares db/billing.db with the desktop app.

Run:
    uvicorn webapp.main:app --host 127.0.0.1 --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import init_db  # noqa: E402
from webapp.routes import api  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="S.S. Blue Metal API",
    version="1.0.0",
    docs_url="/docs" if os.environ.get("API_DOCS", "1") != "0" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if os.environ.get("API_DOCS", "1") != "0" else None,
    lifespan=lifespan,
)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(api)


@app.get("/api/health")
def health():
    return {"status": "ok"}
