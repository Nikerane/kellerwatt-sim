# KellerWatt Battery-Arbitrage Simulation — MVP Design Spec

**Date:** 2026-06-04
**Status:** Approved
**Author:** KellerWatt founder + Claude

## 1. Context

KellerWatt installs 200 kWh LFP batteries in apartment-building basements, leases the
space from owners, and earns money trading electricity (spot arbitrage + grid services +
tariff reduction). The company is pre-seed (TUM ELAB), targeting a 2026 launch.

The pitch's credibility was challenged ("yellow card") on the revenue assumptions. This
MVP is a **simulation dashboard** that runs a basement battery against *real* German
day-ahead prices and reconciles the result to the business-plan assumptions — turning an
asserted spreadsheet into a backtested, slider-driven model that judges can stress-test
live.

The headline deliverable is an **apples-to-apples comparison**: the spreadsheet *assumes*
~€80/MWh net captured spread at 1.5 cycles/day; the simulation *derives* the implied
spread and cycles from an actual dispatch on real prices, and shows both side by side.

## 2. Goals / Non-Goals

**Goals**
- Backtest a 200 kWh / 50 kW / 4-hour battery on real DE-LU day-ahead prices (2024→present).
- Compute, from the actual dispatch: implied captured spread (€/MWh), implied cycles/day,
  year-1 gross, EBITDA, simple payback, unlevered IRR.
- Present a side-by-side "spreadsheet assumed vs simulation produced vs conservative case"
  panel, plus four judge-draggable stress-test sliders (capture %, cycles/day, BKV fee %, CapEx).
- An animated 3-minute demo view (price curve + charge/discharge + SoC + cumulative € counter).
- Run entirely on pre-downloaded data — **no network call on stage, ever**.

**Non-Goals (v1) — deferred to v2**
- Live API calls during the demo. Rolling-intrinsic intraday uplift. True FCR/aFRR
  co-optimization. ML dispatch. Auth / DB / multi-user. React frontend. Modeling a single
  site as its own balancing group (we frame the unit as one node in an aggregated pool;
  the 12% BKV fee is the cost of that pooling).

## 3. Architecture

```
kellerwatt-sim/
  data/
    prices_de_lu.parquet         # pre-downloaded DE-LU day-ahead, 2024-01-01 -> present
    fcr_afrr_2024.csv            # representative ancillary prices (used as parameters)
  src/
    data_load.py    # load_prices(path, start, end) -> DataFrame[ts, price_eur_mwh]
    dispatch.py     # dispatch_lp(prices_day, batt) | dispatch_threshold(prices_day, batt) -> Schedule
    economics.py    # compute_pnl(schedule, prices_day, econ) -> DailyPnL
    metrics.py      # compute_metrics(backtest_result, econ) -> Metrics
    backtest.py     # run_backtest(prices, batt, econ, strategy) -> BacktestResult
    params.py       # BatteryParams, EconParams dataclasses + defaults
  app/
    streamlit_app.py
  notebooks/
    01_download_prices.ipynb     # one-time Energy-Charts -> parquet (+ ENTSO-E cross-check)
  tests/
  requirements.txt  README.md
```

**Key boundary:** `dispatch_lp` and `dispatch_threshold` return the **same `Schedule`**
(per-step `charge_kw`, `discharge_kw`, `soc_kwh`), so they are interchangeable and
everything downstream is strategy-agnostic. Intraday / ML strategies drop in later as
just another `dispatch_*` function.

Each module has one job, a typed interface, and is unit-testable in isolation.

## 4. Data flow

`prices_de_lu.parquet` → `data_load` (stitch hourly→15-min at the 2025-10-01 SDAC go-live)
→ `backtest` loops **day-by-day**: each day's price vector → chosen `dispatch_*` →
`Schedule` → `economics` → `DailyPnL` → aggregated `BacktestResult` → `metrics` →
Streamlit renders. The notebook builds the parquet once; the app never hits the network.

## 5. Data layer

- **Primary source:** Energy-Charts `https://api.energy-charts.info/price?bzn=DE-LU&start=YYYY-MM-DD&end=YYYY-MM-DD`
  — JSON `{unix_seconds[], price[], unit}`, EUR/MWh, no token, CC BY 4.0 (attribute "Energy-Charts.info").
