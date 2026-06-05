# KellerWatt Interactive Playground — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive "Playground" page with stepped sliders that re-run the Python engine via a FastAPI backend hosted on Hugging Face Spaces, with health-check warm-up on page load.

**Architecture:** React slider page on GitHub Pages calls `POST /solve` on a HF Spaces Docker container running the Python engine. The backend bundles cached price data and calls `engine.backtest.run_backtest()` with user-chosen battery + economic params. Sliders are stepped, debounced 500ms, and disabled during fetch. A background `GET /health` ping on page load warms the cold-starting Space.

**Tech Stack:** FastAPI + uvicorn (backend), React + Vite + d3-scale (frontend), Docker (HF Spaces), GitHub Pages (static hosting).

---

### Task 1: Backend FastAPI server

**Files:**
- Create: `backend/main.py`
- Create: `backend/__init__.py` (empty)

- [ ] **Step 1: Create the backend package init**

```bash
mkdir -p backend
touch backend/__init__.py
```

- [ ] **Step 2: Write the FastAPI server**

Write `backend/main.py`:

```python
"""KellerWatt engine API — FastAPI server for the interactive playground.

Deployed to Hugging Face Spaces (free Docker tier). The engine and cached
price data are bundled in the Docker image so no live API calls are needed.
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.backtest import run_backtest
from engine.contracts import SCHEMA_VERSION
from engine.metrics import assumed_case_gross
from engine.params import Battery, Params

app = FastAPI(title="KellerWatt Engine", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


class BatteryRequest(BaseModel):
    capacity_kwh: float
    power_kw: float
    rte: float


class SolveRequest(BaseModel):
    battery: BatteryRequest
    assumed_spread_eur_mwh: float
    cycles_per_day: float
    grid_fee_eur_mwh: float
    exemption: Literal["retained", "lost"]


@app.post("/solve")
async def solve(req: SolveRequest):
    b = req.battery
    battery = Battery(
        capacity_kwh=b.capacity_kwh,
        power_kw=b.power_kw,
        rte=b.rte,
    )
    usable_mwh = battery.usable_mwh

    # Build params for each scenario
    grid_fee = req.grid_fee_eur_mwh

    # --- Ceiling (grid fee = 0 for retained, grid_fee for lost) ---
    params_ret = Params(
        battery=battery, cycle_cap_per_day=req.cycles_per_day,
    )
    bt_ret = run_backtest(params=params_ret, grid_fee_charge=0, use_cache=True, allow_fetch=False)

    # If exemption is lost, also solve with the grid fee
    if req.exemption == "lost" and grid_fee > 0:
        bt_lost = run_backtest(params=Params(battery=battery, cycle_cap_per_day=req.cycles_per_day),
                               grid_fee_charge=grid_fee, use_cache=True, allow_fetch=False)
    else:
        bt_lost = bt_ret

    years = list(bt_ret.years)

    def _ceiling_dict(bt):
        return {
            str(y): {
                "spread_eur_mwh": round(bt.ceiling[y].implied_spread, 1),
                "gross_eur": round(bt.ceiling[y].gross_eur, 0),
                "cycles_ac": round(bt.ceiling[y].cycles_ac, 3),
            }
            for y in years
        }

    def _causal_dict(bt):
        return {
            str(y): {
                "spread_eur_mwh": round(bt.causal[y].implied_spread, 1) if y in bt.causal else None,
                "gross_eur": round(bt.causal[y].gross_eur, 0) if y in bt.causal else None,
                "cycles_ac": round(bt.causal[y].cycles_ac, 3) if y in bt.causal else None,
            }
            for y in years
        }

    assumed_gross = round(assumed_case_gross(
        req.assumed_spread_eur_mwh, usable_mwh, req.cycles_per_day, 365,
    ), 0)

    return {
        "schema_version": SCHEMA_VERSION,
        "years": years,
        "assumed": {
            "spread_eur_mwh": req.assumed_spread_eur_mwh,
            "gross_eur": assumed_gross,
            "cycles_per_day": req.cycles_per_day,
        },
        "ceiling": _ceiling_dict(bt_ret),
        "causal_retained": _causal_dict(bt_ret),
        "causal_lost": _causal_dict(bt_lost),
    }
```

