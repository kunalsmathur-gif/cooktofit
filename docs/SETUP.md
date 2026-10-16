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

## Invite yourself and try the gate locally
```bash
make invite PHONE=+91XXXXXXXXXX NAME=Kunal ROLE=admin HOUSEHOLD=Home   # prints a CTF-… code
make chat PHONE=+91XXXXXXXXXX                                          # type: JOIN CTF-…
```

## External accounts (needed from Phase 1)
Set these up in this order: Meta takes longest because of business verification and template approval. Keep every key in a password manager and in the deploy platform's secret store, **never in this repo** (it's public). Consoles change often; if a label differs, look for the nearest equivalent.

### 1. Meta: WhatsApp Business Platform (Cloud API)
1. **Dedicated number.** Get a new SIM or virtual number that can receive an SMS or voice call. It must **not** be registered on the WhatsApp or WhatsApp Business app (or delete that account first).
2. **Meta Business portfolio.** At business.facebook.com, create a business portfolio with your legal name and a business email.
3. **Developer app.** At developers.facebook.com → My Apps → Create app → type **Business** → add the **WhatsApp** product. This creates a WhatsApp Business Account (WABA) and a free test number.
4. **Add the real number.** WhatsApp → API Setup → *Add phone number*. Set the display name **CookToFit**, category *Health & wellness* (or the nearest option), and verify by OTP. The display name is reviewed by Meta.
5. **Business verification** (Security Centre in Business settings). Upload business or identity documents. You can send a limited number of conversations before verification, which is enough for testing with two people.
6. **Permanent token.** Business settings → Users → *System users* → add an admin system user → assign the app and the WABA → *Generate token* with `whatsapp_business_messaging` and `whatsapp_business_management`. The temporary token in API Setup expires after 24 hours; don't use it for anything lasting.
7. **Values to record:** Phone number ID, WABA ID, App ID, App secret (for webhook signature checks), the system-user token, and a webhook verify token you choose (`openssl rand -hex 16`).
8. **Payment method.** WhatsApp Manager → Billing: add a card. Needed for template messages outside the free window.
9. **Profile hygiene (invite-only):** no website "message us" link, don't publish the number, keep the description short.
10. **Webhook:** done in the Phase 1 WhatsApp slice once the Brain is deployed (callback `https://<brain>/webhooks/whatsapp`, subscribe to `messages`).

⚠️ Check the current India rate card for utility and authentication templates before enabling reminders or OTP login.

### 2. Google Cloud
1. Create a project (e.g. `cooktofit`) at console.cloud.google.com and **link a billing account**. Set a budget alert at ₹500/month (Billing → Budgets & alerts).
2. **Gemini API key.** At aistudio.google.com → *Get API key* → choose the `cooktofit` project. Using a paid-tier project means prompts aren't used for training; check the current terms.
3. **YouTube Data API v3.** APIs & Services → Library → enable it → Credentials → *Create API key*. Restrict the key to the YouTube Data API.
4. **Google sign-in (OAuth).** APIs & Services → *OAuth consent screen*: type **External**, app name CookToFit, publishing status **Testing**, and add your two Google emails as test users. Then Credentials → *Create OAuth client ID* → Web application. Add the Supabase callback (`https://<project-ref>.supabase.co/auth/v1/callback`) as an authorised redirect URI after step 3 below. Record the client ID and secret.
5. **Cloud Run.** Enable the Cloud Run, Artifact Registry and Secret Manager APIs, and choose region `asia-south1` (Mumbai). Deployment itself comes in a later slice.

### 3. Supabase (hosted)
1. Create an organisation and a project at supabase.com on the Free plan. Region **South Asia (Mumbai)**. Generate a strong database password and store it.
2. **Values to record:** Project ref, project URL, publishable (anon) key, secret (service role) key, and the database connection string (Connect → *Session pooler* URI for the Brain).
3. **Google provider.** Authentication → Sign In / Providers → Google: paste the client ID and secret from step 2.4 and copy the callback URL back into the Google OAuth client.
4. **Apply the schema:** `npx supabase login && npx supabase link --project-ref <ref> && npx supabase db push`, then run `supabase/seed.sql` once in the SQL editor.
5. The free plan pauses a project after a week without activity; daily use avoids that.

### 4. Cloudflare R2 (meal photos, later in Phase 1)
Create a Cloudflare account → R2 → create bucket `cooktofit-photos` (private) → *Manage R2 API tokens* → token with Object Read & Write on that bucket only. Record the account ID, access key ID and secret.

### 5. Swiggy MCP (Instamart)
Email Swiggy's MCP/builders team asking them to whitelist our OAuth callback for a personal, invite-only pilot. Until then, the plan B in ARCHITECTURE (a one-time localhost OAuth) applies.

### Where each value goes
| Value | Brain env var (Phase 1) |
|---|---|
| Phone number ID / WABA ID / token / app secret / verify token | `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID`, `WHATSAPP_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` |
| Business number (digits) | `WHATSAPP_NUMBER` |
| Gemini / YouTube keys | `GEMINI_API_KEY`, `YOUTUBE_API_KEY` |
| Supabase DB URI | `DATABASE_URL` |
| Random 32-byte hex | `PHONE_HASH_KEY` |

Google OAuth client values go into Supabase, not the Brain.
