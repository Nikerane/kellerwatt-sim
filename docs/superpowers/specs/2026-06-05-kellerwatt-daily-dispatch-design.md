# KellerWatt Daily Dispatch Visualization — Design Spec

## Overview

Add a "Daily Dispatch" panel to the playground page showing per-interval charge/discharge
decisions on a real German day-ahead price curve. Both strategies (ceiling LP and causal
walk-forward) shown side-by-side. Navigation: Best Day, Worst Day, and a date picker.

## Architecture

```
POST /day-detail  (new endpoint on HF Spaces backend)
  → loads day prices from cache, solves ceiling LP for that single day,
    retrieves matching causal day from continuous walk-forward
  → returns per-interval arrays for both strategies

PlaygroundPage gains a "Daily Dispatch" section below the results table.
  ↔ Best Day / Worst Day buttons + date picker
  ↔ fetch /day-detail on selection
  ↔ renders DailyDispatchChart (new component)
```

## Backend: POST /day-detail

### Request
```json
{
  "date": "2025-03-14",
  "battery": {"capacity_kwh": 200, "power_kw": 50, "rte": 0.90},
  "grid_fee_eur_mwh": 0
}
```

### Response
```json
{
  "date": "2025-03-14",
  "num_intervals": 96,
  "dt_h": 0.25,
  "prices": [42.3, 38.1, ...],
  "best_date": "2025-04-17",
  "worst_date": "2025-01-01",
  "available_dates": ["2025-01-01", ...],
  "ceiling": {
    "gross_eur": 23.45,
    "mwh_discharged": 0.18,
    "mwh_charged": 0.19,
    "avg_buy_price": 38.2,
    "avg_sell_price": 78.9,
    "charge_kw": [0, 0, 50, ...],
    "discharge_kw": [50, 50, 0, ...],
    "soc_kwh": [20, 43, 86, ...]
  },
  "causal": {
    "gross_eur": 18.12,
    "mwh_discharged": 0.15,
    "mwh_charged": 0.16,
    "avg_buy_price": 40.1,
    "avg_sell_price": 75.3,
    "charge_kw": [0, 0, 50, ...],
    "discharge_kw": [0, 50, 0, ...],
    "soc_kwh": [20, 20, 63, ...]
  }
}
```

- `best_date` / `worst_date`: pre-computed from the backtest (highest/lowest gross_eur day)
- `available_dates`: all dates in the price cache for this year

## Frontend: DailyDispatchChart

### Layout
Two side-by-side card panels (ceiling | causal), each containing:
- **Header**: "Bought X kWh @ avg €Y → Sold Z kWh @ avg €W | Net: €V"
- **SVG chart**: 2-axis plot
  - Right axis: price line (€/MWh), stepped
  - Left axis: kW bars — green for discharge, red for charge
  - Dashed overlay: SoC (kWh) over time
- Matches existing brand: Hearth background, Ember for ceiling, neutral for causal

### Height
Compact — the detail view is supplementary, not the main event. ~280–320px per chart,
stacked vertically on narrow screens.

### Navigation bar
```
[★ Best Day]  [▲ Worst Day]  [📅 pick a date...]
```
- Best/Worst: disable if already selected. Pre-computed from `/day-detail` response.
- Date picker: native `<input type="date">`, constrained to `available_dates`.
- Default: Best Day pre-selected.

## Backend changes

`backend/main.py`:
- New `POST /day-detail` endpoint
- Loads day prices from `engine.data_load` for the requested date
- Solves `solve_day_ceiling()` for that single day (fast — ~50ms for one LP)
- Gets causal day data from `run_backtest` (already pre-solved, ceiling cached)
- The causal day result is read from the backtest's internal per-day aggregation
- Returns per-interval arrays (`charge_kw`, `discharge_kw`, `soc_kwh`) from `DayDispatch`

## Edge cases

- Weekend/holiday with flat prices → battery sits idle. Chart shows flat line. Valid.
- Negative price day → charge bars go into negative price territory, sell bars above. Visually striking.
- 23h/25h DST days → handled correctly by engine, chart shows the actual day length.
- Date picker limits to dates with valid price data (no future dates, no missing days).

## Files

- `backend/main.py` — add POST /day-detail endpoint
- `web/src/pages/PlaygroundPage.tsx` — add Daily Dispatch section + navigation + fetch
- `web/src/components/DailyDispatchChart.tsx` — new SVG chart component
- `web/src/components/DailyDispatchChart.test.tsx` — new tests
- `web/src/pages/PlaygroundPage.test.tsx` — add day-detail tests
- `web/src/data/playground.ts` — add DayDetailResponse type
- `web/src/styles/app.css` — dispatch chart styles

## Out of scope

- Animation/playback of dispatch over time
- Comparison with actual trades (this is a simulation)
- Export/CSV of dispatch data
