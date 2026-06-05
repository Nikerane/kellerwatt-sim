# Daily Dispatch Visualization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Daily Dispatch" panel to the playground showing per-interval charge/discharge on a real DE-LU price curve, with Best/Worst day nav and date picker.

**Architecture:** New POST /day-detail endpoint on HF Spaces backend returns per-interval arrays for both strategies. CausalDay gains per-interval arrays. Frontend DailyDispatchChart renders two SVG cards (ceiling | causal) with price lines, charge/discharge bars, and SoC overlay.

**Tech Stack:** FastAPI + Python engine (backend), React + d3-scale + SVG (frontend).

---

### Task 1: Engine — add per-interval arrays to CausalDay

**Files:**
- Modify: `engine/dispatch.py`

- [ ] **Step 1: Add charge_kw, discharge_kw, soc_kwh to CausalDay**

`CausalDay` currently only aggregates daily sums. We need per-interval arrays so the API can return interval-level data.

Read `engine/dispatch.py` and find the `@dataclass(frozen=True)` block for `class CausalDay` (line ~158). Add three new fields:

```python
@dataclass(frozen=True)
class CausalDay:
    day: date
    gross_eur: float
    net_eur: float
    mwh_discharged: float
    mwh_charged: float
    sale_turnover_eur: float
    purchase_turnover_eur: float
    soc_start_kwh: float
    soc_end_kwh: float
    traded: bool
    charge_kw: tuple = ()
    discharge_kw: tuple = ()
    soc_kwh: tuple = ()
```

- [ ] **Step 2: Collect per-interval arrays in run_causal_walkforward**

In `run_causal_walkforward` (line ~228), inside the main per-day loop, we need to collect three lists per day. At the start of each day (before the per-interval `for` loop), add:

```python
day_charge = []
day_discharge = []
day_soc = []
```

Then inside each charge/discharge/idle branch, append to these lists. After each `soc` update in the charge branch (after line 282):

```python
day_charge.append(c_kw)
day_discharge.append(0.0)
day_soc.append(soc)
```

After each `soc` update in the discharge branch (after line 298):

```python
day_charge.append(0.0)
day_discharge.append(d_kw)
day_soc.append(soc)
```

In the idle case (after `continue`), we need to add an idle record. After the charge block's `continue` and the discharge block's `continue`, the code falls through to idle implicitly. But we can't add after the `continue` calls. Better approach: restructure the loop to record at the top.

Actually, simplest approach: record at the bottom of each `for price in day.prices` iteration, after all branching. Since we modified `soc` inside each branch, we just need to capture it.

Switch the loop structure to use recording. Find the `for price in day.prices:` loop body (lines 272-301) and restructure so each branch sets variables rather than `continue`-ing:

```python
    for price in day.prices:
        c_kw = d_kw = 0.0
        # Charge on cheap intervals...
        if traded and price <= ch_thr and soc < smax - _EPS \
                and (price + grid_fee_charge) < dis_thr * rte:
            c_candidate = min(P, (smax - soc) / (eta * dt))
            if c_candidate > _EPS:
                e_ac = c_candidate * dt
                soc += eta * c_candidate * dt
                cost = (price / 1000.0) * e_ac
                g -= cost
                purchase += cost
                net -= ((price + grid_fee_charge) / 1000.0) * e_ac
                mchg += e_ac / 1000.0
                c_kw = c_candidate
        elif traded and price >= dis_thr and soc > smin + _EPS \
                and day_dis_ac < budget_cap - _EPS \
                and (price - degradation_discharge) > ch_thr / rte:
            d_candidate = min(P, (soc - smin) * eta / dt, (budget_cap - day_dis_ac) / dt)
            if d_candidate > _EPS:
                e_ac = d_candidate * dt
                soc -= d_candidate / eta * dt
                rev = (price / 1000.0) * e_ac
                g += rev
                sale += rev
                net += ((price - degradation_discharge) / 1000.0) * e_ac
                mdis += e_ac / 1000.0
                day_dis_ac += e_ac
                d_kw = d_candidate
        # idle: c_kw = d_kw = 0.0 (set at top)
        day_charge.append(c_kw)
        day_discharge.append(d_kw)
        day_soc.append(soc)
```

Then update the `CausalDay` construction at line 304 to include the arrays:

```python
        results.append(CausalDay(day.day, g, net, mdis, mchg, sale, purchase,
                                 soc_start, soc, traded,
                                 tuple(day_charge), tuple(day_discharge), tuple(day_soc)))
```