- [ ] **Step 3: Verify the server imports correctly**

```bash
cd backend && python -c "from main import app; print('OK')"
```

Expected: `OK` (may need to install fastapi first).

---

### Task 2: Backend Dockerfile + requirements

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write requirements.txt**

Write `backend/requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pulp==3.3.2
highspy==1.14.0
numpy==2.4.6
numpy-financial==1.0.0
```

- [ ] **Step 2: Write the Dockerfile**

Write `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for HiGHS (it bundles a shared lib but needs libstdc++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Engine source
COPY engine/ engine/

# Price data cache (bundled, no live fetches in the container)
COPY engine/data/cache/ engine/data/cache/

# FastAPI app
COPY backend/main.py .

# HF Spaces expects port 7860
ENV PORT=7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 3: Build the Docker image locally to verify**

```bash
docker build -t kellerwatt-engine -f backend/Dockerfile .
```

Expected: build succeeds, pulls python:3.11-slim, installs deps.

- [ ] **Step 4: Smoke-test the container**

```bash
docker run -d -p 7860:7860 --name kw-test kellerwatt-engine
sleep 3
curl http://localhost:7860/health
docker stop kw-test && docker rm kw-test
```

Expected: `{"status":"ok"}`.

---

### Task 3: Frontend scaffold — playground HTML entry + Vite config + React entry

**Files:**
- Create: `web/playground.html`
- Create: `web/src/playground.tsx`
- Modify: `web/vite.config.ts`

- [ ] **Step 1: Create playground.html entry point**

Write `web/playground.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KellerWatt — playground</title>
    <meta
      name="description"
      content="Change the battery and economic assumptions. Watch the KellerWatt numbers move — live-solved on a Python engine."
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/playground.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Create React entry point**

Write `web/src/playground.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/inter";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./tokens/colors_and_type.css";
import "./styles/app.css";
import { PlaygroundPage } from "./pages/PlaygroundPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PlaygroundPage />
  </React.StrictMode>,
);
```

- [ ] **Step 3: Add playground entry to Vite config**

Edit `web/vite.config.ts` — add the `playground` entry to `rollupOptions.input`:

```ts
build: {
  rollupOptions: {
    input: {
      main: `${root}index.html`,
      methodology: `${root}methodology.html`,
      playground: `${root}playground.html`,
    },
  },
},
```

##### Instructions for the engineer:
- Read `web/vite.config.ts` to get the current content.
- Locate the `input:` block inside `rollupOptions` (lines 13-17).
- Add line `playground: `${root}playground.html`,` after the methodology line.

- [ ] **Step 4: Verify the scaffold builds**

```bash
cd web && npm run build
```

Expected: build succeeds, `dist/playground.html` exists.

- [ ] **Step 5: Commit**

```bash
git add web/playground.html web/src/playground.tsx web/vite.config.ts backend/
git commit -m "feat(web): playground scaffold + FastAPI backend"
```

---

### Task 4: PlaygroundSlider component

**Files:**
- Create: `web/src/components/PlaygroundSlider.tsx`

- [ ] **Step 1: Write the stepped slider component**

Write `web/src/components/PlaygroundSlider.tsx`:

```tsx
import { DataMono } from "./DataMono";

export interface SliderDef {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit: string;
  /** Optional: format the value differently from the raw number (e.g. "90%" for 0.90). */
  formatValue?: (v: number) => string;
}

interface Props {
  slider: SliderDef;
  value: number;
  onChange: (key: string, value: number) => void;
  disabled: boolean;
}

export function PlaygroundSlider({ slider, value, onChange, disabled }: Props) {
  return (
    <label className="kw-slider" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="kw-slider__label" style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ fontFamily: "var(--sans)", fontSize: "0.85rem", color: "var(--slate)" }}>
          {slider.label}
        </span>
        <DataMono tone="ember" size="sm">
          {slider.formatValue ? slider.formatValue(value) : `${value} ${slider.unit}`}
        </DataMono>
      </span>
      <input
        type="range"
        min={slider.min}
        max={slider.max}
        step={slider.step}
        value={value}
        onChange={(e) => onChange(slider.key, parseFloat(e.target.value))}
        disabled={disabled}
        className="kw-slider__input"
        aria-label={slider.label}
      />
      <span
        className="kw-slider__range-labels"
        style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", opacity: 0.5 }}
      >
        <span>{slider.formatValue ? slider.formatValue(slider.min) : `${slider.min}`}</span>
        <span>{slider.formatValue ? slider.formatValue(slider.max) : `${slider.max}`}</span>
      </span>
    </label>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

---

### Task 5: PlaygroundResults component

**Files:**
- Create: `web/src/components/PlaygroundResults.tsx`

- [ ] **Step 1: Define the API response types**

Write `web/src/data/playground.ts`:

```ts
/** Shape of the POST /solve response from the HF Spaces backend. */
export interface YearResult {
  spread_eur_mwh: number | null;
  gross_eur: number | null;
  cycles_ac: number | null;
}

