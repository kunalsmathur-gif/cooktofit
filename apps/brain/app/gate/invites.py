"""Admin operations on the allow-list. Members cannot invite before launch."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.gate.identity import hash_code, new_invite_code, normalize_phone


class InviteError(Exception):
    pass


@dataclass(frozen=True)
class Invite:
    phone_e164: str
    code: str
    expires_at: datetime


async def _household_id(conn: AsyncConnection[Any], name: str | None) -> UUID | None:
    if not name:
        return None
    cur = await conn.execute("select id from public.households where name = %s limit 1", (name,))
    row = await cur.fetchone()
    if row is None:
        cur = await conn.execute(
            "insert into public.households (name) values (%s) returning id", (name,)
        )
        row = await cur.fetchone()
    assert row is not None
    household_id: UUID = row[0]
    return household_id


async def create_invite(
    conn: AsyncConnection[Any],
    phone: str,
    display_name: str,
    *,
    role: Literal["admin", "member"] = "member",
    household: str | None = None,
    email: str | None = None,
    ttl_days: int = 7,
) -> Invite:
    """Create or reissue an invite. Reissuing resets the code, expiry and failed attempts."""
    phone_e164 = normalize_phone(phone)
    code = new_invite_code()
    async with conn.transaction():
        cur = await conn.execute(
            "select status from public.access_list where phone_e164 = %s for update", (phone_e164,)
        )
        existing = await cur.fetchone()
        if existing and existing[0] == "active":
            raise InviteError(f"{phone_e164} is already an active member")
        household_id = await _household_id(conn, household)
        cur = await conn.execute(
            """insert into public.access_list
                 (phone_e164, email, household_id, display_name, role, status,
                  invite_code_hash, invite_expires_at)
               values (%(phone)s, %(email)s, %(hh)s, %(name)s, %(role)s, 'invited',
                       %(hash)s, now() + make_interval(days => %(ttl)s))
               on conflict (phone_e164) do update set
                 email = coalesce(excluded.email, public.access_list.email),
                 household_id = coalesce(excluded.household_id, public.access_list.household_id),
                 display_name = excluded.display_name, role = excluded.role,
                 status = 'invited', revoked_at = null, failed_attempts = 0,
                 invite_code_hash = excluded.invite_code_hash,
                 invite_expires_at = excluded.invite_expires_at
               returning invite_expires_at""",
            {
                "phone": phone_e164,
                "email": email,
                "hh": household_id,
                "name": display_name,
                "role": role,
                "hash": hash_code(code),
                "ttl": ttl_days,
            },
        )
        row = await cur.fetchone()
    assert row is not None
    return Invite(phone_e164, code, row[0])


async def revoke(conn: AsyncConnection[Any], phone: str) -> bool:
    cur = await conn.execute(
        """update public.access_list
           set status = 'revoked', revoked_at = now(), invite_code_hash = null,
               invite_expires_at = null
           where phone_e164 = %s and status <> 'revoked'""",
        (normalize_phone(phone),),
    )
    return cur.rowcount > 0


async def list_access(conn: AsyncConnection[Any]) -> list[dict[str, Any]]:
    cur = conn.cursor(row_factory=dict_row)
    await cur.execute(
        """select phone_e164, display_name, role, status, failed_attempts,
                  invite_expires_at, activated_at, revoked_at
           from public.access_list order by created_at"""
    )
    return await cur.fetchall()


def invite_link(whatsapp_number: str | None, code: str) -> str | None:
    """Private deep link sent only to the invitee. Never put this in shareable content."""
    if not whatsapp_number:
        return None
    return f"https://wa.me/{whatsapp_number.lstrip('+')}?text=JOIN%20{code}"
