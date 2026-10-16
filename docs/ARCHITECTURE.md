# High-Level System Architecture: CookToFit, v0.2 (WhatsApp-first)

> Supersedes v0.1, an earlier Expo-first draft. Background: `DEEP_DIVE.md`. Decisions: `adr/`.
> MVP users: 2 (Kunal, Advanced persona; wife, Intermediate persona). Budget ≤ ₹1,000/month.

## 1. Overview
```
 Channels                         Brain (FastAPI on Cloud Run, asia-south1)
┌───────────────────────┐        ┌─────────────────────────────────────────────────────────┐
│ WhatsApp Cloud API    │webhook │  Channel adapters  (whatsapp.py · web.py · [expo later])│
│  text/photo/voice,    ├───────►│        │  normalised Message{user, text, media, ctx}    │
│  buttons/lists/Flows, │◄───────┤        ▼                                                 │
│  utility templates    │ send   │  ┌──────────────┐  typed tools   ┌───────────────────┐  │
└───────────────────────┘        │  │ COACH AGENT  ├───────────────►│ Domain services    │  │
┌───────────────────────┐ HTTPS  │  │ (front door) │                │ (deterministic)    │  │
│ Web dashboard         ├───────►│  └──────┬───────┘                │  TargetEngine      │  │
│ Next.js on Vercel     │  JWT   │         │ handoff(intent)        │  NutritionCalc     │  │
│ charts, goals, pantry │        │         ▼                        │  FoodResolver      │  │
└───────────────────────┘        │  ┌──────────────┐                │  Recommender       │  │
                                 │  │COMMERCE AGENT│ MCP (OAuth)    │  Planner           │  │
                                 │  │ (sandboxed)  ├──────► Swiggy  │  SafetyRules       │  │
                                 │  └──────────────┘   Instamart/   └───────────────────┘  │
                                 │                     Food, Zomato*                       │
                                 │  AI skills (single-shot, JSON schema):                  │
                                 │   PlateVision · LabelReader · FoodParser(+voice)        │
                                 │   RecipeAdapter · WeeklyReviewer                        │
                                 │  Background jobs (Cloud Scheduler → endpoints):         │
                                 │   VideoCurator · CatalogIngest · Rollups · Nudges ·     │
                                 │   OrderSync→Pantry · Backups                            │
                                 └──────────┬──────────────────────────┬───────────────────┘
                                            ▼                          ▼
                         Supabase (ap-south-1): Postgres+pgvector,   Gemini API · YouTube Data API
                         Auth, Storage(thumbs) · Cloudflare R2(photos) Open Food Facts API
```
\* Zomato MCP is Phase 2, ⚠️ verify that it's official first.

**Design rules**
1. **Deterministic numbers.** AI identifies foods and estimates grams; all nutrition maths comes from the database.
2. **History is immutable.** Goals are versioned, each day's targets are snapshotted, and every logged item keeps the nutrition values it used.
3. **One brain, many channels.** Channel adapters are thin; all logic lives in the core.
4. **Least privilege for AI.** Each agent sees only the tools and credentials it needs.

## 2. Agent architecture (ADR-006)

### 2.1 Decision
| Layer | What | Count | AI? |
|---|---|---|---|
| **Coach agent** | Front door for every message. Understands what you want, keeps context and memory, calls tools, writes the reply | 1 | Yes (Gemini Flash, tool calling) |
| **Commerce agent** | Builds carts and orders through MCP. Only reachable by handoff from the coach | 1 (MVP: Instamart only) | Yes (sandboxed) |
| **AI skills** | Single-shot calls with a fixed prompt and JSON schema. They don't loop or call tools | 5 | Yes |
| **Domain services** | Targets, nutrition, food matching, recommendations, planning, safety | ~6 | **No** |
| **Background jobs** | Video curation, catalogue loading, rollups, nudges, order sync, backups | ~6 | Some |

The coach **orchestrates; it doesn't compute.** It never does maths, searches YouTube or loads data itself. Goal-setting conversation happens in the coach, but the targets come from `TargetEngine` and `SafetyRules`.

### 2.2 Coach tool surface (read/plan only, no money)
`get_profile`, `set_goal_draft` → `confirm_goal`, `get_remaining`, `log_meal_draft` → `confirm_log`, `analyse_photo` (PlateVision), `scan_label` (LabelReader), `parse_food_text` (FoodParser), `search_food`, `recommend`, `get_recipe`, `get_videos` (reads the cache), `plan_day`, `update_pantry`, `remember_fact`, `render_summary_card`, **`handoff_commerce(intent)`**.

Every write-type tool is a **draft → user confirm** pair. Confirmations arrive as WhatsApp button payloads carrying a signed, single-use token.

### 2.3 Why commerce gets its own agent (expanded scope)
Once you can order ingredients (MVP) and restaurant food (Phase 2), the risks change:

| Concern | Why it needs isolation |
|---|---|
| **Money and irreversibility** | Orders spend money and can't be undone. That's a different risk class from logging a meal |
| **Credentials** | Swiggy and Zomato OAuth tokens live only in the commerce agent's secret scope. The coach never sees them |
| **Prompt injection** | Product titles, menus and descriptions are **untrusted third-party text**. Kept in a sandbox, a malicious menu string can't make the coach change your goals or leak your data |
| **Long tool loops** | Search, variants, pack size, cart and bill take 5–15 MCP calls. Isolating them keeps the coach fast and its context small; commerce can run async ("building your cart…") |
| **Different evaluation** | Commerce is judged on cart correctness and price; coaching is judged on accuracy and tone |

