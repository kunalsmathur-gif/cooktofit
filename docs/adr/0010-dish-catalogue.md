# ADR-010: A classified dish catalogue, computed from ingredients and searchable by the coach

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
People log and ask for *dishes* ("rajma chawal", "masala dosa"), not ingredients. Apps like HealthifyMe keep a large dish database, but most entries have no provenance, one fixed nutrition value per dish, and no link to cooking. We need a dish layer that the logger, the recommender and the meal planner all share, and that the coach agent can search (RAG) without ever inventing numbers (ADR-003).

## Decision
1. **Two layers.** `foods` (ingredients: IFCT, USDA, OFF branded products) and `dishes` (cooked items). A dish's nutrition is **computed** from `dish_ingredients` (grams per serving) using the ingredient layer, then cached; the LLM never writes nutrient values.
2. **Variants.** Each dish can have variants (`home`, `restaurant`, `low_oil`, user's own), differing mainly in fat and portion. Logging asks which one only when it materially changes calories.
3. **Classification** (filterable columns or tag arrays, not free text):
   - cuisine and region (Punjabi, South Indian, Gujarati, Bengali, Maharashtrian… plus global cuisines)
   - meal slot (breakfast, snack, lunch, dinner, dessert)
   - diet (veg, egg, non-veg, Jain, vegan) and allergens
   - cooking method, utensils, cooking modes, active and total time
   - main protein source; nutrition tags (high-protein, high-fibre, low-carb) derived from the computed values
   - serving units (katori, roti, piece, plate, ladle) with gram weights
   - names and aliases: English, Hindi (Devanagari), Hinglish spellings
4. **Retrieval for the coach (hybrid RAG).** Structured SQL filters first (diet, allergens, slot, utensils, time), then a ranked mix of `pg_trgm` name/alias similarity and pgvector embeddings over a short dish description. The coach receives candidate dishes with their computed nutrition and *chooses and explains*; it does not generate nutrition.
5. **Sources, in order.** Indian Nutrient Databank (INDB) recipes → USDA FNDDS for global mixed dishes → OFF for packaged ready-to-eat items → LLM-drafted recipes, accepted only after their ingredients resolve in the ingredient layer and computed values pass sanity checks.
6. **Growth from use (user-agnostic, shared).** An unknown dish logged by any user is decomposed by the LLM into ingredients and grams, computed, and saved with `status='derived'`. It becomes `verified` after repeated confirmations or an admin review, following the same arbitration rules as product submissions (ARCHITECTURE §5.6).
7. **Provenance on every number.** Each dish stores its source, method (`source_reported` or `computed`), confidence and version, and the UI shows it.

## Consequences
- One catalogue powers logging, "what should I cook?" and plans; recipes and nutrition can't drift apart.
- Accuracy depends on recipe quality; restaurant variants are estimates and labelled as such.
- INDB and IFCT licences must be rechecked before any commercial launch (ADR-004).
