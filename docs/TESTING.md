# KellerWatt engine — testing plan

Goal: make the engine **bulletproof** before it feeds the public honesty page. The
engine makes one claim that matters — the validated ceilings 61.1/68.3/77.3 €/MWh —
and several softer ones (the causal estimate, the scenarios). Every claim must be
backed by tests that fail loudly if the math, calendar, or contract drifts.

## Layers

1. **Unit / example tests** (`test_*.py`, one per module) — the TDD spec. Each
   public function has at least one hand-checkable example.
2. **Property-based tests** (`test_properties.py`, Hypothesis) — invariants that
   must hold for *all* inputs, not just the examples:
   - LP ceiling: SoC always in `[soc_min, soc_max]`; cyclic (`soc[-1]==soc_init`);
     `simul_max≈0` (never charge+discharge together); cycle cap respected;
     `gross == sale − purchase ≥ 0`; powers within `[0, P]`.
   - Marginal monotonicity: a grid fee on charge never *increases* gross.
   - Causal: SoC in bounds and continuous across days; daily cycle cap respected;
     first 28 days never trade; turnovers non-negative; `gross == sale − purchase`.
   - Metrics: `cycles_cell == cycles_ac / eta`; identity linear in each factor;
     negative-price cashflow only counts negative intervals.
   - Economics: fee ordering `gross_turnover ≥ sale ≥ net` (for non-negative
     turnover); net monotonic decreasing in fee/rate; ancillary guard boundary.
   - Calendar: `berlin_hours_in_day ∈ {23,24,25}`, exactly 23/25 on the real DST
     Sundays.
3. **Edge / degenerate tests** (`test_edge_cases.py`) — single-interval days,
   all-equal prices, extreme negative/positive prices, empty causal sequences,
   sub-warmup sequences, a fully 15-minute synthetic year, fall-back repeated-hour
   instant distinctness.
4. **Determinism tests** (`test_determinism.py`) — identical inputs ⇒ byte-identical
   results (HiGHS optimal-or-fail, no randomness).
5. **Regression locks** (`test_integration.py`, `@network`) — the validated ceilings
   on real cached prices, tight tolerance; schema-valid export holding 61.1/68.3/77.3.
6. **Contract tests** (`test_contracts.py`, `test_export.py`) — schema validity,
   ID/enum agreement, malformed-doc rejection, producer→consumer field shape.
7. **Adversarial review** — two independent background agents hunt for correctness
   bugs in the engine; confirmed findings become new regression tests (TDD).

## Running

```
.venv/bin/pytest                      # everything (uses cached real prices)
.venv/bin/pytest -m "not network"     # fast: no API / no real-data backtest
.venv/bin/pytest --cov=engine --cov-report=term-missing   # coverage
```

## Coverage target

≥ 95% line coverage on `engine/` excluding the `__main__` CLI glue and the network
fetch path (exercised manually + the `@network` suite). Any uncovered branch must be
either exercised or justified in the PR.

## Non-negotiable invariants (if any of these break, the build is wrong)

- LP ceiling reproduces 61.1 / 68.3 / 77.3 €/MWh on real DE-LU data, `simul == 0`.
- The loader FAILS LOUD on any missing/duplicate/short/long/wrong-resolution day.
- The sanitized artifact never carries a real IRR/payback value.
- IRR/payback always labelled "constant-EBITDA" + status "provisional".