##### Instructions for the engineer:
- Read `engine/dispatch.py` fully to understand the current causal loop (lines 228-305).
- Add `charge_kw`, `discharge_kw`, `soc_kwh` fields to `CausalDay` dataclass.
- Restructure the per-interval loop to track c_kw, d_kw, soc_kwh per interval.
- Pass the three tuples when constructing each `CausalDay`.
- Run existing engine tests to verify nothing is broken.

- [ ] **Step 3: Run engine tests**

```bash
cd /Users/nikerane/repos/kellerwatt-sim && .venv/bin/python -m pytest engine/tests/ -q
```

Expected: all 115 tests pass.

- [ ] **Step 4: Commit**

```bash
git add engine/dispatch.py
git commit -m "feat(engine): add per-interval arrays to CausalDay"
```

---

### Task 2: Backend — add POST /day-detail endpoint

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add the /day-detail endpoint to backend/main.py**

Below the `/solve` endpoint, add a new `POST /day-detail` endpoint. It:
- Accepts a date string, battery params, and grid fee
- Loads the year's prices from cache, finds the matching day
- Solves the ceiling LP for that single day (returns per-interval arrays)
- Runs the full backtest (cached) to get the causal day data
- Computes best/worst day from the ceiling day results

Add these imports at the top of `backend/main.py`:

```python
from datetime import date as DateType
from engine.data_load import load_year
from engine.dispatch import solve_day_ceiling
```

Add these request/response models below the existing ones:

```python
class DayDetailRequest(BaseModel):
    date: str  # "2025-03-14"
    battery: BatteryRequest
    grid_fee_eur_mwh: float


class StrategyDayDetail(BaseModel):
    gross_eur: float
    mwh_discharged: float
    mwh_charged: float
    avg_buy_price: float | None
    avg_sell_price: float | None
    charge_kw: list[float]
    discharge_kw: list[float]
    soc_kwh: list[float]
```

Add the endpoint:

```python
@app.post("/day-detail")
async def day_detail(req: DayDetailRequest):
    target_date = DateType.fromisoformat(req.date)
    year = target_date.year
    b = req.battery
    battery = Battery(
        capacity_kwh=b.capacity_kwh,
        power_kw=b.power_kw,
        rte=b.rte,
    )
    grid_fee = req.grid_fee_eur_mwh

    # Load year's price data
    year_data = load_year(year, allow_fetch=False)
    target_day = None
    for day in year_data.days:
        if day.day == target_date:
            target_day = day
            break
    if target_day is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"no price data for {req.date}")

    # Solve ceiling LP for that single day
    ceil = solve_day_ceiling(
        list(target_day.prices), target_day.dt_h, battery,
        cycle_cap=None, grid_fee_charge=grid_fee,
    )

    # Run full backtest to get causal day arrays (mostly cached)
    from engine.backtest import run_backtest
    bt = run_backtest(
        years=(year,),
        params=Params(battery=battery),
        grid_fee_charge=grid_fee,
        use_cache=True, allow_fetch=False,
    )
    causal_days = bt.causal_result.days
    causal_day = None
    for cd in causal_days:
        if cd.day == target_date:
            causal_day = cd
            break

    def _avg_price(mwh: float, turnover: float) -> float | None:
        if mwh > 0:
            return round(turnover / mwh, 1)
        return None

    def _ceil_detail(day_dispatch):
        return {
            "gross_eur": round(day_dispatch.gross_eur, 2),
            "mwh_discharged": round(day_dispatch.mwh_discharged, 3),
            "mwh_charged": round(day_dispatch.mwh_charged, 3),
            "avg_buy_price": _avg_price(day_dispatch.mwh_charged, day_dispatch.purchase_turnover_eur),
            "avg_sell_price": _avg_price(day_dispatch.mwh_discharged, day_dispatch.sale_turnover_eur),
            "charge_kw": [round(v, 2) for v in day_dispatch.charge_kw] if day_dispatch.charge_kw else [],
            "discharge_kw": [round(v, 2) for v in day_dispatch.discharge_kw] if day_dispatch.discharge_kw else [],
            "soc_kwh": [round(v, 2) for v in day_dispatch.soc_kwh] if day_dispatch.soc_kwh else [],
        }

    def _causal_detail(cday):
        if cday is None:
            return {
                "gross_eur": 0.0, "mwh_discharged": 0.0, "mwh_charged": 0.0,
                "avg_buy_price": None, "avg_sell_price": None,
                "charge_kw": [], "discharge_kw": [], "soc_kwh": [],
            }
        return {
            "gross_eur": round(cday.gross_eur, 2),
            "mwh_discharged": round(cday.mwh_discharged, 3),
            "mwh_charged": round(cday.mwh_charged, 3),
            "avg_buy_price": _avg_price(cday.mwh_charged, cday.purchase_turnover_eur),
            "avg_sell_price": _avg_price(cday.mwh_discharged, cday.sale_turnover_eur),
            "charge_kw": [round(v, 2) for v in cday.charge_kw] if cday.charge_kw else [],
            "discharge_kw": [round(v, 2) for v in cday.discharge_kw] if cday.discharge_kw else [],
            "soc_kwh": [round(v, 2) for v in cday.soc_kwh] if cday.soc_kwh else [],
        }

    # Find best/worst ceiling days by gross
    best_day = worst_day = None
    for day in year_data.days:
        d = solve_day_ceiling(
            list(day.prices), day.dt_h, battery,
            cycle_cap=None, grid_fee_charge=grid_fee,
        )
        if best_day is None or d.gross_eur > best_day[1]:
            best_day = (day.day.isoformat(), d.gross_eur)
        if worst_day is None or d.gross_eur < worst_day[1]:
            worst_day = (day.day.isoformat(), d.gross_eur)

    available_dates = [d.day.isoformat() for d in year_data.days]

    return {
        "date": req.date,
        "num_intervals": len(target_day.prices),
        "dt_h": target_day.dt_h,
        "prices": [round(p, 1) for p in target_day.prices],
        "best_date": best_day[0] if best_day else req.date,
        "worst_date": worst_day[0] if worst_day else req.date,
        "available_dates": available_dates,
        "ceiling": _ceil_detail(ceil),
        "causal": _causal_detail(causal_day),
    }
```

