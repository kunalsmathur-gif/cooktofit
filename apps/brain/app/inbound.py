"""Channel-agnostic inbound pipeline: gate first, then the conversation core."""

from dataclasses import dataclass, field
from typing import Any

from psycopg import AsyncConnection

from app import core
from app.gate.service import Decision, Gate, Inbound


@dataclass(frozen=True)
class Outcome:
    decision: Decision
    replies: list[str] = field(default_factory=list)


async def handle(conn: AsyncConnection[Any], gate: Gate, msg: Inbound) -> Outcome:
    result = await gate.evaluate(conn, msg)
    out = [result.reply] if result.reply else []
    if result.decision is Decision.ALLOW and result.user_id is not None:
        out += await core.respond(result.user_id, msg.text)
    return Outcome(result.decision, out)
