# KellerWatt — Methodology page + formula traceability (design)

> Approved direction (2026-06-05). Second static page that goes a level deeper than
> the honesty page, makes **every number traceable to its formula**, links sources
> wherever possible, and ends in a deployable static bundle (no `npm run dev` to
> view it).

## Context

The honesty page (`/`) presents the validated ceilings, the causal estimate, and
the diligence gaps. It deliberately shows conclusions, not workings. This adds the
workings: a `/methodology` page for a reader who wants to **audit or reproduce** the
result, plus an inline mechanism so any figure on either page reveals the exact
equation, the live values plugged in, and a link to the source/implementation.

Audience: **both** the diligence reader going deeper **and** a technical
reviewer/auditor. Tone: rigorous, honest, link-rich.

## Goals

1. A second page `/methodology` with four blocks: methodology & assumptions, all
   formulas, per-year detail (2023–25), limitations & weak points.
2. **Formula traceability**: a small marker (`ƒ`, dotted underline) on numbers/terms
   that, on hover (desktop) / tap (mobile), pops a card with the typeset formula,
   plain-English meaning, the **live values** from the data, and a "details ↗"
   deep-link. Works on both pages. `/methodology` is the canonical expanded catalog.
3. **Links everywhere**, especially data and sources: Energy-Charts endpoint,
   §118(6) EnWG, the GitHub repo at the pinned commit, the engine file behind each
   formula, the solver.
4. A **deployable** static bundle and a one-time deploy path → a permanent URL.

## Non-goals

- No interactive sliders / what-if controls (honesty discipline; owner app is still
  out of scope).
- No new economics. The math shown is exactly what the engine already computes.
- No server. Purely static; data baked in at build time.

## Architecture

Vite **multi-page** build — two real entry points, no router JS:

```
web/
  index.html            -> / (honesty page, existing)
  methodology.html      -> /methodology.html (new)
  src/
    main.tsx            (honesty entry, existing)
    methodology.tsx     (methodology entry, new)
    pages/
      HonestyPage.tsx   (= current App body, lightly refactored)
      MethodologyPage.tsx
    data/
      formulas.ts       (the formula registry — single source of truth)
      links.ts          (canonical external/source links)
    components/
      FormulaMark.tsx   (inline marker + popover)
      FormulaCard.tsx   (expanded card for /methodology and the popover body)
      Katex.tsx         (thin KaTeX render wrapper, self-hosted)
      SiteNav.tsx       (cross-links between the two pages)
      MarketTable.tsx   (per-year detail)
      Limitations.tsx
```

`vite.config.ts` gains `build.rollupOptions.input = { main, methodology }`. Shared
tokens/components/styles across both entries.

### Formula registry (`src/data/formulas.ts`)

The heart of the feature. One typed array; both `FormulaMark` popovers and the
methodology cards render from it, so a formula is defined once.

```ts
interface Formula {
  id: string;                       // "implied_spread"
  stage: "dispatch" | "economics" | "metrics" | "causal";
  title: string;
  katex: string;                    // typeset form
  plain: string;                    // one-sentence meaning
  variables: { sym: string; desc: string }[];
  live?: (d: SimResults) => { expr: string; note?: string };  // "€77.3 = €7,030 / 91.0 MWh (2025)"
  usedIn: { label: string; href: string }[];   // back-links into the pages
  sources: { label: string; href: string }[];  // engine file, law, solver, paper
}
```

**Catalog (~17 formulas):**
- *Dispatch*: one-way efficiency `η = √RTE`; SoC balance
  `SoCₜ = SoCₜ₋₁ + (η·cₜ − dₜ/η)·Δt`; no-simultaneity `cₜ ≤ P·yₜ, dₜ ≤ P·(1−yₜ)`;
  cyclic SoC `SoC_{T−1} = SoC₀`; cycle cap `Σ dₜ·Δt ≤ cap·E_usable`; AC gross
  `gross = Σ (pₜ/1000)(dₜ − cₜ)·Δt`.
