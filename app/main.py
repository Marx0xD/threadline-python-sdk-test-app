from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import internal_router, orders_router, test_router
from app.core.config import get_settings
from app.db.session import init_db


settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A demo FastAPI order workflow for debugging and investigation.",
    lifespan=lifespan,
)

app.include_router(orders_router)
app.include_router(test_router)
app.include_router(internal_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "orders": "/orders"}
