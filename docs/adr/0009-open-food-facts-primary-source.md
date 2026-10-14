# ADR-009: Open Food Facts as the primary product source

- **Status:** Accepted
- **Date:** 2026-10-14

## Decision

- **Ingestion:** the daily Parquet export (Hugging Face `openfoodfacts/product-database`), filtered to products sold in India, is loaded into `products` with `source='off'`, `source_ref=<barcode>` and `licence='ODbL-1.0'`.
   - **Role of the other sources:** the other enrichment steps run only when Open Food Facts is missing a product or its data fails validation.
   - **Licence obligations (ODbL 1.0):**
     - Show the credit "Product data © Open Food Facts contributors, available under the Open Database License (ODbL)" with a link to openfoodfacts.org, in three places: the dashboard footer and About page, each product page that uses OFF data, and the repo `NOTICE`/README.
     - Keep OFF-derived rows identifiable, so the derived database can be published under ODbL if it is ever shared publicly (share-alike).
     - Product images are CC BY-SA. We don't store them, so this applies only if they are added later.
   - **Contribution back (Phase 2):** corrections and new products are submitted back through the OFF write API with a named app `User-Agent`.

## Context

See `docs/ARCHITECTURE.md` §11 and `docs/DEEP_DIVE.md`.
