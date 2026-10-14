# PRD — CookToFit: Home-Cooking & Nutrition Coach

| | |
|---|---|
| **Status** | Draft v0.2 (WhatsApp-first revision, 2026-10-14) |
| **Owner** | Kunal Mathur |
| **Users (MVP)** | 2 (Kunal: Advanced persona; wife: Intermediate persona) |
| **Platforms** | **WhatsApp** (official Cloud API) for logging, coaching and nudges, plus a **web dashboard** (desktop and mobile browser). The native Expo app is deferred to Phase 2. |
| **AI provider** | Google Gemini (dedicated new API key) |
| **Budget** | ≤ ₹1,000/month running cost |

---

## 1. Problem statement
Home cooks who want to hit their nutrition goals end up juggling three or four disconnected tools:
- a calorie tracker (HealthifyMe, MyFitnessPal)
- recipe sites or YouTube
- a mental list of what's in the fridge
- a guess at how much protein or iron they actually need

None of these tools knows **what's in my kitchen, what equipment I have, how much time I have, and what my body still needs today**, all at once. Indian home food makes it worse: mixed plates, katori portions and hidden ghee or oil make photo-based tracking unreliable.

## 2. Vision
> "Tell me what to cook with what I have, so that I hit my goals, and make logging what I ate effortless."

## 3. Goals and non-goals
### Goals (MVP)
- **G1.** Each user gets a personalised, explainable set of daily macro and micro targets, which they can override.
- **G2.** Meals are recommended for every meal slot to fit the targets.
- **G3.** "What can I cook now?" works from pantry, time, utensils and cooking mode, and returns a recipe plus a vetted video.
- **G4.** A meal can be logged from a photo in ≤ 15 s, including portion confirmation.
- **G5.** Manual logging (dish + quantity, or raw macros) takes ≤ 10 s for common items.
- **G6.** Two users share one kitchen (household).
- **G7.** Everything daily happens in **WhatsApp** (photo, voice or text). There's nothing to install.
- **G8.** Branded packaged products resolve to their **exact label nutrition and serving size** (e.g. "1 scoop = 33 g, 24 g protein").
- **G9.** Missing recipe ingredients can be added to a **Swiggy Instamart** cart, and Instamart orders auto-fill the pantry.
- **G10.** Goal history is preserved over months and years; past days never change when goals or food data change.

### Non-goals (MVP)
- Medical diagnosis or clinical diet prescription (the app gives guidance only and carries a disclaimer).
- A native mobile app, Play Store release, payments or a social feed.
- Wearable or CGM integration (Phase 2+).
- Restaurant food ordering (Phase 2). Blinkit, Zepto and BigBasket ordering (Phase 2, deep links).
- Open-ended general chat. The WhatsApp bot stays scoped to nutrition, cooking and groceries, in line with Meta's Business Solution Terms (AI-provider clause, effective 15 Jan 2026).
- Scraping quick-commerce apps.

## 4. Personas
| Persona | Description | Key need |
|---|---|---|
| **Kunal (Advanced)** | Working professional who trains. Tracks macros and uses branded supplements. Limited time on weekdays. | Full macros and micros, training- vs rest-day targets, exact supplement nutrition, fast logging, own overrides |
| **Partner (Intermediate)** | Watches calories and protein roughly. Has different targets (e.g. iron and calcium focus). Shares the kitchen. | Calories and protein first, other macros optional; personalised portions from the same shared meals |
| **Beginner** (future users) | Wants to eat healthier and doesn't know macros | No numbers at first: plate method, katori language, habit goals; graduates to numbers over time |
| **Household cook** (indirect, Phase 2) | Cooks some meals and prefers Hindi or a regional language | Clear menu and instructions |

## 5. User stories & requirements

Priority: **P0** = MVP must-have · **P1** = MVP nice-to-have · **P2** = Phase 2

