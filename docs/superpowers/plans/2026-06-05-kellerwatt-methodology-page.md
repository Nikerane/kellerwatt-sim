# Methodology Page + Formula Traceability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second static page (`/methodology.html`) plus an inline formula-marker system that makes every number on the honesty page traceable to its typeset equation, live values, and the engine file that implements it — with links to data and sources throughout — and ship it as a deployable static bundle.

**Architecture:** Vite multi-page build (`index.html` + `methodology.html`, no router). A single typed **formula registry** (`src/data/formulas.ts`) is the source of truth, consumed by an inline `FormulaMark` (hover/tap popover) and by expanded cards on the methodology page. A small, tested engine change adds per-year negative-price cashflow and a `market` stats block to the export (schema 1.1.0).

**Tech Stack:** Python 3.12 + PuLP/HiGHS (engine); Vite + React + TS, KaTeX (self-hosted), d3-scale, Vitest + Testing Library (web). Run engine tests with `/Users/nikerane/repos/kellerwatt-sim/.venv/bin/pytest` from the repo root; web from `web/` with `npm run test` / `npm run build`.

**Conventions:**
- Engine TDD: failing test → run red → implement → run green → commit + push.
- Web TDD: Vitest test → red → implement → green. Commit + push after each task.
- Never hardcode a number the engine can produce; read it from the JSON.
- The validated ceilings (61.1/68.3/77.3) and `simul=0` must remain unchanged.

---

## File structure (created / modified)

```
engine/dispatch.py          MOD  DayDispatch.neg_price_cashflow_eur + compute it
engine/backtest.py          MOD  StrategyYear.neg_price_cashflow_eur + aggregate + cache bump
engine/export.py            MOD  emit neg_price_cashflow_eur + market[]
engine/contracts.py         MOD  SCHEMA_VERSION 1.1.0 + minimal_example fields
engine/schema/sim_results.schema.json  MOD  year_result field + market[]
engine/tests/test_*.py      MOD  cover the new fields

web/vite.config.ts          MOD  multi-page input (main + methodology)
web/methodology.html        NEW  second entry point
web/src/methodology.tsx     NEW  methodology entry
web/src/pages/HonestyPage.tsx   NEW  current App body moved here
web/src/pages/MethodologyPage.tsx  NEW
web/src/App.tsx             MOD  thin shell rendering HonestyPage (or delete; main renders HonestyPage)
web/src/data/links.ts       NEW  canonical source/data links
web/src/data/formulas.ts    NEW  formula registry (source of truth)
web/src/components/Katex.tsx        NEW
web/src/components/FormulaCard.tsx  NEW
web/src/components/FormulaMark.tsx  NEW
web/src/components/SiteNav.tsx      NEW
web/src/components/MarketTable.tsx  NEW
web/src/components/Limitations.tsx  NEW
web/src/data/types.ts       MOD  add MarketYear + year_result.neg_price_cashflow_eur
web/scripts/leak-scan.mjs   (unchanged; already scans whole dist)
web/README.md               MOD  deploy instructions
web/vercel.json             NEW  zero-config Vercel
```

---

## Task 1: Engine — per-year negative-price cashflow + market block (schema 1.1.0)

**Files:**
- Modify: `engine/dispatch.py`
- Modify: `engine/backtest.py`
- Modify: `engine/export.py`
- Modify: `engine/contracts.py`
- Modify: `engine/schema/sim_results.schema.json`
- Test: `engine/tests/test_dispatch.py`, `engine/tests/test_backtest.py`, `engine/tests/test_export.py`, `engine/tests/test_contracts.py`

- [ ] **Step 1: Failing test — DayDispatch carries negative-price cashflow.** Add to `engine/tests/test_dispatch.py`:

```python
def test_ceiling_reports_negative_price_cashflow():
    # Charge while paid (negative price), discharge when expensive.
    prices = [-100.0] * 4 + [200.0] * 4
    r = dispatch.solve_day_ceiling(prices, dt_h=1.0, battery=Battery(), cycle_cap=1.5)
    # cashflow during the negative-price intervals only; charging at -100 EARNS.
    assert r.neg_price_cashflow_eur > 0.0
    # empty day -> 0, no crash
    assert dispatch.solve_day_ceiling([], 1.0, Battery(), cycle_cap=1.5).neg_price_cashflow_eur == 0.0
```

