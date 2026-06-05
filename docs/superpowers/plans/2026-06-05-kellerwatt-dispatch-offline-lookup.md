# Offline Daily Dispatch Lookup Table — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship precomputed per-interval dispatch arrays for a grid of slider combos so the Daily Dispatch section works offline without the HF Space backend.

**Architecture:** A Python script precomputes dispatch data for 1,050 slider combos × 5 days each, writing 7 JSON files (one per capacity value). The frontend loads the file matching the current capacity slider, rounds other sliders to the nearest sampled grid point, and looks up precomputed data. If the combo matches, charts render instantly; if not, a "Compute live" button hits the server.

**Tech Stack:** Python (pulp, highs — the existing engine), TypeScript (React), Vite (static file serving from `public/`)

**Spec:** `docs/superpowers/specs/2026-06-05-kellerwatt-dispatch-offline-lookup-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/precompute_dispatch.py` | **Create** | Iterates grid, solves ceiling + causal per combo/day, writes JSON files |
| `web/public/data/dispatch/cap_*.json` | **Create** (by script) | 7 files, one per capacity, each ~400KB gzipped |
| `web/src/data/playground.ts` | **Modify** | Add `DispatchFile` type |
| `web/src/data/dispatchLookup.ts` | **Create** | Rounding, combo key, `DayDetailResponse` construction from file |
| `web/src/data/dispatchLookup.test.ts` | **Create** | Tests for lookup utilities |
| `web/src/pages/PlaygroundPage.tsx` | **Modify** | Load dispatch file, use lookup before server |
| `web/src/pages/PlaygroundPage.test.tsx` | **Modify** | Test offline dispatch rendering, "Compute live" fallback |

---

### Task 1: Precomputation script

**Files:**
- Create: `scripts/precompute_dispatch.py`
- Create (by running script): `web/public/data/dispatch/cap_050.json` … `cap_500.json`

- [ ] **Step 1: Write the precomputation script**