Important: the `run_backtest` call in `/day-detail` returns the `BacktestResult` which also needs to expose `bt.causal_result` (the raw `CausalResult` with per-day details). We need to check this — currently `BacktestResult` stores aggregated causal data, not the raw `CausalResult`.

##### Instructions for the engineer:
- Read the current `backend/main.py`.
- Add imports for `date`, `load_year`, `solve_day_ceiling`.
- Add request/response models.
- Add the POST /day-detail endpoint.
- Update `engine/backtest.py` to also expose `causal_result` on `BacktestResult`.

- [ ] **Step 2: Expose causal_result in BacktestResult**

Read `engine/backtest.py`. The `run_backtest()` function creates a `causal_result` variable but the `BacktestResult` dataclass doesn't include it. Add a `causal_result` field to `BacktestResult`:

```python
@dataclass(frozen=True)
class BacktestResult:
    years: tuple
    ceiling: dict
    causal: dict
    causal_terminal_value_eur: float
    year_data: dict
    causal_result: CausalResult  # NEW
```

Update the return in `run_backtest()`:

```python
    return BacktestResult(
        years=tuple(years),
        ceiling=ceiling,
        causal=causal,
        causal_terminal_value_eur=causal_result.terminal_value_eur,
        year_data=year_data,
        causal_result=causal_result,
    )
```

Also update `aggregate_causal` callers — the aggregate pass already works on the `CausalResult`, so no changes needed there.

- [ ] **Step 3: Verify backend compiles**

```bash
cd /Users/nikerane/repos/kellerwatt-sim && .venv/bin/python -c "from backend.main import app; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Run engine tests after backtest.py change**

```bash
cd /Users/nikerane/repos/kellerwatt-sim && .venv/bin/python -m pytest engine/tests/ -q
```

Expected: all 115 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py engine/backtest.py
git commit -m "feat(backend): add POST /day-detail endpoint for per-day dispatch"
```

---

### Task 3: Frontend — DayDetailResponse type + DailyDispatchChart component

**Files:**
- Modify: `web/src/data/playground.ts`
- Create: `web/src/components/DailyDispatchChart.tsx`

- [ ] **Step 1: Add DayDetailResponse types**

Add to `web/src/data/playground.ts`:

```ts
export interface StrategyDayDetail {
  gross_eur: number;
  mwh_discharged: number;
  mwh_charged: number;
  avg_buy_price: number | null;
  avg_sell_price: number | null;
  charge_kw: number[];
  discharge_kw: number[];
  soc_kwh: number[];
}

export interface DayDetailResponse {
  date: string;
  num_intervals: number;
  dt_h: number;
  prices: number[];
  best_date: string;
  worst_date: string;
  available_dates: string[];
  ceiling: StrategyDayDetail;
  causal: StrategyDayDetail;
}
```

