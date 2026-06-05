# KellerWatt Offline Daily Dispatch Lookup — Design

**Date:** 2026-06-05
**Status:** Approved

## Goal

Make the Daily Dispatch section work fully offline without the live HF Space backend, by shipping precomputed per-interval arrays for a grid of slider combinations. The live server remains as fallback for slider values outside the sampled grid.

## Architecture

```
sliders settle
  → round to nearest sampled grid point
  → build combo key: "{power}_{rte}_{grid_fee}"
  → lookup in loaded capacity file
  → hit: render charts instantly, show "Precomputed ✓"
  → miss: show "Compute live" button, call /day-detail as fallback
```

## Sampled grid points

| Parameter     | Full range    | Step | Sampled                              | Count |
|---------------|---------------|------|--------------------------------------|-------|
| capacity_kwh  | 50–500        | 25   | 50, 100, 175, 250, 350, 450, 500    | 7     |
| power_kw      | 25–250        | 25   | 25, 50, 100, 150, 200, 250           | 6     |
| rte           | 0.75–0.95     | 0.05 | 0.75, 0.80, 0.85, 0.90, 0.95         | 5     |
| grid_fee      | 0–50          | 5    | 0, 10, 20, 30, 50                    | 5     |

**Total: 7 × 6 × 5 × 5 = 1,050 combinations.**

## Per-combo days (5 each)

1. Best day (highest ceiling gross_eur for the year)
2. Worst day (lowest ceiling gross_eur)
3. Spring equinox — March 21
4. Summer solstice — June 21
5. Winter typical — January 15

All based on 2025 price data (the most recent full year).

## File structure

```
web/public/data/dispatch/
  cap_050.json    (~400 KB gzipped)
  cap_100.json
  cap_175.json
  cap_250.json
  cap_350.json
  cap_450.json
  cap_500.json
```

Each file covers **one capacity value** × (6 powers × 5 RTEs × 5 grid_fees) = **150 combos** × 5 days = **750 day-results**.

### JSON schema

```json
{
  "capacity_kwh": 200,
  "days": {
    "2025-01-20": {
      "prices": [91.9, 88.9, ...],
      "dt_h": 1.0
    },
    "...": "..."
  },
  "combos": {
    "50_0.90_0": {
      "ceiling": {
        "2025-01-20": {
          "gross_eur": 21.82,
          "mwh_discharged": 0.171,
          "mwh_charged": 0.19,
          "avg_buy_price": 20.5,
          "avg_sell_price": 123.8,
          "charge_kw": [0.0, 0.0, ...],
          "discharge_kw": [0.0, 0.0, ...],
          "soc_kwh": [20.0, 20.0, ...]
        },
        "...": "..."
      },
      "causal": { "...": "..." }
    },
    "...": "..."
  }
}
```

Combo key format: `"{power_kw}_{rte}_{grid_fee}"` — e.g., `"50_0.90_0"`.

## Precomputation script

`scripts/precompute_dispatch.py`:

- Iterates the 7 × 6 × 5 × 5 grid
- For each combo: loads 2025 price data, solves ceiling LP per day, runs causal backtest per day
- Identifies best/worst days by ceiling gross_eur for the year, plus seasonal dates
- Writes 7 JSON files to `web/public/data/dispatch/`
- Run once, commit output. Re-run if grid or selected days change.

## Frontend changes

### New types (`web/src/data/playground.ts`)

```ts
export interface DispatchFile {
  capacity_kwh: number;
  days: Record<string, { prices: number[]; dt_h: number }>;
  combos: Record<string, {
    ceiling: Record<string, StrategyDayDetail>;
    causal: Record<string, StrategyDayDetail>;
  }>;
}
```

### PlaygroundPage changes

1. **New state:** `dispatchFile: DispatchFile | null`, `lookupDays: string[]` (the 5 known dates)
2. **On mount & on capacity change:** `fetch(/data/dispatch/cap_{xxx}.json)` → set `dispatchFile`, extract the 5 day keys → set `lookupDays`
3. **`fetchDayDetail` modified:** check combo key against `dispatchFile.combos`:
   - Hit → construct `DayDetailResponse` from file, set state. Skip server call. Show "Precomputed ✓".
   - Miss → call `/day-detail` as before. Show "Compute live" button.
4. **Navigation tweak:** when using precomputed data, the date picker and Best/Worst buttons only navigate among the 5 available dates (hide or gray out the full date picker for the demo flow).
5. **Status badge for lookup state:** green "Precomputed" dot when data is from cache, amber "Compute live" button when server fetch is needed.

### Rounding logic

```ts
function nearestGridPoint(value: number, grid: number[]): number {
  return grid.reduce((prev, curr) =>
    Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
  );
}
```

Grids are baked-in constants matching the sampled values above.

## Testing

### `web/src/data/dispatchLookup.test.ts`

```ts
// Rounding logic
// nearestGridPoint(205, [50, 100, 175, 250, ...]) → 175
// nearestGridPoint(90, [25, 50, 100, ...]) → 100

// Combo key building
// buildComboKey({ power_kw: 50, rte: 0.90, grid_fee: 0 }) → "50_0.9_0"

// File loading mock — fetch resolves with a DispatchFile, component renders from it
```

### `web/src/pages/PlaygroundPage.test.tsx`

- Add test: "renders daily dispatch from precomputed data without server call"
- Add test: "shows 'Compute live' when combo is not in lookup file"
- Add test: "capacity change triggers new file load"

### `web/src/components/DailyDispatchChart.test.tsx`

- No changes needed — component is data-agnostic, already tested with `DayDetailResponse`

## CSS

Minimal: a green "Precomputed" badge and amber "Compute live" button style. Reuse existing `kw-toggle__btn` and `kw-status` patterns.

## Deploy

- `scripts/precompute_dispatch.py` output goes to `web/public/data/dispatch/`
- `npm run build` picks up `public/` files via Vite
- Deploy to GitHub Pages as before
- Note: .gitignore should NOT exclude `public/data/dispatch/`