```python
#!/usr/bin/env python3
"""Precompute daily dispatch arrays for the offline lookup table.

Iterates a grid of (capacity_kwh, power_kw, rte, grid_fee) combos, solves
both ceiling LP and causal walk-forward for each, and writes one JSON file
per capacity value to web/public/data/dispatch/.

Usage:
    python scripts/precompute_dispatch.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

# Ensure the repo root is on sys.path so engine/ imports work.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.backtest import run_backtest
from engine.data_load import load_year
from engine.dispatch import solve_day_ceiling
from engine.params import Battery, Params

# ---- grid definition ----
CAPACITIES = [50, 100, 175, 250, 350, 450, 500]
POWERS = [25, 50, 100, 150, 200, 250]
RTES = [0.75, 0.80, 0.85, 0.90, 0.95]
GRID_FEES = [0, 10, 20, 30, 50]

# Fixed seasonal dates (always 2025, the most recent full year).
SPRING = date(2025, 3, 21)
SUMMER = date(2025, 6, 21)
WINTER = date(2025, 1, 15)

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "public", "data", "dispatch",
)


def combo_key(power_kw: int, rte: float, grid_fee: int) -> str:
    return f"{power_kw}_{rte}_{grid_fee}"


def avg_price(mwh: float, turnover: float) -> float | None:
    if mwh > 0 and turnover > 0:
        return round(turnover / mwh, 1)
    return None


def strategy_detail(day_dispatch) -> dict:
    """Convert a ceiling or causal day result to the JSON-serialisable format."""
    return {
        "gross_eur": round(day_dispatch.gross_eur, 2),
        "mwh_discharged": round(day_dispatch.mwh_discharged, 3),
        "mwh_charged": round(day_dispatch.mwh_charged, 3),
        "avg_buy_price": avg_price(
            day_dispatch.mwh_charged, day_dispatch.purchase_turnover_eur
        ),
        "avg_sell_price": avg_price(
            day_dispatch.mwh_discharged, day_dispatch.sale_turnover_eur
        ),
        "charge_kw": [round(v, 2) for v in day_dispatch.charge_kw]
        if day_dispatch.charge_kw
        else [],
        "discharge_kw": [round(v, 2) for v in day_dispatch.discharge_kw]
        if day_dispatch.discharge_kw
        else [],
        "soc_kwh": [round(v, 2) for v in day_dispatch.soc_kwh]
        if day_dispatch.soc_kwh
        else [],
    }


def precompute():
    os.makedirs(OUT_DIR, exist_ok=True)

    year_data = load_year(2025, allow_fetch=False)
    days_list = list(year_data.days)
    day_map = {d.day: d for d in days_list}

    # Pre-compute best/worst for each (battery, grid_fee) pair so we can
    # identify which dates to include without re-solving the entire year
    # per combo.  We still need to re-solve per combo to get per-day arrays
    # for the 5 selected dates, but we can identify best/worst dates cheaply
    # by scanning the pre-solved year-data cache.

    total_combos = len(CAPACITIES) * len(POWERS) * len(RTES) * len(GRID_FEES)
    done = 0

    for cap in CAPACITIES:
        # Each capacity file has its own top-level dictionary.
        file_data: dict = {
            "capacity_kwh": cap,
            "days": {},   # date_str → {prices, dt_h}
            "combos": {}, # combo_key → {best_date, worst_date, ceiling, causal}
        }

        for power in POWERS:
            for rte in RTES:
                for grid_fee in GRID_FEES:
                    battery = Battery(capacity_kwh=cap, power_kw=power, rte=rte)
                    ck = combo_key(power, rte, grid_fee)

                    # ---- find best and worst ceiling days for this combo ----
                    best_date = None
                    worst_date = None
                    best_gross = -float("inf")
                    worst_gross = float("inf")

                    for d in days_list:
                        ceil = solve_day_ceiling(
                            list(d.prices), d.dt_h, battery,
                            cycle_cap=None, grid_fee_charge=grid_fee,
                        )
                        if ceil.gross_eur > best_gross:
                            best_gross = ceil.gross_eur
                            best_date = d.day
                        if ceil.gross_eur < worst_gross:
                            worst_gross = ceil.gross_eur
                            worst_date = d.day

                    # ---- collect the 5 target dates ----
                    target_dates: list[date] = [
                        best_date,   # type: ignore[list-item]
                        worst_date,  # type: ignore[list-item]
                        SPRING,
                        SUMMER,
                        WINTER,
                    ]

                    # Deduplicate (best/worst could land on a seasonal date).
                    seen = set()
                    unique_dates = []
                    for d in target_dates:
                        if d not in seen:
                            seen.add(d)
                            unique_dates.append(d)

                    # ---- solve each target date for ceiling + causal ----
                    # Run one backtest to get all causal days (cached per battery).
                    bt = run_backtest(
                        years=(2025,),
                        params=Params(battery=battery),
                        grid_fee_charge=grid_fee,
                        use_cache=True, allow_fetch=False,
                    )
                    causal_by_date = {}
                    if bt.causal_result:
                        for cd in bt.causal_result.days:
                            causal_by_date[cd.day] = cd

                    combo_ceiling: dict[str, dict] = {}
                    combo_causal: dict[str, dict] = {}

                    for d in unique_dates:
                        ds = d.isoformat()
                        td = day_map[d]

                        # Prices — store once per date at file level.
                        if ds not in file_data["days"]:
                            file_data["days"][ds] = {
                                "prices": [round(p, 1) for p in td.prices],
                                "dt_h": td.dt_h,
                            }

                        # Ceiling
                        ceil = solve_day_ceiling(
                            list(td.prices), td.dt_h, battery,
                            cycle_cap=None, grid_fee_charge=grid_fee,
                        )
                        combo_ceiling[ds] = strategy_detail(ceil)

                        # Causal
                        cday = causal_by_date.get(d)
                        if cday is not None:
                            combo_causal[ds] = strategy_detail(cday)
                        else:
                            combo_causal[ds] = {
                                "gross_eur": 0.0, "mwh_discharged": 0.0,
                                "mwh_charged": 0.0,
                                "avg_buy_price": None, "avg_sell_price": None,
                                "charge_kw": [], "discharge_kw": [], "soc_kwh": [],
                            }

                    file_data["combos"][ck] = {
                        "best_date": best_date.isoformat(),
                        "worst_date": worst_date.isoformat(),
                        "ceiling": combo_ceiling,
                        "causal": combo_causal,
                    }

                    done += 1
                    if done % 10 == 0:
                        print(f"  {done}/{total_combos} combos done")

        # Write per-capacity file.
        out_path = os.path.join(OUT_DIR, f"cap_{cap:03d}.json")
        with open(out_path, "w") as f:
            json.dump(file_data, f)
        print(f"Wrote {out_path} ({len(file_data['combos'])} combos, {len(file_data['days'])} days)")

    print(f"Done — {total_combos} combos across {len(CAPACITIES)} files.")


if __name__ == "__main__":
    precompute()
```