- **Cross-check:** ENTSO-E via `entsoe-py` (`query_day_ahead_prices('DE_LU', ...)`), free
  emailed token, used only in the notebook to validate magnitudes — never at runtime.
- **Parquet schema:** `ts` (UTC, tz-aware), `price_eur_mwh` (float). Resolution: hourly
  before 2025-10-01, 15-minute from 2025-10-01 (SDAC 15-min day-ahead go-live). `data_load`
  upsamples pre-Oct-2025 hourly to 15-min (forward-fill within the hour) so the backtest
  runs a uniform Δt=0.25h grid; this choice is documented and toggleable.
- `fcr_afrr_2024.csv`: representative FCR (~€50/MW per 4h-block context) and aFRR capacity
  (~€13/MW/h up, €10/MW/h down) from regelleistung.net, consumed as economic parameters.

## 6. Dispatch engine

**Battery params (fixed, exposed as parameters):** capacity 200 kWh, power 50 kW
(→ 4-hour), SoC band 10–100%, round-trip efficiency 90% (η_chg = η_dis = √0.9 ≈ 0.949).

**LP (primary), solved per delivery day** — T quarter-hour steps, Δt = 0.25 h:
- Variables: `c_t ≥ 0` (charge kW), `d_t ≥ 0` (discharge kW), `SoC_t` (kWh).
- Objective: maximize `Σ price_t·(d_t·η_dis − c_t/η_chg)·Δt − λ·Σ(c_t+d_t)·Δt`
  (last term = degradation cost; λ ≈ battery_cost / (cycle_life · throughput_per_cycle)).
