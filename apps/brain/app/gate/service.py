"""Invite-only access gate (ARCHITECTURE §9.1).

Runs before any media download, LLM call or tool, so a non-member costs nothing.
Access is decided only by the sender's verified phone number; message content can
activate an invite only when it comes from the invited number itself.
"""

import hmac
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.gate import replies
from app.gate.identity import extract_code, hash_code, hash_phone

log = logging.getLogger(__name__)

ALERT_AFTER_FOREIGN_ATTEMPTS = 3
REPLY_ONCE_DAYS = 30
ACTIVATION_LOCK_KEY = "cooktofit.activation"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    WAITLIST = "waitlist"
    WAITLIST_REMOVED = "waitlist_removed"
    CODE_MISMATCH = "code_mismatch"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    CAPACITY_FULL = "capacity_full"
    CAPPED = "capped"
    PAUSED = "paused"
    IGNORED = "ignored"


@dataclass(frozen=True)
class Inbound:
    from_phone: str  # E.164, as verified by the channel
    text: str | None
    is_group: bool = False


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    reply: str | None = None
    user_id: UUID | None = None


Row = dict[str, Any]


class Gate:
    def __init__(self, phone_hash_key: str) -> None:
        self._key = phone_hash_key

    async def evaluate(self, conn: AsyncConnection[Any], msg: Inbound) -> GateResult:
        async with conn.transaction():
            result = await self._decide(conn, msg)
            await conn.execute(
                """insert into public.gate_events (phone_hash, decision, replied)
                   values (%s, %s, %s)""",
                (
                    hash_phone(msg.from_phone, self._key),
                    result.decision.value,
                    result.reply is not None,
                ),
            )
        return result

    async def _decide(self, conn: AsyncConnection[Any], msg: Inbound) -> GateResult:
        if msg.is_group:
            return GateResult(Decision.IGNORED)

        cur = conn.cursor(row_factory=dict_row)
        await cur.execute("select * from public.app_settings where id = 1")
        settings = await cur.fetchone()
        if settings is None:
            raise RuntimeError("app_settings row missing; run the seed")

        await cur.execute(
            """select a.*, a.invite_expires_at > now() as invite_in_date
               from public.access_list a where a.phone_e164 = %s for update""",
            (msg.from_phone,),
        )
        member = await cur.fetchone()

        if member and member["status"] == "active":
            return await self._member(conn, member, settings)
        if member and member["status"] == "invited":
            return await self._activate(conn, member, msg, settings)
        return await self._non_member(conn, msg, settings)

    async def _member(self, conn: AsyncConnection[Any], member: Row, settings: Row) -> GateResult:
        user_id: UUID = member["user_id"]
        if settings["paused"]:
            return GateResult(Decision.PAUSED, replies.PAUSED, user_id)

        cur = await conn.execute(
            """insert into public.usage_counters (user_id, day, kind, count)
               select u.id, (now() at time zone u.timezone)::date, 'message', 1
               from public.users u where u.id = %s
               on conflict (user_id, day, kind)
               do update set count = public.usage_counters.count + 1
               returning count""",
            (user_id,),
        )
        row = await cur.fetchone()
        count = row[0] if row else 0
        cap: int = settings["daily_message_cap"]
        if count > cap:
            # Tell them once; stay silent for the rest of the day.
            return GateResult(
                Decision.CAPPED, replies.CAPPED if count == cap + 1 else None, user_id
            )
        return GateResult(Decision.ALLOW, None, user_id)

    async def _activate(
        self, conn: AsyncConnection[Any], invite: Row, msg: Inbound, settings: Row
    ) -> GateResult:
        phone = invite["phone_e164"]
        locked = invite["failed_attempts"] >= settings["invite_max_failed_attempts"]
        if not invite["invite_code_hash"] or not invite["invite_in_date"] or locked:
            return GateResult(Decision.EXPIRED, replies.INVITE_EXPIRED)

        code = extract_code(msg.text)
        if code is None:
            return GateResult(Decision.DENY, replies.CODE_NEEDED)

        if not hmac.compare_digest(hash_code(code), invite["invite_code_hash"]):
            cur = await conn.execute(
                """update public.access_list set failed_attempts = failed_attempts + 1
                   where phone_e164 = %s returning failed_attempts""",
                (phone,),
            )
            row = await cur.fetchone()
            now_locked = row is not None and row[0] >= settings["invite_max_failed_attempts"]
            reply = replies.INVITE_EXPIRED if now_locked else replies.CODE_WRONG
            return GateResult(Decision.CODE_MISMATCH, reply)

        # Serialise activations so two at once can't overshoot max_active_users.
        await conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (ACTIVATION_LOCK_KEY,))
        cur = await conn.execute("select count(*) from public.access_list where status = 'active'")
        row = await cur.fetchone()
        if row and row[0] >= settings["max_active_users"]:
            log.warning(
                "activation blocked: max_active_users=%s reached", settings["max_active_users"]
            )
            return GateResult(Decision.CAPACITY_FULL, replies.CAPACITY_FULL)

        user_id: UUID | None = invite["user_id"]  # set when re-inviting a revoked member
        if user_id is None:
            cur = await conn.execute(
                """insert into public.users (household_id, display_name)
                   values (%s, %s) returning id""",
                (invite["household_id"], invite["display_name"]),
            )
            created = await cur.fetchone()
            assert created is not None
            user_id = created[0]
        await conn.execute(
            """insert into public.channel_identities (user_id, channel, external_id, verified_at)
               values (%s, 'whatsapp', %s, now())
               on conflict (channel, external_id)
               do update set user_id = excluded.user_id, verified_at = now()""",
            (user_id, phone),
        )
        await conn.execute(
            """update public.access_list
               set status = 'active', user_id = %s, activated_at = now(), revoked_at = null,
                   invite_code_hash = null, invite_expires_at = null, failed_attempts = 0
               where phone_e164 = %s""",
            (user_id, phone),
        )
        return GateResult(Decision.ACTIVATED, replies.activated(invite["display_name"]), user_id)

    async def _non_member(
        self, conn: AsyncConnection[Any], msg: Inbound, settings: Row
    ) -> GateResult:
        command = (msg.text or "").strip().upper()

        # Honour removal requests even in silent mode.
        if command == "STOP":
            cur = await conn.execute(
                "delete from public.waitlist where phone_e164 = %s", (msg.from_phone,)
            )
            if cur.rowcount:
                return GateResult(Decision.WAITLIST_REMOVED, replies.WAITLIST_REMOVED)

        decision = Decision.DENY
        code = extract_code(msg.text)
        if code is not None:
            decision = Decision.CODE_MISMATCH
            await self._record_foreign_code(conn, code, msg.from_phone)

        if settings["gate_mode"] == "open":
            log.warning("gate_mode=open has no self-signup yet; treating non-member as invite_only")

        if settings["non_member_reply"] == "silent":
            return GateResult(decision)

        if command == "WAITLIST":
            await conn.execute(
                """insert into public.waitlist (phone_e164, consent_at) values (%s, now())
                   on conflict (phone_e164)
                   do update set attempts = public.waitlist.attempts + 1""",
                (msg.from_phone,),
            )
            return GateResult(Decision.WAITLIST, replies.WAITLIST_JOINED)

        cur = await conn.execute(
            """select exists (
                  select 1 from public.gate_events
                  where phone_hash = %s and replied
                    and at > now() - make_interval(days => %s))""",
            (hash_phone(msg.from_phone, self._key), REPLY_ONCE_DAYS),
        )
        row = await cur.fetchone()
        already_replied = bool(row and row[0])
        return GateResult(decision, None if already_replied else replies.NON_MEMBER)

    async def _record_foreign_code(
        self, conn: AsyncConnection[Any], code: str, sender: str
    ) -> None:
        """A valid code from the wrong number counts against the invite but never consumes it."""
        cur = await conn.execute(
            """update public.access_list set failed_attempts = failed_attempts + 1
               where invite_code_hash = %s and status = 'invited' and phone_e164 <> %s
               returning failed_attempts""",
            (hash_code(code), sender),
        )
        row = await cur.fetchone()
        if row and row[0] >= ALERT_AFTER_FOREIGN_ATTEMPTS:
            log.warning("invite code used from %s other numbers; possible forwarding", row[0])