- [ ] **Step 2: Run the precomputation script**

Run: `python scripts/precompute_dispatch.py`

Expected: 7 JSON files written to `web/public/data/dispatch/`. Each file ~2–5 MB uncompressed. Script takes 5–15 minutes (the backtest is cached per battery, so most time is in the best/worst day scan — 365 ceiling solves per combo).

Check output:
```bash
ls -lh web/public/data/dispatch/
```

Expected: 7 files, each non-empty.

- [ ] **Step 3: Commit the precomputed data**

```bash
git add web/public/data/dispatch/ scripts/precompute_dispatch.py
git commit -m "feat: add precomputed daily dispatch lookup files + generation script"
```

---

### Task 2: Frontend types + lookup utility

**Files:**
- Modify: `web/src/data/playground.ts` — add `DispatchFile` interface
- Create: `web/src/data/dispatchLookup.ts` — lookup logic
- Create: `web/src/data/dispatchLookup.test.ts` — tests

- [ ] **Step 1: Add DispatchFile type to playground.ts**

Append to `web/src/data/playground.ts`:

```typescript
/** Shape of a precomputed dispatch lookup file (cap_050.json, etc.). */
export interface DispatchFile {
  capacity_kwh: number;
  days: Record<string, { prices: number[]; dt_h: number }>;
  combos: Record<string, {
    best_date: string;
    worst_date: string;
    ceiling: Record<string, StrategyDayDetail>;
    causal: Record<string, StrategyDayDetail>;
  }>;
}
```

- [ ] **Step 2: Write the dispatchLookup module**

Create `web/src/data/dispatchLookup.ts`:

```typescript
import type { DayDetailResponse, DispatchFile } from "./playground";

/** Grid points used in the precomputed lookup table. */
export const CAPACITY_GRID = [50, 100, 175, 250, 350, 450, 500];
export const POWER_GRID = [25, 50, 100, 150, 200, 250];
export const RTE_GRID = [0.75, 0.80, 0.85, 0.90, 0.95];
export const GRID_FEE_GRID = [0, 10, 20, 30, 50];

/** Round a value to the nearest point in a sorted grid. */
export function nearestGridPoint(value: number, grid: number[]): number {
  let best = grid[0];
  let bestDist = Math.abs(value - best);
  for (let i = 1; i < grid.length; i++) {
    const dist = Math.abs(value - grid[i]);
    if (dist < bestDist) {
      bestDist = dist;
      best = grid[i];
    }
  }
  return best;
}

/**
 * Build the combo key used in DispatchFile.combos.
 * RTE is serialised without trailing zeros: 0.9 not 0.90.
 */
export function buildComboKey(power_kw: number, rte: number, grid_fee: number): string {
  return `${power_kw}_${rte}_${grid_fee}`;
}

/** The three fixed seasonal dates (always in the precomputed data). */
export const SEASONAL_DATES = ["2025-03-21", "2025-06-21", "2025-01-15"];

/**
 * Load a DispatchFile for a given capacity (asynchronous fetch).
 * Returns null if the file doesn't exist (404).
 */
export async function loadDispatchFile(capacityKwh: number): Promise<DispatchFile | null> {
  const rounded = nearestGridPoint(capacityKwh, CAPACITY_GRID);
  const filename = `cap_${String(rounded).padStart(3, "0")}.json`;
  try {
    const res = await fetch(`./data/dispatch/${filename}`);
    if (!res.ok) return null;
    return (await res.json()) as DispatchFile;
  } catch {
    return null;
  }
}

/**
 * Try to resolve a DayDetailResponse from the precomputed lookup file.
 * Returns null if the combo is not in the file.
 */
export function resolveFromLookup(
  file: DispatchFile,
  powerKw: number,
  rte: number,
  gridFee: number,
  dateStr: string,
): DayDetailResponse | null {
  const roundedPower = nearestGridPoint(powerKw, POWER_GRID);
  const roundedRte = nearestGridPoint(rte, RTE_GRID);
  const roundedFee = nearestGridPoint(gridFee, GRID_FEE_GRID);
  const key = buildComboKey(roundedPower, roundedRte, roundedFee);

  const combo = file.combos[key];
  if (!combo) return null;

  const dayInfo = file.days[dateStr];
  if (!dayInfo) return null;

  const ceiling = combo.ceiling[dateStr];
  const causal = combo.causal[dateStr];
  if (!ceiling || !causal) return null;

  // Collect all available dates for this combo (best + worst + seasonal).
  const available = [combo.best_date, combo.worst_date, ...SEASONAL_DATES]
    .filter((d, i, arr) => arr.indexOf(d) === i) // deduplicate
    .filter((d) => combo.ceiling[d]); // must have data

  return {
    date: dateStr,
    num_intervals: dayInfo.prices.length,
    dt_h: dayInfo.dt_h,
    prices: dayInfo.prices,
    best_date: combo.best_date,
    worst_date: combo.worst_date,
    available_dates: available,
    ceiling,
    causal,
  };
}
```