- [ ] **Step 2: Write DailyDispatchChart component**

Write `web/src/components/DailyDispatchChart.tsx`:

```tsx
import { scaleLinear } from "d3-scale";
import type { DayDetailResponse } from "../data/playground";
import { DataMono } from "./DataMono";
import { Eyebrow } from "./Eyebrow";

const W = 280;
const H = 260;
const M = { top: 18, right: 32, bottom: 34, left: 38 };

function barPath(
  values: number[],
  x: (i: number) => number,
  y: (v: number) => number,
  baseline: number,
  barW: number,
  color: string,
): string {
  let d = "";
  for (let i = 0; i < values.length; i++) {
    if (values[i] <= 0) continue;
    const bx = x(i) - barW / 2;
    const bw = barW;
    const bh = Math.abs(y(values[i]) - y(baseline));
    const by = y(values[i]);
    d += `M${bx.toFixed(1)},${by.toFixed(1)}h${bw.toFixed(1)}v${bh.toFixed(1)}h${-bw.toFixed(1)}Z`;
  }
  return d;
}

interface Props {
  data: DayDetailResponse;
  strategy: "ceiling" | "causal";
}

export function DailyDispatchChart({ data, strategy }: Props) {
  const detail = data[strategy];
  const prices = data.prices;
  const N = data.num_intervals;

  const priceMin = Math.min(0, ...prices);
  const priceMax = Math.max(...prices) + 20;
  const kwMax = 50; // battery power is always 50 kW
  const socMax = 200; // battery capacity

  const x = scaleLinear().domain([0, N]).range([M.left, W - M.right]);
  const yPrice = scaleLinear().domain([priceMin, priceMax]).range([H - M.bottom, M.top]);
  const yKw = scaleLinear().domain([0, kwMax]).range([H - M.bottom, M.top]);
  const ySoc = scaleLinear().domain([0, socMax]).range([H - M.bottom, M.top]);

  const barW = Math.max(1, (W - M.left - M.right) / N - 0.5);

  // Stepped price line
  let pricePath = "";
  for (let i = 0; i < N; i++) {
    const px = x(i);
    const py = yPrice(prices[i]);
    pricePath += `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`;
  }

  // SoC dashed line
  let socPath = "";
  for (let i = 0; i < detail.soc_kwh.length; i++) {
    const px = x(i);
    const py = ySoc(detail.soc_kwh[i]);
    socPath += `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`;
  }

  const chargePath = barPath(detail.charge_kw, x, yKw, 0, barW, "var(--clay-red)");
  const dischargePath = barPath(detail.discharge_kw, x, yKw, 0, barW, "#4CAF50");

  const tone = strategy === "ceiling" ? "ember" : "neutral";
  const title = strategy === "ceiling" ? "Ceiling (perfect foresight)" : "Causal (walk-forward)";

  const avgBuy = detail.avg_buy_price !== null ? `€${detail.avg_buy_price}` : "—";
  const avgSell = detail.avg_sell_price !== null ? `€${detail.avg_sell_price}` : "—";

  return (
    <div className="kw-card" style={{ padding: "20px 24px" }}>
      <span style={{ display: "block", marginBottom: 14 }}>
        <Eyebrow>{title}</Eyebrow>
      </span>
      <p style={{ fontSize: "0.82rem", fontFamily: "var(--mono)", lineHeight: 1.5, margin: 0 }}>
        Bought{" "}
        <DataMono tone="muted" size="sm">{detail.mwh_charged.toFixed(3)}</DataMono>
        {" "}MWh @ avg {avgBuy}{" "}
        → Sold{" "}
        <DataMono tone="muted" size="sm">{detail.mwh_discharged.toFixed(3)}</DataMono>
        {" "}MWh @ avg {avgSell}{" "}
        | Net: <DataMono tone={tone} size="sm">€{detail.gross_eur.toFixed(2)}</DataMono>
      </p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}: bought ${detail.mwh_charged.toFixed(2)}MWh, sold ${detail.mwh_discharged.toFixed(2)}MWh, net €${detail.gross_eur.toFixed(2)}`}
        style={{ width: "100%", marginTop: 16 }}
      >
        {/* Price line */}
        <path d={pricePath} fill="none" stroke="rgba(245,241,234,0.45)" strokeWidth={1.2} />
        {/* Zero line */}
        <line x1={M.left} x2={W - M.right} y1={yPrice(0)} y2={yPrice(0)} stroke="rgba(245,241,234,0.2)" strokeWidth={0.5} />
        {/* Charge bars */}
        <path d={chargePath} fill="var(--clay-red)" opacity={0.7} />
        {/* Discharge bars */}
        <path d={dischargePath} fill="#4CAF50" opacity={0.7} />
        {/* SoC line (dashed) */}
        {socPath && <path d={socPath} fill="none" stroke="var(--ember)" strokeWidth={1.0} strokeDasharray="3,3" opacity={0.6} />}
      </svg>
      <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: "0.72rem", opacity: 0.6 }}>
        <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--clay-red)", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }} />Charge</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, background: "#4CAF50", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }} />Discharge</span>
        <span><span style={{ display: "inline-block", width: 10, borderTop: "1.5px dashed var(--ember)", verticalAlign: "middle", marginRight: 4 }} />SoC</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

