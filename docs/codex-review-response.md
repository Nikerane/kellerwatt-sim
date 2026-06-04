# Codex Review — Response & Disposition

> Independent Codex review (2026-06-04) found 5 CRITICAL + 11 MAJOR + 2 MINOR issues.
> This doc records the **empirical validation result** and the **disposition of every finding**.
> Code-level criticals are fixed in `scripts/validate_number.py` (run and verified); the rest
> are locked-in corrections for the production engine or external business/legal actions.

## The validation result (Codex #18 — done)

`scripts/validate_number.py` downloads real DE-LU 2024 day-ahead prices (Energy-Charts, no
token), groups by **Europe/Berlin** delivery day, and runs a **corrected** perfect-day-ahead-
foresight LP (no simultaneous charge/discharge, AC-side cashflows, RTE applied once, cyclic
SoC, cycle cap). It is reported strictly as an **upper bound — no capture-% fudge.**

| | implied spread | cycles/day | annual gross |
|---|---|---|---|
| Business plan **assumes** | €80/MWh | 1.50 | €9,947 |
| **Perfect-foresight ceiling, capped 1.5** | **€68.3/MWh** | 1.37 | ~€6,150 |
| **Perfect-foresight ceiling, uncapped** | €61.7/MWh | 1.56 | ~€6,330 |

Data sanity: 8,784 hourly prices, 0 nulls, range −135.4…+936.3 €/MWh, 457 negative-price
hours, 366 Berlin days (histogram 23/24/25 h → DST handled), `max simultaneous c&d = 0`.

**Conclusion:** the arbitrage assumption is optimistic. Even a perfect-foresight ceiling is
~15% below €80/MWh; realistic causal capture (~85% of foresight) ≈ **€55–61/MWh**, gross
≈ **€5,200–5,400/yr** from day-ahead arbitrage alone. **Re-base the deck on ~€60/MWh**, show
any FCR/aFRR ancillary as a clearly separated line, and frame this as the honest finding the
team surfaced — not a number to defend.

## Disposition of all 18 findings

**CRITICAL**
1. **Simultaneous charge/discharge** — **FIXED** in spike via binary mutual-exclusion
   (`c_t ≤ P·y_t`, `d_t ≤ P·(1−y_t)`); verified `max simul = 0`. Carry into the production LP.
2. **UTC vs Berlin delivery days** — **FIXED** in spike (`Europe/Berlin` grouping; 23/25 h DST
   days handled). Carry into production.
3. **Capture-% = REV_SCALE fudge** — **FIXED (framing)**: present the LP strictly as a
   perfect-foresight **ceiling** and report a **[causal floor … foresight ceiling]** bracket,
   never `LP × 0.85`. Drop `capture_pct` as the "realistic" number.
4. **Instant-economics preserves irrational dispatch** — **ACCEPTED**: marginal trading
   charges (grid fee on charge, degradation) must sit **inside** the dispatch objective and
   trigger a re-solve; only non-marginal params (CapEx, fixed fees) stay in the instant layer.
5. **JSON export absent from plan** — **ACCEPTED**: replace plan T11–T12 (Streamlit) with a
   tested `export_results.py` emitting **schema-versioned** JSON (dates→ISO strings,
   numpy→lists) with required-field validation.

**MAJOR**
6. **€80/1.5 optimistic** — **RESOLVED empirically** (see result): real ceiling €62–68/MWh.
7. **Assumed case not reconciled** — **ACCEPTED**: compute the assumed case from the *same*
   equations (spread × usable MWh × days + separated ancillary − fees), not stored constants.
8. **Lone 200 kWh unit is a fictional trader** — **BUSINESS ACTION**: obtain one real
   aggregator/BKV term sheet (min portfolio, revenue share, dispatch rights, settlement) and
   model its actual fee basis. Not solvable in code.
9. **§118(6) EnWG as a slider** — **ACCEPTED**: present binary **"exemption retained / lost"**
   scenarios backed by legal advice; keep a slider only for secondary sensitivity.
10. **Threshold vs LP not comparable** — **ACCEPTED**: give both identical initial/terminal
    SoC rules (cyclic) or an explicit terminal-energy valuation.
11. **Cycle metric AC vs cell** — **ACCEPTED**: report **both** AC-delivered and
    cell-throughput-equivalent cycles; use cell throughput for degradation/lifetime claims.
12. **Negative-price attribution invalid** — **ACCEPTED**: rename to **"cashflow during
    negative-price intervals"** (spike already does) or implement charge→discharge attribution.
13. **IRR oversimplified** — **ACCEPTED**: label **"constant-EBITDA project IRR"** until a real
    annual cashflow model exists (degradation decline, replacement, terminal value, price-year
    scenarios).
14. **BKV fee basis inconsistent** — **ACCEPTED**: define precisely (turnover vs net margin)
    from an actual fee schedule; test purchase-turnover, sale-turnover, and net-margin bases.
15. **Silent data gaps** — **FIXED** in spike (reports nulls dropped + hours-per-day histogram,
    skips incomplete days). Production loader must **fail loud** on coverage/resolution/tz/
    duplicate violations.
18. **Validate-first slice too big** — **DONE**: this one-file spike *is* the minimal
    validation; ran it, got the number, before any production module.

**MINOR**
16. **"Representative week" is one day** — **ACCEPTED**: export a real 7-day sample or relabel
    "representative day".
17. **Scope too large for the evidence** — **ACCEPTED (scope cut)**: build only the **engine +
    one static honesty page** until the economics survive review. Defer owner app, film, and
    the full motion system.

## Net effect on the build

The "validate the number first" decision paid off: it surfaced two real correctness bugs (#1,
#2) and **empirically disproved the €80 assumption** before a line of UI was written. Next:
re-base the economics on ~€60/MWh, narrow scope to engine + one honesty page (#17), and pursue
the aggregator term sheet (#8) and legal scenarios (#9) — the two things code can't settle.
