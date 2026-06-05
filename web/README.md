# KellerWatt — honesty page (web)

A single static page (Vite + React + TS) that reads the engine's **sanitized**
results JSON and presents: the validated perfect-foresight ceilings, the causal
walk-forward estimate, the conservative `exemption_lost` case, and what is still in
diligence. Brand per `../DESIGN.md`.

## Data flow

```
engine  →  dist/sanitized/sim_results.json  →  npm run sync:data  →  src/data/sim_results.json  →  page
```

The **real** artifact (`dist/real/`) is gitignored and never referenced here. The
build runs a leak scan (`scripts/scan-sanitized.mjs`) that fails if any
confidential marker reaches the public bundle.

> Note (flagged for confirmation): the validated ceilings €61.1 / 68.3 / 77.3 are
> public, market-derived figures and the honest finding the page exists to show, so
> they are intentionally kept in the sanitized bundle. The leak scan targets
> genuinely-confidential inputs (real CapEx, real fee schedule, real IRR), not the
> ceilings.

## Commands

```bash
npm install
npm run sync:data     # copy the latest sanitized artifact in (run engine export first)
npm run dev           # local dev server
npm run verify        # typecheck + tests + leak scan
npm run build         # typecheck + bundle + leak scan  ->  dist/
npm run preview       # serve the built bundle
```

Regenerate the data from the repo root:

```bash
.venv/bin/python -m engine.export   # writes dist/sanitized/sim_results.json
cd web && npm run sync:data
```

## Deploy

`npm run build` emits a self-contained static `dist/` (relative `base`, self-hosted
fonts — no Google CDN, GDPR-friendly). Deploy `dist/` to GitHub Pages or Vercel as a
static site. The build aborts if the leak scan fails, so a confidential leak can
never ship.