export interface SolveResponse {
  schema_version: string;
  years: number[];
  assumed: {
    spread_eur_mwh: number;
    gross_eur: number;
    cycles_per_day: number;
  };
  ceiling: Record<string, YearResult>;
  causal_retained: Record<string, YearResult>;
  causal_lost: Record<string, YearResult>;
}
```

- [ ] **Step 2: Write the PlaygroundResults component**

Write `web/src/components/PlaygroundResults.tsx`:

```tsx
import { DataMono } from "./DataMono";
import type { SolveResponse } from "../data/playground";
import { euro, eurPerMwh, cycles } from "../data/load";

interface Props {
  data: SolveResponse;
  year: number;
}

interface Col {
  key: string;
  title: string;
  sub: string;
  tone: "ember" | "muted" | "neutral";
  spread: number | null;
  annual: number | null;
  cyclesPerDay: number | null;
}

export function PlaygroundResults({ data, year }: Props) {
  const yr = String(year);
  const ceil = data.ceiling[yr];
  const causalR = data.causal_retained[yr];
  const causalL = data.causal_lost[yr];

  const cols: Col[] = [
    {
      key: "assumed", title: "Assumed", sub: "your inputs", tone: "muted",
      spread: data.assumed.spread_eur_mwh,
      annual: data.assumed.gross_eur,
      cyclesPerDay: data.assumed.cycles_per_day,
    },
    {
      key: "ceiling", title: "Ceiling", sub: "perfect foresight", tone: "ember",
      spread: ceil?.spread_eur_mwh ?? null,
      annual: ceil?.gross_eur ?? null,
      cyclesPerDay: ceil?.cycles_ac ?? null,
    },
    {
      key: "causal-retained", title: "Causal", sub: "exemption retained", tone: "neutral",
      spread: causalR?.spread_eur_mwh ?? null,
      annual: causalR?.gross_eur ?? null,
      cyclesPerDay: causalR?.cycles_ac ?? null,
    },
    {
      key: "causal-lost", title: "Conservative", sub: "exemption lost", tone: "neutral",
      spread: causalL?.spread_eur_mwh ?? null,
      annual: causalL?.gross_eur ?? null,
      cyclesPerDay: causalL?.cycles_ac ?? null,
    },
  ];

  const valCls = (c: Col) => (c.key === "ceiling" ? "kw-table__col-validated" : "");

  return (
    <table className="kw-table" style={{ marginTop: 32 }}>
      <caption className="kw-eyebrow" style={{ marginBottom: 18 }}>
        Captured spread · {year}
      </caption>
      <thead>
        <tr>
          <th scope="col" aria-label="metric" />
          {cols.map((c) => (
            <th scope="col" key={c.key} className={valCls(c)}>
              {c.title}
              <span className="kw-table__row-note">{c.sub}</span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">
            Implied spread
            <span className="kw-table__row-note">€ / MWh discharged</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone={c.tone} size="lg">
                {eurPerMwh(c.spread)}
              </DataMono>
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Annual figure
            <span className="kw-table__row-note">gross / net per year</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone={c.tone === "ember" ? "ember" : "neutral"}>{euro(c.annual)}</DataMono>
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Cycles / day
            <span className="kw-table__row-note">AC delivered</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone="muted">{cycles(c.cyclesPerDay)}</DataMono>
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

---

### Task 6: PlaygroundPage — slider UI + fetch logic + debounce + warm-up

**Files:**
- Create: `web/src/pages/PlaygroundPage.tsx`

- [ ] **Step 1: Write the SVG spread chart for live results**

Write `web/src/components/PlaygroundChart.tsx`:

```tsx
import { scaleLinear, scalePoint } from "d3-scale";
import type { SolveResponse } from "../data/playground";

const W = 600;
const H = 300;
const M = { top: 20, right: 28, bottom: 44, left: 52 };

function linePath(pts: Array<[number, number]>): string {
  return pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

interface Props {
  data: SolveResponse;
}

export function PlaygroundChart({ data }: Props) {
  const years = data.years;
  const assumed = data.assumed.spread_eur_mwh;
  const ceiling = years.map((y) => data.ceiling[String(y)]?.spread_eur_mwh ?? 0);
  const causal = years.map((y) => data.causal_retained[String(y)]?.spread_eur_mwh ?? 0);

  const yMax = Math.ceil((Math.max(assumed, ...ceiling) + 6) / 10) * 10;
  const x = scalePoint<string>().domain(years.map(String)).range([M.left, W - M.right]).padding(0.5);
  const y = scaleLinear().domain([0, yMax]).range([H - M.bottom, M.top]);

  const px = (i: number) => x(String(years[i]))!;
  const ceilPts = ceiling.map((v, i) => [px(i), y(v)] as [number, number]);
  const causPts = causal.map((v, i) => [px(i), y(v)] as [number, number]);
  const bracket =
    linePath(ceilPts) +
    " " +
    linePath([...causPts].reverse()).replace("M", "L") +
    " Z";
  const yTicks = [0, 20, 40, 60, 80, 100, 120].filter((t) => t <= yMax);

  return (
    <div className="kw-chart" style={{ marginTop: 40 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Playground spread chart. Assumed €${assumed}/MWh. ${years
          .map((yr, i) => `${yr}: ceiling €${ceiling[i].toFixed(1)}, causal €${causal[i].toFixed(1)}`)
          .join("; ")}.`}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line className="kw-chart__grid" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text className="kw-chart__axis" x={M.left - 12} y={y(t)} dy="0.32em" textAnchor="end">
              {t}
            </text>
          </g>
        ))}
        <path className="kw-chart__bracket" d={bracket} />
        <line className="kw-chart__assumed" x1={M.left} x2={W - M.right} y1={y(assumed)} y2={y(assumed)} />
        <text className="kw-chart__axis" x={W - M.right} y={y(assumed) - 8} textAnchor="end">
          €{assumed} assumed
        </text>
        <path className="kw-chart__causal" d={linePath(causPts)} />
        <path className="kw-chart__ceiling" d={linePath(ceilPts)} />
        {ceilPts.map(([cx, cy], i) => (
          <g key={i}>
            <circle className="kw-chart__dot" cx={cx} cy={cy} r={4.5} />
            <text className="kw-chart__axis" x={cx} y={cy - 14} textAnchor="middle"
              style={{ fill: "var(--ember)", fontSize: 13 }}>
              €{ceiling[i].toFixed(1)}
            </text>
          </g>
        ))}
        {causPts.map(([cx, cy], i) => (
          <text key={i} className="kw-chart__axis" x={cx} y={cy + 20} textAnchor="middle">
            €{causal[i].toFixed(1)}
          </text>
        ))}
        {years.map((yr, i) => (
          <text key={yr} className="kw-chart__axis" x={px(i)} y={H - M.bottom + 26} textAnchor="middle">
            {yr}
          </text>
        ))}
      </svg>
      <div className="kw-chart__legend">
        <span><span className="kw-chart__swatch" style={{ borderColor: "var(--ember)" }} />Ceiling</span>
        <span><span className="kw-chart__swatch" style={{ borderColor: "rgba(245,241,234,0.85)" }} />Causal</span>
        <span><span className="kw-chart__swatch" style={{ borderColor: "rgba(245,241,234,0.45)", borderTopStyle: "dashed" }} />Assumed</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write the PlaygroundPage component**

Write `web/src/pages/PlaygroundPage.tsx`:

```tsx
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { DataMono } from "../components/DataMono";
import { PlaygroundSlider } from "../components/PlaygroundSlider";
import { PlaygroundResults } from "../components/PlaygroundResults";
import { PlaygroundChart } from "../components/PlaygroundChart";
import type { SliderDef } from "../components/PlaygroundSlider";
import type { SolveResponse } from "../data/playground";
import { results as defaultResults, euro } from "../data/load";
import { YEARS } from "../data/load";

// ------- engine URL (HF Space) ----------
// When running locally without the HF backend, leave as empty string to use baked-in defaults only.
const ENGINE_URL = "https://nikerane-kellerwatt-engine.hf.space";

// ------- slider definitions ----------
const SLIDERS: SliderDef[] = [
  { key: "capacity_kwh", label: "Battery capacity", min: 50, max: 500, step: 25, default: 200, unit: "kWh" },
  { key: "power_kw", label: "Power rating", min: 25, max: 250, step: 25, default: 50, unit: "kW" },
  { key: "rte", label: "Round-trip efficiency", min: 0.75, max: 0.95, step: 0.05, default: 0.90, unit: "%",
    formatValue: (v: number) => `${Math.round(v * 100)}%` },
  { key: "assumed_spread", label: "Assumed spread", min: 20, max: 120, step: 5, default: 80, unit: "€/MWh" },
  { key: "cycles_per_day", label: "Daily cycle cap", min: 0.5, max: 3.0, step: 0.25, default: 1.5, unit: "cyc/day" },
  { key: "grid_fee", label: "Grid energy fee", min: 0, max: 50, step: 5, default: 0, unit: "€/MWh" },
];

type EngineStatus = "warming" | "ready" | "solving" | "solved" | "error";

/** Build default SolveResponse from the baked-in sim_results.json so the page
    shows real numbers before the backend wakes up. */
function defaultSolveResponse(): SolveResponse {
  const bp = defaultResults.assumptions.business_plan;
  const years = defaultResults.provenance.years;
  const ceil: Record<string, { spread_eur_mwh: number | null; gross_eur: number | null; cycles_ac: number | null }> = {};
  const causal: Record<string, { spread_eur_mwh: number | null; gross_eur: number | null; cycles_ac: number | null }> = {};
  for (const s of defaultResults.strategies) {
    for (const yr of s.years) {
      const key = String(yr.year);
      if (s.id === "lp_ceiling") {
        ceil[key] = { spread_eur_mwh: yr.ceiling_eur_mwh, gross_eur: yr.gross_eur, cycles_ac: yr.cycles_ac };
      } else if (s.id === "causal_walkforward") {
        causal[key] = { spread_eur_mwh: yr.causal_eur_mwh, gross_eur: yr.gross_eur, cycles_ac: yr.cycles_ac };
      }
    }
  }
  return {
    schema_version: defaultResults.schema_version,
    years,
    assumed: { spread_eur_mwh: bp.assumed_spread_eur_mwh, gross_eur: bp.assumed_gross_eur, cycles_per_day: bp.assumed_cycles_per_day },
    ceiling: ceil,
    causal_retained: causal,
    causal_lost: causal, // fallback: same as retained until live solve
  };
}

export function PlaygroundPage() {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(SLIDERS.map((s) => [s.key, s.default]))
  );
  const [exemption, setExemption] = useState<"retained" | "lost">("retained");
  const [response, setResponse] = useState<SolveResponse>(defaultSolveResponse);
  const [engineStatus, setEngineStatus] = useState<EngineStatus>("warming");
  const latest = Math.max(...YEARS);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const healthPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // ------ health-check warm-up on mount ------
  useEffect(() => {
    mountedRef.current = true;
    let attempts = 0;
    const poll = () => {
      if (!ENGINE_URL) {
        setEngineStatus("ready");
        return;
      }
      fetch(`${ENGINE_URL}/health`)
        .then((r) => {
          if (r.ok && mountedRef.current) {
            setEngineStatus("ready");
            if (healthPollRef.current) clearInterval(healthPollRef.current);
          }
        })
        .catch(() => { /* still warming */ });
      attempts++;
      if (attempts > 12) {
        // 60s timeout — engine didn't come up
        if (healthPollRef.current) clearInterval(healthPollRef.current);
        if (mountedRef.current) setEngineStatus("error");
      }
    };
    poll(); // immediate first attempt
    healthPollRef.current = setInterval(poll, 5000);
    return () => {
      mountedRef.current = false;
      if (healthPollRef.current) clearInterval(healthPollRef.current);
    };
  }, []);

  // ------ debounced solve ------
  const solve = useCallback(
    (vals: Record<string, number>, exc: "retained" | "lost") => {
      if (!ENGINE_URL) return;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(async () => {
        setEngineStatus("solving");
        try {
          const res = await fetch(`${ENGINE_URL}/solve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              battery: {
                capacity_kwh: vals.capacity_kwh,
                power_kw: vals.power_kw,
                rte: vals.rte,
              },
              assumed_spread_eur_mwh: vals.assumed_spread,
              cycles_per_day: vals.cycles_per_day,
              grid_fee_eur_mwh: vals.grid_fee,
              exemption: exc,
            }),
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data: SolveResponse = await res.json();
          if (mountedRef.current) {
            setResponse(data);
            setEngineStatus("solved");
          }
        } catch {
          if (mountedRef.current) setEngineStatus("error");
        }
      }, 500);
    },
    [],
  );

  const handleSlider = useCallback(
    (key: string, value: number) => {
      const next = { ...values, [key]: value };
      setValues(next);
      solve(next, exemption);
    },
    [values, exemption, solve],
  );

  const handleExemption = useCallback(
    (exc: "retained" | "lost") => {
      setExemption(exc);
      solve(values, exc);
    },
    [values, solve],
  );

  const disabled = engineStatus === "solving";

  return (
    <main className="kw-page">
      <SiteNav current="playground" />

      {/* Hero */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <div className="kw-fade">
            <Eyebrow ember>Interactive playground</Eyebrow>
          </div>
          <div className="kw-fade kw-fade--2" style={{ marginTop: 28 }}>
            <Couplet
              as="h1"
              size="xl"
              first="Change the assumptions."
              second="Watch the numbers move."
            />
          </div>
          <p className="kw-lead kw-fade kw-fade--3" style={{ marginTop: 28 }}>
            Every slider change re-runs the Python arbitrage engine live —
            the same solver, the same real DE-LU prices. Results appear in seconds.
          </p>
        </div>
      </section>

      {/* Sliders panel */}
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
            <Eyebrow>Parameters</Eyebrow>
            <EngineBadge status={engineStatus} onRetry={() => solve(values, exemption)} />
          </div>
          <div
            className="kw-sliders-grid"
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 24 }}
          >
            {SLIDERS.map((s) => (
              <PlaygroundSlider
                key={s.key}
                slider={s}
                value={values[s.key]}
                onChange={handleSlider}
                disabled={disabled}
              />
            ))}
            {/* exemption toggle */}
            <label className="kw-toggle" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ fontFamily: "var(--sans)", fontSize: "0.85rem", color: "var(--slate)" }}>
                §118(6) exemption
              </span>
              <span style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className={`kw-toggle__btn ${exemption === "retained" ? "kw-toggle__btn--active" : ""}`}
                  onClick={() => handleExemption("retained")}
                  disabled={disabled}
                >
                  Retained
                </button>
                <button
                  type="button"
                  className={`kw-toggle__btn ${exemption === "lost" ? "kw-toggle__btn--active" : ""}`}
                  onClick={() => handleExemption("lost")}
                  disabled={disabled}
                >
                  Lost
                </button>
              </span>
            </label>
          </div>
        </div>
      </section>

      {/* Results */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <Eyebrow ember>Results — live solved</Eyebrow>
          <div style={{ overflowX: "auto" }}>
            <PlaygroundResults data={response} year={latest} />
          </div>
          <PlaygroundChart data={response} />
        </div>
      </section>

      <footer className="kw-footer">
        <Eyebrow>Engine</Eyebrow>
        <p style={{ marginTop: 14 }}>
          Same Python solver (HiGHS {defaultResults.solver.version}) with real DE-LU day-ahead
          prices from Energy-Charts. Ceilings are perfect-foresight upper bounds. Causal is a
          backtested estimate. IRR / payback stay null until diligence items land.
        </p>
      </footer>
    </main>
  );
}

