from typing import Any

import pytest
from psycopg import AsyncConnection

from app.gate import invites, replies
from app.gate.service import Decision, Gate, Inbound
from app.inbound import handle

Conn = AsyncConnection[Any]
KEY = "test-key"
KUNAL = "+919800000001"
WIFE = "+919800000002"
STRANGER = "+919800000099"


@pytest.fixture
def gate() -> Gate:
    return Gate(KEY)


async def settings(conn: Conn, **values: object) -> None:
    sets = ", ".join(f"{k} = %({k})s" for k in values)
    await conn.execute(f"update public.app_settings set {sets} where id = 1", values)  # noqa: S608


async def activate(conn: Conn, gate: Gate, phone: str, name: str) -> None:
    inv = await invites.create_invite(conn, phone, name, household="Home")
    res = await gate.evaluate(conn, Inbound(phone, f"JOIN {inv.code}"))
    assert res.decision is Decision.ACTIVATED


async def count(conn: Conn, sql: str, *args: object) -> int:
    cur = await conn.execute(sql, args)
    row = await cur.fetchone()
    assert row is not None
    return int(row[0])


async def test_invited_number_activates_with_its_code(conn: Conn, gate: Gate) -> None:
    inv = await invites.create_invite(conn, KUNAL, "Kunal", role="admin", household="Home")
    res = await gate.evaluate(conn, Inbound(KUNAL, f"JOIN {inv.code}"))
    assert res.decision is Decision.ACTIVATED
    assert res.reply == replies.activated("Kunal")
    assert (
        await count(
            conn, "select count(*) from public.channel_identities where external_id = %s", KUNAL
        )
        == 1
    )
    assert await count(conn, "select count(*) from public.access_list where status = 'active'") == 1
    # The code is single-use: it's wiped on activation.
    assert (
        await count(
            conn, "select count(*) from public.access_list where invite_code_hash is not null"
        )
        == 0
    )