### 2.4 Commerce agent contract
```
handoff_commerce(intent) where intent is one of:
  GroceryCart   {household_id, items:[{food_id|product_id, qty_g|units, brand_pref?}],
                 budget_inr?, substitutions: allow|ask|deny, deliver_to: address_id}
  FoodOrder     {user_id, slot, remaining_macros, diet_rules, max_price_inr,
                 max_eta_min, cuisines?}                               ← Phase 2
returns  CartProposal {lines:[{platform_sku, title, brand, pack, qty, price,
                 matched_product_id, match_confidence}], unmatched[], bill, eta,
                 proposal_id, expires_at}
         FoodOptions  {options:[{restaurant, dish, price, eta, est_macros,
                 fit_score, est_confidence}], proposal_id}             ← Phase 2
```
**Commerce agent tools:** Swiggy Instamart MCP (search, cart get/update, bill, place order). Phase 2 adds Swiggy Food MCP and Zomato MCP, plus `ProductMatcher`, `NutritionCalc.estimate_dish` and `get_brand_prefs`, all read-only.

**Guardrails (all deterministic code, outside the LLM):**
1. **Human in the loop:** `place_order` is never exposed to the LLM. It runs only when *you* tap "✅ Place order (COD ₹642)", which carries a signed token bound to `proposal_id` and the bill hash. If the cart changes, the token is invalid.
2. **Caps:** a per-order maximum (default ₹2,000), a daily maximum and a maximum item count. Anything over the limit needs a second confirmation.
3. **Allow-list:** only Swiggy (and Zomato in Phase 2). No arbitrary URLs. COD only for now.
4. **Idempotency and audit:** `orders(proposal_id UNIQUE, status, bill_json, placed_by, confirmed_at)`. Every MCP call is logged.
5. **Untrusted-text handling:** MCP results are wrapped as data, never treated as instructions. The coach only receives the structured `CartProposal`.
6. **Dry-run mode:** carts are built but never placed. This is the default until the flow has been tested.

**After an order:**
- `OrderSync` imports delivered items into the pantry as brand-specific products.
- **Phase 2:** a delivered food order becomes a pre-filled meal log draft ("Your Paneer Tikka Bowl arrived. Log it? ~540 kcal, 38 g P").

**Food ordering (Phase 2):**
- Menu items rarely include nutrition. `NutritionCalc.estimate_dish` maps the dish name to the database (INDB recipes), adds a restaurant oil factor of about 1.3× fat, and returns a confidence band.
- Options are ranked by fit to your remaining macros, then by price and delivery time. The bot always shows "≈" figures and a confidence level.

### 2.5 When we'd split further
Add another agent only if a capability (a) needs its own credentials or risk boundary, or (b) has long multi-step loops. Likely future candidates are a **Cook-mode agent** (multilingual WhatsApp to a household cook) and a **Lab-report agent** (PDF to biomarkers, with medical-safety review). The cost of each extra agent is about 1–3 s of latency and extra tokens per hop.

## 3. Components

### 3.1 Channel adapters
- **WhatsApp** (`channels/whatsapp.py`):
  - Webhook verification. `X-Hub-Signature-256` HMAC check; dedupe on `message.id`. Media is downloaded through the Graph API.
  - **Voice:** OGG/Opus is sent straight to Gemini (audio input; Hindi and English).
  - **Outbound:** text, image (summary cards), reply buttons (≤ 3), list messages (≤ 10 rows) and **Flows** (onboarding, pantry/kitchen setup, portion editor).
  - **Templates (utility):** meal reminder, evening remaining budget, weekly review, cart ready.
  - **24-hour window:** free-form replies inside the customer-service window; templates outside it.