### Epic A: Profile & nutrition targets
| ID | Story | Priority |
|---|---|---|
| A1 | As a user I enter age, sex, height, weight, activity level and goal (lose, maintain, gain, recomposition), with an optional pace | P0 |
| A2 | The app computes calories (Mifflin-St Jeor × activity ± goal delta), protein, carbs, fat and fibre | P0 |
| A3 | The app computes micronutrient targets (iron, calcium, Vit D, B12, folate, zinc, magnesium, potassium, sodium cap, Vit C, Vit A, omega-3) from ICMR-NIN 2020 RDA/EAR by age, sex and physiological state | P0 |
| A4 | I can override any target, or enter a whole goal set myself (e.g. from my dietitian) | P0 |
| A5 | Each target has a "Why this number?" explanation | P1 |
| A6 | I set my diet type (veg, eggetarian, non-veg, per day of week, e.g. "veg on Tuesdays"), allergies, dislikes and cuisines I like | P0 |
| A7 | Targets adapt from my weight trend (adaptive TDEE) | P2 |
| A8 | I upload a blood-test PDF; deficiencies are flagged and become focus nutrients | P2 |
| A9 | Onboarding asks about 8 core questions, then **one persona question** ("How do you think about food today?"). That answer branches into Beginner, Intermediate or Advanced follow-ups, decides which numbers I see, and sets the coaching language | P0 |
| A10 | Advanced users enter body-fat %, training days and their current macros or TDEE, and get **training- vs rest-day targets** | P0 |
| A11 | Goal types: outcome (weight or recomposition), performance, health (with a disclaimer) and habit. One primary goal and up to two secondary goals | P1 |
| A12 | Goals are **versioned in phases** (e.g. cut for 12 weeks, then maintain). Each day's targets are saved, so history never changes | P0 |
| A13 | Safety: calorie floors (~1,200 kcal for women, ~1,500 for men), maximum loss of ~1% of body weight per week, and red flags (under 18, BMI < 18.5 with a weight-loss goal, pregnancy, kidney disease with high protein, a short eating-disorder screen) block aggressive targets | P0 |
| A14 | Further questions come gradually over the first two weeks (sleep, schedule, budget, fasting days, dislikes); Beginners are offered a "graduation" to numbers | P1 |

**Acceptance criteria (A2/A3):** given the same inputs, outputs are deterministic. Values match a reference spreadsheet within ±1%. Changing weight recalculates within 1 s.

### Epic B: Kitchen setup (pantry, utensils, cooking modes)
| ID | Story | Priority |
|---|---|---|
| B1 | I add pantry items quickly through searchable chips, Hindi or English names, or voice ("add paneer, spinach, 2 dozen eggs") | P0 |
| B2 | Items have an optional quantity and expiry date; items about to expire are highlighted | P1 |
| B3 | I tick the utensils I own (pressure cooker, kadhai, tawa, non-stick pan, blender, mixer-grinder, idli stand, baking tray…) | P0 |
| B4 | I tick my cooking modes (gas, induction, microwave, OTG/oven, air fryer, electric kettle, Instant Pot, no-cook) | P0 |
| B5 | The pantry is shared by the household; changes sync to both users | P0 |
| B6 | Cooking a recipe offers to deduct the ingredients used from the pantry | P1 |
| B7 | The pantry fills automatically from grocery orders or receipt photos | P2 |

### Epic C: Recommendations
| ID | Story | Priority |
|---|---|---|
| C1 | "What should I cook?": I enter the meal slot, time available (e.g. 20 min) and optionally a mood or cuisine, and get the top 5 dishes | P0 |
| C2 | Recommendations respect diet, allergies, utensils, cooking modes and time as **hard** constraints | P0 |
| C3 | Ranking favours fit to the **remaining** daily macro and micro budget, pantry coverage, variety and past ratings | P0 |
| C4 | Each card shows kcal and P/C/F per serving, % of remaining budget, pantry coverage ("missing: coriander") and the micronutrient highlights | P0 |
| C5 | Daily plan: suggestions for breakfast, snack, lunch, dinner and dessert that fit the day's targets together | P0 |
| C6 | "Swap" any suggestion; the rest of the day rebalances | P1 |
| C7 | "Close the gap": in the evening, suggest a snack or dinner that fixes today's shortfall (e.g. +25 g protein, +5 mg iron) | P1 |
| C8 | Desserts are suggested within budget (healthier versions are fine) | P0 |
| C9 | Household plan: one dish for both of us, with different portion sizes per person | P1 |
| C10 | Weekly meal-prep plan plus a consolidated grocery list | P2 |

