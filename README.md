# KellerWatt

> **Power that pays you back.** Rent the basement, install the battery, trade the spread.

This repo holds the **MVP** for KellerWatt: a rigorous battery-arbitrage simulation plus a
warm, editorial brand foundation. It is the single source of truth — start here.

---

## 1. What KellerWatt is

KellerWatt rents unused apartment-building basements, installs **200 kWh LFP batteries**, and
trades electricity (spot arbitrage + grid services + tariff reduction). Owners earn passive
rent (~€800–1,200/yr); KellerWatt earns ~€8–9.7k gross/unit/yr. It attacks Germany's storage
gap (~100–170 GWh needed by 2030, ~24 GWh installed) and the price volatility that gap creates
(−€135 to +€936/MWh in 2024). Pre-seed, TUM ELAB, Munich & Düsseldorf first. Public site:
nikerane.github.io/kellerwatt.

**The MVP's job:** turn an *asserted* spreadsheet into a *backtested, slider-driven* model.
The headline is an apples-to-apples reconciliation — the business plan **assumes** ~€80/MWh
captured spread at 1.5 cycles/day; the simulation **derives** the implied spread and cycles
from a real dispatch on real German prices, and shows both side by side. This is the honest
version of the prototype's `REV_SCALE = 1.9` fudge factor.

---

## 2. Architecture — one foundation

```
  Energy-Charts DE-LU prices ──▶  PYTHON ENGINE (headless)            ──▶  sim_results.json
  (pre-downloaded parquet)        data_load · dispatch · economics ·       (the interface)
                                  metrics · backtest                         │
                                                                             ▼
                                                        VITE + REACT + TS  (one token foundation)
                                                        ├─ Landing page  (editorial, Hearth/Bone)
                                                        ├─ Owner app     (dark; SoC ring; day chart)
                                                        └─ Honesty panel (assumed vs simulated)
                                                        + Film (Remotion, separate track)
```

- **Python is a headless engine**, not a UI. It emits `sim_results.json`. **Streamlit is retired.**
- **All public surfaces are Vite + React + TypeScript**, sharing one CSS-variable token
  foundation (ported from `app-package/assets/colors_and_type.css`).
- **Dispatch ↔ economics split:** the expensive LP dispatch is computed/cached once; the cheap
  economics layer (capture %, BKV fee, CapEx, grid fee) recomputes instantly — so the
  judge-draggable sliders stay responsive.

**JSON contract (engine → web):**
```json
{ "meta": {…},
  "days": [{"date","gross_eur","mwh_discharged","mwh_charged","neg_price_gross_eur"}],
  "sample": {"prices":[], "charge_kw":[], "discharge_kw":[], "soc_kwh":[], "dt_h":0.25},
  "metrics": {"implied_spread_eur_mwh","implied_cycles_day","year1_gross_eur",
              "year1_ebitda_eur","payback_years","irr","neg_price_share"},
  "conservative": {"…same metrics…"},
  "assumed": {"spread_eur_mwh","cycles_day","gross_eur","ebitda_eur","irr","payback_yr"} }
```

---

## 3. Repository map

| Path | What it is |
|---|---|
| `DESIGN.md` | Machine-readable brand spec. Open AI build sessions with "use DESIGN.md" → zero drift. |
| `docs/brand/brand-guidelines.md` | Canonical brand philosophy + the chosen **foundation stack**. |
| `docs/brand/inspiration-research.md` | 8-source design deep-dive: reference sites, patterns, motion vocabulary, film. |
| `docs/superpowers/specs/2026-06-04-…-design.md` | Engine design spec (with the React-pivot banner). |
| `docs/superpowers/plans/2026-06-04-…-sim.md` | TDD implementation plan for the Python engine (T1–T10). |
| `src/ app/ data/ tests/ notebooks/` | (scaffolded dirs — engine code not written yet). |

> External: `~/repos/app-package/` is the existing branded **owner-app prototype** (static
> CDN-React) — port its `colors_and_type.css` tokens and atoms (`Ring`, `DayChart`, `Card`,
> `Eyebrow`); do not copy its `REV_SCALE` sim.

---

## 4. Locked decisions

- Python headless engine → `sim_results.json`; **Streamlit retired**.
- Battery fixed at **200 kWh / 50 kW / 4-hour**, RTE 0.90, SoC 10–100%; everything else a parameter.
- Dispatch: **perfect-day-ahead-foresight LP** (PuLP/HiGHS) primary + **threshold** toggle; same `Schedule` interface.
- Data: **Energy-Charts** `?bzn=DE-LU` (no token), pre-downloaded to parquet; **no network on stage**.
- Frontend: **Vite + React + TypeScript**, static. Two builds, one codebase: local (real numbers) + sanitized public.
- Baseline figures = research defaults, swappable in one `params.py` constant.

---

## 5. Brand essence