function EngineBadge({ status, onRetry }: { status: EngineStatus; onRetry: () => void }) {
  const config: Record<EngineStatus, { text: string; dot: string }> = {
    warming: { text: "Warming up…", dot: "var(--ember)" },
    ready: { text: "Ready ✓", dot: "#4CAF50" },
    solving: { text: "Solving…", dot: "var(--ember)" },
    solved: { text: "Solved ✓", dot: "#4CAF50" },
    error: { text: "Unreachable", dot: "var(--clay-red)" },
  };
  const c = config[status];
  const isError = status === "error";

  return (
    <span
      role="status"
      aria-live="polite"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: "0.78rem",
        fontFamily: "var(--mono)",
        color: c.dot,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: c.dot,
          animation: status === "warming" || status === "solving" ? "kw-pulse 1.4s ease-in-out infinite" : undefined,
        }}
      />
      {c.text}
      {isError && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginLeft: 6,
            background: "none",
            border: "1px solid var(--clay-red)",
            color: "var(--clay-red)",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: "0.72rem",
            padding: "1px 6px",
          }}
        >
          Retry
        </button>
      )}
    </span>
  );
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Verify the build succeeds**

```bash
cd web && npm run build
```

Expected: build succeeds, `dist/playground.html` exists.

- [ ] **Step 5: Commit**