- [ ] **Step 3: Write the failing test for dispatchLookup**

Create `web/src/data/dispatchLookup.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import {
  nearestGridPoint,
  buildComboKey,
  resolveFromLookup,
  CAPACITY_GRID,
  POWER_GRID,
  RTE_GRID,
  GRID_FEE_GRID,
  loadDispatchFile,
  SEASONAL_DATES,
} from "./dispatchLookup";
import type { DispatchFile } from "./playground";

describe("nearestGridPoint", () => {
  it("returns exact match", () => {
    expect(nearestGridPoint(250, CAPACITY_GRID)).toBe(250);
  });

  it("rounds up to nearest", () => {
    expect(nearestGridPoint(205, CAPACITY_GRID)).toBe(175);
    expect(nearestGridPoint(290, CAPACITY_GRID)).toBe(250);
  });

  it("rounds down to nearest", () => {
    expect(nearestGridPoint(230, CAPACITY_GRID)).toBe(250);
  });

  it("clamps to first", () => {
    expect(nearestGridPoint(10, CAPACITY_GRID)).toBe(50);
  });

  it("clamps to last", () => {
    expect(nearestGridPoint(999, CAPACITY_GRID)).toBe(500);
  });

  it("works for power grid", () => {
    expect(nearestGridPoint(55, POWER_GRID)).toBe(50);
    expect(nearestGridPoint(80, POWER_GRID)).toBe(100);
  });

  it("works for RTE grid", () => {
    expect(nearestGridPoint(0.87, RTE_GRID)).toBe(0.85);
    expect(nearestGridPoint(0.88, RTE_GRID)).toBe(0.90);
  });

  it("works for grid fee grid", () => {
    expect(nearestGridPoint(7, GRID_FEE_GRID)).toBe(10);
    expect(nearestGridPoint(3, GRID_FEE_GRID)).toBe(0);
  });
});

describe("buildComboKey", () => {
  it("builds correct key format", () => {
    expect(buildComboKey(50, 0.90, 0)).toBe("50_0.9_0");
    expect(buildComboKey(100, 0.75, 20)).toBe("100_0.75_20");
    expect(buildComboKey(250, 0.95, 50)).toBe("250_0.95_50");
  });
});

describe("resolveFromLookup", () => {
  const mockFile: DispatchFile = {
    capacity_kwh: 200,
    days: {
      "2025-01-20": { prices: [91.9, 88.9, 87.2], dt_h: 1.0 },
      "2025-10-04": { prices: [50.0, 45.0, 40.0], dt_h: 1.0 },
      "2025-03-21": { prices: [60.0, 55.0, 50.0], dt_h: 1.0 },
    },
    combos: {
      "50_0.9_0": {
        best_date: "2025-01-20",
        worst_date: "2025-10-04",
        ceiling: {
          "2025-01-20": {
            gross_eur: 21.82, mwh_discharged: 0.171, mwh_charged: 0.19,
            avg_buy_price: 20.5, avg_sell_price: 123.8,
            charge_kw: [0, 50, 50], discharge_kw: [0, 0, 50], soc_kwh: [20, 63, 20],
          },
          "2025-03-21": {
            gross_eur: 10.0, mwh_discharged: 0.1, mwh_charged: 0.11,
            avg_buy_price: 30.0, avg_sell_price: 80.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
        },
        causal: {
          "2025-01-20": {
            gross_eur: 15.84, mwh_discharged: 0.171, mwh_charged: 0.19,
            avg_buy_price: 15.7, avg_sell_price: 110.2,
            charge_kw: [0, 50, 39], discharge_kw: [0, 0, 0], soc_kwh: [20, 63, 100],
          },
          "2025-03-21": {
            gross_eur: 8.0, mwh_discharged: 0.1, mwh_charged: 0.11,
            avg_buy_price: 25.0, avg_sell_price: 75.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
        },
      },
    },
  };

  it("returns a DayDetailResponse for a known combo + date", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-01-20");
    expect(result).not.toBeNull();
    expect(result!.date).toBe("2025-01-20");
    expect(result!.num_intervals).toBe(3);
    expect(result!.prices).toEqual([91.9, 88.9, 87.2]);
    expect(result!.ceiling.gross_eur).toBe(21.82);
    expect(result!.causal.gross_eur).toBe(15.84);
    expect(result!.best_date).toBe("2025-01-20");
    expect(result!.worst_date).toBe("2025-10-04");
  });

  it("rounds slider values to nearest grid point", () => {
    // 55 rounds to 50, 0.88 rounds to 0.90, 3 rounds to 0
    const result = resolveFromLookup(mockFile, 55, 0.88, 3, "2025-01-20");
    expect(result).not.toBeNull();
  });

  it("returns null for missing combo", () => {
    const result = resolveFromLookup(mockFile, 25, 0.90, 0, "2025-01-20");
    expect(result).toBeNull();
  });

  it("returns null for missing date", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-12-25");
    expect(result).toBeNull();
  });

  it("available_dates includes best, worst, and seasonal", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-01-20");
    expect(result!.available_dates).toContain("2025-01-20");
    expect(result!.available_dates).toContain("2025-10-04");
    expect(result!.available_dates).toContain("2025-03-21");
  });
});

describe("loadDispatchFile", () => {
  it("fetches the correct file for a capacity", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ capacity_kwh: 250, days: {}, combos: {} }),
    });
    globalThis.fetch = mockFetch as any;

    const result = await loadDispatchFile(250);
    expect(result).not.toBeNull();
    expect(result!.capacity_kwh).toBe(250);
    expect(mockFetch).toHaveBeenCalledWith("./data/dispatch/cap_250.json");
  });

  it("returns null on 404", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false });
    globalThis.fetch = mockFetch as any;

    const result = await loadDispatchFile(999);
    expect(result).toBeNull();
  });

  it("rounds to nearest capacity before fetching", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ capacity_kwh: 175, days: {}, combos: {} }),
    });
    globalThis.fetch = mockFetch as any;

    await loadDispatchFile(190);
    expect(mockFetch).toHaveBeenCalledWith("./data/dispatch/cap_175.json");
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `npx vitest run src/data/dispatchLookup.test.ts`

Expected: FAIL — `dispatchLookup.ts` doesn't exist yet.

- [ ] **Step 5: Run tests to verify they pass**

After writing `dispatchLookup.ts` and `DispatchFile` type:

Run: `npx vitest run src/data/dispatchLookup.test.ts`

Expected: PASS (all 14 tests).

- [ ] **Step 6: Commit**

```bash
git add web/src/data/playground.ts web/src/data/dispatchLookup.ts web/src/data/dispatchLookup.test.ts
git commit -m "feat: add DispatchFile type, lookup utility + tests"
```

---

### Task 3: Wire offline lookup into PlaygroundPage

**Files:**
- Modify: `web/src/pages/PlaygroundPage.tsx`

- [ ] **Step 1: Modify PlaygroundPage to use lookup**

The changes to `PlaygroundPage.tsx`:

**Import the new module:**
```tsx
import { loadDispatchFile, resolveFromLookup, SEASONAL_DATES, buildComboKey } from "../data/dispatchLookup";
import type { DispatchFile } from "../data/playground";
```

**New state:**
```tsx
const [dispatchFile, setDispatchFile] = useState<DispatchFile | null>(null);
const [lookupHit, setLookupHit] = useState<boolean>(false);
```

**Load dispatch file on mount + on capacity change:**
```tsx
// Load the dispatch lookup file whenever capacity changes
useEffect(() => {
  let cancelled = false;
  loadDispatchFile(values.capacity_kwh).then((df) => {
    if (!cancelled) setDispatchFile(df);
  });
  return () => { cancelled = true; };
}, [values.capacity_kwh]);
```

**Modify `fetchDayDetail` to try lookup first:**
```tsx
const fetchDayDetail = useCallback(
  async (dateStr: string) => {
    // Try precomputed lookup first.
    if (dispatchFile) {
      const resolved = resolveFromLookup(
        dispatchFile, values.power_kw, values.rte, values.grid_fee, dateStr,
      );
      if (resolved) {
        setDayDetail(resolved);
        setSelectedDate(dateStr);
        setLookupHit(true);
        return;
      }
    }

    // Fallback: live server.
    if (!ENGINE_URL) return;
    setLookupHit(false);
    setDayLoading(true);
    try {
      const res = await fetch(`${ENGINE_URL}/day-detail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: dateStr,
          battery: {
            capacity_kwh: values.capacity_kwh,
            power_kw: values.power_kw,
            rte: values.rte,
          },
          grid_fee_eur_mwh: values.grid_fee,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: DayDetailResponse = await res.json();
      if (mountedRef.current) {
        setDayDetail(data);
        setSelectedDate(dateStr);
      }
    } catch {
      /* keep previous detail if fetch fails */
    } finally {
      if (mountedRef.current) setDayLoading(false);
    }
  },
  [values, dispatchFile],
);
```

**Modify auto-fetch to trigger when dispatch file loads:**
```tsx
useEffect(() => {
  if (dispatchFile && dayDetail === null) {
    // Pick the first seasonal date as default.
    fetchDayDetail(SEASONAL_DATES[0]);
  }
}, [dispatchFile, dayDetail, fetchDayDetail]);
```

**Remove the old auto-fetch on "solved" — replace with:**
(Remove the old useEffect that triggers on `engineStatus === "solved"`.)

**Update the Daily Dispatch section — date picker shows only available dates when using lookup:**
```tsx
<input
  type="date"
  className="kw-toggle__btn"
  value={selectedDate}
  min={dayDetail?.available_dates[0] ?? ""}
  max={dayDetail?.available_dates[dayDetail.available_dates.length - 1] ?? ""}
  onChange={(e) => fetchDayDetail(e.target.value)}
  disabled={dayLoading}
  style={{ fontSize: "0.8rem", fontFamily: "var(--mono)" }}
/>
```

**Add a lookup status indicator next to the nav controls:**
```tsx
{dayDetail && (
  <span style={{
    fontSize: "0.72rem",
    fontFamily: "var(--mono)",
    color: lookupHit ? "#4CAF50" : "var(--ember)",
  }}>
    {lookupHit ? "Precomputed ✓" : "Compute live"}
  </span>
)}
```

**Update the offline empty state — remove or change the "requires live backend" message:**
```tsx
{!dayDetail && !ENGINE_URL && (
  <p style={{ fontSize: "0.88rem", opacity: 0.6 }}>
    Daily dispatch requires the live engine backend.
  </p>
)}
```
Change to:
```tsx
{!dayDetail && (
  <p style={{ fontSize: "0.88rem", opacity: 0.6 }}>
    Adjust sliders to see daily dispatch charts.
  </p>
)}
```

- [ ] **Step 2: Run existing tests to check for regressions**

Run: `npx vitest run src/pages/PlaygroundPage.test.tsx`

Expected: Some tests may fail because the component now calls `fetch("./data/dispatch/cap_200.json")` automatically. We'll update the tests in Task 4.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/PlaygroundPage.tsx
git commit -m "feat: wire offline dispatch lookup into PlaygroundPage"
```

---

### Task 4: Update PlaygroundPage tests

**Files:**
- Modify: `web/src/pages/PlaygroundPage.test.tsx`

- [ ] **Step 1: Update the test setup with a mock dispatch file**

Replace the existing test file with updated tests that mock the dispatch file fetch:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlaygroundPage } from "./PlaygroundPage";

// Mock fetch globally — the page calls the HF Space backend and dispatch files.
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as any;

// Mock precomputed dispatch file.
const MOCK_DISPATCH_FILE = {
  capacity_kwh: 200,
  days: {
    "2025-03-21": { prices: [50, 45, 40], dt_h: 1.0 },
    "2025-06-21": { prices: [30, 35, 40], dt_h: 1.0 },
    "2025-01-15": { prices: [70, 65, 60], dt_h: 1.0 },
    "2025-01-20": { prices: [91.9, 88.9, 87.2], dt_h: 1.0 },
    "2025-10-04": { prices: [20, 25, 30], dt_h: 1.0 },
  },
  combos: {
    "50_0.9_0": {
      best_date: "2025-01-20",
      worst_date: "2025-10-04",
      ceiling: {
        "2025-03-21": {
          gross_eur: 15.0, mwh_discharged: 0.1, mwh_charged: 0.11,
          avg_buy_price: 30.0, avg_sell_price: 100.0,
          charge_kw: [0, 50, 0], discharge_kw: [0, 0, 50], soc_kwh: [50, 100, 50],
        },
        "2025-06-21": {
          gross_eur: 12.0, mwh_discharged: 0.08, mwh_charged: 0.09,
          avg_buy_price: 25.0, avg_sell_price: 90.0,
          charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [50, 50, 50],
        },
        "2025-01-15": {
          gross_eur: 18.0, mwh_discharged: 0.12, mwh_charged: 0.13,
          avg_buy_price: 35.0, avg_sell_price: 110.0,
          charge_kw: [50, 0, 0], discharge_kw: [0, 0, 50], soc_kwh: [100, 100, 50],
        },
        "2025-01-20": {
          gross_eur: 21.82, mwh_discharged: 0.171, mwh_charged: 0.19,
          avg_buy_price: 20.5, avg_sell_price: 123.8,
          charge_kw: [0, 50, 50], discharge_kw: [0, 0, 50], soc_kwh: [20, 63, 20],
        },
        "2025-10-04": {
          gross_eur: 5.0, mwh_discharged: 0.05, mwh_charged: 0.06,
          avg_buy_price: 40.0, avg_sell_price: 80.0,
          charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [50, 50, 50],
        },
      },
      causal: {
        "2025-03-21": {
          gross_eur: 10.0, mwh_discharged: 0.1, mwh_charged: 0.11,
          avg_buy_price: 28.0, avg_sell_price: 95.0,
          charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [50, 50, 50],
        },
        "2025-06-21": {
          gross_eur: 8.0, mwh_discharged: 0.08, mwh_charged: 0.09,
          avg_buy_price: 22.0, avg_sell_price: 85.0,
          charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [50, 50, 50],
        },
        "2025-01-15": {
          gross_eur: 14.0, mwh_discharged: 0.12, mwh_charged: 0.13,
          avg_buy_price: 32.0, avg_sell_price: 105.0,
          charge_kw: [50, 0, 0], discharge_kw: [0, 0, 50], soc_kwh: [100, 100, 50],
        },
        "2025-01-20": {
          gross_eur: 15.84, mwh_discharged: 0.171, mwh_charged: 0.19,
          avg_buy_price: 15.7, avg_sell_price: 110.2,
          charge_kw: [0, 50, 39], discharge_kw: [0, 0, 0], soc_kwh: [20, 63, 100],
        },
        "2025-10-04": {
          gross_eur: 3.0, mwh_discharged: 0.05, mwh_charged: 0.06,
          avg_buy_price: 38.0, avg_sell_price: 78.0,
          charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [50, 50, 50],
        },
      },
    },
  },
};

beforeEach(() => {
  mockFetch.mockReset();
  // Default: first call returns the dispatch file, subsequent calls return health.
  mockFetch
    .mockResolvedValueOnce({
      ok: true,
      json: async () => MOCK_DISPATCH_FILE,
    })
    .mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok" }),
    });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PlaygroundPage", () => {
  it("renders the hero couplet", () => {
    render(<PlaygroundPage />);
    expect(
      screen.getByRole("heading", { name: /Change the assumptions\./ }),
    ).toBeInTheDocument();
  });

  it("renders all six sliders", () => {
    render(<PlaygroundPage />);
    expect(screen.getByLabelText("Battery capacity")).toBeInTheDocument();
    expect(screen.getByLabelText("Power rating")).toBeInTheDocument();
    expect(screen.getByLabelText("Round-trip efficiency")).toBeInTheDocument();
    expect(screen.getByLabelText("Assumed spread")).toBeInTheDocument();
    expect(screen.getByLabelText("Daily cycle cap")).toBeInTheDocument();
    expect(screen.getByLabelText("Grid energy fee")).toBeInTheDocument();
  });

  it("renders the exemption toggle with both options", () => {
    render(<PlaygroundPage />);
    expect(
      screen.getByRole("button", { name: "Retained" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lost" })).toBeInTheDocument();
  });

  it("shows default results on initial render (baked-in data)", () => {
    render(<PlaygroundPage />);
    expect(screen.getByText("Captured spread · 2025")).toBeInTheDocument();
  });

  it("renders cross-page nav with playground link", () => {
    render(<PlaygroundPage />);
    expect(screen.getByRole("link", { name: "Playground" })).toHaveAttribute(
      "href",
      "/playground.html",
    );
  });

  it("slider changes update value displays without crashing", () => {
    render(<PlaygroundPage />);
    const slider = screen.getByLabelText(
      "Battery capacity",
    ) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "300" } });
    expect(screen.getByText("300 kWh")).toBeInTheDocument();
  });

  it("renders daily dispatch from precomputed data without server call", async () => {
    render(<PlaygroundPage />);
    // Wait for the dispatch file to load and auto-render.
    expect(await screen.findByText(/Precomputed/, {}, { timeout: 2000 })).toBeInTheDocument();
    // Charts should be visible — both ceiling and causal.
    expect(screen.getByText("Ceiling (perfect foresight)")).toBeInTheDocument();
    expect(screen.getByText("Causal (walk-forward)")).toBeInTheDocument();
    // "Compute live" should NOT appear — we hit the lookup.
    expect(screen.queryByText(/Compute live/)).toBeNull();
  });

  it("shows ready status after health check resolves", async () => {
    render(<PlaygroundPage />);
    expect(await screen.findByText(/Ready/, {}, { timeout: 2000 })).toBeInTheDocument();
  });

  it("renders daily dispatch section with nav controls", () => {
    render(<PlaygroundPage />);
    expect(screen.getByText(/Daily dispatch/)).toBeInTheDocument();
    expect(screen.getByText(/Best Day/)).toBeInTheDocument();
    expect(screen.getByText(/Worst Day/)).toBeInTheDocument();
    const dateInput = document.querySelector('input[type="date"]');
    expect(dateInput).toBeInTheDocument();
  });

  it("does not show 'requires live backend' message", async () => {
    render(<PlaygroundPage />);
    await waitFor(() => {
      expect(
        screen.queryByText(/requires the live engine backend/),
      ).toBeNull();
    });
  });
});
```

- [ ] **Step 2: Run PlaygroundPage tests**

Run: `npx vitest run src/pages/PlaygroundPage.test.tsx`

Expected: All tests pass. The mock returns the dispatch file first, so the precomputed path is taken.

- [ ] **Step 3: Run the full test suite**

Run: `npx vitest run`

Expected: All tests pass (dispatchLookup + DailyDispatchChart + PlaygroundPage + existing).

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/PlaygroundPage.test.tsx
git commit -m "test: add offline dispatch lookup tests to PlaygroundPage"
```

---

### Task 5: Build and deploy

- [ ] **Step 1: Run the precomputation script (if not already done)**

Run: `python scripts/precompute_dispatch.py`

(This step is already done in Task 1, but verify the files exist.)

```bash
ls -la web/public/data/dispatch/
```

- [ ] **Step 2: Build the frontend**

Run:
```bash
npm run build
```

Expected: Build succeeds. The `dist/` dir includes `data/dispatch/` files.

- [ ] **Step 3: Verify offline behavior works**

Open `dist/playground.html` locally (or use `npx vite preview`) and check:
- Daily Dispatch section renders charts on load (from precomputed data)
- "Precomputed ✓" badge is visible
- Best Day, Worst Day buttons work
- Date picker works for the 5 available dates

- [ ] **Step 4: Deploy to GitHub Pages**

```bash
npx gh-pages -d dist
```

- [ ] **Step 5: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: deploy offline dispatch lookup"
```