### Epic D: Recipes & videos
| ID | Story | Priority |
|---|---|---|
| D1 | A recipe has ingredients scaled to servings, steps, time, utensils, cooking mode and nutrition per serving | P0 |
| D2 | A recipe adapts to my equipment (e.g. "air-fryer version of samosa", "no-oven cake in pressure cooker") | P0 |
| D3 | 1–3 YouTube videos per recipe, ranked by a trusted-creator allow-list plus engagement and sentiment | P0 |
| D4 | I can rate, favourite and add notes to a recipe ("less salt next time") | P1 |
| D5 | Cooking mode: full-screen steps, keeps the screen awake, built-in timers | P1 |
| D6 | Hands-free voice step-through | P2 |
| D7 | Send the recipe to the household cook in Hindi or a regional language via WhatsApp | P2 |

### Epic E: Photo logging
| ID | Story | Priority |
|---|---|---|
| E1 | I take a photo, or pick one from the gallery, and assign a meal slot (auto-suggested from the time of day) | P0 |
| E2 | The app detects each dish on the plate (multi-item), with a confidence score | P0 |
| E3 | The app estimates the portion in grams and shows it in natural units (katori, roti count, piece, ladle, cup) | P0 |
| E4 | Confirm & Adjust: I can rename a dish, change the portion with sliders, add missed items, and set an "extra oil/ghee" toggle | P0 |
| E5 | Nutrition is computed from the food DB (not the LLM) and logged | P0 |
| E6 | The app learns my corrections (e.g. my katori = 180 ml, my roti = 35 g) | P1 |
| E7 | Works offline: the photo is queued and analysed when back online | P1 |
| E8 | "Log for both": one photo split between the two users by portion | P1 |

**Acceptance criteria:** median time from photo to logged ≤ 15 s. On an internal eval set of 100 home-cooked plates:
- Top-1 dish identification ≥ 80%.
- Calorie error after user confirmation ≤ 15% median.

### Epic F: Manual logging
| ID | Story | Priority |
|---|---|---|
| F1 | Natural-language entry, typed or spoken: "2 rotis, 1 katori rajma, half cup curd" | P0 |
| F2 | Search the food DB with Hindi/English aliases, plus recents and favourites | P0 |
| F3 | Raw entry of kcal, P, C and F (plus optional micros) for custom items | P0 |
| F4 | Barcode scan for packaged foods (Open Food Facts) | P1 |
| F5 | Copy a meal from yesterday or a template ("my usual breakfast") | P1 |
| F6 | Save my own recipe and log a portion of it | P1 |

### Epic G: Dashboard & insights
| ID | Story | Priority |
|---|---|---|
| G1 | Today: calorie ring, macro bars, top micronutrient bars, meals logged | P0 |
| G2 | Remaining budget is visible everywhere recommendations appear | P0 |
| G3 | Weekly view: averages, micronutrient gaps, streaks | P1 |
| G4 | Weekly AI review (wins, gaps, one focus for next week) | P2 |
| G5 | Switch to view my partner's dashboard (with consent) | P1 |