- [ ] **Step 2: Run red.** `/.../.venv/bin/pytest engine/tests/test_dispatch.py::test_ceiling_reports_negative_price_cashflow -q` → FAIL (no attribute `neg_price_cashflow_eur`).

- [ ] **Step 3: Implement in `engine/dispatch.py`.** Add the field to `DayDispatch` (after `purchase_turnover_eur`):

```python
    neg_price_cashflow_eur: float  # cashflow during negative-price intervals (Codex 12)
```

In the `T == 0` early return, add `0.0` in that position. In the normal return, compute and pass it. Add the import at top: `from engine.metrics import cashflow_during_negative_intervals`. Before building the return, add:

```python
    neg_cf = cashflow_during_negative_intervals(prices, cv, dv, dt_h)
```

and pass `neg_price_cashflow_eur=neg_cf` in the `DayDispatch(...)` constructor. (`metrics` does not import `dispatch`, so no cycle.)

- [ ] **Step 4: Run green.** Same pytest command → PASS.

- [ ] **Step 5: Failing test — backtest aggregates it, cache is versioned.** Add to `engine/tests/test_backtest.py`:

```python
def test_aggregate_ceiling_sums_neg_price_cashflow():
    b = Battery()
    days = [_fake_day(100.0, 1.0, 1.1, 120.0, 20.0), _fake_day(50.0, 0.5, 0.55, 60.0, 10.0)]
    sy = bt.aggregate_ceiling(days, b, year=2024, day_count=2)
    assert sy.neg_price_cashflow_eur == pytest.approx(0.0)  # _fake_day defaults to 0
```

Update `_fake_day` in that file to pass `neg_price_cashflow_eur=0.0` to `DayDispatch(...)`.

- [ ] **Step 6: Run red.** `pytest engine/tests/test_backtest.py -q` → FAIL (StrategyYear has no `neg_price_cashflow_eur` / constructor mismatch).

- [ ] **Step 7: Implement in `engine/backtest.py`.**
  - Add `neg_price_cashflow_eur: float | None = None` to `StrategyYear`.
  - In `aggregate_ceiling`, compute `neg = sum(d.neg_price_cashflow_eur for d in days)` and pass `neg_price_cashflow_eur=neg`.
  - In the cache: add `"cache_v": 2` to the dict hashed by `_ceiling_signature` (invalidates old caches lacking the field). In `_solve_ceiling_days`, add `"neg_cf": r.neg_price_cashflow_eur` to the stored row dict, and when reconstructing `DayDispatch` from cache pass `neg_price_cashflow_eur=row["neg_cf"]`.
  - `aggregate_causal` leaves `neg_price_cashflow_eur=None`.

- [ ] **Step 8: Run green.** `pytest engine/tests/test_backtest.py -q` → PASS.

- [ ] **Step 9: Failing test — schema 1.1.0, year_result + market.** In `engine/tests/test_contracts.py` add:

```python
def test_schema_version_is_1_1_0():
    assert contracts.SCHEMA_VERSION == "1.1.0"

def test_year_result_requires_neg_price_cashflow(schema):
    req = schema["$defs"]["year_result"]["required"]
    assert "neg_price_cashflow_eur" in req

def test_market_block_in_schema_and_example(schema):
    assert "market" in schema["properties"]
    Draft202012Validator(schema).validate(contracts.minimal_example())
```

- [ ] **Step 10: Run red.** `pytest engine/tests/test_contracts.py -q` → FAIL.

- [ ] **Step 11: Implement contracts + schema.**
  - `engine/contracts.py`: `SCHEMA_VERSION = "1.1.0"`. In `minimal_example()` add `"neg_price_cashflow_eur": 0.0` to the year_result dict, and add a top-level `"market": [{"year": 2024, "negative_intervals": 457, "price_min": -135.4, "price_max": 936.3, "day_count": 366}]`.
  - `engine/schema/sim_results.schema.json`:
    - In `$defs.year_result`: add `"neg_price_cashflow_eur": {"type": ["number","null"]}` to `properties` and to `required`.
    - Add top-level `"market"` to `properties`: `{"type":"array","items":{"$ref":"#/$defs/market_year"}}` and to the root `required`.
    - Add `$defs.market_year`: `{"type":"object","additionalProperties":false,"required":["year","negative_intervals","price_min","price_max","day_count"],"properties":{"year":{"type":"integer"},"negative_intervals":{"type":"integer"},"price_min":{"type":"number"},"price_max":{"type":"number"},"day_count":{"type":"integer"}}}`.