Editorial, not enterprise. Calm — a partner, not a cheerleader. (Full spec: `DESIGN.md`,
`docs/brand/brand-guidelines.md`.)

- **Voice:** contrast couplets — "Cheap power exists. Most homes can't reach it." Sentence case; no exclamation marks; numbers in Mono, currency-first (€9,700).
- **Color (restraint):** Hearth `#1F3A34` · **Ember `#E89B4F` (signal only — once per screen, never a fill)** · Bone `#F5F1EA` · Slate `#2C2E2D` · Stone `#E8E2D7` · Dusk `#4A3850` · Clay-red `#D98A7A` (negatives only). Flat fields, no gradients.
- **Type:** Fraunces (serif headlines) · Inter (UI) · JetBrains Mono (numbers + tracked uppercase eyebrows).
- **Texture:** hex-cell @6–7% on dark only. No stock photos, no filled icons, no decorative SVG.
- **Layout/motion:** 1200px, 0.5px hairlines, 18px cards, two-layer shadows; warm easing `cubic-bezier(0.2,0.7,0.2,1.0)`, 120/220/420ms, fades over slides, no scroll-jack/parallax, idle ±1–2px sine drift.
- **Color-role contract for data:** Ember = active/revenue · Clay-red = cost/negative · Bone = neutral/label · Hearth = surface/divider. Never rainbow a chart.

---

## 6. Foundation stack (chosen primitives)

| Category | Pick |
|---|---|
| Motion (web) | **Motion** (`motion`) — easing token drops in; `AnimatePresence` cross-fades; idle sine via `useTime` |
| Motion (film) | **Remotion** (React→MP4) primary; GSAP fallback — frame-perfect fonts/colors/grain/camera-push |
| Data-viz | **`d3-scale` + `d3-shape` + hand-rolled SVG** — no chart library (they fight the brand) |
| Headless UI | **Radix UI** + **Vaul** (sheets); **cherry-pick shadcn/ui** logic via a `shadcn-bridge.css`, strip Tailwind |
| Icons | **Lucide** (stroke-only) or Phosphor "thin" |
| Texture | inline SVG **`feTurbulence`** grain + radial vignette + hex `<pattern>` |
| Fonts | **Fontsource** self-host (not Google CDN — GDPR; German brand) |

**De-generic-fier:** replace shadcn's `focus-visible:ring-2` with `outline:1.5px solid Ember`.

---

## 7. Inspiration distilled (full detail in `docs/brand/inspiration-research.md`)

- **Reference sites (verified, on-brand):** stripe.dev, editorialnew.com, lifeworld.wetransfer.com, stripesessions.com (#221b35 ≈ Hearth), wilderness-international.org, betterenergy.com, artlist.io trend report.
- **SoC ring = stroke-only** (Ember arc on @12% track over `#101D18`, pulsing head, no gradient fill — reads as a window).
- **Honesty panel** on Bone (daylight = honesty): 3 columns Assumed / Simulated / Δ; Fraunces-italic headers, Mono values, Δ in Ember/Clay-red, no borders.
- **Motion vocabulary:** `fadeUp · fadeIn · staggerGroup · stateTap · counterIn · idleDrift · crossFadeSlide` — exact Motion params on our easing. Counters via `@number-flow/react`; logo rail via MagicUI Marquee.
- **Film:** Remotion + a 7-scene storyboard (battery travels through all scenes; couplet copy per scene).
- **Skip:** designrocket.io (Figma→Lovable course, off-brand); HeyGen as a film renderer (pauses GSAP).

---

## 8. Build roadmap

1. **Engine** (TDD plan T1–T10): data_load → threshold + LP dispatch → economics → metrics → backtest → **`sim_results.json` export**.
2. **Web foundation:** Vite scaffold → port `colors_and_type.css` → `shadcn-bridge.css` + global Ember focus-ring/18px overrides → ~10 primitives (`Eyebrow`, `Couplet`, `DataMono`, `Card`, `HexField`, `Button`, `Ring`, `DayChart`, `Bars`, `FlowArrows`).
3. **Surfaces:** build the **SoC ring** + **Bone honesty panel** first (they anchor the brand promise), then the owner app screens and the landing.
4. **Film:** bootstrap Remotion with the grain+vignette overlay + `<BatteryObject>` before scene content.

---

## 9. Status

Greenfield. **3 design docs + DESIGN.md committed and pushed** to
`github.com/Nikerane/kellerwatt-sim` (public, branch `main`). **No app code yet** — by design;
the architecture and brand foundation were locked first. Repo is **local + GitHub**; nothing
else is deployed.

**Validated (2026-06-04):** `scripts/validate_number.py` ran the corrected perfect-foresight LP
on real 2024 DE-LU prices → implied spread **€62–68/MWh at ~1.4 cycles/day**, vs the assumed
€80/MWh & 1.5. The arbitrage assumption is optimistic; re-base on ~€60/MWh. See
`docs/codex-review-response.md` for the full result and the disposition of all 18 findings.