### Epic H: WhatsApp channel (MVP primary interface)
| ID | Story | Priority |
|---|---|---|
| H1 | I message the CookToFit WhatsApp number. My phone number is linked to my account, and my household is linked too | P0 |
| H2 | I send a **photo** of my plate and get a draft ("2 roti, 1 katori dal ≈ 410 kcal") with ✅ Log and ✏️ Adjust buttons | P0 |
| H3 | I send a **voice note** in Hindi or English, or text ("2 roti + 1 scoop whey"), and it's parsed and confirmed the same way | P0 |
| H4 | Onboarding, pantry and utensil setup, and detailed portion edits use **WhatsApp Flows** (native forms) | P0 |
| H5 | "What should I cook?" returns the top 3 dishes as a list message. Picking one sends the recipe, a YouTube link and the missing ingredients, with an "Add to Instamart cart" button | P0 |
| H6 | "How am I doing?" returns a **PNG summary card** (macro rings, micronutrient gaps) plus a magic link to the web dashboard | P0 |
| H7 | Proactive nudges use approved **utility templates**: meal reminders and an evening "remaining budget" message. I can turn them off | P1 |
| H8 | Off-topic requests get a polite decline that points back to food, cooking and goals | P0 |
| H10 | **Share my stats with people who aren't users:** "Share today", "share my week" or a 📤 button gives a branded **ShareCard PNG** (today or week adherence, streak, milestone, recipe I cooked, or a plan for the cook). I forward it natively in WhatsApp. Privacy defaults show percentages and streaks only; I can opt in to more fields. An optional expiring read-only web link is available | P1 |
| H11 | Shares contain **no link, QR code or call to action to join** before launch. A referral call to action is behind a launch flag | P0 |
| H9 | Coach memory: the bot remembers stable facts about me ("dislikes karela", "whey = Whole Truth chocolate") and uses them | P1 |

**Acceptance criteria:** photo to draft reply in ≤ 8 s (p50). Webhooks are signature-verified and idempotent. Every message is free inside the 24-hour customer-service window.

### Epic L: Invite-only access (pre-launch cost and virality control)
| ID | Story | Priority |
|---|---|---|
| L1 | As admin, I invite someone by **phone number** from the dashboard (name, household, expiry). They get a single-use `wa.me` link and code. Only that number can activate it | P0 |
| L2 | Anyone not on the allow-list who messages the number gets **no AI processing at all**: no media download, no LLM call, no data stored apart from a hashed attempt counter. Default is silence; optionally one static "invite-only, reply WAITLIST" message every 30 days | P0 |
| L3 | Forwarding an invite link, code, recipe card or summary to another person does **not** grant access. Codes are bound to the invited phone number, and cards carry no "chat with us" link or QR code before launch | P0 |
| L4 | Members can't invite others before launch (flag `invites_per_member = 0`, adjustable later for a controlled beta) | P0 |
| L5 | Caps: maximum active users, per-user daily message, photo and URL limits, a per-user monthly AI budget, and a global monthly spend kill switch (alert at 80%, pause at 100%) | P0 |
| L6 | As admin, I can see gate stats (denied attempts, distinct unknown numbers, waitlist size), revoke a member instantly and switch `gate_mode` to open at launch | P1 |
| L7 | A non-member who replies WAITLIST is stored, with consent, and notified at launch | P2 |

**Acceptance criteria:** a non-member message costs ₹0 in AI and produces no row in any user-data table. Activating with a valid code from a different number fails. Group messages are ignored.

### Epic N: Web portal (desktop and mobile)
| ID | Story | Priority |
|---|---|---|
| N1 | I can use the full portal on **mobile browsers (responsive, ≥360 px)** and desktop, and install it to my home screen (PWA) | P0 |
| N2 | I sign in with **mobile OTP**, delivered as a WhatsApp authentication template (SMS fallback after launch) | P0 |
| N3 | I can also sign in with **Google**, linked to my account | P0 |
| N4 | In WhatsApp, "Open dashboard" gives me a one-tap signed link (single-use, 10 minutes) | P0 |
| N5 | Only invited (allow-listed) members can sign in by any method. OTP sends are rate-limited and OTPs expire after 5 minutes. I can sign out of all devices | P0 |

**Acceptance criteria:** Lighthouse mobile score ≥ 90 for performance and accessibility on Today and History. No horizontal scrolling at 360 px. WCAG AA contrast with the brand tokens.

