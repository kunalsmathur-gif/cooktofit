"""Local stand-in for the WhatsApp channel. Disabled outside local/test."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.gate.identity import normalize_phone
from app.gate.service import Gate, Inbound
from app.inbound import handle

router = APIRouter(prefix="/dev", tags=["dev"])


class SimIn(BaseModel):
    from_phone: str
    text: str | None = None
    is_group: bool = False


class SimOut(BaseModel):
    decision: str
    replies: list[str]


def require_dev(settings: Annotated[Settings, Depends(get_settings)]) -> Settings:
    if not settings.is_dev:
        raise HTTPException(status_code=404)
    return settings


@router.post("/simulate")
async def simulate(
    body: SimIn, request: Request, settings: Annotated[Settings, Depends(require_dev)]
) -> SimOut:
    try:
        phone = normalize_phone(body.from_phone)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    gate = Gate(settings.phone_hash_key.get_secret_value())
    async with request.app.state.pool.connection() as conn:
        outcome = await handle(conn, gate, Inbound(phone, body.text, body.is_group))
    return SimOut(decision=outcome.decision.value, replies=outcome.replies)