- *Causal*: trailing thresholds `charge if pₜ ≤ Q_low(28d)`,
  `discharge if pₜ ≥ Q_high(28d)`, dt-weighted quantile note.
- *Metrics*: implied spread `gross / MWh_dis`; assumed-case identity
  `spread × E_usable[MWh] × cyc/day × days`; `cycles_ac`; `cycles_cell = cycles_ac/η`;
  negative-price cashflow `Σ_{p<0}(p/1000)(d−c)Δt`; **unlevered** IRR
  `IRR([−CapEx, EBITDA, …])`; payback `CapEx / EBITDA`.
- *Economics*: BKV sale/gross/net bases; grid-fee cost `fee·MWh_charged`; net annual
  `margin − grid_cost − BKV + ancillary`.

Each card's `sources` links the **engine file** that implements it (GitHub blob at
the pinned commit) so the page is literally an index into the code.

### Links (`src/data/links.ts`)

Canonical, reused everywhere:
- Data: `https://api.energy-charts.info/price?bzn=DE-LU&start=…&end=…` + Energy-Charts
  home + API docs.
- Law: §118(6) EnWG (`gesetze-im-internet.de/enwg_2005/__118.html`).
- Code: repo root + `blob/<commit>/engine/<file>.py` + the JSON schema.
- Solver: HiGHS, PuLP.
The provenance footer and per-year table become link-rich; `git_commit` from the
artifact builds the blob URLs.

## Engine change (small, tested)

The export lacks two things the detail table/cards want:
1. Per-year **negative-price cashflow** for the ceiling (Codex 12 metric, currently
   computed nowhere in the aggregate path). Add `neg_price_cashflow_eur` to each
   `DayDispatch` (it has the arrays + prices), aggregate in `backtest`, surface in
   `StrategyYear`, emit in the `year_result`.
2. A per-year **`market`** block (from `YearData`): `{year, negative_intervals,
   price_min, price_max, day_count}`.

Schema: add `year_result.neg_price_cashflow_eur` (number|null) and a top-level
`market[]`. Bump `schema_version` to `1.1.0`. Update `minimal_example`, the producer,
and contract tests. Engine TDD as usual; ceilings unchanged.

## Testing

- **Engine**: new fields computed correctly (neg-price cashflow sign on a known
  profile; market stats match `YearData`); schema still validates; ceilings still
  61.1/68.3/77.3.
- **Web (vitest)**: every formula's `live()` expression is consistent with the JSON
  it reads; every `usedIn`/`sources` href is a non-empty `https`/in-app URL; KaTeX
  strings render without throwing; `FormulaMark` shows/hides the popover; the
  methodology page renders one card per registry entry; the per-year table matches
  the data; cross-page nav links resolve.
- **Leak scan**: extended to the methodology bundle too (build gate unchanged).

## Deploy (kills the `npm run dev` loop)

`npm run build` already emits a host-agnostic static `dist/` (`base: "./"`,
self-hosted fonts). Multi-page adds `methodology.html` to the output. Provide:
- `web/vercel.json` (or rely on Vercel's Vite auto-detect) — zero-config: connect the
  repo, build `npm run build`, output `web/dist`.
- A Pages path documented in `web/README.md` (the existing `ci-web.yml.example` plus
  a deploy job) for whoever has a workflow-scope token.
Outcome: one connect step → a permanent URL; `npm run dev` is only ever for local
editing.

## Sequencing

1. Engine: export `neg_price_cashflow` + `market[]`, schema 1.1.0, tests; regenerate.
2. Web scaffold: multi-page config, `links.ts`, KaTeX wrapper, SiteNav, refactor
   honesty page into `pages/HonestyPage`.
3. Formula registry + `FormulaCard` + `FormulaMark` (+ tests).
4. `/methodology`: assumptions, formula catalog, per-year `MarketTable`, limitations.
5. Wire `FormulaMark` into the honesty page's key figures.
6. Link audit (provenance, sources), deploy config + README, full verify + leak scan.

## Open defaults taken

- **KaTeX** (self-hosted) for typeset math — this page is about rigor.
- **Host-agnostic build** with both Vercel and Pages documented; no host lock-in.