- [ ] **Step 12: Run green.** `pytest engine/tests/test_contracts.py -q` → PASS.

- [ ] **Step 13: Failing test — export emits the fields.** In `engine/tests/test_export.py` extend `_strategy_year` to pass `neg_price_cashflow_eur=12.0` and add:

```python
def test_export_emits_neg_cashflow_and_market(results):
    ceiling = next(s for s in results["strategies"] if s["id"] == "lp_ceiling")
    assert all("neg_price_cashflow_eur" in yr for yr in ceiling["years"])
    assert isinstance(results["market"], list) and results["market"][0]["year"] in (2023, 2024, 2025)
```

(Also update `_fake_year_data` already returns `negative_intervals`, `price_min`, `price_max` — good.)

- [ ] **Step 14: Run red.** `pytest engine/tests/test_export.py -q` → FAIL.

- [ ] **Step 15: Implement in `engine/export.py`.**
  - In `_year_result`, add `"neg_price_cashflow_eur": _round(getattr(sy, "neg_price_cashflow_eur", None), 0)`.
  - In `build_results`, build `market` from `bt_result.year_data`:

```python
    market = [
        {
            "year": y,
            "negative_intervals": bt_result.year_data[y].negative_intervals,
            "price_min": round(bt_result.year_data[y].price_min, 1),
            "price_max": round(bt_result.year_data[y].price_max, 1),
            "day_count": bt_result.year_data[y].day_count,
        }
        for y in years
    ]
```

  Add `"market": market` to the `doc` dict (before the final `validate`).

- [ ] **Step 16: Run green + full engine suite.** `/.../.venv/bin/pytest` → all PASS (109+ new). Confirm `pytest -k integration` still locks 61.1/68.3/77.3.

- [ ] **Step 17: Regenerate artifacts + commit + push.**

```bash
/Users/nikerane/repos/kellerwatt-sim/.venv/bin/python -m engine.export
git -C /Users/nikerane/repos/kellerwatt-sim add -A
git -C /Users/nikerane/repos/kellerwatt-sim commit -m "feat(engine): per-year neg-price cashflow + market block, schema 1.1.0"
git -C /Users/nikerane/repos/kellerwatt-sim push origin main
```

---

## Task 2: Web multi-page scaffold + KaTeX + links + page split

**Files:**
- Modify: `web/vite.config.ts`
- Create: `web/methodology.html`, `web/src/methodology.tsx`, `web/src/pages/HonestyPage.tsx`, `web/src/pages/MethodologyPage.tsx`, `web/src/data/links.ts`, `web/src/components/Katex.tsx`, `web/src/components/SiteNav.tsx`, `web/vercel.json`
- Modify: `web/src/main.tsx`, `web/src/data/types.ts`, `web/package.json` (add katex)

- [ ] **Step 1: Install KaTeX.** `cd web && npm install katex@^0.16.11 && npm install -D @types/katex@^0.16.7`

- [ ] **Step 2: Vite multi-page input.** In `web/vite.config.ts` add inside `defineConfig({... })`:

```ts
import { resolve } from "node:path";
// ...
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        methodology: resolve(__dirname, "methodology.html"),
      },
    },
  },
```

(Keep `base: "./"`, `plugins`, `test`.) If `__dirname` is unavailable under ESM, use `fileURLToPath(new URL(".", import.meta.url))`.

- [ ] **Step 3: Second HTML entry.** Create `web/methodology.html` — copy `index.html`, change `<title>` to "KellerWatt — methodology & formulas", and `src="/src/methodology.tsx"`.

- [ ] **Step 4: Page split (failing test first).** Create `web/src/pages/HonestyPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { HonestyPage } from "./HonestyPage";
it("honesty page still leads with the hero couplet", () => {
  render(<HonestyPage />);
  expect(screen.getByRole("heading", { name: /We assumed €80 a megawatt-hour\./ })).toBeInTheDocument();
});
```

