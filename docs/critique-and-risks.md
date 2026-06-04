# KellerWatt — Critique & Risk Register

> Adversarial self-review (2026-06-04). The point is to find the cracks before building.
> **Decision taken:** *validate the core number first* — build the thinnest engine slice, run a
> real 2024 backtest, and see the implied spread before building any UI.

## Ranked weak spots

### 1. The "honesty" engine may not be honest yet — and its honest answer might disprove the plan
- We replaced the prototype's `REV_SCALE = 1.9` fudge with **perfect-day-ahead-foresight LP ×
  an 85% `capture %` slider**. Perfect foresight is an upper bound no operator reaches, and
  `capture %` is a single hand-set scalar standing in for all forecast-error reality —
  structurally the same "tuned knob," better dressed.
- Our own deep-research warned €80/MWh at 1.5 cycles/day is a *good-year, fully-optimized*
  number (2024 avg daily spread ~€130/MWh; a deep cycle nets €60–95/MWh; the 1.5th cycle is
  much thinner; real short-duration DE fleets cycle ~1.1–1.3×/day). So the real backtest may
  land **below €80**, i.e. the headline output is "our plan is optimistic" — shown to the
  judges who already yellow-carded us.
- **Unresolved tension:** is this a *truth-seeking* tool or a *persuasion* tool? A truth tool
  that disproves the deck is a gift in private and a grenade on stage. **Stance to adopt:** be
  the team that *found* the optimism and re-framed honestly (conservative case as the base
  case). Resolve before any pitch use.

### 2. A single 200 kWh unit can't actually trade — partly fiction
One 200 kWh / 50 kW unit is below any aggregator's tradeable minimum. Spot arbitrage is only
real *inside a pool*, and pooling caps the upside the LP grants in full (shared capacity,
aggregator cut/queue). Modeling a lone price-taking arbitrageur overstates capture. Mitigation:
frame as one node in a pool **and** reflect the pooling haircut, not just the 12% BKV fee.

### 3. Existential regulatory risk modeled as a soft slider
Economics rest on §118(6) EnWG + StromStG exemptions; AgNes is live. Grid-fee-on-charge as a
slider defaulting to 0 frames a potentially *business-ending binary* as a gentle tunable. Show
it as a labelled scenario with a clear "exemption lost" case, not just a knob near zero.

### 4. Effort allocation — possibly polishing the wrong thing
The binding constraints are **demand proof (LOI, a real building)** and **defensible
economics** — what the judges hit. A landing page + owner app + 7-scene film + engine is a
quarter of work. The **owner app demos a product that does not exist** ("watch your battery
trade live", zero batteries installed) — to a sophisticated audience this can read as
*vaporware*, not traction. Consider cutting to the one artifact that de-risks the pitch.

## The unifying thread

We built scaffolding (brand, stack, plan, film) around a **core number we have never
computed.** No 2024 prices downloaded, no backtest run. The cheapest, highest-leverage action
is to compute the real implied spread. Everything else is premature until that number exists.

## Decision & immediate next step

**Validate the number first.** Build the thin engine slice (data_load → LP/threshold dispatch →
economics → metrics, per the existing TDD plan T1–T9), download real DE-LU 2024 prices, run one
backtest, and read the implied spread + cycles. Let that number reshape the deck, the brand
claims, and the build scope — *before* any surface is built.
