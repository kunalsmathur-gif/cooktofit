# Local setup

## Prerequisites
| Tool | Version | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | latest | Installs Python 3.12 for `apps/brain` |
| Node.js | 22+ | `apps/web` and the Supabase CLI (via `npx`) |
| Docker | any | Docker Desktop, or [Colima](https://github.com/abiosoft/colima) (`colima start`) |
| make | any | Optional; every target is a plain shell command |

## Quick start
```bash
make install     # uv sync + npm ci
make db-start    # local Supabase: Postgres on :54322, API on :54321
make db-reset    # apply migrations + seed
make brain       # http://localhost:8000/readyz → {"status":"ok","database":"up"}
make web         # http://localhost:3000
make check       # lint, typecheck, unit tests, pgTAP — same as CI
```
Copy `apps/brain/.env.example` to `apps/brain/.env` only if you need to override defaults; the defaults point at local Supabase.

## Behind a TLS-intercepting proxy
If HTTPS fails with `CERTIFICATE_VERIFY_FAILED` / `SELF_SIGNED_CERT_IN_CHAIN`, point tools at a CA bundle that includes your proxy's root:
```bash
export NODE_EXTRA_CA_CERTS=/path/to/ca-bundle.pem               # node, npm, npx
export SSL_CERT_FILE=/path/to/ca-bundle.pem UV_SYSTEM_CERTS=1    # uv, Python
```

## External accounts (needed from Phase 1, not for Phase 0)
| Account | Used for |
|---|---|
| Supabase project (Mumbai region) | Hosted Postgres, Auth, Storage |
| Meta Business + WhatsApp Business Account + dedicated number | WhatsApp Cloud API, templates, Flows, OTP auth template |
| Google Cloud project | Cloud Run (brain), Gemini API key, Google OAuth client for web sign-in, YouTube Data API |
| Cloudflare R2 | Meal-photo storage |
| Swiggy MCP access | Instamart cart (callback whitelisting; see ARCHITECTURE) |

Secrets go in the deploy platform's secret store, never in this repo.
