# ADR-007: Automated branded-catalogue pipeline

- **Status:** Accepted
- **Date:** 2026-10-14

## Decision

The branded catalogue is built by an **automated multi-source enrichment pipeline**: OFF mirror, polite public product-page crawling (no login, robots.txt honoured), back-of-pack image OCR, brand sites, and grounded search with consensus validation. No logged-in or private-API scraping, no CAPTCHA bypass. Ordering uses official MCPs only. GS1 DataKart when commercial.

## Context

See `docs/ARCHITECTURE.md` §11 and `docs/DEEP_DIVE.md`.
