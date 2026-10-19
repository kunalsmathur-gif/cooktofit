# Brain (FastAPI)

The CookToFit backend: the conversation core, domain services, WhatsApp webhook and background jobs. So far it has health checks, the **invite-only access gate** (ARCHITECTURE §9.1) and a local WhatsApp simulator.

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```
Database tests run against local Supabase (`make db-start`) and are skipped if it isn't running, unless `REQUIRE_DB=1`.

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness check. Never touches dependencies. |
| `GET /readyz` | Readiness check. Runs `select 1` against Postgres; 503 if unreachable. |
| `POST /dev/simulate` | `{"from_phone": "+91…", "text": "…"}` → gate decision and replies. Local/test only (404 elsewhere). |

## Invites and the simulator
```bash
uv run python -m app.cli invite +919876543210 "Kunal" --role admin --household "Home"
uv run python -m app.cli list
uv run python -m app.cli revoke +919876543210
uv run python -m app.cli chat +919876543210     # type "JOIN CTF-…" to activate
```
Message flow: **gate → pause switch → daily cap → conversation core** (a stub for now). Non-members cost nothing: no media download, no LLM call, only a keyed hash of their number is logged.

| Setting (`app_settings`) | Default | Effect |
|---|---|---|
| `non_member_reply` | `silent` | `static_once_30d` sends one fixed reply per number per 30 days and enables `WAITLIST`/`STOP` |
| `max_active_users` | 10 | Activation refused beyond this |
| `invite_max_failed_attempts` | 5 | Wrong codes from the invited number lock the invite |
| `daily_message_cap` | 200 | Per member per local day; one notice, then silence |
| `paused` | false | Manual kill switch; members get a "paused" reply |

## Nutrition targets engine

`app/targets/` turns a profile into daily kcal, macro and micronutrient targets. It is pure and
deterministic (no DB, no LLM), and every number carries a plain-English "why".

- Energy: Mifflin-St Jeor (Katch-McArdle with body fat; a known TDEE wins) × activity, then goal pace
  (capped at 1%/wk loss, 0.5%/wk gain) and a calorie floor.
- Protein by goal and training; fat 25% of kcal; carbs fill the rest; fibre 20 g per 1,000 kcal.
- Micronutrients: ICMR-NIN 2020 RDA (`app/targets/data/icmr_nin_2020.json`, source and caveats inside).
  Omega-3 has no ICMR g/day value, so it is not targeted.
- Safety: under-18, underweight, pregnancy/lactation, eating-disorder screen, kidney disease and
  insulin-treated diabetes force maintenance and a "see a professional" flag.
- User overrides win (`apply_overrides`), except kcal below the floor unless clinician-set.
- `FORMULA_VERSION` is stamped on every result so stored targets stay explainable.

```bash
uv run python -m app.cli targets --sex male --age 30 --height 175 --weight 75 --activity moderate
```
