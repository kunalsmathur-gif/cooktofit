# CookToFit: deep dive on four foundational questions

Status: thinking doc, nothing built yet. Facts were checked on 2026-10-14 where marked ✅. Items marked ⚠️ are assumptions to verify.

---

## 1. Data storage for long-term goals

### What "long-term" really demands
Goals change over months and years (cut → maintain → bulk → pregnancy → recovery). The trap is storing only the "current goal" and recomputing history from it. When targets or food data change, last year's charts would then quietly rewrite themselves. So the design rule is: **history is immutable; every number is stored as it was at the time.**

### Storage choice
**Postgres (Supabase) stays the single source of truth.** No time-series DB or NoSQL is needed.

| Scale | Log rows/yr | Verdict |
|---|---|---|
| 2 users | ~11k meal items | Trivial |
| 1k users | ~5.5M | Fine with indexes |
| 100k users | ~550M | Partition `meal_log_items` by month; still Postgres |

Postgres also gives you `pgvector` (food/recipe search and coach memory), JSONB (raw AI outputs), row-level security (per-user privacy) and `pg_cron` (nightly rollups).

### Key modelling patterns
1. **Temporal (versioned) goals.** `goal_plans` holds the user's intent (e.g. "lose 6 kg by March"). `goal_phases` holds the periods within it (cut 12 wk, diet break 2 wk, maintain), each with `effective_from` and `effective_to`. `target_sets` holds the computed targets for a phase plus `formula_version` and `inputs_snapshot`. Overrides create a new version; nothing is updated in place.
2. **Daily target snapshot.** `daily_targets(user, date, target_set_id, kcal, protein…, training_day bool)`. It is written once per day, so "was I on track on 12 March?" is always answerable, even after the goals change.
3. **Nutrient snapshot on every log item.** `meal_log_items` copies the nutrients it used plus `food_id` / `product_id` and `source_version`. Later corrections to the food DB don't change past days. A "re-compute with new data" job can be run on purpose if wanted.
4. **Corrections are events, not overwrites.** An edited log keeps `supersedes_id`, which gives an audit trail and also training data for the photo model ("AI said 150 g, user said 220 g").
5. **Body and health time series.** `body_metrics` (weight, waist, BF%, sleep, steps; source = manual / Health Connect), `progress_photos` and `lab_results` (biomarker, value, unit, ref range, report_id). These drive the adaptive TDEE and micronutrient gap logic.
6. **Rollups for long horizons.** Nightly `daily_summary` (totals, adherence %, gaps), plus weekly and monthly views. Year-long charts read rollups, never raw logs.
7. **Coach memory.** `user_facts` (structured: "dislikes karela", "trains 6 am Mon/Wed/Fri", "whey = The Whole Truth chocolate"), `conversation_summaries` (rolling summaries) and embeddings. This is what makes the coach feel like it knows you after six months. It matters even more if WhatsApp becomes the main interface.
8. **Milestones and streaks.** These are derived tables, so they can be rebuilt.

### Media and cost watch-outs
- **Photos are the real storage cost.** About 20 photos a day × 150 KB WebP comes to roughly 1.1 GB a year, which already exceeds Supabase free storage (1 GB). Fixes: keep a 512 px thumbnail forever and delete or archive originals after 90 days, or move the photo bucket to Cloudflare R2 (10 GB free, no egress fees).
- **Database:** Supabase free tier is 500 MB, which is enough for 2 users for many years without photos.
- **Backups:** the free tier has no point-in-time recovery, so run a nightly `pg_dump` to GCS or R2 (encrypted), plus a one-click "export my data" (CSV/JSON) for DPDP Act compliance.
- **Lab reports and health data** go in a separate private bucket with signed URLs only. Collect consent per data category.

---

## 2. Brand-specific ingredient and product inventory

### The core insight
Generic food DBs (IFCT, USDA) can't say that one scoop of The Whole Truth whey is 24 g protein. That requires a **branded product catalogue** with label data and serving definitions. **Quick-commerce apps are not a reliable source of nutrition data.** Their listings are built for price and pack size; the nutrition panel is usually only an image of the back of the pack, if it's there at all. The label itself is the source of truth, and FSSAI regulations require Indian packaged foods to show nutrition per 100 g and per serving.

