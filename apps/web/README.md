# Web (Next.js)

The mobile-first dashboard and installable PWA. In Phase 0 it's a shell: brand theme, navigation (bottom bar on mobile, sidebar on desktop) and placeholder pages.

```bash
npm ci
npm run dev        # http://localhost:3000
npm run lint && npm run typecheck && npm test && npm run build
```

- Brand colours live in `src/app/globals.css`. `npm test` checks that they match `assets/brand/tokens.json`.
- `AGENTS.md` is maintained by Next.js. Read `node_modules/next/dist/docs/` before using new APIs.