- **Web** (`apps/web`, Next.js):
  - **Mobile-first responsive design.** Every page works at 360 px wide and up; desktop gets a wider multi-column layout. It's an installable **PWA** (manifest and icons from the brand kit) so it can sit on the home screen. Touch targets are at least 44 px; charts reflow, and tables become cards on mobile.
  - **Sign-in methods (all gated by `access_list`):**
    1. **Mobile OTP:** the user enters their phone number, and a 6-digit OTP arrives as a **WhatsApp authentication template** (copy-code button).
       - It uses the Supabase Auth *Send SMS hook* pointed at our Brain.
       - Indian SMS would need DLT sender and template registration; WhatsApp avoids that and the user already has the chat.
       - Rate limits: 5 sends per hour per number and per IP; the OTP expires after 5 minutes. Cost is about one auth-template charge per login (⚠️ check the rate card).
       - SMS (MSG91 or Twilio, DLT-registered) is a fallback only at launch.
    2. **Google sign-in:** Supabase Google OAuth. The email must match an `access_list` entry, or be linked to an existing member after their first OTP login.
    3. **"Open dashboard" from WhatsApp:** a signed single-use 10-minute link, sent inside the free service window. Costs ₹0.
  - **Identity:** the phone number is the primary identity (it's the WhatsApp ID). Google email is a linked identity in `auth.identities` / `channel_identities`. Sessions last 30 days with refresh, and the user can sign out of all devices.
  - Pages: Today, History and Goals timeline, Plans and Shopping, Pantry and Kitchen, Products, Share, Settings and Integrations. Plus `/admin` for admins.
  - Reads Supabase directly under row-level security (RLS); writes go through the Brain.
- **Scope guard:** an intent classifier runs first. Off-topic requests get a polite decline, per Meta's January 2026 AI-provider terms.

### 3.2 Domain services (no LLM)
| Service | Responsibility |
|---|---|
| `TargetEngine` | Mifflin-St Jeor, TDEE, goal delta, macros by persona and goal, ICMR-NIN 2020 micronutrients, training- vs rest-day split. Versioned via `formula_version` |
| `SafetyRules` | Calorie floors, maximum loss rate and red-flag blocks; runs on every goal or target change |
| `FoodResolver` | Matching order: alias → trigram → pgvector. Branded product priority: user-verified → Open Food Facts → label OCR → D2C → generic → user-supplied photo/URL (asked only when nothing else validates) |
| `NutritionCalc` | per_100g × grams, oil and cooking factors, recipe totals, dish estimates |
| `Recommender` | Hard filters (diet, allergy, utensils, modes, time, pantry), then a score (macro fit, micronutrient gaps, pantry use, expiring items, variety, ratings) |
| `Planner` | Day, week or month meal plans for N people (household members plus guests). Day plans: greedy. Week plans: OR-Tools CP-SAT (macro fit per member, variety, time per day, batch/leftover links, budget). Month plans: four weekly solves linked by variety rules, each week finalised about 3 days ahead so it uses the current pantry. Outputs plan entries and portions per person |
| `ShoppingListBuilder` | Total planned ingredients − pantry − set-aside items → pack-size rounding with brand preference → **freshness-timed buckets** (non-perishables upfront; perishables ≤ N days before use) → `GroceryCart` intents for the commerce agent |

### 3.3 AI skills (single-shot, JSON schema, versioned prompts)
| Skill | Model | Input → output |
|---|---|---|
| PlateVision | Gemini Flash | Photo → `[{dish, est_grams, unit_guess, visible_fat, confidence}]` |
| LabelReader | Gemini Flash | Pack photo → `{brand, name, serving_label, serving_g, per_100g{}, per_serving{}, allergens, veg_mark}`, cross-checked so that per-serving ≈ per_100g × serving_g/100 |
| FoodParser | Flash-Lite (audio-capable) | Text or voice → `[{item, qty, unit, brand?}]` |
| RecipeAdapter | Flash | Recipe + constraints → adapted steps and ingredients (validated via NutritionCalc) |
| WeeklyReviewer | Flash, batch | Weekly rollups → three insights plus one focus |

### 3.4 Background jobs
| Job | Schedule | Notes |
|---|---|---|
| VideoCurator | Nightly | YouTube search (cached 30 days) plus trusted-creator boost, like/view ratio and sampled comment sentiment. Reuses WanderPlanner logic |
| CatalogIngest | On demand | Food databases, D2C SKU seeding and Open Food Facts India delta (§5) |
| Rollups | Nightly | `daily_summary`, weekly and monthly views, streaks |
| Nudges | Cron per user timezone | Utility templates; respects quiet hours and opt-outs |
| OrderSync | After an order and hourly | Instamart order history → pantry |
| Backups | Nightly | `pg_dump` → R2 (encrypted); photo originals → R2 lifecycle |

## 4. Data model (key tables)
```
-- identity & channels
households · users · channel_identities(user_id, channel, external_id[phone], verified_at)
integration_tokens(user_id, provider[swiggy|zomato], enc_access, enc_refresh, scopes, expires_at)

-- goals (temporal, immutable)
profiles(user_id, persona[beginner|intermediate|advanced], sex, dob, height_cm, …, diet_rules jsonb)
goal_plans(id, user_id, type[outcome|performance|health|habit], statement, target_value, target_date, status)
goal_phases(id, goal_plan_id, kind[cut|maintain|gain|recomp|diet_break], effective_from, effective_to)
target_sets(id, goal_phase_id, formula_version, inputs_snapshot jsonb, values jsonb, source[computed|override], created_at)
daily_targets(user_id, date, target_set_id, training_day, values jsonb)          -- written once/day

-- body & health time-series
body_metrics(user_id, ts, metric, value, unit, source) · lab_results(user_id, report_id, biomarker, value, unit, ref_low, ref_high)

-- foods & products
foods(id, source[IFCT|INDB|USDA|OFF|USER], name, name_hi, per_100g jsonb, embedding)
food_aliases · portion_units(food_id|product_id, unit, grams, user_id|null)
products(id, gtin, brand, name, variant, pack_size, serving_label, serving_g, per_100g jsonb,
         source[user_label|d2c|off|listing], source_ref, confidence, verified_by, label_photo, version)
product_listings(product_id, platform, platform_sku, title, price, mrp, last_seen_at)
analytics_events(id, user_id, name, props_json, channel, at)          -- registry-validated names
ai_calls(id, user_id NULL, skill, model, in_tokens, out_tokens, images, grounded_queries,
         cost_paise, latency_ms, ok, at) · price_table(model, unit, paise, valid_from)
wa_billing(id, user_id, template, category, cost_paise, at) · infra_costs(month, provider, inr)
metrics_daily(day, metric, dims_json, value) · cost_daily(day, provider, skill, user_id, paise)
job_runs(job, started_at, finished_at, ok, stats_json) · safety_events(user_id, rule, at)
admin_audit(admin_id, action, target, reason, at)
access_list(phone_e164 PK, user_id NULL, role[admin|member], status[invited|active|revoked],
            invited_by, invite_code_hash, invite_expires_at, failed_attempts, activated_at, revoked_at)
gate_events(id, phone_hash, decision[allow|deny|waitlist|code_mismatch], at)   -- no message content
waitlist(phone_e164, consent_at, source, first_seen_at, attempts)
usage_counters(user_id, day, msgs, photos, url_fetches, ai_cost_paise)
app_settings(gate_mode[invite_only|open], non_member_reply[silent|static_once_30d], max_active_users,
             invites_per_member, global_monthly_budget_inr, per_user_monthly_budget_inr)
product_submissions(id, product_id NULL, submitted_by, kind[photo|url], trigger[last_resort|dispute],
                    raw_ref /*private bucket key or URL*/, extracted_json, extraction_conf,
                    status[pending|accepted|corroborated|contested|rejected|new_product],
                    resulting_product_version, reviewer_note, created_at)
user_reputation(user_id, submissions, accepted, overturned, quarantined)

-- kitchen & recipes
pantry_items(household_id, food_id|product_id, qty, unit, opened_at, expires_at, source)
kitchen(household_id, utensils[], cook_modes[])
recipes · recipe_ingredients · recipe_nutrition · recipe_videos · trusted_creators · ratings

-- logs (immutable + corrections)
meal_logs(id, user_id, eaten_at, slot, source[photo|voice|text|barcode|recipe|order], media_ref)
meal_log_items(log_id, food_id|product_id|recipe_id, grams, unit_display, nutrients_snapshot jsonb,
               source_version, supersedes_id, ai_estimate jsonb)
daily_summary(user_id, date, totals jsonb, adherence, gaps jsonb)

-- conversation & memory
conversations · messages(id, conversation_id, role, content, media_ref, tool_calls jsonb)
conversation_summaries(user_id, period, summary, embedding) · user_facts(user_id, key, value, confidence, source_msg_id)

-- planning
meal_plans(id, household_id, horizon[day|week|month], start_date, end_date, settings jsonb, status)
meal_plan_entries(id, plan_id, date, slot, recipe_id, servings jsonb{user_id|guest_type: portions},
                  batch_id, leftover_of_id, status[planned|cooked|skipped|swapped|ate_out])
plan_diners(plan_id, date, user_id|null, guest_type[adult|child|light]|null, count)
pantry_reservations(pantry_item_id, plan_entry_id, qty)        -- set aside, so other plans/recommendations don't use it
shopping_lists(id, plan_id, created_at) · shopping_buckets(id, list_id, buy_by_date, status, cart_proposal_id)
shopping_items(bucket_id, food_id|product_id, qty_needed, pack_qty, pack_count, perishable, status)

-- commerce
cart_proposals(id, user_id, intent jsonb, lines jsonb, bill_hash, expires_at, status)
orders(proposal_id UNIQUE, platform, status, bill jsonb, confirmed_by, confirmed_at, delivered_at)
ai_calls(id, user_id, agent|skill, model, tokens, cost_inr, latency_ms, ok)
```
- **RLS:** personal tables are visible only to their owner. Household tables (pantry, kitchen, household products) are visible to all members. Commerce tables are readable only by the owner; writes go through the service role.
- **Storage:**
  - WebP thumbnails at 512 px are kept forever in Supabase Storage.
  - Originals go to R2 and are deleted or archived after 90 days.
  - Lab reports go in a separate private bucket.

## 5. Data sources and open-source repos (checked 2026-10-14)

### 5.1 Use: core nutrition data
| Source | What | Licence | Use |
|---|---|---|---|
| **IFCT 2017** (ICMR-NIN). Machine-readable via `nodef/ifct2017` (542 foods, 151 components) | Raw Indian foods with micronutrients | Data © ICMR-NIN. ⚠️ The repo's packaging is **AGPL-3.0** | Load the **data tables** in an offline script; don't link the AGPL code into the service. Licence check before going commercial |
| **INDB** (Indian Nutrient Databank). `lindsayjaacks/Indian-Nutrient-Databank-INDB-` | ~1,000 cooked Indian recipes with nutrients | ⚠️ No licence file; cite the paper and ask the authors before commercial use | Recipe nutrition for dal, sabzi, roti and more; dish estimates for food orders |
| **USDA FoodData Central** | Global foods and micronutrient fallback | Public domain (CC0) | Fallback values |
| **Open Food Facts** (dumps + API; `openfoodfacts-python`) | Packaged products by barcode, including some Indian brands | Data **ODbL** (share-alike for derived databases) | Barcode lookup. Keep OFF-derived rows attributable; contribute label scans back |
| **FoodOn** (`FoodOntology/foodon`) | Food and ingredient ontology, synonyms | CC-BY-4.0 | Canonical ingredient IDs and synonyms for matching |

### 5.2 Use: libraries
| Repo | Licence | Use |
|---|---|---|
| `strangetom/ingredient-parser` (actively maintained) | MIT | Parse "2 cups atta, 1 tbsp ghee" into quantity, unit and name for recipe imports. Indian units (katori, ladle, pinch) added on top |
| `hhursev/recipe-scrapers` (supports 400+ sites) | MIT | "Import this recipe" when you paste a link (personal use; respect each site's terms) |
| `openfoodfacts/openfoodfacts-python` | ⚠️ check | Open Food Facts API client |

### 5.3 Reference only: open-source kitchen apps (learn the models, don't copy AGPL code)
| App | Licence | What to learn |
|---|---|---|
| **Grocy** (9.6k ★) | MIT | Pantry and stock model: units, conversions, best-before dates, consume/open events, shopping list from minimum stock. **Closest to our pantry needs** |
| **Mealie** (13.6k ★) | AGPL-3.0 | Recipe schema, ingredient-to-food linking, meal planner, URL import |
| **Tandoor** (8.7k ★) | ⚠️ custom | Food/unit/ingredient normalisation and shopping lists |
| **KitchenOwl** (3.7k ★) | AGPL-3.0 | Household-shared lists and item recognition |
| `loveucifer/neologger` | MIT | Example combining OFF and IFCT in a tracker |

### 5.4 Avoid or limit
- **Logged-in or private-API quick-commerce scrapers** (`ISudhan/wescrapping-with-playwright`, `princ0301/QuickCompare` and others): use as structure references only. We build our own polite **public-page** adapters (§5.5). Ordering stays on the official Swiggy MCP.
- **Scraped recipe datasets without a licence** (e.g. `kanishk307/IndianFoodDatasetGeneration`, 6k Indian recipes): fine only as a personal evaluation set. Not for shipping.
- **CC-BY-SA recipe sets** (e.g. `farcrak/unitools-recipes`): usable, but derivatives must also be shared under CC-BY-SA.

### 5.5 Branded catalogue: automated enrichment pipeline
```
jobs/catalog/
  seed_universe   ← Instamart order history (MCP) + Planner ingredient searches (MCP)
                    + D2C brand list (~30) + OFF India mirror (10.7k w/ nutrition) + FMCG staples sitemaps
  enrich(sku) waterfall (stop when validated):
    A off_mirror        GTIN / fuzzy brand+name+variant
    B pdp_text          polite public-page adapters (BigBasket, Zepto*, JioMart) → embedded JSON/text
    C pdp_images        back-of-pack gallery images → LabelReader (Gemini Batch API)
    D brand_site        per-brand adapters (sitemap → PDP) → B/C
    E instamart_mcp     product details/images if exposed ⚠️ → C
    F grounded_search   Gemini + Google Search grounding, ≥2 cited sources agree
    G generic_map       IFCT/INDB/USDA category equivalent (badge, provisional)
    H user_supplied     triggered two ways: (1) LAST RESORT when A–G fail / only generic,
                        (2) DISPUTE: user taps "Not right?" on any product/log value
                        photo (front+back) → LabelReader; URL → fetch once (public, no login) → B/C extraction
                        → product_submissions row → validate → identity check → arbitrate (see §5.6)
                        → accepted value written to the GLOBAL catalogue (user-agnostic) as a new products.version
  validate            Atwater ±15%, per-serving↔per-100g, category ranges, cross-source consensus → confidence
  resolve_identity    GTIN | brand+name+variant+pack + embeddings → products / product_listings
  refresh             monthly re-check; value change → new products.version
  * drop any source that is anti-bot-blocked; never solve CAPTCHAs; store facts + source URL, not images
```
Scale target: about 15–25k food SKUs. Cost: LabelReader batch for about 5k images plus grounded queries for the long tail is a one-off of roughly ₹500–1,500 ⚠️ (check current Gemini pricing), then small increments.

### 5.6 User submissions & disputes: a shared, user-agnostic catalogue
Every successful extraction from a user's photo or URL is stored in the **global** `products` catalogue, so the next user who logs or plans with that product gets it automatically. Nothing is scoped to a household or user. Only the audit trail records who submitted.

```
"Not right?" / last-resort prompt → user sends label photo or URL
  → product_submissions(status=pending)           -- raw input kept privately for audit; EXIF stripped
  → extract (LabelReader / page parser) → validate (Atwater ±15%, per-serving↔per-100g, ranges)
  → identity check: barcode / brand / name / variant / pack in the photo or page must match the product
       mismatch → treat as a NEW product (or a new variant) instead of overwriting
  → arbitrate against the current value:
       no current value / generic only         → accept, confidence = user_label
       agrees with current (±10%)              → accept as corroboration, confidence ↑
       differs, submission is a clear label     → accept as new version (likely reformulation / bad OFF row),
         photo that passes validation             previous version kept; flagged for refresh (re-run A–F)
       differs, URL-only or low extraction conf → hold as "contested": show both values to the submitter,
                                                  apply to the submitter's own logs now, promote globally once
                                                  a 2nd independent source/submission agrees
  → on accept: products.version++, source='user_photo'|'user_url', submission_id linked
  → recompute affected meal_log_items for the submitter (others keep their historical snapshots;
     their future logs use the new version; optional "update past logs?" prompt)
  → if source was OFF: queue a correction to contribute back to Open Food Facts (Phase 2, opt-in)
```
Abuse/quality controls: rate limit per user, reputation score (accepted ÷ total submissions), auto-quarantine for submitters whose values are repeatedly overturned, and an admin review queue in the dashboard for contested items.

**Phase 3 (commercial):** license **GS1 India DataKart** (national GTIN product master) and/or a commercial nutrition API, and re-check each crawled source's terms.

### 5.7 Sharing stats with people who aren't users
- **Bot:** "Share today" (or a 📤 button on the summary) → choose what to share → server renders a **ShareCard PNG** → the bot sends it to you → **you forward it** with WhatsApp's native forward to anyone.
  - We never message non-users. The gate forbids it, and it would cost template fees.
- **Card types:** Today (percentage of calories and protein hit, meals logged, a "Nailed it / Close / Reset tomorrow" verdict), Week (adherence %, streak, best day), Milestone (e.g. 30-day logging streak, protein target hit 7/7), Recipe I cooked (dish photo, macros per serving), Plan (tomorrow's or this week's menu, e.g. for a spouse or the cook).
- **Privacy defaults:**
  - Shown: percentages of target, streaks and verdicts.
  - Hidden: weight, body fat, absolute calorie targets, lab values and medical flags. Each field can be turned on per share.
  - Only the user's first name or a nickname appears.
- **Optional web link** (`/s/{id}`): a static, read-only snapshot. It expires in 7 days, carries `noindex`, has no login, contains no other data and can be revoked.
- **Anti-virality before launch:** cards and links carry only the brand wordmark and tagline. No `wa.me` link, QR code or call to action. After launch, a feature flag adds a referral call to action and invite code (tied to a referral quota).
- **Tables:** `shares(id, user_id, kind, fields_json, image_key, web_slug NULL, expires_at, revoked_at, created_at)`. Each share writes a `share_created` analytics event. The admin console counts shares as an engagement and growth metric.

## 6. Key flows

### 6.1 Onboarding (WhatsApp Flow)
```
"Hi" → Flow: 8 core questions → persona question → persona-specific screen
     → TargetEngine + SafetyRules → summary card + "Looks right? ✅ / ✏️"
     → goal_plan + goal_phase + target_set saved; progressive questions scheduled
```

### 6.2 Photo log
```
photo → PlateVision → FoodResolver (+ user's portion calibration) → NutritionCalc
     → draft reply "2 roti, dal 180 g, ~410 kcal · P 16 g" [✅ Log] [✏️ Adjust → Flow]
     → confirm → meal_log_items with nutrients_snapshot; corrections update calibration
```

### 6.3 Cook, then shop
```
"what's for dinner, 30 min" → Recommender (remaining budget, pantry, kitchen)
   → list message (top 3) → pick → recipe + cached video + missing items
   → [🛒 Add missing to Instamart] → handoff_commerce(GroceryCart)
   → CartProposal → "6 items, ₹642 COD, ETA 14 min" [✅ Place] [✏️ Edit] [✖]
   → (signed confirm) → place_order → orders → OrderSync → pantry
```

### 6.4 Plan ahead, then shop (early planners)
```
"plan next week, 4 people, lunch+dinner, veg Tue" → Flow (headcount per day, guests, time limits, budget)
   → Planner (CP-SAT) → meal_plan + entries + per-person portions + pantry set-asides
   → summary card + web link (calendar grid)
   → ShoppingListBuilder → buckets: [Now: staples ₹1,240] [Wed: veg+dairy ₹560] [Sat: veg+chicken ₹710]
   → [🛒 Cart for "Now"] → handoff_commerce(GroceryCart) → signed confirm → order
   → scheduled bucket → utility template "Wednesday top-up cart is ready" → confirm → order
   swap/skip/ate-out → re-solve remaining days → list diff → buckets updated
```

### 6.5 Order instead of cook (Phase 2)
```
"too tired to cook" → handoff_commerce(FoodOrder{remaining macros, diet, ≤ ₹400, ≤ 40 min})
   → FoodOptions ranked by fit → pick → confirm → order → on delivery: log draft
```

## 7. AI usage and cost (2 users)
| Component | Model | Calls a day | Notes |
|---|---|---|---|
| Coach turns | Flash | ~40 | Summarised memory keeps context under 8k tokens |
| PlateVision / LabelReader | Flash | ~10 | Image ≤ 1024 px |
| FoodParser (text/voice) | Flash-Lite | ~20 | |
| Commerce | Flash | ~2–5 sessions | 5–15 tool calls each |
| WeeklyReviewer, VideoCurator sentiment | Flash-Lite | batch | |

- **Estimate:** about ₹200–400 a month for AI, plus ₹0–50 for WhatsApp. Everything else is on free tiers.
- **AICostGuard** enforces daily per-user caps, and every call is logged to `ai_calls`.

## 8. Deployment
| Piece | Hosting |
|---|---|
| Brain (agents, services, webhook) | Cloud Run, `asia-south1`; minimum 1 instance during waking hours ⚠️ (avoids cold starts on WhatsApp replies; or use the CPU-boost free tier) |
| Web dashboard | Vercel (free) |
| Database, auth, thumbnails | Supabase, `ap-south-1` (free) |
| Photo originals, backups | Cloudflare R2 (10 GB free) |
| WhatsApp | Meta Cloud API direct (no BSP). Dedicated number; business verification before display-name approval |
| Secrets | GCP Secret Manager. Swiggy tokens are encrypted with a separate key that only the commerce module can read |
| CI | GitHub Actions: lint, type-check, pytest, prompt and eval smoke tests |

## 9. Security and privacy
- Webhook HMAC check, signed single-use confirm tokens, RLS everywhere, the service role only inside the Brain.
- Health data is disclosed to users as passing through Meta (transport) and Google (inference). Lab reports are web-only.
- DPDP Act: consent per data category, data export and account deletion.
- **Prompt-injection posture:** user and third-party text never grants permissions. Tool permissions are fixed per agent.

### 9.1 Invite-only access gate (pre-launch)
The aim is that forwarding a message, card or the number itself to someone who wasn't invited costs us nothing and spreads nothing.

```
WhatsApp webhook → verify HMAC → dedupe(message_id) → ACCESS GATE ──member──→ Conversation Core
                                                    │
                                                    └─non-member→ NO media download, NO LLM call, NO user data stored
                                                                  → hashed-phone attempt counter (virality signal)
                                                                  → reply per gate_mode:
                                                                      silent (default)  | one static reply per number per 30 days:
                                                                      "CookToFit is invite-only right now. Reply WAITLIST to be notified."
                                                                  → "WAITLIST" → store phone with explicit consent in waitlist
```
- **The gate runs first**, before media download, Gemini or any tool, so a non-member costs about zero. Inbound messages are free, and a static reply inside the service window is free.
- **The allow-list is bound to the phone number.** Access is decided by the sender's WhatsApp ID (the E.164 number Meta verified), not by anything in the message. A forwarded invite link, code or screenshot does nothing from another number.
- **Invites are admin-only.** You create an invite in the dashboard with the phone number, name, household and an expiry (default 7 days). The invitee gets a `wa.me` deep link with a single-use code.
  - Activation needs **both** the invited phone number and the code.
  - A code sent from any other number is rejected, doesn't use up the invite, and counts as a failed attempt; you get an alert after 3.
- **Members can't invite anyone before launch** (`invites_per_member = 0`). The flag allows a controlled beta later (e.g. 2 invites each).
- **Caps (app_settings):**
  - `max_active_users` (default 10).
  - Per-user daily limits: processed messages (200), photos (30) and URL fetches (20).
  - A per-user monthly AI budget.
  - A **global monthly spend kill switch**: at 80% you get an alert; at 100% the bot sends members "paused" and the gate blocks paid work.
- **Nothing in the product invites others to use it:**
  - Shareable PNG cards and recipe messages carry no `wa.me` link, QR code or "chat with us" call to action before launch. The brand watermark only.
  - The number isn't published anywhere, and the business profile has no "Message us" link.
  - Templates are only ever sent to active members.
- **Groups and broadcast:** group messages are ignored, and the number is never added to groups.
- **Dashboard:** Supabase Auth sign-in is limited to the same allow-list. Magic links are issued only to active members.
- **Revoking access:** an admin can revoke at any time; the number is then treated as a non-member immediately. All gate decisions are audit-logged.
- **Launch switch:** set `gate_mode=open` with `max_active_users` raised. The waitlist becomes the first launch wave.

### 9.2 Admin console (`/admin` in the Next.js dashboard; role=admin only)
| Tab | What it shows | Source |
|---|---|---|
| **Overview** | Today and 30 days: active users, meals logged, AI spend vs budget, gate denials, open hygiene alerts | Rollups |
| **Access & growth** | Invites sent → activated → onboarded → activated user (≥3 meals logged in the first 7 days) funnel; invite expiry and code mismatches; waitlist size and trend; denied attempts and **distinct unknown numbers per week** (word-of-mouth signal before launch); `gate_mode`, caps and revoke controls | `access_list`, `gate_events`, `waitlist` |
| **User activity** | DAU/WAU/MAU, stickiness (DAU÷MAU), D1/D7/D30 retention cohorts, logging coverage (% of days with ≥2 meals logged), streaks, channel mix (WhatsApp vs web), feature use (photo, voice, text, recommend, plan-ahead, Instamart, disputes), recommendation acceptance rate, time from photo to confirmation | `analytics_events` → `metrics_daily` |
| **Spend** | Cost by **provider** (Gemini by model, WhatsApp templates, Cloud Run, Supabase, R2, Google Search grounding), by **feature or skill** (PlateVision, LabelReader, coach turns, catalogue jobs) and by **user**. Shows cost per active user per month, cost per logged meal, month-end forecast, and budget burn with alerts at 80% and 100% | `ai_calls` ledger + `wa_billing` + monthly infra import |
| **Hygiene: data** | Catalogue: share of products from OFF, crawled pages or user submissions; validation failure rate; queue of **contested submissions** (approve/reject); submitter reputation and quarantines; OFF sync status; products only on generic estimates that people log most often (fix first) | `products`, `product_submissions`, `user_reputation` |
| **Hygiene: system** | Webhook errors and latency (p50/p95), job runs (OFF sync, enrichment, rollups, backups) with last-success time, LLM error and retry rate, WhatsApp **quality rating** and template status, Swiggy token expiry, YouTube quota | `job_runs`, logs, Meta API |
| **Safety & commerce** | Red-flag safety-rule triggers (counts only), commerce proposals vs confirmations, cap hits, rejected `place_order` attempts, dry-run vs live | `safety_events`, `orders`, `commerce_audit` |
| **Audit log** | Every admin action and every break-glass access | `admin_audit` |

- **Privacy (DPDP):** admin views use **aggregates and operational data only**. They never show meal contents, photos, weight, lab results or chat text. Seeing one user's health data requires a **break-glass** action with a reason. It's time-boxed, recorded in `admin_audit`, and the user can see that it happened.
  - The two of you can always see your own data in the normal dashboard.
- **Instrumentation:** a typed `analytics_events(user_id, name, props_json, channel, at)` table, written by the Conversation Core and the web app.
  - Event names are kept in one registry: `meal_logged`, `photo_received`, `recommendation_shown/accepted`, `plan_created`, `cart_proposed/confirmed`, `dispute_opened/resolved` and others.
  - There's no third-party analytics SDK, so health-related usage data stays in our own Postgres. PostHog self-hosted is an option later.
- **Cost ledger:** every LLM call writes `ai_calls(user_id NULL, skill, model, in_tokens, out_tokens, images, grounded_queries, cost_paise, latency_ms, ok)`, using a versioned `price_table`.
  - WhatsApp template sends are priced from the rate card.
  - Infra costs (Cloud Run, Supabase, R2) are imported monthly or entered by hand.
- **Rollups:** `metrics_daily` and `cost_daily` are refreshed every 15 minutes and nightly; cohorts are computed nightly.
- **Alerts:** budget at 80% or 100%, webhook error spike, job missed for more than 24 h, WhatsApp quality rating dropping to Medium, a submitter quarantined, a commerce cap hit. Alerts go to the admin by WhatsApp utility template and by email.
- **Stack:** Next.js server components with SQL views, charts with Recharts or Tremor, and RLS `is_admin()` on every admin view. No separate BI tool in the MVP.

## 10. Repo layout (new repo `cooktofit/`)
```
services/brain/
  channels/ (whatsapp, web)  agents/ (coach, commerce)  skills/ (plate_vision, label_reader, food_parser, recipe_adapter, weekly_reviewer)
  domain/ (targets, safety, resolver, nutrition, recommender, planner)  jobs/  integrations/ (swiggy_mcp, youtube, off)
apps/web/                 Next.js dashboard
supabase/                 migrations, RLS, seed
scripts/ingest/           ifct, indb, usda, off, foodon, brands
evals/                    plates/, labels/, carts/, coach-conversations/
docs/                     PRD, DEEP_DIVE, ADRs, brand/
```

## 11. Architecture decisions (become ADRs)
1. **ADR-001:** WhatsApp plus a web dashboard for the MVP; the native Expo app is deferred.
2. **ADR-002:** Supabase Postgres as the single source of truth, with a temporal/immutable history model.
3. **ADR-003:** Deterministic nutrition from the database; the LLM never sets the numbers.
4. **ADR-004:** India-first data (IFCT, INDB), USDA fallback, a branded catalogue with label OCR.
5. **ADR-005:** Gemini behind a provider interface.
6. **ADR-006:** One coach agent plus one sandboxed commerce agent, single-shot AI skills and deterministic services. Order placement only on a human-signed confirmation.
7. **ADR-007 (revised):** The branded catalogue is built by an **automated multi-source enrichment pipeline**: OFF mirror, polite public product-page crawling (no login, robots.txt honoured), back-of-pack image OCR, brand sites, and grounded search with consensus validation. No logged-in or private-API scraping, no CAPTCHA bypass. Ordering uses official MCPs only. GS1 DataKart when commercial.
8. **ADR-008:** No Telegram fallback for now; the risk from Meta's AI-provider policy is accepted, and the shared conversation core keeps alternatives cheap.
9. **ADR-009: Open Food Facts is the primary branded-product source, with visible credit.**
   - **Ingestion:** the daily Parquet export (Hugging Face `openfoodfacts/product-database`), filtered to products sold in India, is loaded into `products` with `source='off'`, `source_ref=<barcode>` and `licence='ODbL-1.0'`.
   - **Role of the other sources:** the other enrichment steps run only when Open Food Facts is missing a product or its data fails validation.
   - **Licence obligations (ODbL 1.0):**
     - Show the credit "Product data © Open Food Facts contributors, available under the Open Database License (ODbL)" with a link to openfoodfacts.org, in three places: the dashboard footer and About page, each product page that uses OFF data, and the repo `NOTICE`/README.
     - Keep OFF-derived rows identifiable, so the derived database can be published under ODbL if it is ever shared publicly (share-alike).
     - Product images are CC BY-SA. We don't store them, so this applies only if they are added later.
   - **Contribution back (Phase 2):** corrections and new products are submitted back through the OFF write API with a named app `User-Agent`.
10. **ADR-010: Classified dish catalogue.** Dishes are a separate layer whose nutrition is computed from ingredients, with variants (home, restaurant, low-oil), classification (cuisine/region, meal slot, diet, allergens, method, utensils, time, protein source, serving units, multilingual aliases), hybrid retrieval (SQL filters + pg_trgm + pgvector) for the coach, and growth from use via the shared submission rules. See `docs/adr/0010-dish-catalogue.md`.
