# KellerWatt Interactive Playground — Design Spec

## Overview

Add an interactive "Playground" page where the user drags sliders to vary battery
and economic parameters and sees live-solved results (ceiling spread, causal
spread, IRR, payback, etc.). The frontend (React on GitHub Pages) calls a Python
FastAPI backend hosted on Hugging Face Spaces. The page auto-warms the backend
so cold-start latency is hidden.

## Architecture

```
GitHub Pages (nikerane.github.io/kellerwatt-sim)
  /index.html         honesty page (existing)
  /methodology.html   formula traceability (existing stub)
  /playground.html    NEW — interactive sliders

Hugging Face Spaces (Nikerane/kellerwatt-engine)
  POST /solve  → runs engine, returns fresh results
  GET  /health → pong (warm-up on page load)
```

- Frontend: React + Vite multi-page build (adds `playground.html` entry).
- Backend: FastAPI with the Python engine baked into the Docker image.
- Price data: cached in the image (bundled at build time, no live API calls).
- Communication: `fetch()` from the React page to `https://nikerane-kellerwatt-engine.hf.space`.

## Slider Parameters

| Parameter | Default | Min | Max | Step | Unit |
|---|---|---|---|---|---|
| Battery capacity | 200 | 50 | 500 | 25 | kWh |
| Power rating | 50 | 25 | 250 | 25 | kW |
| Round-trip efficiency | 90 | 75 | 95 | 5 | % |
| Assumed spread | 80 | 20 | 120 | 5 | €/MWh |
| Daily cycle cap | 1.5 | 0.5 | 3.0 | 0.25 | cycles/day |
| Grid energy fee | 0 | 0 | 50 | 5 | €/MWh |
| §118(6) exemption | Retained | — | — | Toggle | — |

All stepped — no fractional values the engine can't solve.

## Page Design

### Layout
- **Top bar** — sliders in a horizontal scrollable band (or wrap onto 2 rows on narrow screens). Mono labels + current value readout.
- **Hero** — Ember couplet: "Change the assumptions. Watch the numbers move."
- **Main panel** — CaseTable (4 columns: assumed/ceiling/causal/conservative) updates live after each solve.
- **Side info** — spread chart or single-year bar chart showing the solved result vs. base case.

### UX states
1. **Warming** — "Engine: waking up…" pill (subtle animated ember dot). Fires on mount, waits for health check response.
2. **Ready** — "Engine: ready ✓" (green dot). User hasn't dragged yet.
3. **Solving** — spinner on the results area. Disabled sliders during fetch to prevent queue pile-up.
4. **Solved** — results rendered. Sliders re-enabled.
5. **Error** — "Couldn't reach the engine" with a retry button.

### Warm-up strategy
On page load, a `fetch(GET /health)` fires immediately. The page renders the
default (baked-in) results while the backend cold-starts (~30s worst case).
By the time the user finishes reading the hero and scans the default results,
the engine is warm. The health check polls every 5s until it succeeds, then
shows "Ready".

### Debounce
Slider drags are debounced 500ms — the user can scrub freely without firing a
request per step. Only the last settled value triggers a solve.

## Backend API

### POST /solve

Request:
```json
{
  "battery": {"capacity_kwh": 200, "power_kw": 50, "rte": 0.90},
  "spread_eur_mwh": 80.0,
  "cycles_per_day": 1.5,
  "grid_fee_eur_mwh": 0,
  "exemption": "retained"
}
```

Response:
```json
{
  "schema_version": "1.1.0",
  "ceiling": {
    "spread_eur_mwh": [61.1, 68.3, 77.3],
    "gross_eur": [5500, 6150, 6960],
    "cycles_ac": [1.12, 1.25, 1.41]
  },
  "causal": {
    "spread_eur_mwh": [19.2, 20.8, 27.1],
    "gross_eur": [1728, 1872, 2439],
    "cycles_ac": [0.45, 0.49, 0.56]
  },
  "scenarios": {
    "retained": {"implied_spread": 27.1, "irr": null, "payback": null},
    "lost": {"implied_spread": 19.2, "irr": null, "payback": null}
  }
}
```

IRR/payback stay null (same sanitization policy).

### GET /health

Returns `{"status":"ok"}`. Used for warm-up ping.

## Backend Implementation

- `backend/main.py` — FastAPI app, ~80 lines. Imports engine modules.
- `backend/Dockerfile` — Python 3.11, installs deps + engine, `uvicorn main:app`.
- `backend/requirements.txt` — same pins as pyproject.toml + fastapi + uvicorn.
- Price data: baked into the image via `COPY engine/data/cache /app/engine/data/cache`.
- No GPU needed. CPU-only HF Space free tier is sufficient.

## Deploy

### Initial setup (one-time)
```bash
hf auth login                    # link HF account
hf space create kellerwatt-engine --sdk docker  # create Space
```

### Per-release
```bash
# Backend
hf space push nikerane/kellerwatt-engine

# Frontend (from web/)
npm run build
npx gh-pages -d dist -m "deploy playground"
```

## Files touched

- `backend/main.py` — new, FastAPI server
- `backend/Dockerfile` — new
- `backend/requirements.txt` — new
- `web/playground.html` — new, Vite entry
- `web/src/playground.tsx` — new, React entry
- `web/src/pages/PlaygroundPage.tsx` — new, slider UI + fetch logic
- `web/src/pages/PlaygroundPage.test.tsx` — new
- `web/src/components/SliderGroup.tsx` — new, reusable stepped slider
- `web/src/components/SolveResult.tsx` — new, live-updating results display
- `web/vite.config.ts` — add playground entry
- `web/src/components/SiteNav.tsx` — add "Playground" link

## Out of scope

- Live Python re-run on arbitrary non-stepped values (solved by steps)
- Multi-user concurrency (single-user tool, free tier)
- Auth / API keys (public tool, public backend)
- Mobile-first design (desktop-first, mobile readable)
