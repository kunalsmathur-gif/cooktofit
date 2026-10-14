# Plan: Home-Cooking & Nutrition Coach app — CookToFit

## 1. Problem & approach
A two-user (you and your wife) Android + desktop app that:
- works out each person's macro and micro targets and also accepts targets you set yourself
- plans meals (breakfast, snack, lunch, dinner, dessert) to fit those targets
- suggests dishes based on your pantry, available time, utensils and cooking modes, with a recipe and a vetted YouTube video for each
- logs what you eat from a photo (with portion size) or by manual entry

**Approach:** a new standalone repo. Expo (React Native) gives you one codebase for Android and a web/PWA build for desktop. The backend is FastAPI plus Supabase (Postgres, Auth, Storage). Gemini, on a new API key, handles vision and reasoning. Nutrition numbers come from food-composition databases. The LLM only identifies foods and estimates grams; it never decides the calories. Everything should stay within ₹1,000/month.

Decisions confirmed so far: separate repo · Indian home cooking first, with global cuisines too · veg, egg and non-veg · Gemini · budget under ₹1k/month.

### ⚡ Revised direction (2026-10-14). This supersedes the Expo-first approach above.
- **MVP interface:** WhatsApp (official Cloud API) for logging, coaching, nudges and "what should I cook?", plus a **small web dashboard** (Next.js, desktop and mobile browser) for charts, goal history, pantry and settings. **The native Expo app is deferred.**
- **Invite-only before launch:** a phone-bound allow-list checked at the webhook *before* any AI or media work. Admin-only invites (single-use, bound to the invited number), so forwarding grants nothing. Non-members get silence or one static waitlist reply. User caps, rate limits and a spend kill switch. No `wa.me` links or QR codes in shareable cards. See ARCH §9.1, PRD Epic L.
- **Admin console** (`/admin`, admin-only): spend by provider, feature and user with budget burn and forecast; access and growth funnel plus word-of-mouth signal; DAU/WAU/MAU, retention cohorts and feature adoption; system and data hygiene (jobs, webhooks, WhatsApp quality rating, contested-submission queue); safety and commerce events. Aggregates only, plus audited break-glass access to one user's health data. Built on our own event and cost ledgers, with no third-party analytics. See ARCH §9.2, PRD Epic M.
- **Web portal:** mobile-first responsive design and an installable PWA. Sign-in by **mobile OTP via a WhatsApp authentication template** (avoids India's SMS registration rules; SMS fallback later), **Google**, or a one-tap link from WhatsApp. All methods allow-list gated. See PRD Epic N.
- **Share stats with people who aren't users:** privacy-safe ShareCard PNGs (day, week, streak, milestone, recipe, plan) that the user forwards natively in WhatsApp. No join link or QR code before launch. See ARCH §5.7, PRD H10–H11.
- **No Telegram fallback** for now. The risk from Meta's AI policy is accepted, and the shared conversation core keeps the option open.
- **Branded products are in the MVP**, with full seeding: about 200 D2C fitness and health SKUs, barcode lookup via Open Food Facts, and label-photo OCR only as a last resort.
- **Swiggy Instamart MCP is in the MVP:** pantry auto-fill from orders and a cart built from missing ingredients. ⚠️ OAuth callbacks are whitelisted. Plan A: ask Swiggy to whitelist our callback. Plan B for personal use: complete OAuth once via the allowed `http://localhost` redirect, then store and refresh the token server-side. COD only.
- **Personas:** Kunal is Advanced (full macros, training- vs rest-day targets, supplements). His wife is Intermediate (calories and protein first, other macros optional).
- **Benchmark (instinct.com):** not yet reviewed. Do this by hand before designing the WhatsApp flows.
- Detail and rationale: `docs/DEEP_DIVE.md`.

---

## 2. Architecture

> **MVP update:** the "Expo app" box below is replaced by **WhatsApp Cloud API webhook → Conversation Core (FastAPI agent with typed tools)** plus a **Next.js web dashboard** (Supabase Auth with Google SSO, or a WhatsApp magic link). New tables: `goal_plans`/`goal_phases`/`target_sets`/`daily_targets`, `products`/`product_listings`, `body_metrics`, `lab_results`, `user_facts`, `conversations`/`messages`, `channel_identities` (phone → user), `integration_tokens` (Swiggy OAuth, encrypted). See DEEP_DIVE §1, §2 and §4.

```
Expo app (Android APK via EAS + Web/PWA for desktop)   ← deferred to post-MVP
  ├─ Expo Router, TanStack Query, Zustand, NativeWind
  ├─ expo-camera / image-picker → upload to Supabase Storage
  └─ Supabase Auth (Google SSO, 2 allow-listed emails)
            │  JWT
FastAPI "brain" (Cloud Run free tier / Render)
  ├─ /targets      → BMR/TDEE + ICMR-NIN 2020 RDA engine (deterministic)
  ├─ /log/photo    → Gemini 2.5 Flash vision → items + grams → DB lookup
  ├─ /log/manual   → fuzzy search over food DB + LLM fallback parser
  ├─ /recommend    → constraint filter (pantry/time/utensils/mode/diet)
  │                   + macro-fit scoring + LLM recipe generation
  ├─ /videos       → YouTube Data API v3 + trusted-creator ranking (cached)
  └─ /plan         → day/week planner (greedy/ILP fit to remaining targets)
Supabase Postgres
  ├─ users, profiles, goals, targets
  ├─ foods (IFCT 2017 + INDB + USDA FDC + Open Food Facts), food_aliases
  ├─ recipes, recipe_ingredients, recipe_videos
  ├─ pantry_items, utensils, cooking_modes
  └─ meal_logs, meal_log_items, photos
```

Why these choices:
- **Expo over a PWA:** you get a proper camera, offline queueing, and Health Connect later on. Expo Web covers desktop. Distribute as an APK (EAS internal build), so there's no Play Store review.
- **Supabase:** auth, Postgres (with pgvector for dish search), and photo storage on a free tier. The free tier pauses only after 7 days with no activity, which daily use avoids.
- **FastAPI:** reuses patterns you already have in WanderPlanner (Gemini client, YouTube scoring, Python tooling). Alternative: Supabase Edge Functions, which means fewer services but Deno/TS.
- **Gemini 2.5 Flash** for vision and recipes. Use structured JSON output. Use Flash-Lite for cheap parsing.

### Nutrition data (the moat for Indian food)
| Source | Use |
|---|---|
| **IFCT 2017 (ICMR-NIN)** | Raw Indian ingredients, including micronutrients |
| **INDB – Indian Nutrient Databank** | ~1,000 cooked Indian recipes (dal, sabzi, roti…) |
| **USDA FoodData Central** | Global ingredients and fallback micronutrients |
| **Open Food Facts** | Packaged foods via barcode scan |
| **ICMR-NIN RDA/EAR 2020** | Micronutrient targets for Indian adults |

### Target engine (deterministic, explainable)
- Mifflin-St Jeor BMR × activity factor = TDEE, then adjust for the goal (cut, maintain or gain).
- Protein of 1.2–2.0 g/kg depending on goal; fat 20–30%; carbs make up the rest; fibre 25–40 g.
- Micronutrients from ICMR-NIN 2020, by sex, age and pregnancy/lactation status.
- User overrides always win. Every target has a "why this number" explanation.
- Phase 2: an adaptive TDEE from the weight trend (MacroFactor-style).

### Photo logging pipeline
1. Take the photo. The prompt asks for a reference object if one is present (katori, standard plate, hand, spoon).
2. Gemini vision returns `[ {dish, confidence, est_grams, visible_oil/ghee, cooking_method} ]`.
3. Each dish maps to the food DB through aliases plus embedding search.
4. A **confirm & adjust** screen offers portion sliders in Indian units (katori, roti count, ladle, piece) and a "hidden oil" toggle.
5. Corrections are saved per user, so repeat meals become one-tap and accuracy improves over time.

### Manual logging
- Natural-language entry, e.g. "2 rotis, 1 katori rajma, half cup curd", is parsed by an LLM and then looked up in the DB.
- Search with recents and favourites, plus "same as yesterday's lunch".
- Direct macro entry for packaged items, or a barcode scan.

### Recommendation engine
1. **Hard filters:** diet type, allergies, utensils, cooking modes (gas, microwave, oven, air fryer, pressure cooker, induction), max time, pantry coverage of at least X% (missing items listed).
2. **Score** = macro/micro fit to the *remaining* daily budget + pantry use (expiring items first) + variety (no repeats within N days) + ratings from the two of you.
3. **Sources:** a curated recipe DB, seeded from INDB recipes plus LLM-generated recipes that have been validated against the DB. Gemini adapts a recipe to the available utensils (e.g. "air-fryer version").
4. **Videos:** YouTube Data API search, ranked by an allow-list of trusted creators plus like/view ratio, subscriber count and comment sentiment. Results are cached per dish because of the 10k-unit daily quota.

---

## 3. Competitor scan and gaps
| App | Strength | What it lacks for you |
|---|---|---|
| **HealthifyMe** (Snap) | Indian food DB, photo logging | Coach-upsell heavy; no pantry, utensil or time-aware cooking; weak micronutrients |
| **MyFitnessPal** | Huge DB, barcodes | Crowd-sourced Indian entries are unreliable; photo logging paywalled; no cooking help |
| **Cronometer** | Best micronutrient tracking | Western DB; poor at Indian dishes; no recommendations |
| **MacroFactor** | Adaptive TDEE, great logging UX | No Indian focus, no recipes or pantry, no photo logging (until recently) |
| **Cal AI / SnapCalorie / Foodvisor** | Fast photo-to-calories | Fail on mixed Indian plates and hidden ghee/oil; no portion confirmation in katori units |
| **Samsung Food (Whisk), Mealime, SuperCook** | Pantry-based recipes and grocery lists | Not macro- or micronutrient-driven; no utensil or cook-mode constraints; no Indian depth |
| **Eat This Much** | Auto meal plans to macros | Western recipes; ignores pantry, time and equipment |
| **Fittr / Ultrahuman** | Indian fitness community, CGM | Coach- or hardware-centric, not a home-cooking assistant |

**White space nobody covers well:**
1. Meal suggestions that respect **pantry, utensils, cooking mode and time together** while fitting the remaining macro and micro budget.
2. **Indian mixed-plate photo logging** with katori-based portions and hidden-fat correction.
3. **Household mode:** cook one dish and the app splits portions to fit each person's different targets.
4. **Micronutrient gap closing**, e.g. "You're low on iron and B12 this week, so here are 3 dishes from your pantry."
5. **Curated video quality**: trusted creators rather than a raw YouTube search.
6. **Cook (maid) mode:** send tomorrow's menu and instructions to your household cook in Hindi or a regional language via WhatsApp. This is a big India-specific differentiator.

---

## 4. Phases

### Phase 0: Foundations (revised)
- Repo with a FastAPI core and a Next.js web dashboard scaffold.
- Supabase project, with Google auth allow-listed for the two of you.
- Meta Business account, WABA, a dedicated WhatsApp number and a webhook on Cloud Run.
- CI. Expo/EAS is deferred.

### Phase 1: MVP (for the two of you; WhatsApp + web)
- **Persona onboarding:** about 8 core questions, then the Beginner/Intermediate/Advanced branch, delivered as a WhatsApp Flow. Computed targets with manual override; training- vs rest-day targets for Advanced.
- **Temporal data model:** versioned goals, daily target snapshots, immutable logs.
- **Food DB ingest:** IFCT, INDB and a USDA subset, with aliases and Hindi names.
- **Branded product catalogue:** about 200 D2C SKUs seeded, Open Food Facts barcode lookup, label OCR as fallback, catalogue shared by the household.
- **Logging in WhatsApp:** photo, voice note or text ("2 roti + 1 katori dal + 1 scoop whey"), with a confirm/adjust step using buttons or a Flow.
- **Daily summary:** a WhatsApp PNG card plus the web dashboard (macro rings, micronutrient bars, remaining budget, goal history).
- **Pantry, utensils and cooking modes:** set up through a Flow or the web. Auto-filled from Instamart orders.
- **"What should I cook?" in WhatsApp:** recipe, YouTube link, and meal suggestions across breakfast, snack, lunch, dinner and dessert.
- **Instamart MCP:** cart for missing ingredients (COD).
- **Plan ahead (early planners):** day, week or month plans for N people (household plus guests, headcount per day), batch/leftover cooking, a consolidated shopping list minus pantry and set-asides, freshness-timed top-up carts to Instamart, and a living plan that re-solves after swaps. Day and week plans in the MVP; month plans are P1.
- **Household:** each person chats 1:1; shared pantry and catalogue; split portions.
- **Utility-template nudges:** meal reminders and the evening "remaining budget" message.

### Phase 2: Differentiators
- **Order instead of cook:** Swiggy Food MCP (official ✅) / Zomato MCP (⚠️ verify). When you don't want to cook, rank nearby dishes by fit to the remaining macros.
- **Native Expo Android app**, once the WhatsApp loop is proven (camera, Health Connect, offline).
- **More grocery channels:** Zepto, Blinkit and BigBasket via deep links (no official MCP).
- **Auto pantry update** from grocery order history or receipt photos; expiry tracking with a "use it up" priority.
- **Weekly meal-prep planner** with a consolidated grocery list and batch-cooking schedule.
- **Hands-free cooking mode:** voice step-by-step and timers (reuse Anya voice patterns from WanderPlanner).
- **Cook/maid mode:** WhatsApp the menu and recipe in Hindi or a regional language.
- **Health Connect:** weight, steps and activity drive an adaptive TDEE.
- **Blood report upload (PDF):** flag deficiencies (Vit D, B12, iron, HbA1c) and re-weight recommendations.
- **Restaurant menu photo:** "what should I order here?"
- **Fasting/festival modes:** Navratri, Ekadashi, Ramadan, and intermittent fasting windows.
- **Leftover remix:** "turn last night's dal into…"
- **Cost per meal** and grocery budget tracking.
- **WhatsApp logging bot:** moved into the MVP as the primary interface.
- **Weekly AI review:** trends, wins and one focus for next week.

### Phase 3: Scale beyond 2 users
Multi-tenant hardening, Play Store listing, subscriptions, rate limits and per-user AI cost caps, a moderated recipe DB, privacy and DPDP Act compliance for health data, and an evaluation set for photo accuracy.

---

## 5. Cost estimate (2 users)
- **Gemini Flash** (~10 photos and ~20 text calls a day): a few cents a day, so roughly ₹100–300/month.
- **Supabase:** free tier. **Cloud Run:** free tier. **YouTube API:** free (quota-cached).
- **EAS builds:** free tier. **Domain:** optional.
- **Total:** comfortably under ₹1,000/month.

## 6. Risks and mitigations
- **Photo calorie accuracy** (±20–30% is typical). Mitigate with the confirm & adjust step, reference objects, learning from your corrections, and computing nutrition from the DB rather than trusting the LLM's numbers.
- **Data licensing:** IFCT and INDB are fine for personal use, but terms must be checked before going commercial.
- **YouTube quota:** cache results and pre-compute videos for the recipe catalogue.
- **MCP availability for Swiggy, Zomato and quick commerce:** verify before Phase 2. Deep links are the fallback.
- **Health data privacy:** row-level security in Supabase, encryption of photos at rest, and data stored in an India region if possible.

## 7. Companion docs
- Detailed PRD: `docs/PRD.md` (epics A–G, user stories with priorities, acceptance criteria, metrics, NFRs)
- Deep dive on storage, branded products, goal onboarding and WhatsApp: `docs/DEEP_DIVE.md`
- High-level architecture: `docs/ARCHITECTURE.md` (components, data model, key flows, AI cost control, deployment, Phase 2 integration points)
- ADRs: `docs/adr/`. Brand kit: `assets/brand/`.

## 8. Deep dive: foundational decisions (see `docs/DEEP_DIVE.md`)
1. **Storage:** Postgres stays the single source of truth. History is immutable: goals are versioned with phases; there is a daily target snapshot; every log item stores the nutrients it used; corrections are events. Rollups serve long-range charts. Coach memory uses `user_facts` plus summaries plus pgvector. Photos go to R2 or a thumbnail lifecycle, because Supabase free storage runs out in about a year. Nightly encrypted `pg_dump`.
2. **Branded products:** a `products` catalogue with serving definitions (e.g. "1 scoop = 33 g"). Built by an **automated enrichment pipeline**, with no user effort. **Open Food Facts is the primary source** (daily export, 10.7k Indian products with nutrition), credited visibly in the dashboard, product views and repo NOTICE under ODbL (ADR-009). Gaps are filled by polite public product-page crawling, back-of-pack image OCR, brand sites and grounded search, with automatic validation. No logged-in scraping. GS1 DataKart when commercial. The official **Swiggy MCP** (Instamart, Food, Dineout) is used for cart and ordering, not nutrition. It is COD only and needs OAuth callback whitelisting.
3. **Goals:** about 8 universal questions, then a persona branch (Beginner, Intermediate, Advanced) that changes the questions, the visible numbers and the language. Goal types: outcome, performance, health and habit. Further questions are asked gradually. Safety floors and red-flag rules.
4. **WhatsApp:** feasible with the official Cloud API, Flows and templates, at roughly ₹0–50/month for two people. Meta's January 2026 ban on general-purpose AI bots means the bot must stay a scoped nutrition service. Build a **channel-agnostic conversation core**, with Telegram and web as fallbacks.

## 9. Open items
- Health inputs for the MVP were not specified. The plan assumes Health Connect and blood reports wait for Phase 2.
- Branding: DONE. CookToFit · "Every meal is a rep." · Monoline Flex Pan icon · Espresso & Terracotta (light+dark). Kit in `assets/brand/` (storyboard.html, SVG+PNG, tokens.json) — copy to repo `assets/` + `docs/brand/` at scaffold time.
