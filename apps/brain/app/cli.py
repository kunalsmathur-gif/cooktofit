"""Admin CLI and terminal chat simulator.

uv run python -m app.cli invite +919876543210 "Kunal" --role admin --household "Home"
uv run python -m app.cli list
uv run python -m app.cli revoke +919876543210
uv run python -m app.cli chat +919876543210
"""

import argparse
import asyncio
import sys
from typing import Any

import psycopg

from app.config import get_settings
from app.gate import invites
from app.gate.identity import normalize_phone
from app.gate.service import Gate, Inbound
from app.inbound import handle
from app.targets.engine import compute
from app.targets.models import Activity, Goal, Persona, Physiology, Profile, Sex


async def _connect() -> psycopg.AsyncConnection[Any]:
    s = get_settings()
    return await psycopg.AsyncConnection.connect(
        s.database_url, autocommit=True, connect_timeout=s.db_connect_timeout_s
    )


async def cmd_invite(a: argparse.Namespace) -> int:
    s = get_settings()
    async with await _connect() as conn:
        try:
            inv = await invites.create_invite(
                conn,
                a.phone,
                a.name,
                role=a.role,
                household=a.household,
                email=a.email,
                ttl_days=s.invite_ttl_days,
            )
        except invites.InviteError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"Invited {inv.phone_e164} (expires {inv.expires_at:%Y-%m-%d %H:%M %Z})")
    print(f"Code: {inv.code}")
    link = invites.invite_link(s.whatsapp_number, inv.code)
    print(f"Link: {link}" if link else "Link: set WHATSAPP_NUMBER to generate a wa.me link")
    print("Send this privately to the invitee only. It works only from their number.")
    return 0


async def cmd_revoke(a: argparse.Namespace) -> int:
    async with await _connect() as conn:
        changed = await invites.revoke(conn, a.phone)
    print("revoked" if changed else "no change (unknown or already revoked)")
    return 0


async def cmd_list(_: argparse.Namespace) -> int:
    async with await _connect() as conn:
        rows = await invites.list_access(conn)
    for r in rows:
        print(
            f"{r['phone_e164']:<16} {r['display_name']:<16} {r['role']:<7} {r['status']:<8} "
            f"fails={r['failed_attempts']}"
        )
    if not rows:
        print("(empty)")
    return 0


async def cmd_chat(a: argparse.Namespace) -> int:
    phone = normalize_phone(a.phone)
    gate = Gate(get_settings().phone_hash_key.get_secret_value())
    print(f"Simulating WhatsApp from {phone}. Ctrl-D to quit.")
    async with await _connect() as conn:
        while True:
            try:
                text = await asyncio.to_thread(input, "you> ")
            except EOFError:
                print()
                return 0
            outcome = await handle(conn, gate, Inbound(phone, text, a.group))
            for reply in outcome.replies or ["(no reply)"]:
                print(f"bot> {reply}")
            print(f"     [{outcome.decision}]")


async def cmd_targets(a: argparse.Namespace) -> int:
    ts = compute(
        Profile(
            sex=Sex(a.sex),
            age=a.age,
            height_cm=a.height,
            weight_kg=a.weight,
            activity=Activity(a.activity),
            goal=Goal(a.goal),
            persona=Persona(a.persona),
            pace_kg_per_week=a.pace,
            body_fat_pct=a.body_fat,
            known_tdee_kcal=a.tdee,
            training_days_per_week=a.training_days,
            physiology=Physiology(a.physiology),
        )
    )
    print(f"Formula {ts.formula_version} · {ts.reference} · goal: {ts.effective_goal}")
    for key, t in ts.targets.items():
        mark = "*" if key in ts.visible else " "
        cmp = {"min": "≥", "max": "≤"}.get(t.kind, " ")
        print(f"{mark} {key:<15} {cmp}{t.value:>7g} {t.unit:<4}  {t.why}")
    if ts.training_day and ts.rest_day:
        print(
            f"  training day: {ts.training_day.kcal:g} kcal, {ts.training_day.carbs_g:g} g carbs"
            f" · rest day: {ts.rest_day.kcal:g} kcal, {ts.rest_day.carbs_g:g} g carbs"
        )
    for f in ts.flags:
        print(f"[{f.severity}] {f.message}")
    print("* = shown to this persona")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cooktofit")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("invite", help="invite (or re-invite) a phone number")
    i.add_argument("phone")
    i.add_argument("name")
    i.add_argument("--role", choices=["admin", "member"], default="member")
    i.add_argument("--household")
    i.add_argument("--email")
    i.set_defaults(fn=cmd_invite)

    r = sub.add_parser("revoke", help="revoke access immediately")
    r.add_argument("phone")
    r.set_defaults(fn=cmd_revoke)

    sub.add_parser("list", help="show the allow-list").set_defaults(fn=cmd_list)

    c = sub.add_parser("chat", help="chat as a phone number through the real gate")
    c.add_argument("phone")
    c.add_argument("--group", action="store_true", help="pretend it's a group message")
    c.set_defaults(fn=cmd_chat)

    t = sub.add_parser("targets", help="compute nutrition targets (no DB needed)")
    t.add_argument("--sex", choices=[x.value for x in Sex], required=True)
    t.add_argument("--age", type=int, required=True)
    t.add_argument("--height", type=float, required=True, help="cm")
    t.add_argument("--weight", type=float, required=True, help="kg")
    t.add_argument("--activity", choices=[x.value for x in Activity], default="light")
    t.add_argument("--goal", choices=[x.value for x in Goal], default="maintain")
    t.add_argument("--persona", choices=[x.value for x in Persona], default="intermediate")
    t.add_argument("--pace", type=float, help="kg per week")
    t.add_argument("--body-fat", type=float)
    t.add_argument("--tdee", type=int, help="your tracked maintenance kcal")
    t.add_argument("--training-days", type=int, default=0)
    t.add_argument("--physiology", choices=[x.value for x in Physiology], default="none")
    t.set_defaults(fn=cmd_targets)

    a = p.parse_args(argv)
    result: int = asyncio.run(a.fn(a))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