async def test_member_messages_reach_core(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    out = await handle(conn, gate, Inbound(KUNAL, "hi"))
    assert out.decision is Decision.ALLOW
    assert out.replies  # the core answered


async def test_forwarded_code_from_another_number_does_nothing(conn: Conn, gate: Gate) -> None:
    await settings(conn, non_member_reply="static_once_30d")
    inv = await invites.create_invite(conn, WIFE, "Wife")
    res = await gate.evaluate(conn, Inbound(STRANGER, f"JOIN {inv.code}"))
    assert res.decision is Decision.CODE_MISMATCH
    assert res.user_id is None
    # Invite not consumed; the attempt is counted against it.
    row = await (
        await conn.execute(
            "select status, failed_attempts from public.access_list where phone_e164 = %s", (WIFE,)
        )
    ).fetchone()
    assert row == ("invited", 1)
    # The real invitee can still activate.
    assert (await gate.evaluate(conn, Inbound(WIFE, inv.code))).decision is Decision.ACTIVATED


async def test_invited_number_needs_code_and_locks_after_wrong_codes(
    conn: Conn, gate: Gate
) -> None:
    await settings(conn, invite_max_failed_attempts=2)
    inv = await invites.create_invite(conn, WIFE, "Wife")
    assert (await gate.evaluate(conn, Inbound(WIFE, "hello"))).reply == replies.CODE_NEEDED
    first = await gate.evaluate(conn, Inbound(WIFE, "CTF-AAAAAAAAAA"))
    assert (first.decision, first.reply) == (Decision.CODE_MISMATCH, replies.CODE_WRONG)
    second = await gate.evaluate(conn, Inbound(WIFE, "CTF-BBBBBBBBBB"))
    assert second.reply == replies.INVITE_EXPIRED
    # Even the right code is refused once locked.
    assert (await gate.evaluate(conn, Inbound(WIFE, inv.code))).decision is Decision.EXPIRED


async def test_expired_invite_is_refused(conn: Conn, gate: Gate) -> None:
    inv = await invites.create_invite(conn, WIFE, "Wife")
    await conn.execute(
        "update public.access_list set invite_expires_at = now() - interval '1 minute'"
    )
    assert (await gate.evaluate(conn, Inbound(WIFE, inv.code))).decision is Decision.EXPIRED


async def test_capacity_limit(conn: Conn, gate: Gate) -> None:
    await settings(conn, max_active_users=1)
    await activate(conn, gate, KUNAL, "Kunal")
    inv = await invites.create_invite(conn, WIFE, "Wife")
    res = await gate.evaluate(conn, Inbound(WIFE, inv.code))
    assert (res.decision, res.reply) == (Decision.CAPACITY_FULL, replies.CAPACITY_FULL)


async def test_non_member_silent_by_default(conn: Conn, gate: Gate) -> None:
    out = await handle(conn, gate, Inbound(STRANGER, "hi, my friend sent me this"))
    assert (out.decision, out.replies) == (Decision.DENY, [])
    assert await count(conn, "select count(*) from public.gate_events where decision = 'deny'") == 1
    # Silent mode doesn't collect numbers either.
    await handle(conn, gate, Inbound(STRANGER, "WAITLIST"))
    assert await count(conn, "select count(*) from public.waitlist") == 0


async def test_non_member_static_reply_once_then_waitlist(conn: Conn, gate: Gate) -> None:
    await settings(conn, non_member_reply="static_once_30d")
    assert (await gate.evaluate(conn, Inbound(STRANGER, "hi"))).reply == replies.NON_MEMBER
    assert (await gate.evaluate(conn, Inbound(STRANGER, "hello?"))).reply is None
    res = await gate.evaluate(conn, Inbound(STRANGER, " waitlist "))
    assert (res.decision, res.reply) == (Decision.WAITLIST, replies.WAITLIST_JOINED)
    assert (
        await count(conn, "select count(*) from public.waitlist where phone_e164 = %s", STRANGER)
        == 1
    )
    res = await gate.evaluate(conn, Inbound(STRANGER, "STOP"))
    assert res.decision is Decision.WAITLIST_REMOVED
    assert await count(conn, "select count(*) from public.waitlist") == 0


async def test_gate_log_never_stores_raw_phone(conn: Conn, gate: Gate) -> None:
    await gate.evaluate(conn, Inbound(STRANGER, "hi"))
    assert (
        await count(
            conn, "select count(*) from public.gate_events where phone_hash like %s", "%9800000099%"
        )
        == 0
    )


async def test_revoked_member_is_cut_off_immediately(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    assert await invites.revoke(conn, KUNAL)
    assert (await gate.evaluate(conn, Inbound(KUNAL, "hi"))).decision is Decision.DENY


async def test_reinvited_member_keeps_their_user(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    before = await count(conn, "select count(*) from public.users")
    await invites.revoke(conn, KUNAL)
    await activate(conn, gate, KUNAL, "Kunal")
    assert await count(conn, "select count(*) from public.users") == before


async def test_cannot_reinvite_active_member(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    with pytest.raises(invites.InviteError):
        await invites.create_invite(conn, KUNAL, "Kunal")


async def test_daily_cap_replies_once(conn: Conn, gate: Gate) -> None:
    await settings(conn, daily_message_cap=2)
    await activate(conn, gate, KUNAL, "Kunal")
    decisions = [await gate.evaluate(conn, Inbound(KUNAL, "hi")) for _ in range(4)]
    assert [d.decision for d in decisions] == [
        Decision.ALLOW,
        Decision.ALLOW,
        Decision.CAPPED,
        Decision.CAPPED,
    ]
    assert [d.reply for d in decisions[2:]] == [replies.CAPPED, None]


async def test_pause_switch(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    await settings(conn, paused=True)
    out = await handle(conn, gate, Inbound(KUNAL, "hi"))
    assert (out.decision, out.replies) == (Decision.PAUSED, [replies.PAUSED])


async def test_group_messages_ignored(conn: Conn, gate: Gate) -> None:
    await activate(conn, gate, KUNAL, "Kunal")
    out = await handle(conn, gate, Inbound(KUNAL, "hi", is_group=True))
    assert (out.decision, out.replies) == (Decision.IGNORED, [])


def test_invite_link_only_with_number() -> None:
    assert invites.invite_link(None, "CTF-X") is None
    assert (
        invites.invite_link("+919999999999", "CTF-X")
        == "https://wa.me/919999999999?text=JOIN%20CTF-X"
    )
