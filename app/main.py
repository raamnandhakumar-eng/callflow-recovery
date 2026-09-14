import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.readiness import router as readiness_router
from app.api.routes import router
from app.config import get_settings
from app.db import Base, engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("callflow")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CallFlow Recovery",
    version="0.2.0",
    description="Voice-to-outcome vertical slice with RAG, booking, CRM, SMS, and analytics.",
    lifespan=lifespan,
)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
app.include_router(router)
app.include_router(readiness_router)


def is_admin_write(path: str, method: str) -> bool:
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    return path == "/v1/knowledge/documents" or (
        path.startswith("/v1/learning/") and path.endswith("/approve")
    )


@app.middleware("http")
async def protect_admin_writes(request: Request, call_next):
    if is_admin_write(request.url.path, request.method):
        supplied_key = request.headers.get("x-admin-key")
        if settings.admin_api_key:
            if supplied_key != settings.admin_api_key:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Admin authorization required"},
                )
        elif settings.app_env in {"demo", "production"}:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "Knowledge administration is disabled on the public demo. "
                        "Configure ADMIN_API_KEY to enable protected writes."
                    )
                },
            )
    return await call_next(request)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request_id,
                    "path": request.url.path,
                    "error": str(exc),
                }
            )
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal error", "request_id": request_id},
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            }
        )
    )
    return response
