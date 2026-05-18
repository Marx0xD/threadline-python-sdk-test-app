from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import internal_router, orders_router, test_router
from app.core.config import get_settings
from app.db.session import init_db
from threadline.client import Threadline
from threadline.integrations.fastapi import ThreadlineMiddleware

settings = get_settings()
threadline_client = Threadline(
    service_name=settings.app_name,
    environment=settings.environment,
    sidecar_url=settings.threadline_sidecar_url,
    instrumentations= ["httpx"],
    auto_trace_enabled=True
)   

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        yield
    finally:
        threadline_client.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A demo FastAPI order workflow for debugging and investigation.",
    lifespan=lifespan,
)
app.add_middleware(ThreadlineMiddleware, threadline=threadline_client)
app.include_router(orders_router)
app.include_router(test_router)
app.include_router(internal_router)


@app.get("/")
def root() -> dict[str, str]:
    threadline_client.step(
        "app.root.viewed",
        route="/",
        transport="http",
        metadata={"docs": "/docs", "orders": "/orders"},
    )
    return {"app": settings.app_name, "docs": "/docs", "orders": "/orders"}
