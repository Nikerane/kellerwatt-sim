# KellerWatt — Two Open Actions (team hand-off)

> These are the two things our simulation and code **cannot** settle — and they are now the
> highest-leverage items for the pitch. Both came out of an independent technical review of our
> model (see `docs/codex-review-response.md`, findings #8 and #9).
>
> **Why they matter together:** our 2023–2025 backtest shows arbitrage alone earns ~€55–66/MWh
> realistically (not the €80 in the old deck). At that level the unit economics are **sensitive**,
> so the two things that decide whether the business works are (1) *can a single basement battery
> actually reach the market, and on what terms*, and (2) *do we keep the grid-fee exemption*.
> Regulatory/commercial figures cited below are from our earlier desk research and must be
> **confirmed with the source** — that confirmation is exactly the job.

---

## Action 1 — Get a real aggregator / BKV term sheet

**Owner:** ___   **Target:** one written indicative offer within ~2–3 weeks

### Why
Our model assumes a single 200 kWh / 50 kW battery earns spot-market arbitrage revenue directly.
In reality a unit that small is **below the minimum size** any licensed trader (BKV = balancing-
group responsible party) or aggregator / virtual power plant (VPP) will trade standalone. The
battery can only earn money **inside an aggregated pool** run by a licensed trader. Pooling
changes the numbers: there's a minimum portfolio, the aggregator takes a cut (we *assumed* 12%),
they control dispatch, and the per-unit captured spread is diluted versus the theoretical optimum.
Right now this is an assumption with no commercial backing.

### What we need
An **indicative term sheet / offer** from at least one aggregator so we can replace assumptions
with real terms.

### Who to approach (German VPP / aggregator candidates)
Next Kraftwerke, Entrix, Enspired, Flexpower, Suena, sonnen/VPP, Nodes. Frame the intro as a
**pipeline of basement batteries** (a planned fleet), not one unit — aggregators engage with
pipelines, not single assets. The TUM ELAB / incubator network may have warm intros.

### Exact questions to ask
1. **Minimum size** — will you onboard a single 200 kWh / 50 kW unit, or only a pool of N units /
   X MW? What's the path for a startup starting with one pilot?
2. **Fee structure & basis** — % of revenue, fixed €/MW/yr, or €/MWh? Is the fee on **gross
   turnover, net margin, or delivered energy**? (This single definition swings the economics.)
3. **Markets traded for us** — day-ahead, intraday continuous, FCR, aFRR? Can ancillary + arbitrage
   be **stacked**, and how is the battery's power/SoC partitioned between them?
4. **Dispatch control** — fully delegated to you, or do we set strategy/constraints? Any guaranteed
   or required cycles/day or availability? Battery warranty / degradation implications.
5. **Settlement & balancing** — who is the BKV, who carries imbalance risk, metering requirements,
   any §14a EnWG interaction.
6. **Track record** — your **realized** revenue for a comparable *short-duration* (≤4-hour) battery
   in 2024–2025, in €/kW/yr or €/MWh delivered. (This is the reality check against our €55–66/MWh.)
7. **Contract** — length, exit terms, performance guarantees, and technical/IT integration
   (control box, comms, FCR/aFRR prequalification).

### Done =
A written indicative offer stating: minimum portfolio, **fee basis + %**, markets traded, dispatch
rights, and ideally a realized €/MWh benchmark — enough to replace the "12% BKV fee + standalone
trading" assumption with real terms.

---

## Action 2 — Legal opinion on the §118(6) EnWG grid-fee exemption

**Owner:** ___   **Target:** a written legal memo within ~3–4 weeks

### Why
A large part of our economics depends on **not paying grid fees (Netzentgelte) or electricity tax
on the energy the battery charges.** Two rules underpin this (to be confirmed by counsel):
- **§118(6) EnWG** — storage commissioned after 2008 and **before 4 Aug 2029** is exempt from grid
  fees for 20 years, provided electricity is fed back into the same grid.
- **§5(4) StromStG** — avoids double electricity-taxation of stored energy.

**The risk is binary, not a slider.** The Bundesnetzagentur's **AgNes** process is reforming these
exemptions (2025–2026). Our desk research suggested the likely direction is a **capacity-based fee
(~€4–7k/MW/yr) with full grandfathering** for projects commissioned before 4 Aug 2029 with FID
before the final decision — near-best-case. But the rejected **energy-based** alternative
(~€66.50/MWh) would strip **~4 points off IRR** and could make a unit uneconomic. We need to know
which applies to us, and how to lock in the good case.

### Who to approach
A German **energy-law (Energierecht)** firm with a storage/BESS practice — e.g. Becker Büttner Held
(BBH), Raue, Watson Farley & Williams, Osborne Clarke, Noerr — **or** a regulatory consultancy.
Check first whether TUM ELAB / the incubator has a legal partner or clinic (cheaper first stop).

### Exact questions for counsel
1. Does a 200 kWh basement battery that buys from and sells back to the **public** grid qualify for
   the §118(6) grid-fee exemption **today**? Under exactly what conditions (commissioning date,
   "feed back into the same grid," metering topology)?
2. **AgNes status (mid-2026):** confirmed direction, timeline to final decision, and the
   **grandfathering** conditions (commissioning before 4 Aug 2029; **FID before the final
   decision**). Can our pilot timeline lock in grandfathering — and what do we have to do **now**?
3. If a **capacity fee (€4–7k/MW/yr)** vs an **energy fee (€/MWh)** applies, which one hits us and
   when? Quantify both for a 50 kW / 200 kWh unit.
4. **§5(4) StromStG** electricity-tax treatment of charged-then-discharged energy — exempt? Any
   Hauptzollamt registration obligations?
5. **§14a EnWG** (reduced grid fees / DSO throttling for controllable consumers) — does taking it
   help or hurt, and does it interact with §118(6)?
6. Any **other levies** on charged energy (KWKG, §19 StromNEV, offshore, concession/Konzessions-
   abgabe) and whether storage is exempt.
7. What **documentation/structure** preserves the best regulatory position now (evidence of FID,
   commissioning plan, metering, balancing-group setup)?

### Done =
A written legal memo answering: (a) do we qualify today, (b) the grandfathering window and how to
lock it, (c) the **quantified downside if lost** — enough to present **two scenarios in the deck,
"exemption retained" vs "exemption lost,"** replacing the soft slider in our model.

---

## How these feed back into the model
- Action 1's fee basis & % → replaces the assumed 12% BKV fee and the standalone-trading line.
- Action 1's realized €/MWh benchmark → sanity-checks our €55–66/MWh causal estimate.
- Action 2's two scenarios → replace the grid-fee slider with named "retained / lost" cases.

Until both land, treat the unit economics as **provisional** and lead the pitch with the
**validated, defensible** arbitrage range (€55–66/MWh, widening year over year) plus these two
diligence items shown as *in progress* — that honesty is a strength, not a gap.