```bash
git add web/src/data/playground.ts web/src/components/PlaygroundSlider.tsx web/src/components/PlaygroundResults.tsx web/src/components/PlaygroundChart.tsx web/src/pages/PlaygroundPage.tsx
git commit -m "feat(web): playground page with sliders, live solve, warm-up"
```

---

### Task 7: PlaygroundPage tests + CSS tokens for slider

**Files:**
- Create: `web/src/pages/PlaygroundPage.test.tsx`
- Modify: `web/src/styles/app.css`

- [ ] **Step 1: Write the PlaygroundPage test**

Write `web/src/pages/PlaygroundPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { PlaygroundPage } from "./PlaygroundPage";

// We mock fetch globally — the page calls the HF Space backend.
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as any;

beforeEach(() => {
  mockFetch.mockReset();
  // Default: health check succeeds immediately
  mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) });
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
    expect(screen.getByRole("button", { name: "Retained" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lost" })).toBeInTheDocument();
  });

  it("shows default results on initial render (baked-in data)", () => {
    render(<PlaygroundPage />);
    // The default baked-in data should show something for the latest year
    expect(screen.getByText("Captured spread · 2025")).toBeInTheDocument();
  });

  it("shows warming status on mount", () => {
    render(<PlaygroundPage />);
    expect(screen.getByText("Warming up…")).toBeInTheDocument();
  });

  it("transitions to ready when health check succeeds", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) });
    render(<PlaygroundPage />);
    await waitFor(() => {
      expect(screen.getByText(/Ready/)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("renders cross-page nav with playground link", () => {
    render(<PlaygroundPage />);
    expect(screen.getByRole("link", { name: "Playground" })).toHaveAttribute(
      "href",
      "/playground.html",
    );
  });

  it("slider changes update values without crashing", () => {
    render(<PlaygroundPage />);
    const slider = screen.getByLabelText("Battery capacity") as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "300" } });
    // It shouldn't crash — value update is synchronous
    expect(screen.getByText("300 kWh")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests — expect 2 failures (nav link + engine status)**

```bash
cd web && npx vitest run src/pages/PlaygroundPage.test.tsx
```

Expected: at least 2 failures — "Playground" nav link doesn't exist yet (missing from SiteNav), and warming/ready status text may not match. Other tests may pass or fail depending on defaults.

- [ ] **Step 3: Add slider + toggle CSS tokens**

Append to `web/src/styles/app.css`:

```css
/* ---- playground slider ---- */

