# Agent instructions — CookToFit

CookToFit is a standalone project (repo `kunalsmathur-gif/cooktofit`). It is unrelated to WanderPlanner;
run agent sessions from this directory and keep all code, docs, data caches and progress notes here.

## Layout
- `apps/brain` — FastAPI service (Python 3.12, uv). Gate, conversation core, targets engine, food DB.
- `apps/web` — Next.js dashboard/PWA (read `node_modules/next/dist/docs` before using Next APIs).
- `supabase/` — migrations and pgTAP tests. `docs/` — PRD, ARCHITECTURE, DEEP_DIVE, PLAN (with progress log), ADRs.
- Domain language: `CONTEXT.md`. Decisions: `docs/adr/`.
- Downloaded third-party datasets go in `.cache/` (gitignored). Never commit them; see NOTICE for licences.

## Workflow
- Thin vertical slices: implement → `make check` (ruff, mypy, pytest, web lint/typecheck, pgTAP) → commit → push → CI green.
- After each slice, append a line to the Progress section of `docs/PLAN.md`.
- Commit trailer: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## Machine notes (Kunal's laptop)
- `GH_TOKEN` in the env has no write access: prefix `gh` writes and `git push` with `env -u GH_TOKEN -u GITHUB_TOKEN`.
- Corporate TLS interception: Python/uv need `SSL_CERT_FILE=~/.certs/corp-ca-bundle.pem UV_SYSTEM_CERTS=1`;
  npm/npx need `NODE_EXTRA_CA_CERTS=~/.certs/corp-ca-bundle.pem`.
- Docker via Colima. Local Supabase: `npx -y supabase@2.121.0 start -x studio,edge-runtime,imgproxy,vector,logflare,supavisor,mailpit,realtime`
  (DB at 127.0.0.1:54322, postgres/postgres).
