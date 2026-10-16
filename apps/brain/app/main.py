import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app import db
from app.channels import simulator
from app.config import Settings, get_settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = db.make_pool(get_settings())
    await pool.open(wait=False)  # start even if the DB is down; /readyz reports it
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="CookToFit Brain", version="0.1.0", lifespan=lifespan)
app.include_router(simulator.router)

SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(settings: SettingsDep) -> JSONResponse:
    try:
        await db.ping(settings)
    except Exception:
        log.exception("readiness check failed: database unreachable")
        return JSONResponse({"status": "unavailable", "database": "down"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "up"})