.kw-slider__input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: var(--border);
  cursor: pointer;
}

.kw-slider__input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ember);
  cursor: pointer;
  border: 2px solid var(--bone);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
}

.kw-slider__input::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ember);
  cursor: pointer;
  border: 2px solid var(--bone);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
}

.kw-slider__input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ---- exemption toggle ---- */

.kw-toggle__btn {
  padding: 4px 14px;
  border: 1px solid var(--border);
  border-radius: var(--r-4);
  background: transparent;
  color: var(--slate);
  font-family: var(--mono);
  font-size: 0.82rem;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}

.kw-toggle__btn--active {
  border-color: var(--ember);
  background: rgba(232, 155, 79, 0.12);
  color: var(--ember);
}

.kw-toggle__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ---- pulse animation for engine status dot ---- */

@keyframes kw-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
```

- [ ] **Step 4: Run all tests**

```bash
cd web && npx vitest run
```

Expected: the two nav-related tests still fail (SiteNav doesn't have "Playground" yet). All other tests should pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/PlaygroundPage.test.tsx web/src/styles/app.css
git commit -m "test(web): PlaygroundPage tests + slider CSS tokens"
```

---

### Task 8: Add "Playground" link to SiteNav

**Files:**
- Modify: `web/src/components/SiteNav.tsx`