---

### Task 4: Wire Daily Dispatch into PlaygroundPage

**Files:**
- Modify: `web/src/pages/PlaygroundPage.tsx`

- [ ] **Step 1: Add daily dispatch state and fetch logic to PlaygroundPage**

Below the existing state declarations in `PlaygroundPage`, add:

```tsx
const [dayDetail, setDayDetail] = useState<DayDetailResponse | null>(null);
const [selectedDate, setSelectedDate] = useState<string>("");
const [dayLoading, setDayLoading] = useState(false);
const dayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
```

Add a fetch function for day details:

```tsx
const fetchDayDetail = useCallback(
  async (dateStr: string) => {
    if (!ENGINE_URL) return;
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
      // Keep previous detail if fetch fails
    } finally {
      if (mountedRef.current) setDayLoading(false);
    }
  },
  [values],
);

// Auto-fetch best day when engine is ready and solve is complete
useEffect(() => {
  if (engineStatus === "solved" && dayDetail === null && ENGINE_URL) {
    // The solve response has years — fetch best day for the latest year
    const latestYear = Math.max(...response.years);
    // We don't know best_date until we ask. Just use a known good date.
    fetchDayDetail(`${latestYear}-06-15`);
  }
}, [engineStatus, dayDetail, response.years, fetchDayDetail]);
```

Add the Daily Dispatch section below the Results section (before the footer). Import `DailyDispatchChart` and `DayDetailResponse`:

```tsx
import { DailyDispatchChart } from "../components/DailyDispatchChart";
import type { DayDetailResponse } from "../data/playground";
```

Add the section:

```tsx
{/* Daily Dispatch */}
<section className="kw-section kw-section--bone">
  <div className="kw-section__inner">
    <Eyebrow>Daily dispatch</Eyebrow>
    <p className="kw-lead" style={{ marginTop: 8, marginBottom: 20 }}>
      See the battery trade on a real day. The price curve shows the day-ahead
      market; green bars are discharge, red bars are charge.
    </p>

    {/* Navigation */}
    <div style={{ display: "flex", gap: 10, marginBottom: 24, flexWrap: "wrap", alignItems: "center" }}>
      <button
        type="button"
        className="kw-toggle__btn"
        disabled={!dayDetail || selectedDate === dayDetail.best_date}
        onClick={() => fetchDayDetail(dayDetail!.best_date)}
        style={{ fontSize: "0.8rem" }}
      >
        ★ Best Day
      </button>
      <button
        type="button"
        className="kw-toggle__btn"
        disabled={!dayDetail || selectedDate === dayDetail.worst_date}
        onClick={() => fetchDayDetail(dayDetail!.worst_date)}
        style={{ fontSize: "0.8rem" }}
      >
        ▼ Worst Day
      </button>
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
      {dayLoading && <span style={{ fontSize: "0.78rem", opacity: 0.6 }}>Loading…</span>}
    </div>

    {dayDetail && (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <DailyDispatchChart data={dayDetail} strategy="ceiling" />
        <DailyDispatchChart data={dayDetail} strategy="causal" />
      </div>
    )}
    {!dayDetail && !ENGINE_URL && (
      <p style={{ fontSize: "0.88rem", opacity: 0.6 }}>
        Daily dispatch visualization requires the live engine backend.
      </p>
    )}
  </div>
</section>
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

---

### Task 5: Tests + CSS + final verify

**Files:**
- Create: `web/src/components/DailyDispatchChart.test.tsx`
- Modify: `web/src/pages/PlaygroundPage.test.tsx` (minor updates)
- Modify: `web/src/styles/app.css`

- [ ] **Step 1: Write DailyDispatchChart test**

Write `web/src/components/DailyDispatchChart.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DailyDispatchChart } from "./DailyDispatchChart";
import type { DayDetailResponse } from "../data/playground";