### Epic M: Admin console (hygiene, growth, spend, activity)
| ID | Story | Priority |
|---|---|---|
| M1 | **Spend:** I see AI, WhatsApp and infra cost by provider, feature and user. It shows cost per active user and per logged meal, a month-end forecast and budget burn, with alerts at 80% and 100% | P0 |
| M2 | **Access & growth:** invite → activation → onboarding → activated-user funnel, waitlist trend, denied attempts and distinct unknown numbers per week (word-of-mouth signal), with gate controls (caps, revoke, `gate_mode`) | P0 |
| M3 | **System hygiene:** webhook errors and latency, background job health with last success time, LLM error rate, WhatsApp quality rating and template status, Swiggy token expiry, YouTube quota | P0 |
| M4 | **Data hygiene:** catalogue source mix, validation failures, contested-submission review queue (approve/reject), submitter reputation and quarantines, OFF sync status, most-logged products that still use generic estimates | P1 |
| M5 | **User activity:** DAU/WAU/MAU, stickiness, D1/D7/D30 retention cohorts, logging coverage, streaks, channel mix, feature adoption, recommendation acceptance, photo-to-confirm time | P1 |
| M6 | **Safety & commerce:** safety-rule triggers (counts), cart proposals vs confirmations, cap hits, blocked order attempts | P1 |
| M7 | **Privacy:** admin views are aggregate or operational only. No meal contents, photos, body metrics, lab results or chat text. Viewing one user's health data needs break-glass access with a reason, a time limit and an audit entry that the user can see | P0 |
| M8 | Alerts reach me on WhatsApp and email: budget, error spikes, missed jobs, quality-rating drop, quarantines, commerce cap hits | P1 |

**Acceptance criteria:** every LLM call and template send has a cost row. Spend totals reconcile with provider invoices to within 5% monthly. Admin routes are blocked for non-admins by RLS and by server checks.

### Epic I: Branded product catalogue
| ID | Story | Priority |
|---|---|---|
| I1 | The catalogue **builds itself, with no user effort**. It's seeded from my Instamart orders, the Planner's shopping needs, about 30 fitness and health D2C brands, Open Food Facts India (about 10.7k products) and FMCG staples. Each product has label nutrition and a **serving definition** | P0 |
| I1b | Each SKU is enriched automatically by a waterfall: Open Food Facts → public product-page text → back-of-pack image OCR → brand site → grounded web search → generic fallback | P0 |
| I1c | Values are validated automatically (energy check, serving consistency, category ranges, agreement between sources). Each product gets a confidence score and is versioned when the brand reformulates | P0 |
| I2 | I scan or send a **barcode** and it resolves via the catalogue, then Open Food Facts | P0 |
| I3 | **Last-resort user input:** if every automated source fails (or only a generic estimate exists), the coach logs the generic estimate with a badge and offers once: *"Send a photo of the nutrition label or a product link to make this exact."* I can send a **label photo** (WhatsApp or web upload) or a **product URL** (any public page: brand site, BigBasket, Zepto, Amazon). It's parsed, validated (energy check, serving consistency), shown as a draft for me to confirm, then saved to the **shared catalogue** (user-agnostic: every future user benefits) and **my past logs of that product are re-computed**. It's never mandatory. I can also send a photo or link proactively to correct any product | P1 |
| I4 | Logging "1 scoop whey" uses *my* product, not generic whey | P0 |
| I5 | **Open Food Facts is the primary source.** Nutrient priority: user-verified → Open Food Facts (if it passes validation) → label (image OCR) → product-page text → brand site → grounded search → generic → user-supplied photo/URL (last resort, on request). Once I confirm a user-supplied value it becomes *user-verified* and ranks first. Other sources only fill gaps or replace Open Food Facts values that fail validation. Generic fallbacks show a badge | P0 |
| I8 | **Dispute any value ("Not right?"):** on any product or logged item (WhatsApp button or dashboard), I can contest the nutrition and send a label photo or product URL as evidence. Nutrients are re-extracted, validated and compared with the current value; I see old vs new before confirming, and my logs are re-computed | P1 |
| I9 | **Every successful user photo/URL extraction is stored in the shared catalogue for next time**, independent of who sent it. It's versioned with provenance (source, submission id). Guardrails: identity check (the photo/page must match the product, otherwise a new product/variant is created), validation, and arbitration: a clear validated label photo becomes a new version; weaker evidence stays "contested" (applies to the submitter only) until a second source agrees. Submitter identity is kept only in the audit trail | P1 |
| I6 | **Credit to Open Food Facts:** any product whose data came from Open Food Facts shows "Data: Open Food Facts (ODbL)" on its detail view in the dashboard. The dashboard footer and About page show the full licence notice. WhatsApp product cards carry a short "via Open Food Facts" | P0 |
| I7 | Corrections and missing products we find are **contributed back** to Open Food Facts (Phase 2; opt-in, via its API) | P2 |