- [ ] **Step 1: Update the SiteNav component**

Edit `web/src/components/SiteNav.tsx`:
- Change the `current` prop type from `"honesty" | "methodology"` to `"honesty" | "methodology" | "playground"`
- Add the "Playground" nav link after the Methodology link

```tsx
/** Cross-page navigation between the honesty page, methodology page, and playground. */
export function SiteNav({ current }: { current: "honesty" | "methodology" | "playground" }) {
  return (
    <nav className="kw-nav" aria-label="Primary">
      <a className="kw-nav__brand" href="/index.html">KellerWatt</a>
      <span className="kw-nav__links">
        <a aria-current={current === "honesty" ? "page" : undefined} href="/index.html">
          The number
        </a>
        <a aria-current={current === "methodology" ? "page" : undefined} href="/methodology.html">
          Methodology
        </a>
        <a aria-current={current === "playground" ? "page" : undefined} href="/playground.html">
          Playground
        </a>
      </span>
    </nav>
  );
}
```

##### Instructions for the engineer:
- Read `web/src/components/SiteNav.tsx` to get the current content.
- Replace `"honesty" | "methodology"` with `"honesty" | "methodology" | "playground"` in the type annotation on line 2.
- Add the "Playground" `<a>` tag after the Methodology `<a>` tag on line 11.