- [ ] **Step 5: Run red.** `cd web && npx vitest run src/pages/HonestyPage.test.tsx` → FAIL (no module).

- [ ] **Step 6: Move App body → HonestyPage.** Create `web/src/pages/HonestyPage.tsx` exporting `HonestyPage` with the **current `App.tsx` body** (rename `App` → `HonestyPage`). Add `<SiteNav current="honesty" />` at the top of the returned `<main>`. Update `web/src/main.tsx` to import and render `HonestyPage`. Keep `web/src/App.tsx` as `export { HonestyPage as App } from "./pages/HonestyPage";` so existing `App.test.tsx` keeps passing (or update the import in `App.test.tsx`).

- [ ] **Step 7: Run green.** `npx vitest run src/pages/HonestyPage.test.tsx src/App.test.tsx` → PASS.

- [ ] **Step 8: Methodology entry + minimal page.** Create `web/src/methodology.tsx` (mirror `main.tsx` imports, render `<MethodologyPage />`). Create `web/src/pages/MethodologyPage.tsx` returning a stub `<main><SiteNav current="methodology" /><h1 className="kw-couplet ...">Methodology</h1></main>` for now (filled in Task 4).

- [ ] **Step 9: SiteNav.** Create `web/src/components/SiteNav.tsx`:

```tsx
export function SiteNav({ current }: { current: "honesty" | "methodology" }) {
  return (
    <nav className="kw-nav" aria-label="Primary">
      <a className="kw-nav__brand" href="/index.html">KellerWatt</a>
      <span className="kw-nav__links">
        <a aria-current={current === "honesty" ? "page" : undefined} href="/index.html">The number</a>
        <a aria-current={current === "methodology" ? "page" : undefined} href="/methodology.html">Methodology</a>
      </span>
    </nav>
  );
}
```

Add `.kw-nav` styles to `src/styles/app.css` (hairline bottom, mono small links, Ember `aria-current`).

- [ ] **Step 10: Katex wrapper (failing test).** Create `web/src/components/Katex.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { Katex } from "./Katex";
it("renders tex to katex html without throwing", () => {
  const { container } = render(<Katex tex={"a = \\frac{b}{c}"} />);
  expect(container.querySelector(".katex")).toBeTruthy();
});
```

- [ ] **Step 11: Run red.** `npx vitest run src/components/Katex.test.tsx` → FAIL.

- [ ] **Step 12: Implement Katex.** Create `web/src/components/Katex.tsx`:

```tsx
import katex from "katex";
import "katex/dist/katex.min.css";
export function Katex({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = katex.renderToString(tex, { throwOnError: false, displayMode: display });
  return <span className="kw-katex" dangerouslySetInnerHTML={{ __html: html }} />;
}
```

- [ ] **Step 13: Run green.** Same command → PASS.

- [ ] **Step 14: links.ts.** Create `web/src/data/links.ts` with canonical links and a commit-aware code-link helper:

```ts
import { results } from "./load";
const COMMIT = results.provenance.git_commit ?? "main";
const REPO = "https://github.com/Nikerane/kellerwatt-sim";
export const LINKS = {
  energyChartsApi: "https://api.energy-charts.info/price?bzn=DE-LU",
  energyCharts: "https://energy-charts.info/",
  energyChartsDocs: "https://api.energy-charts.info/",
  enwg118: "https://www.gesetze-im-internet.de/enwg_2005/__118.html",
  repo: REPO,
  highs: "https://highs.dev/",
  pulp: "https://coin-or.github.io/pulp/",
  schema: `${REPO}/blob/${COMMIT}/engine/schema/sim_results.schema.json`,
};
export function engineFile(path: string, anchor?: string): string {
  return `${REPO}/blob/${COMMIT}/engine/${path}${anchor ? "#" + anchor : ""}`;
}
```

- [ ] **Step 15: types.ts.** In `web/src/data/types.ts`: add `neg_price_cashflow_eur: number | null;` to `YearResult`; add `export interface MarketYear { year: number; negative_intervals: number; price_min: number; price_max: number; day_count: number; }`; add `market: MarketYear[];` to `SimResults`.

- [ ] **Step 16: vercel.json + commit.** Create `web/vercel.json`:

```json
{ "buildCommand": "npm run build", "outputDirectory": "dist", "framework": "vite",
  "cleanUrls": true, "rewrites": [{ "source": "/methodology", "destination": "/methodology.html" }] }
```

Run `npm run build` (must succeed + leak-scan pass). Commit + push: `feat(web): multi-page scaffold, KaTeX, links, page split`.

---

## Task 3: Formula registry + FormulaCard + FormulaMark

**Files:**
- Create: `web/src/data/formulas.ts`, `web/src/components/FormulaCard.tsx`, `web/src/components/FormulaMark.tsx`
- Test: `web/src/data/formulas.test.ts`, `web/src/components/FormulaMark.test.tsx`

- [ ] **Step 1: Failing test — registry integrity.** Create `web/src/data/formulas.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { FORMULAS, getFormula } from "./formulas";
import { results } from "./load";

describe("formula registry", () => {
  it("has unique ids and required fields", () => {
    const ids = FORMULAS.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const f of FORMULAS) {
      expect(f.katex.length).toBeGreaterThan(0);
      expect(f.plain.length).toBeGreaterThan(0);
      expect(f.sources.length).toBeGreaterThan(0);
    }
  });
  it("every source/usedIn href is non-empty and https or in-app", () => {
    for (const f of FORMULAS)
      for (const l of [...f.sources, ...f.usedIn])
        expect(l.href).toMatch(/^(https:\/\/|\/|#)/);
  });
  it("live() runs against the real data without throwing", () => {
    for (const f of FORMULAS) if (f.live) expect(() => f.live!(results)).not.toThrow();
  });
  it("implied_spread live value matches the data", () => {
    const f = getFormula("implied_spread");
    expect(f.live!(results).expr).toMatch(/77\.3/);
  });
});
```

- [ ] **Step 2: Run red.** `npx vitest run src/data/formulas.test.ts` → FAIL.

- [ ] **Step 3: Implement the registry.** Create `web/src/data/formulas.ts`. Define the type and the catalog. Type:

```ts
import type { SimResults } from "./types";
import { LINKS, engineFile } from "./links";
import { strategy, yearOf } from "./load";

export interface FLink { label: string; href: string; }
export interface Formula {
  id: string;
  stage: "dispatch" | "causal" | "metrics" | "economics";
  title: string;
  katex: string;
  plain: string;
  variables: { sym: string; desc: string }[];
  usedIn: FLink[];
  sources: FLink[];
  live?: (d: SimResults) => { expr: string; note?: string };
}
export const FORMULAS: Formula[] = [ /* entries below */ ];
export function getFormula(id: string): Formula {
  const f = FORMULAS.find((x) => x.id === id);
  if (!f) throw new Error(`unknown formula ${id}`);
  return f;
}
```

Catalog — implement all of these (`katex` as TeX strings, `plain` one sentence, `sources` includes `{label:"engine/...", href: engineFile("...")}` and any law/solver link, `usedIn` links into the pages, `live` where a number exists). The 17 entries:

| id | stage | katex (TeX) | live |
|---|---|---|---|
| `eta_one_way` | dispatch | `\eta = \sqrt{\mathrm{RTE}}` | `η = √0.90 = 0.9487` |
| `soc_balance` | dispatch | `\mathrm{SoC}_t = \mathrm{SoC}_{t-1} + (\eta c_t - d_t/\eta)\,\Delta t` | — |
| `no_simultaneity` | dispatch | `c_t \le P y_t,\; d_t \le P(1-y_t),\; y_t\in\{0,1\}` | — |
| `cyclic_soc` | dispatch | `\mathrm{SoC}_{T-1} = \mathrm{SoC}_0` | — |
| `cycle_cap` | dispatch | `\sum_t d_t\,\Delta t \le \mathrm{cap}\cdot E_{\text{usable}}` | `1.5 × 180 = 270 kWh/day` |
| `ac_gross` | dispatch | `\mathrm{gross} = \sum_t \tfrac{p_t}{1000}(d_t-c_t)\,\Delta t` | ceiling 2025 gross |
| `causal_thresholds` | causal | `\text{charge if } p_t \le Q_{0.40},\;\text{discharge if } p_t \ge Q_{0.60}` (28-day trailing, dt-weighted) | — |
| `implied_spread` | metrics | `\text{spread} = \mathrm{gross} / \mathrm{MWh}_{\text{dis}}` | `€77.3 = €7,030 / 91.0 MWh (2025)` |
| `assumed_identity` | metrics | `\mathrm{gross} = \text{spread}\cdot E_{\text{usable}}\cdot \text{cyc/day}\cdot \text{days}` | `€7,884 = 80 × 0.18 × 1.5 × 365` |
| `cycles_ac` | metrics | `\text{cyc}_{ac} = \mathrm{MWh}_{\text{dis}} / (E_{\text{usable}}\cdot \text{days})` | 2025 value |
| `cycles_cell` | metrics | `\text{cyc}_{cell} = \text{cyc}_{ac}/\eta` | — |
| `neg_price_cashflow` | metrics | `\sum_{p_t<0} \tfrac{p_t}{1000}(d_t-c_t)\,\Delta t` | per-year value from `market`/year_result |
| `unlevered_irr` | metrics | `\mathrm{IRR}\big([-\mathrm{CapEx},\,\mathrm{EBITDA},\dots]\big)` | "provisional" note |
| `payback` | metrics | `\text{payback} = \mathrm{CapEx}/\mathrm{EBITDA}` | "provisional" note |
| `bkv_bases` | economics | `\text{sale}: r\,S;\;\text{gross}: r(|S|+|B|);\;\text{net}: r(S-B)` | — |
| `grid_fee_cost` | economics | `\text{cost} = f_{\text{€/MWh}}\cdot \mathrm{MWh}_{\text{charged}}` | lost-scenario value |
| `net_annual` | economics | `\text{net} = \text{margin} - \text{grid} - \text{BKV} + \text{ancillary}` | scenario net |

Each `live` reads from `results` (e.g. `implied_spread.live` = `() => ({ expr: `€${yearOf(strategy("lp_ceiling"),2025).ceiling_eur_mwh} = €${...gross} / ${...mwh} MWh (2025)` })`). Use the actual rounded fields already in the JSON.

- [ ] **Step 4: Run green.** `npx vitest run src/data/formulas.test.ts` → PASS.

- [ ] **Step 5: FormulaCard.** Create `web/src/components/FormulaCard.tsx`. Render **only `<span>` elements** (block via CSS) so it nests cleanly inside both an inline popover and a page `<div>`:

```tsx
import { Katex } from "./Katex";
import { results } from "../data/load";
import type { Formula } from "../data/formulas";

export function FormulaCard({ formula, compact = false }: { formula: Formula; compact?: boolean }) {
  const live = formula.live?.(results);
  return (
    <span className="kw-fcard" id={compact ? undefined : formula.id}>
      <span className="kw-fcard__title">{formula.title}</span>
      <span className="kw-fcard__eq"><Katex tex={formula.katex} display /></span>
      {live && <span className="kw-fcard__live"><Katex tex={live.expr} />{live.note ? ` — ${live.note}` : ""}</span>}
      <span className="kw-fcard__plain">{formula.plain}</span>
      {!compact && formula.variables.length > 0 && (
        <span className="kw-fcard__vars">
          {formula.variables.map((v) => <span key={v.sym} className="kw-fcard__var"><Katex tex={v.sym} /> {v.desc}</span>)}
        </span>
      )}
      <span className="kw-fcard__links">
        {[...formula.sources, ...(compact ? [] : formula.usedIn)].map((l) => (
          <a key={l.href} href={l.href} className="kw-fcard__link"
             {...(l.href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}>{l.label}</a>
        ))}
      </span>
    </span>
  );
}
```

Add `.kw-fcard*` styles to `app.css` (paper surface, hairline, block spans, mono live line). Live-value text — if `live.expr` is a TeX string render via Katex; if you store plain strings, swap to text. (Decide per entry; the table above uses TeX-able expressions.)

- [ ] **Step 6: Failing test — FormulaMark.** Create `web/src/components/FormulaMark.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { FormulaMark } from "./FormulaMark";
it("reveals the formula card on click and links to the methodology anchor", () => {
  render(<FormulaMark id="implied_spread">€77.3</FormulaMark>);
  const btn = screen.getByRole("button");
  expect(screen.queryByRole("tooltip")).toBeNull();
  fireEvent.click(btn);
  expect(screen.getByRole("tooltip")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /details/i })).toHaveAttribute("href", "/methodology.html#implied_spread");
});
```