### Epic J: Swiggy Instamart (official MCP)
| ID | Story | Priority |
|---|---|---|
| J1 | I connect my Swiggy account once (OAuth) | P0 |
| J2 | Missing ingredients for a chosen recipe are matched to Instamart products (preferring brands I already own) and added to my cart. I review before ordering (COD) | P0 |
| J3 | My Instamart orders auto-fill the pantry with brand-specific products | P1 |

**Dependency:** Swiggy has to whitelist our OAuth callback. Fallback for personal use: a one-time localhost OAuth, with the token refreshed on the server.

### Epic K: Advance meal planning (day / week / month) and shopping list
For early planners: plan ahead for any number of people, then buy only what the pantry lacks.

| ID | Story | Priority |
|---|---|---|
| K1 | I ask for a plan for **a day, a week or a month** (e.g. "Plan next week, 4 people, lunch and dinner only") | P0 day/week · P1 month |
| K2 | I set **who's eating**. Household members use their own targets. **Guests** are counted as adult, child or light eater with standard portions. Headcount can vary by day ("Saturday: 6 people") | P0 |
| K3 | Planning rules: diet rules per day (e.g. veg on Tuesdays), cooking-time limit on weekdays vs weekends, utensils and modes, cuisine mix, no repeats within N days, fasting or festival days, budget per day or week | P0 |
| K4 | **Batch cooking and leftovers:** "cook once, eat twice" (dinner rajma becomes the next day's lunch) and weekend meal prep | P1 |
| K5 | Each person's portions are sized to their targets; guests get standard portions | P0 |
| K6 | **Consolidated shopping list** = total planned ingredients − pantry − items already set aside for other planned meals. Rounded up to real pack sizes, using my preferred brands | P0 |
| K7 | **Purchases are timed for freshness:** non-perishables are bought upfront; perishables (veg, dairy, meat) are split into top-up carts timed before they're needed (e.g. every 3–4 days). A month plan never buys a month of spinach on day 1 | P0 |
| K8 | One tap sends the list (or the next top-up) to the **Instamart cart** through the commerce agent, with the usual signed confirmation. Before each scheduled top-up, a reminder says "Week 2 veggies cart is ready" | P0 |
| K9 | **Living plan:** I can swap a meal, skip one, or mark that I ate out, and the remaining plan, shopping list and macros adjust automatically | P1 |
| K10 | The plan shows in WhatsApp as a summary card plus "today's menu" each morning. The full calendar grid and shopping list are on the web, with drag-to-swap | P0 |
| K11 | Cook-mode export: send the day's or week's menu to the household cook in Hindi or a regional language | P2 |

**Acceptance criteria:**
- A week plan for 2–6 people generates in ≤ 20 s.
- Each household member's daily average is within ±10% of calories and ≥ 90% of protein.
- The shopping list adds no items already in stock or set aside for other planned meals.
- Perishables are bought no more than 4 days before use (configurable).

## 6. Phase 2 differentiators (backlog)
| Feature | Description |
|---|---|
| **Order instead of cook** | A sandboxed commerce agent uses the Swiggy Food MCP (official) and Zomato MCP (⚠️ verify). It ranks dishes by fit to the remaining macros (estimated via INDB, with a restaurant oil factor) and orders only after a signed confirmation. The delivered meal becomes a pre-filled log draft. |
| **More grocery platforms** | Instamart is in the MVP (Epic J). Zepto, Blinkit and BigBasket get deep links only (no official MCP; scraping not allowed) |
| **Auto pantry** | Pantry updates from order history and receipt OCR; expiry-driven "use it up" |
| **Meal-prep planner** | Weekly plan, batch-cooking schedule, grocery list |
| **Cook/maid mode** | WhatsApp the menu and steps in Hindi or a regional language, with a voice note |
| **Health Connect** | Weight, steps and workouts drive an adaptive TDEE |
| **Blood report** | PDF parse, deficiency flags, re-weighted recommendations |
| **Restaurant menu photo** | "What should I order here to stay on track?" |
| **Fasting/festival modes** | Navratri, Ekadashi, Ramadan, intermittent fasting windows |
| **Leftover remix** | Turn leftovers into new dishes |
| **Cost per meal** | Grocery budget tracking |
| ~~WhatsApp logging bot~~ | Moved to the MVP (Epic H) |
| **Smart scale / CGM** | Precise portions; glycemic response per dish |

## 7. Competitive differentiation
| Gap in the market | How CookToFit addresses it |
|---|---|
| Trackers don't help you cook; recipe apps don't track | One loop: pantry → recommendation → recipe → log |
| Photo AI fails on Indian mixed plates and hidden fat | Indian-tuned prompt, katori units, oil toggle, learning from corrections |
| Micronutrients are ignored | ICMR-NIN micronutrient targets plus "close the gap" suggestions |
| Single-user apps vs. shared kitchens | Household: one dish, split portions per person |
| Equipment-agnostic recipes | Hard constraints on utensils and cooking mode, plus recipe adaptation |
| Random YouTube results | Trusted-creator allow-list and quality scoring |

## 8. UX principles
- **Two-tap default paths:** log a usual meal, or ask "what to cook".
- Show **remaining budget** rather than totals consumed.
- Indian units first, grams on tap.
- Explain every number.
- Accessible on desktop with a keyboard; one-handed on mobile.

### Key surfaces
**WhatsApp (daily use)**
1. Onboarding Flow (core questions, persona branch, targets summary)
2. Log: photo, voice or text, then a draft with ✅/✏️ (portion-editor Flow)
3. Cook: "what's for dinner?", a list of 3 dishes, then recipe, video and missing items, with 🛒 Instamart
4. Cart proposal: items, bill and ETA, with ✅ Place (COD) / ✏️ / ✖
5. Summary card (PNG) on request and in the evening nudge
6. Pantry/Kitchen Flow

**Web dashboard (depth)**
1. Today (rings, micronutrient bars, remaining budget)
2. History and goals timeline (phases, targets over time, weight trend)
3. Pantry, kitchen and products (branded catalogue, label verification queue)
4. Plan (day/week)
5. Settings (persona, overrides, household, integrations such as Swiggy, privacy and export)

## 9. Success metrics (2-user pilot, 8 weeks)
- Days logged per week per user ≥ 6.
- Share of meals logged via photo ≥ 50%.
- Share of home-cooked meals that came from an app recommendation ≥ 40%.
- Days within ±10% of calorie target and ≥ 90% of protein target ≥ 4 per week.
- Median time to log ≤ 15 s (photo) and ≤ 10 s (repeat or manual).
- Gap in the 3 focus micronutrients reduced week-over-week.
- Running cost ≤ ₹1,000/month.

## 10. Non-functional requirements
- **Performance:** dashboard loads in < 1 s from cache; recommendations return in < 5 s; photo analysis takes < 10 s.
- **Offline:** WhatsApp queues messages on the phone. The web dashboard is read-only from cache.
- **WhatsApp latency:** photo to draft ≤ 8 s p50; text reply ≤ 4 s p50. Cloud Run warm during waking hours.
- **Commerce safety:** orders are placed only on a signed, single-use, user-tapped confirmation; per-order and daily ₹ caps; dry-run by default until tested.
- **Privacy:** health data is private per user. Partner visibility is opt-in. Photos are stored privately with signed URLs. India region where possible. A data export and delete option exists.
- **Security:** WhatsApp numbers and every web sign-in method (mobile OTP via WhatsApp, Google, WhatsApp link) limited to allow-listed members; webhook HMAC verification; row-level security on every table; API keys only on the server; Swiggy tokens encrypted and readable only by the commerce module.
- **Reliability:** if Gemini fails, fall back to manual logging; the YouTube cache means quota exhaustion never blocks a recipe.
- **Observability:** every AI call logged with its tokens, latency and cost; per-user daily AI cost cap.
- **Compliance (Phase 3):** DPDP Act 2023 consent, a medical disclaimer, and licence review for food data.

## 11. Assumptions & dependencies
- Gemini 2.5 Flash vision is good enough with structured prompts. This is to be validated with a 100-plate eval set in Phase 1.
- IFCT 2017 and INDB data are usable for personal and non-commercial use; licensing must be re-checked before scaling.
- YouTube Data API quota of 10k units/day is enough with caching.
- The Swiggy MCP (Instamart, Food, Dineout) is official ✅. Our OAuth callback needs Swiggy's whitelisting; fallback is a one-time localhost OAuth for personal use. Zomato MCP: ⚠️ to verify. Blinkit and Zepto: no official API.
- Meta allows AI used by a business to serve its customers, but bans general-purpose AI assistants (from 15 Jan 2026). CookToFit stays narrowly scoped.
- Open-source data and licences are listed in ARCHITECTURE.md §5 (IFCT packaging is AGPL, INDB has no licence, OFF is ODbL, USDA is public domain).

## 12. Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Photo portion error | Wrong tracking leads to lost trust | Confirm step, reference objects, personal calibration, DB-computed nutrition |
| Recipe hallucination (wrong steps or nutrition) | Bad food or wrong numbers | Validate ingredients against the DB; compute nutrition deterministically; prefer the curated catalogue |
| Logging fatigue | Churn | Repeat-meal one-tap, NL entry, photo-first |
| AI cost creep | Over budget | Flash-Lite for parsing, caching, per-user caps |
| Data licensing at scale | Blocks commercial launch | Legal review in Phase 3; USDA (public domain) fallback |
| Meta changes or enforces the AI policy against us | Channel loss | Narrow scope, shared conversation core, web dashboard always available, Expo app in Phase 2 |
| Swiggy MCP access or OAuth whitelisting denied | No auto-cart | Deep link with a copy-paste list; localhost OAuth for personal use |
| Wrong item or wrong quantity ordered | Money wasted | Signed human confirmation, caps, dry-run default, cart diff shown before placing |
| Prompt injection via menus or product text | Agent misuse | Sandboxed commerce agent; third-party text treated as data only; fixed tool permissions |

## 13. Release plan
| Phase | Scope |
|---|---|
| **0: Foundations** | Repo, FastAPI Brain, Next.js web, Supabase, Meta WABA and number, webhook, CI |
| **1: MVP** | P0s of epics A–K (WhatsApp, branded catalogue, Instamart in dry-run, then live), then the P1s |
| **1.5: Pilot** | 8-week usage by the 2 users, eval set, tuning |
| **2: Differentiators** | Section 6 backlog, prioritised by pilot learnings |
| **3: Scale** | Multi-tenant, Play Store, subscriptions, compliance |

## 14. Open questions
1. Health inputs for the MVP (Health Connect, blood reports): currently deferred to Phase 2.
2. ~~Branding~~ — resolved: see `brand/final/README.md` (tagline "Every meal is a rep.", Espresso & Terracotta, Monoline Flex Pan). Trademark search still pending.
3. Is a household cook in the loop today? This affects the priority of cook mode.
5. instinct.com benchmark: blocked by the corporate proxy; review on a personal network before designing the WhatsApp flows.
4. Should the dashboard show a partner's data by default?