### Product data model
```
products            (id, gtin/barcode, brand, name, variant/flavour, pack_size,
                     serving_label "1 scoop", serving_g 33, nutrients_per_100g JSONB,
                     ingredients_text, allergens, veg_mark, source, source_ref,
                     confidence, verified_by, label_photo_url, version, updated_at)
product_listings    (product_id, platform: instamart|blinkit|zepto|bigbasket|amazon,
                     platform_sku, title_on_platform, price, mrp, last_seen_at)
pantry_items        (user/household, product_id NULL | food_id NULL, qty, unit,
                     opened_at, expires_at, source: manual|order|receipt|barcode)
```
**Nutrient resolution order when logging or planning:** user-verified product → Open Food Facts → label OCR → brand website → generic food (IFCT/USDA) → *last resort:* ask the user for a label photo or product URL (optional). Anything that falls back to generic shows a "generic estimate" badge.

### How products get in: an automated pipeline with no user effort (revised 2026-10-14)
**Principle:** the catalogue builds itself. Users never paste links or take label photos; the label photo is only an optional, rare last resort.

#### Step 1: decide *which* SKUs matter (don't try to cover everything)
A household buys roughly 150–300 distinct branded food SKUs a year. The catalogue is seeded from:
1. **Your Instamart order history** (official MCP): the exact SKUs you buy. Highest priority.
2. **Products the Planner will buy:** for every ingredient in a planned recipe, the top Instamart MCP search results.
3. **A fitness and health brand list** of about 30 D2C brands (The Whole Truth, MuscleBlaze, Yoga Bar, Epigamia, Super You, Amul Pro and others), covering all their SKUs.
4. **Bulk Open Food Facts India:** ✅ **10,745 Indian products with complete nutrition facts** (checked 2026-10-14), out of about 21k tagged as sold in India. Mirrored from the official daily Parquet export on Hugging Face (`openfoodfacts/product-database`, ODbL), so there's no need to scrape.
   - **Other public datasets reviewed (2026-10-14):**
     - Kaggle `lalit7881/indian-packaged-foods-nutritional-dataset-2026`: 852 SKUs from labels, CC0. Import it as a one-time extra seed, but it has no barcodes, so match on name.
     - Kaggle BigBasket (`surajjha101`, about 28k products; CC BY-NC-SA): no nutrition. Useful only for the product list and pack sizes.
     - Kaggle Zepto and Blinkit datasets: prices and sales only, no nutrition.
     - GitHub `devnarsinghani22/india-label-index`: derived from OFF.
     - GitHub `dpangarkar2/POINT`: an empty placeholder repo.
     - **No public copy of GS1 DataKart exists.**
   - **`openfoodfacts/nutrient-detection-layout`** (Hugging Face) is an open model that reads nutrition tables from pack photos. It's a cheap alternative or cross-check for the Gemini step that reads pack photos (waterfall step C).