- [ ] **Step 7: Run red.** `npx vitest run src/components/FormulaMark.test.tsx` → FAIL.

- [ ] **Step 8: Implement FormulaMark.** Create `web/src/components/FormulaMark.tsx`:

```tsx
import { useId, useState } from "react";
import type { ReactNode } from "react";
import { getFormula } from "../data/formulas";
import { FormulaCard } from "./FormulaCard";

export function FormulaMark({ id, children }: { id: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const popId = useId();
  const f = getFormula(id);
  return (
    <span className="kw-fmark" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="kw-fmark__trigger" aria-expanded={open}
        aria-describedby={open ? popId : undefined} onClick={() => setOpen((o) => !o)}>
        {children}<sup className="kw-fmark__glyph" aria-hidden>ƒ</sup>
      </button>
      {open && (
        <span role="tooltip" id={popId} className="kw-fmark__pop">
          <FormulaCard formula={f} compact />
          <a className="kw-fmark__more" href={`/methodology.html#${f.id}`}>details ↗</a>
        </span>
      )}
    </span>
  );
}
```

Add `.kw-fmark` (inline, position relative), `.kw-fmark__trigger` (unstyled button, dotted underline), `.kw-fmark__glyph` (small Ember `ƒ`), `.kw-fmark__pop` (absolute, paper card, z-index, max-width ~320px) to `app.css`.

- [ ] **Step 9: Run green.** `npx vitest run src/components/FormulaMark.test.tsx` → PASS.

- [ ] **Step 10: Commit + push.** `feat(web): formula registry + FormulaCard + FormulaMark`.

---

## Task 4: Methodology page (assumptions, formula catalog, per-year table, limitations)

**Files:**
- Modify: `web/src/pages/MethodologyPage.tsx`
- Create: `web/src/components/MarketTable.tsx`, `web/src/components/Limitations.tsx`
- Test: `web/src/pages/MethodologyPage.test.tsx`, `web/src/components/MarketTable.test.tsx`

- [ ] **Step 1: Failing test — MarketTable.** Create `web/src/components/MarketTable.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MarketTable } from "./MarketTable";
it("renders a row per market year with negative-interval counts", () => {
  render(<MarketTable />);
  expect(screen.getByText(/2024/)).toBeInTheDocument();
  expect(screen.getByText("457")).toBeInTheDocument(); // 2024 negative intervals
});
```

- [ ] **Step 2: Run red → implement MarketTable.** Read `results.market` and the ceiling/causal `years`; render a table: columns = year; rows = ceiling spread, causal spread, gross, cycles_ac, cycles_cell, negative intervals (`market`), neg-price cashflow (`year_result`), day count. Use `DataMono` for values and `FormulaMark` on the metric row labels (e.g. wrap "Cycles / cell" with `<FormulaMark id="cycles_cell">`). Link the source: a caption linking `LINKS.energyChartsApi`. Run test → PASS.

- [ ] **Step 3: Failing test — Limitations.** Create test asserting `Limitations` renders the five known weak points (causal-policy latitude, missing IRR model, lone-unit, ancillary excluded, backward-looking). Implement `web/src/components/Limitations.tsx` as a definition list of those items (text from the spec's "limitations" + the review). Run → PASS.

- [ ] **Step 4: Failing test — MethodologyPage composition.** Create `web/src/pages/MethodologyPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MethodologyPage } from "./MethodologyPage";
import { FORMULAS } from "../data/formulas";
it("renders one formula card per registry entry and the per-year table", () => {
  const { container } = render(<MethodologyPage />);
  for (const f of FORMULAS) expect(container.querySelector(`#${f.id}`)).toBeTruthy();
  expect(screen.getByText(/457/)).toBeInTheDocument();
});
```

- [ ] **Step 5: Run red → implement MethodologyPage.** Compose sections (Hearth/Bone alternation, `SiteNav`, `Eyebrow`/`Couplet`):
  1. **Assumptions** (Bone): a parameters table from `results.assumptions` (battery, RTE, cycle cap, operating days, fee basis, the two scenario fees) — each value `DataMono`, each link to the engine file via `LINKS`/`engineFile("params.py")`.
  2. **Formulas** (Bone/long): group `FORMULAS` by `stage`; render `<FormulaCard formula={f} />` for each (block). Anchor ids enable deep-links from `FormulaMark`.
  3. **Per-year detail** (Hearth): `<MarketTable />`.
  4. **Limitations** (Bone): `<Limitations />`.
  5. Provenance footer (reuse the honesty footer, link-rich).
  Run test → PASS.

- [ ] **Step 6: Build + leak-scan + commit.** `npm run build` (both entries, scan passes). Commit + push: `feat(web): methodology page — assumptions, formulas, per-year, limitations`.

---

## Task 5: Wire FormulaMark into the honesty page + link audit

**Files:**
- Modify: `web/src/pages/HonestyPage.tsx`, `web/src/components/CaseTable.tsx`, `web/src/components/SpreadChart.tsx` (legend/source link), footer
- Test: `web/src/pages/HonestyPage.test.tsx`

- [ ] **Step 1: Failing test.** Extend `HonestyPage.test.tsx`:

```tsx
it("exposes formula markers on key figures and links sources", () => {
  render(<HonestyPage />);
  expect(screen.getAllByRole("button").some((b) => b.textContent?.includes("ƒ"))).toBe(true);
  expect(screen.getByRole("link", { name: /Energy-Charts/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run red → wire marks.** In `CaseTable`, wrap the "Implied spread" row label with `<FormulaMark id="implied_spread">`, "Cycles / day" with `id="cycles_ac"`, "Project IRR" with `id="unlevered_irr"`, "Annual figure" with `id="ac_gross"`, "Assumed" column note with `id="assumed_identity"`. In the hero, wrap the "Causal of ceiling 32–47%" stat with a `FormulaMark id="implied_spread"` (or a dedicated capture formula if added). In the footer/provenance add an explicit `Energy-Charts` source link (`LINKS.energyCharts`) and a repo link. Run → PASS.

- [ ] **Step 3: Link audit (manual + test).** Add a vitest in `src/data/links.test.ts` asserting every `LINKS.*` is https and `engineFile("dispatch.py")` contains the commit/`blob`. Grep the codebase for any remaining hardcoded source strings and replace with `LINKS`. Run full web suite.

- [ ] **Step 4: Commit + push.** `feat(web): formula markers on honesty page + link audit`.

---

## Task 6: Deploy + docs + full verification

**Files:**
- Modify: `web/README.md`, `web/ci-web.yml.example`

- [ ] **Step 1: README deploy section.** Document: `npm run build` → static `web/dist` with `index.html` + `methodology.html`; **Vercel** (import repo, root `web/`, zero-config via `vercel.json`) → permanent URL; **Pages** alternative (commit `ci-web.yml.example` to `.github/workflows/`, enable Pages on the artifact). State plainly: *the deployed site runs nothing; `npm run dev` is local-only.*

- [ ] **Step 2: Full verification.** From repo root: `/.../.venv/bin/pytest` (engine green, ceilings locked). From `web/`: `npm run verify` (typecheck + vitest + leak-scan) and `npm run build` (both entries + scan). Confirm `dist/methodology.html` exists and the leak-scan passes on the larger bundle.

- [ ] **Step 3: Regenerate + sync data if engine changed, then commit + push.** `docs: deploy instructions + final verification`.

---

## Self-review notes

- **Spec coverage:** methodology page (T4) · all four content blocks (T4) · formula registry + hover/tap marker + cards (T3) · live values + back-links + source links (T3/T5) · links-everywhere (T2 links.ts, T4/T5 wiring, T5 audit) · engine neg-price cashflow + market + schema 1.1.0 (T1) · KaTeX (T2) · multi-page route (T2) · deploy host-agnostic (T2 vercel.json, T6 docs) · testing throughout. ✓
- **No placeholders:** every step names files, code, commands, expected pass/fail.
- **Type consistency:** `Formula`, `getFormula`, `FORMULAS`, `FormulaCard({formula,compact})`, `FormulaMark({id,children})`, `StrategyYear.neg_price_cashflow_eur`, `MarketYear`, `results.market` used consistently across tasks.
- **Guardrail:** ceilings 61.1/68.3/77.3 and `simul=0` asserted unchanged in T1 Step 16.
