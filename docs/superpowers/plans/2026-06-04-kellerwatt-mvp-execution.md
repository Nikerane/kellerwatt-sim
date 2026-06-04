# KellerWatt MVP — Execution Plan (Codex-cross-checked)

> **This supersedes** `2026-06-04-kellerwatt-arbitrage-sim.md` (the original TDD plan). It is the
> scope-cut, twice-reviewed plan: engine + one honesty page. Approved 2026-06-04.

## Context

We validated the core economics on real 2023–2025 DE-LU prices with a corrected LP
(`scripts/validate_number.py`). **What is actually validated** is the *perfect-foresight
ceiling*: **€61.1 / 68.3 / 77.3 per MWh** (2023/24/25), always below the deck's assumed €80,
with spreads **widening**. The "~€55–66/MWh realistic" figure is an **85%-of-ceiling estimate,
NOT yet a backtested causal result** — until a causal strategy is implemented it is an
*unvalidated sensitivity*, never "firm/realistic" (Codex cross-check finding 1).

A prior Codex review found 18 issues in the original plan (`docs/codex-review-response.md`); a
second Codex pass cross-checked *this* plan and found 14 more. Both are folded in below.

Scope-cut MVP (review #17): corrected headless Python engine → JSON → one static, on-brand
"honesty page" (validated ceilings + clearly-labelled estimates, IRR *provisional*). **Out of
scope:** owner app, film, full motion system, FCR/aFRR co-optimization, live API, Streamlit.
**Parallel (teammate):** aggregator term sheet (#8), §118(6) legal memo (#9) —
`docs/open-actions-for-team.md`.

## Architecture

```
engine/ (Python)  data → dispatch(LP ceiling + causal benchmark) → economics → metrics → backtest → export
web/ (Vite+React+TS)  reads a results JSON → static honesty page
```
Reuse the validated spike as reference for the LP, Berlin grouping, validation, multi-year run.

## A0 — Contracts first (BEFORE any module; Codex 5, 6, 7)

- **JSON Schema** at `engine/schema/sim_results.schema.json`: concrete fields/types/units/
  nullability + `schema_version`. Required: `schema_version`, `provenance`, `solver`
  (name+version+status+tolerance), `assumptions`, `strategies[]` (`lp_ceiling`,
  `causal_walkforward`), `scenarios[]` (`causal_exemption_retained`, `causal_exemption_lost`),
  per-year `{year, ceiling_eur_mwh, causal_eur_mwh|null, cycles_ac, cycles_cell, gross_eur}`,
  each metric carrying `methodology_label` + `status` (`validated|estimate|provisional`).
- **Fee-basis models** up front (Codex 4): BKV fee on `gross_turnover|sale_turnover|net_margin`,
  parameterised, **inside the dispatch objective** where marginal.
- **Case IDs**: `causal_exemption_retained` (grid-fee 0), `causal_exemption_lost` (energy fee
  €/MWh on charge); **ancillary defaults to 0** in both.

## A — Engine (TDD)

`engine/{params,data_load,dispatch,economics,metrics,backtest,export}.py`, `engine/tests/`.

- **A1 scaffold.** pyproject (pulp[highs], numpy-financial, jsonschema, pytest), pinned solver.
- **A2 data (Codex 9).** Berlin-local delivery days; exact calendar rules: inclusive Berlin
  date range; require 365/366 complete days; allow DST 23/25-h + quarter-hour equivalents;
  validate the 2025-10-01 hourly→15-min transition; **fail loud** on unexplained missing/
  duplicate (no silent skip); report nulls + points/day histogram.
- **A3 dispatch (Codex 1,3,4,10).** (a) **LP ceiling** = spike: binary no-simultaneity, AC-side
  cashflows, RTE once, cyclic SoC, cycle cap, **all marginal charges in the objective**.
  (b) **Causal walk-forward benchmark** (replaces capture-% fudge): quantile thresholds fixed
  from the trailing 28 complete Berlin days, no current-day recalibration, SoC carried
  continuously between days, fixed initial SoC, deterministic terminal restoration, identical
  power/eff/cap/marginal-cost. Report as causal-benchmark-vs-ceiling **bracket**, not a floor.
  Solver returns **optimal or fail**; record solver metadata.
- **A4 economics.** BKV fee: implement + **test all three bases**. Grid-fee: two named
  scenarios (not a slider). FCR/aFRR: **default 0**; if shown, export reserved power/energy +
  availability + cap, forbid full-capacity ancillary + full-capacity arbitrage together.
- **A5 metrics (Codex 5,11).** Implied spread = gross / MWh discharged. **Assumed-case
  identity** = `spread × usable_MWh × cycles_per_day × operating_days` (+ separated ancillary −
  fees); identity test. Export both `cycles_ac` + `cycles_cell` (formulas); cell-throughput for
  degradation. Neg-price metric → "cashflow during negative-price intervals." IRR →
  `methodology_label:"constant-EBITDA project IRR"` + `status:"provisional"`.
- **A6 backtest.** 2023–2025, day-by-day, cached dispatch, both strategies.
- **A7 export (Codex 2,6,13).** Validate against the A0 schema. **Two separate artifacts**:
  `dist/real/sim_results.json` (never committed/public) + `dist/sanitized/sim_results.json`.
  Drop the `sample` field unless used. Producer + React-consumer parse tests.
- **A8 integration (Codex 8).** Assert each year's ceiling within tight tolerance of
  61.1/68.3/77.3 €/MWh (+ gross, cycles, day-count, `simul==0`). Causal fixtures only after the
  causal strategy reproducibly runs.

## B — Honesty page (Vite + React + TS; scope-cut, Codex 14)

- **B1** scaffold + tokens (`colors_and_type.css`) + Fontsource fonts + Ember focus-ring / 18px.
- **B2** minimal primitives: `Eyebrow`, `Couplet`, `DataMono` (tnum), `Card`. **Defer**
  `HexField`, idle drift, non-essential motion.
- **B3** case table: Assumed €80 / LP ceiling (validated) / Causal (benchmark) / Conservative
  `exemption_lost`; Mono values; IRR/payback show methodology label + "provisional."
- **B4** widening-spread chart: d3-scale + hand-rolled SVG, 2023→2025 ceiling-vs-causal bracket.
- **B5** minimal composition: one Hearth hero couplet, chart, table, diligence-in-progress.
  `fadeUp` entrance only.
- **B6** deploy: sanitized artifact → public static (Pages/Vercel); real stays local; CI step
  fails if real case IDs or €61/68/77 appear in the sanitized bundle.

## Sequencing

A0 → A1–A8 (~3 days) → B1–B6 (~2 days). Diligence #8/#9 parallel; an aggregator dispatch
restriction may become an **engine change**, not pure data.

## Verification

`pytest -q` green (calendar/fail-loud, no-simultaneity, BKV bases, assumed identity, cycle
formulas, schema producer+consumer, per-year ceiling fixtures) · `python -m engine.export` →
both artifacts validate, ceilings 61.1/68.3/77.3 · `npm run build && preview` → table+chart from
JSON, IRR provisional, sanitized scan passes · brand check vs `DESIGN.md`.

## Honesty guardrails (non-negotiable)

- **Validated = the ceilings only**; causal/85% is an *estimate* until the walk-forward runs.
- Real numbers never reach a public artifact.
- IRR/payback provisional until #8 (fee basis) + #9 (grid-fee scenario) land.