5. **Top Indian FMCG staples** (Amul, Mother Dairy, Aashirvaad, Tata, Britannia, ITC, Haldiram's, MTR…), taken from public category sitemaps.

The realistic catalogue is about 15–25k food SKUs. Enrichment of any newly bought SKU is triggered automatically after an order.

#### Step 2: an enrichment waterfall per SKU (fully automatic)
| # | Source | How | Finding |
|---|---|---|---|
| A | **Open Food Facts mirror** | GTIN match, or brand + name + variant fuzzy match | ✅ 10.7k Indian products with nutrition; ODbL |
| B | **Public product pages with nutrition as *text*** (Zepto, per you; BigBasket) | Polite crawler of **public pages, no login**, food categories only. Reads embedded JSON (`__NEXT_DATA__`/JSON-LD) first | Zepto robots.txt is `Allow: /` but its anti-bot returned 202/429 to curl and headless Chrome. BigBasket allows product pages. **Swiggy disallows `/product`** (use the MCP) |
| C | **Back-of-pack images on public product pages** (JioMart, BigBasket, Zepto, brand sites) | Product image galleries usually include the nutrition panel. **Gemini LabelReader in batch** (Batch API ≈ half price) | ✅ JioMart pages are public (200) and robots allows, but nutrition is **only in images**, so OCR is the universal key |
| D | **Brand websites** (D2C) | Sitemap → product page → embedded JSON plus panel images → C | The Whole Truth runs on Next.js (not Shopify), so it needs per-site adapters |
| E | **Instamart MCP product details** | Description, images and attributes, if the MCP exposes them (⚠️ verify the fields) → C | Official and clean, if available |
| F | **Gemini + Google Search grounding** | "Nutrition facts per 100 g of <brand> <product> <variant>" → values plus cited URLs. Accepted only with ≥ 2 independent sources | Catches long-tail items. Costs a little per grounded query ⚠️ |
| G | **Generic fallback** | Map to an IFCT/INDB/USDA category equivalent (e.g. branded paneer → IFCT paneer) | Shown with a "generic estimate" badge |
| H | **User-supplied (last resort *or* dispute)** | Offered once when A–G fail, **or** whenever a user taps "Not right?" to contest a value. Photo → LabelReader; URL → one-off public fetch → page/image extraction. Validated, identity-checked, arbitrated against the current value, then confirmed by the user | Stored in the **shared, user-agnostic catalogue** as a new version for everyone next time; weak or conflicting evidence stays "contested" until a second source agrees. See ARCH §5.6 |

**Later (scale):**
- **GS1 India DataKart** is the national product-data repository (GTIN master data supplied by brand owners). It's a paid subscription for retailers and solution providers, and it's the *authoritative* licensed source once we go commercial.
- Commercial APIs (FatSecret, Edamam, Nutritionix) ⚠️ check their India coverage before paying.

#### Step 3: validate before trusting (automatic)
- **Energy check:** kcal ≈ 4×protein + 4×carbs + 9×fat (+2×fibre), within ±10–15%.
- **Serving consistency:** per-serving ≈ per-100 g × serving_g / 100.
- **Category plausibility:** e.g. whey has 60–90 g protein per 100 g; paneer has 15–22 g.
- **Cross-source agreement:** sources that agree → `confidence` high. Disagreements → keep the label-image value and queue it for review on the web dashboard (optional; the household is never blocked).
- **Version history:** brands reformulate. When values change, create a new `products.version`. Past logs keep their snapshot.

#### Step 4: match products across platforms
- **Identity:** GTIN when known. Otherwise (brand, normalised name, variant, pack size) plus embeddings.
- `product_listings` maps one product to its Instamart, Zepto, BigBasket and JioMart SKUs, so the Planner can use nutrition from one source and buy on Instamart.

#### Raw ingredients (unbranded)
- Fresh produce, loose dals, grains, meat and eggs map to **IFCT 2017**, **INDB** and **USDA**. No brand needed.
- Quick-commerce "Onion 1 kg" maps to IFCT onion automatically.
- Optional: the older NIN *Nutritive Value of Indian Foods* tables for wider coverage.

#### Legal and ethical crawling posture
- Public pages only, no login. Honour robots.txt and use a low rate (≤ 1 request every few seconds per site), a clear user-agent and caching.
- Never bypass CAPTCHAs.
- Nutrition values are factual data. **Store the extracted facts and the source URL, not the images.**
- **Open Food Facts is the primary source (decided 2026-10-14).** Credit it visibly: "Product data © Open Food Facts contributors, ODbL", with a link, in the dashboard footer and About page, on each product view, and in the repo NOTICE. Keep OFF-derived rows identifiable (`source='off'`, licence column), so a derived database can be shared under ODbL if it's ever published. Contribute corrections back in Phase 2. See ARCH ADR-009.
- ⚠️ Review each platform's terms of use before going beyond personal use. Prefer DataKart or partnerships for a commercial launch.
- If anti-bot blocks a source (e.g. Zepto from Cloud Run IPs), drop it. The waterfall has enough redundancy that no single source is critical.

### Existing open-source quick-commerce scrapers
`ISudhan/wescrapping-with-playwright`, `princ0301/QuickCompare`, `SumaVanthan/insta-price-compare`, `HridayKadam/Scrap`, `KshKnsl/QuickCom`, `DevWizard-Vandan/aerodata-qcomm` and `Hardik500/quick-commerce-mcp`.
- They're price-comparison hobby projects (logged-in sessions, private APIs). Useful as **references for page structure**, not as dependencies.
- We build our own small, polite, public-page adapters.

### Official route ✅: Swiggy MCP
Swiggy publishes official MCP servers for Food, Instamart and Dineout (`mcp.swiggy.com/{food,im,dineout}`). They cover product search by name, category or brand at your location, cart management and order placement.
- **Limits:** COD only. The OAuth redirect URIs are whitelisted (Claude, ChatGPT, VS Code, localhost), so a custom server or WhatsApp backend needs Swiggy to whitelist your callback ("contact us").
- **Fit:** good for building a cart from missing recipe ingredients and for "order instead of cook". Not a nutrition source.
- **Others:** the Zomato MCP exists per community demos (⚠️ official endpoint and terms still to verify). Blinkit and Zepto have no official MCP or API (⚠️ re-check later); use deep links or search URLs.

### Product-level UX
- Pantry brands come from Instamart orders automatically. Otherwise the bot asks once by text: "Which whey? The Whole Truth chocolate / MuscleBlaze / other".
- Logging "1 scoop whey" then resolves to *your* product, with its exact serving definition.
- No links or screenshots are needed. A label photo is only an optional last resort for a product missing from every source.

---

## 3. Goal setting: beginner vs gym bro

### Principle: progressive profiling, not a 40-question form
Ask the **minimum needed to produce safe, useful targets** (about 8 questions, under 90 seconds). Then learn the rest from behaviour and short follow-up questions over the first two weeks.

### Step 1: universal core (always asked)
Sex, age, height, weight, activity level (examples, not jargon), primary goal, diet type (veg / egg / non-veg / Jain), allergies and intolerances.

### Step 2: the persona branch, chosen by one self-selection question
"How do you think about food today?"
1. 🌱 *"I just want to eat healthier / lose some weight"* → **Beginner**
2. 🏃 *"I watch calories / protein roughly"* → **Intermediate**
3. 🏋️ *"I track macros / train seriously"* → **Advanced**

| | Beginner | Intermediate | Advanced ("gym bro") |
|---|---|---|---|
| Extra questions | Meal timings, who cooks, favourite dishes | Training days, target rate (kg/wk) | Body-fat %, training split, current macros or TDEE, supplements (brand + scoop), refeeds / carb cycling, protein per meal |
| What they see | **No macro numbers at first.** Plate method in katoris, "protein at every meal", traffic-light days | Calories + protein, other macros optional | Full macros, micros, training- vs rest-day targets, adaptive TDEE, weekly averages |
| Language | "Add a katori of dal" | "You need 30 g more protein" | "P 162/180 · C 210/240 · F 58/65" |
| Coaching | Habit goals, one change per week | Weekly trends | Weekly check-in, rate-of-loss adjustments |
| Override | Hidden | Allowed | First-class: type in your own numbers |

Beginners **graduate** automatically: after N days of consistent logging the app offers "Want to see your protein number?" The persona is a dial, not a cage.

### Step 3: goal types, because not everything is weight
- **Outcome:** lose, maintain or gain weight; recomposition.
- **Performance:** strength, endurance, a marathon.
- **Health:** PCOS, prediabetes or HbA1c, thyroid, BP, cholesterol, anaemia or B12, pregnancy or lactation. ⚠️ Needs a medical disclaimer and conservative rules.
- **Habit:** cook at home 5 times a week, eat 25 g fibre a day, no packaged snacks.
- A user can hold one primary goal and up to two secondary goals.

### Step 4: progressive questions later
These come up over time ("quick question 🙂"):
- Sleep, stress, work schedule
- Cooking skill and time per meal
- Budget
- Fasting days (Navratri, Ekadashi, Ramadan, IF)
- Dislikes
- Health conditions
- Lab report upload

### Safety guardrails (non-negotiable)
- **Calorie floors:** about 1,200 kcal for women and about 1,500 kcal for men unless a clinician has set something else. Maximum loss rate about 1% of body weight per week.
- **Red flags that block aggressive targets and suggest a professional:** under 18; BMI under 18.5 with a weight-loss goal; pregnancy; kidney disease with high protein; diabetes on insulin; a 3-question eating-disorder screen (SCOFF-style).
- **No guilt language.** This matches the brand voice.

### For you two specifically
You are likely Intermediate or Advanced and your wife may be a different persona. Household mode is persona-aware: the same dal, with different portions *and* a different presentation for each of you.

---

## 4. WhatsApp-first instead of an app

### Why it's compelling
- Zero install, and the habit already exists.
- Logging becomes "send a photo or voice note".
- Nudges arrive where you already are.
- Perfect for India and for cook (maid) mode.

### The hard constraint ⚠️ Meta policy, effective 15 Jan 2026 ✅
WhatsApp Business Solution Terms now **ban "AI Providers" whose primary functionality is a general-purpose AI assistant** (ChatGPT, Perplexity and others were removed). Businesses using AI **to serve their own customers** are still allowed.

**Implications:**
- CookToFit must be a **nutrition and cooking service that uses AI**, not an open "ask me anything" bot.
- Keep the scope narrow (logging, plans, recipes, pantry, orders) and politely refuse off-topic requests.
- It's still Meta's "sole discretion", so **design for channel independence** and keep Telegram and the web app as fallbacks.
- EU, Italy and Brazil regulators are probing the rule, so it may change.

### What it takes (official Cloud API, recommended)
1. A Meta Business account, a WhatsApp Business account (WABA) and a **dedicated phone number** that isn't on regular WhatsApp. Business verification is needed for higher limits and a display name. The 5-recipient test number is enough for a private two-user pilot.
2. A webhook on FastAPI (Cloud Run) that receives messages, images and voice notes (OGG/Opus). Verify the `X-Hub-Signature-256` header and make handling idempotent.
3. Media handling: download through the Graph API, then send to Gemini (vision for photos, audio for voice notes in Hindi or English).
4. **Templates** for proactive messages: meal reminders, weekly review and cook-mode menus. Templates need Meta approval. Use the *utility* category.
5. **Interactive UI inside WhatsApp:**
   - Reply buttons (max 3), list messages (max 10 rows), location requests.
   - **WhatsApp Flows**: native multi-screen forms, ideal for onboarding, pantry and utensil setup, and portion confirmation.
6. **Rich output:** WhatsApp can't render charts, so send a server-rendered PNG card (macro rings, weekly trend) or a magic link to a lightweight **web dashboard**.

### Cost ✅ (per-message pricing since July 2025)
- Messages *you* receive are free.
- Replies within the 24-hour customer service window are free, including utility templates.
- Only templates sent **outside** the window are charged (utility costs a few paise to about ₹0.15 in India ⚠️ check the current rate card).
- For two people who message daily: about ₹0 to ₹50 a month.
- A BSP (Gupshup, AiSensy, Interakt, WATI, Twilio) adds a platform fee. Going direct with Cloud API is cheapest.

### Invite-only gate before launch (cost and virality control)
- **What costs money:** inbound messages are free. The real costs are AI calls, media handling and any template we send. So the gate sits **at the webhook, before any of that**.
- **Phone-bound allow-list:** the sender's WhatsApp number (verified by Meta) decides access. Invite codes are tied to that number, so forwarding a link, code, card or the number itself grants nothing.
- **Non-members:** silence by default, or one static "invite-only, reply WAITLIST" message every 30 days. No LLM call, no media download. Only a hashed attempt counter is stored, which also measures organic word-of-mouth before launch.
- **Admin-only invites**, a cap on active users, per-user rate limits and AI budgets, a global spend kill switch, no shareable links or QR codes in cards, and group messages ignored.
- At launch, flip `gate_mode=open`; the waitlist becomes wave 1. Details in ARCH §9.1 and PRD Epic L.

### Avoid
Unofficial libraries (`whatsapp-web.js`, `Baileys`) break ToS and risk the number being banned. Fine for a weekend hack, not a product.

### Architecture change: one brain, many channels
```
           ┌── WhatsApp (Cloud API webhook) ──┐
Channels → ├── Telegram bot (fallback)        ├→ Conversation Core (FastAPI)
           ├── Web dashboard / PWA            │    • identity: phone/email → user
           └── Expo app (later, optional)  ───┘    • session state + coach memory
                                                   • LLM agent w/ typed tools:
                                                     log_meal, confirm_portion, get_remaining,
                                                     recommend_dishes, add_pantry, scan_label,
                                                     set_goal, plan_week, order_instamart(MCP)
                                                   • deterministic engines (targets, DB lookup)
```
The LLM only routes and parses; numbers always come from the deterministic engines and the DB. The same core serves every channel, so moving from WhatsApp to an app later costs nothing.

### Hard parts specific to WhatsApp
- **Confirmation UX:** "Detected: 2 roti, 1 katori dal (180 g) ~410 kcal ✅ / ✏️ Adjust". Use buttons for the common case and a Flow for detailed edits.
- **Ambiguity:** keep the conversation state machine *around* the agent (awaiting_portion, awaiting_label_photo…).
- **Household:** the Cloud API is 1:1, not group-friendly. Each person chats separately, linked to a shared household.
- **Swiggy MCP OAuth:** needs Swiggy to whitelist your callback (see §2).
- **Privacy:** health data passes through Meta's transport (messages are end-to-end encrypted to the Cloud API, then decrypted on Meta's servers). Disclose this; keep lab reports in-app or web only.

### Recommendation
**WhatsApp for capture and nudges, a web dashboard for depth.** Logging (photo, voice, text), "what should I cook?", reminders and cook mode all happen in WhatsApp. Charts, goal history, pantry management and settings live in a small web app (Next.js or Expo Web). **Defer the native Android app** until the WhatsApp loop is proven. This cuts MVP scope roughly in half and removes app distribution entirely.

### About Muse / Instinct
I couldn't verify these products (search returned nothing). Please share links. If they are WhatsApp-native coaches, the questions to check are: which channel API they use, how they comply with the January 2026 rule, and their onboarding flow.