- SoC balance: `SoC_t = SoC_{t-1} + (η_chg·c_t − d_t/η_dis)·Δt`.
- Power: `0 ≤ c_t, d_t ≤ 50`. Energy: `0.10·200 ≤ SoC_t ≤ 200`.
- Throughput / cycle cap: `Σ d_t·Δt ≤ cycles_cap · E_usable` (slider; default 1.5).
- Boundary: `SoC_0 = SoC_T` (each day's P&L is self-contained).
- Solved with PuLP + HiGHS (`pip install pulp[highs]`); <1s/day.
- **RTE is applied in exactly one place** (the energy balance) to avoid double-taxing efficiency.

**Threshold (toggle):** charge in the cheapest-N / below buy-€ quarter-hours, discharge in
the dearest-N / above sell-€, subject to the same SoC/power/cycle bounds. Returns the same
`Schedule`. Demonstrates "even a dumb rule earns X".

## 7. Economics + honesty layer

`compute_pnl` turns each `Schedule` into P&L using:
- BKV / aggregator fee (default **12% of trading revenue**).
- FCR/aFRR shown as a **separate, capped, partitioned line** — reserves a power fraction +
  SoC band, **never additive on the full 200 kWh**. Modeled as a parameterized annual figure
  with the partition enforced, not co-optimized.
- **Grid fee on charged energy (€/MWh), default 0**, with a clearly labelled downside
  scenario (the rejected energy-based AgNes alternative, ~€66.50/MWh, strips ~4 pts off IRR).
- Degradation (€/MWh throughput), CapEx, OpEx/yr, owner lease (€800–1,200/yr).

`compute_metrics` **derives from the actual dispatch** (does not assume):
- **implied captured spread (€/MWh)** = gross trading revenue ÷ MWh discharged.
- **implied cycles/day** = MWh discharged ÷ (E_usable × operating days).
- year-1 gross, EBITDA, simple payback, unlevered IRR (CapEx annualized via standard annuity).
- **€ of profit attributable to negative-price hours** (sensitivity flag; Germany had 457
  negative-price hours in 2024, 573 in 2025).
- A **capture-haircut factor** (default 85%) applied to LP gross to model live vs
  perfect-foresight capture; this drives the "conservative case".

## 8. UI / 3-minute demo

- **Animated core:** one representative week — price curve, charge (green) at troughs /
  discharge (red) at peaks, SoC bar, **cumulative € counter ticking up** (~10s playthrough).
- **Honesty panel (3 columns):**
  - *Spreadsheet assumed* — €80/MWh · 1.5 cyc/day → €9,947 gross / €6,758 EBITDA / ~5yr / ~18.7% IRR.
  - *Simulation produced* — implied €X/MWh · Y cyc/day → recomputed figures.
  - *Conservative* — capture haircut ~85%, grid-fee downside on, cycles from profitability.
- **Four stress-test sliders** judges can drag — capture %, cycles/day cap, BKV fee %, CapEx —
  with payback/IRR updating live. Plus a strategy toggle (LP / threshold) and the
  grid-fee-on-charge downside slider.
- **Modo anchor** shown as a directional reality check: 4-hour German BESS, 2026 COD, ~13.7%
  unlevered IRR (utility-scale, fully-stacked — not like-for-like, labelled as such).

## 9. Parameters & defaults

| Param | Default | Slider? |
|---|---|---|
| capacity_kwh | 200 | no |
| power_kw | 50 | no |
| soc_min / soc_max | 10% / 100% | no |
| eta_rt | 0.90 | no |
| cycles_cap (per day) | 1.5 | **yes** |
| capture_pct | 85% | **yes** |
| bkv_fee_pct | 12% | **yes** |
| capex_eur | ≈140,000 (research default) | **yes** |
| grid_fee_on_charge_eur_mwh | 0 | **yes** (downside) |
| fcr_afrr_eur_yr | from csv, capped | no |
| degradation_eur_mwh | derived | no |
| owner_lease_eur_yr | 1,000 | no |

All baseline figures (the "Spreadsheet assumed" column — €9,947 gross / €6,758 EBITDA /
~18.7% IRR / ~5yr payback / CapEx ≈€140k) live as documented defaults in a single
`params.py` (a `BASELINE` constant), so the founder swaps in the real spreadsheet numbers
by editing one file. A `SANITIZED` preset with placeholder figures drives the public build.

## 10. Risk / plot-hole guardrails (built into the model)

- **FCR/aFRR stacking:** capped + partitioned line; never additive on the same 200 kWh.
- **Cycles realism:** LP *derives* cycles from profitability; default the conservative slider
  lower (real short-duration DE fleets cycle ~1.1–1.3×/day).
- **RTE double-count:** applied once, in the energy balance.
- **Grid-fee/StromStG exemptions (§118(6) EnWG, AgNes):** grid-fee-on-charge slider + labelled
  downside scenario; treat as needing legal verification before any fundraising claim.
- **§14a curtailment:** optional small annual cycle haircut when enabled.
- **BKV minimum portfolio:** frame the unit as one node in an aggregated pool.
- **Perfect-foresight gap:** capture-haircut (~85%) baked into the conservative case.
- **Negative-price hours:** LP exploits them; report the € share they contribute.
- **Empirical reality gate:** if 2024 implied spread comes in < ~€60/MWh, revise the base
  case down *before* the pitch, not on stage.

## 11. Testing

- **Unit — dispatch:** on a toy price vector, LP charges cheap / discharges dear; SoC and
  power bounds respected; `SoC_0 = SoC_T`; throughput ≤ cycle cap. Threshold respects the
  same bounds.
- **Unit — economics:** a known `Schedule` maps to a known `DailyPnL`.
- **Unit — metrics:** implied-spread identity (gross ÷ MWh discharged) and implied-cycles
  identity hold on synthetic input.
- **Integration:** full 2024 backtest produces an implied spread in a plausible band
  (~€40–110/MWh) and an IRR directionally near the Modo ~13.7% anchor.

## 12. Tech stack & deployment

Python 3.12 · pandas · numpy · numpy-financial (IRR) · pulp[highs] · plotly · streamlit ·
entsoe-py (data-prep only). React/Next is explicitly out of scope for v1 (flashier but costs
days we don't have).

**Deployment (two builds, one codebase):**
- **Local, real numbers** — `streamlit run` on the founder's laptop for the live pitch;
  `params.py:BASELINE` holds the true figures, never committed/deployed.
- **Sanitized public** — same app deployed to Streamlit Community Cloud using
  `params.py:SANITIZED` (placeholder figures), selected via an env var / `?preset=` query
  param so judges can open it without exposing the real economics.