const mockData: DayDetailResponse = {
  date: "2025-03-14",
  num_intervals: 96,
  dt_h: 0.25,
  prices: Array.from({ length: 96 }, (_, i) => 30 + i * 0.5),
  best_date: "2025-04-17",
  worst_date: "2025-01-01",
  available_dates: ["2025-01-01", "2025-03-14", "2025-04-17"],
  ceiling: {
    gross_eur: 23.45,
    mwh_discharged: 0.18,
    mwh_charged: 0.19,
    avg_buy_price: 38.2,
    avg_sell_price: 78.9,
    charge_kw: [0, 50, 50, 0],
    discharge_kw: [50, 0, 0, 0],
    soc_kwh: [20, 63, 106, 86],
  },
  causal: {
    gross_eur: 18.12,
    mwh_discharged: 0.15,
    mwh_charged: 0.16,
    avg_buy_price: 40.1,
    avg_sell_price: 75.3,
    charge_kw: [0, 50, 0, 0],
    discharge_kw: [0, 0, 0, 0],
    soc_kwh: [20, 63, 63, 63],
  },
};

describe("DailyDispatchChart", () => {
  it("renders ceiling strategy title", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(
      screen.getByText("Ceiling (perfect foresight)"),
    ).toBeInTheDocument();
  });

  it("renders causal strategy title", () => {
    render(<DailyDispatchChart data={mockData} strategy="causal" />);
    expect(
      screen.getByText("Causal (walk-forward)"),
    ).toBeInTheDocument();
  });

  it("shows the net margin in the summary", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByText(/€23\.45/)).toBeInTheDocument();
  });

  it("shows avg buy and sell prices", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByText(/€38\.2/)).toBeInTheDocument();
    expect(screen.getByText(/€78\.9/)).toBeInTheDocument();
  });

  it("renders an SVG chart", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("handles empty arrays gracefully", () => {
    const emptyData: DayDetailResponse = {
      ...mockData,
      num_intervals: 0,
      prices: [],
      ceiling: {
        ...mockData.ceiling,
        charge_kw: [],
        discharge_kw: [],
        soc_kwh: [],
      },
    };
    render(<DailyDispatchChart data={emptyData} strategy="ceiling" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests — expect 7 passed**

```bash
cd web && npx vitest run src/components/DailyDispatchChart.test.tsx
```

Expected: 7 passed.

- [ ] **Step 3: Update PlaygroundPage test for new nav buttons**

Add to `PlaygroundPage.test.tsx` — a test for best/worst day buttons and date picker being visible:

```tsx
  it("renders daily dispatch nav controls", () => {
    render(<PlaygroundPage />);
    expect(screen.getByText(/Best Day/)).toBeInTheDocument();
    expect(screen.getByText(/Worst Day/)).toBeInTheDocument();
    // The date input should be there
    const dateInput = document.querySelector('input[type="date"]');
    expect(dateInput).toBeInTheDocument();
  });
```

- [ ] **Step 4: Add minimal CSS for the dispatch chart cards**

Append to `web/src/styles/app.css`:

```css
/* ---- daily dispatch ----------------------------------------------------- */

@media (max-width: 700px) {
  .kw-dispatch-grid {
    grid-template-columns: 1fr !important;
  }
}
```

Also update the grid in `PlaygroundPage.tsx` to use `className="kw-dispatch-grid"` instead of inline style:

```tsx
<div className="kw-dispatch-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
```

- [ ] **Step 5: Full verify**

```bash
cd web && npm run verify
```

Expected: typecheck + all tests + build + leak scan all green.

- [ ] **Step 6: Run engine tests**

```bash
cd /Users/nikerane/repos/kellerwatt-sim && .venv/bin/python -m pytest engine/tests/ -q
```

Expected: all 115 engine tests pass.

- [ ] **Step 7: Commit**

```bash
git add web/src/data/playground.ts web/src/components/DailyDispatchChart.tsx web/src/components/DailyDispatchChart.test.tsx web/src/pages/PlaygroundPage.tsx web/src/pages/PlaygroundPage.test.tsx web/src/styles/app.css
git commit -m "feat(web): daily dispatch chart with Best/Worst day nav"
```
