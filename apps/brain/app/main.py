import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app import db
from app.config import Settings, get_settings

log = logging.getLogger(__name__)

app = FastAPI(title="CookToFit Brain", version="0.1.0")

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