- [ ] **Step 2: Run all tests — expect all passing**

```bash
cd web && npx vitest run
```

Expected: all tests pass (including PlaygroundPage nav test).

- [ ] **Step 3: Full verify**

```bash
cd web && npm run verify
```

Expected: typecheck + tests + leak scan all green.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/SiteNav.tsx
git commit -m "feat(web): add Playground link to SiteNav"
```

---

### Task 9: Final verification + build

**Files:** None new.

- [ ] **Step 1: Run the full web verification**

```bash
cd web && npm run verify
```

Expected: typecheck clean, all tests pass, leak scan clean.

- [ ] **Step 2: Run engine tests to ensure nothing broken**

```bash
cd /Users/nikerane/repos/kellerwatt-sim && .venv/bin/python -m pytest engine/tests/ -q
```

Expected: all engine tests pass.

- [ ] **Step 3: Run the backend smoke-test (if Docker is available)**

```bash
docker build -t kellerwatt-engine -f backend/Dockerfile . && docker run -d -p 7860:7860 --name kw-final-test kellerwatt-engine && sleep 3 && curl http://localhost:7860/health && curl -s -X POST http://localhost:7860/solve -H 'Content-Type: application/json' -d '{"battery":{"capacity_kwh":200,"power_kw":50,"rte":0.90},"assumed_spread_eur_mwh":80,"cycles_per_day":1.5,"grid_fee_eur_mwh":0,"exemption":"retained"}' | python -m json.tool | head -20 && docker stop kw-final-test && docker rm kw-final-test
```

Expected: `{"status":"ok"}` followed by a valid solve response with years and ceiling data.

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final playground verification"
```
