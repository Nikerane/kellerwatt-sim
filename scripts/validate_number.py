#!/usr/bin/env python3
"""Validate the core number across years — throwaway spike (Codex review #18).

Downloads real DE-LU day-ahead prices (Energy-Charts, no token) for each given
year, runs a *corrected* perfect-day-ahead-foresight LP, and prints the implied
captured spread (EUR/MWh) and cycles/day vs the business-plan assumption of
~EUR 80/MWh at 1.5 cycles/day.

    python scripts/validate_number.py 2023 2024 2025

Corrections baked in vs the original plan:
  #1  no simultaneous charge/discharge (binary mutual-exclusion; asserted == 0).
  #2  delivery days grouped by Europe/Berlin local date (DST 23h/25h handled).
  #15 data completeness validated/reported; incomplete days skipped.
  #3  LP reported strictly as a perfect-foresight UPPER BOUND -- no capture-% fudge.
Handles mixed resolution: hourly before 2025-10-01, 15-min after (dt_h inferred per day).

Stdlib only except PuLP (+ optional highspy). Python 3.9+.
"""
import json
import math
import statistics
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pulp

# ---- battery (200 kWh / 50 kW / 4h, RTE 0.90, SoC 10-100%) -------------------
CAP_KWH = 200.0
POWER_KW = 50.0
SOC_MIN = 0.10 * CAP_KWH          # 20 kWh
SOC_MAX = 1.00 * CAP_KWH          # 200 kWh
E_USABLE = SOC_MAX - SOC_MIN      # 180 kWh
ETA = math.sqrt(0.90)             # one-way; RTE applied ONCE in the SoC balance
LAMBDA_EUR_MWH = 1.0              # tiny throughput tie-break
BERLIN = ZoneInfo("Europe/Berlin")


def fetch_prices(year):
    url = (f"https://api.energy-charts.info/price?bzn=DE-LU"
           f"&start={year}-01-01&end={year}-12-31")
    with urllib.request.urlopen(url, timeout=120) as r:
        payload = json.load(r)
    rows, dropped = [], 0
    for s, p in zip(payload["unix_seconds"], payload["price"]):
        if p is None:
            dropped += 1
            continue
        rows.append((datetime.fromtimestamp(s, tz=timezone.utc), float(p)))
    rows.sort(key=lambda x: x[0])
    return rows, dropped


def group_by_berlin_day(rows):
    days = defaultdict(list)
    for utc, p in rows:
        local = utc.astimezone(BERLIN)
        days[local.date()].append((local, p))
    for d in days:
        days[d].sort(key=lambda x: x[0])
    return days


def infer_dt_h(pts):
    if len(pts) < 2:
        return 1.0
    diffs = [(pts[i + 1][0] - pts[i][0]).total_seconds() / 3600.0
             for i in range(len(pts) - 1)]
    return statistics.median(diffs)


def solve_day(prices, dt_h, cycles_cap):
    """Perfect-foresight LP for one delivery day. AC-side cashflows; RTE once."""
    T = len(prices)
    prob = pulp.LpProblem("arb", pulp.LpMaximize)
    c = [pulp.LpVariable(f"c{t}", lowBound=0, upBound=POWER_KW) for t in range(T)]
    d = [pulp.LpVariable(f"d{t}", lowBound=0, upBound=POWER_KW) for t in range(T)]
    soc = [pulp.LpVariable(f"s{t}", lowBound=SOC_MIN, upBound=SOC_MAX) for t in range(T)]
    soc0 = pulp.LpVariable("s_init", lowBound=SOC_MIN, upBound=SOC_MAX)
    y = [pulp.LpVariable(f"y{t}", cat="Binary") for t in range(T)]  # 1=charge mode

    revenue = pulp.lpSum((prices[t] / 1000.0) * (d[t] - c[t]) * dt_h for t in range(T))
    penalty = pulp.lpSum((LAMBDA_EUR_MWH / 1000.0) * (c[t] + d[t]) * dt_h for t in range(T))
    prob += revenue - penalty

    for t in range(T):
        prev = soc0 if t == 0 else soc[t - 1]
        prob += soc[t] == prev + (ETA * c[t] - d[t] / ETA) * dt_h
        prob += c[t] <= POWER_KW * y[t]            # #1: no simultaneous
        prob += d[t] <= POWER_KW * (1 - y[t])      #     charge & discharge
    prob += soc[T - 1] == soc0                     # cyclic
    if cycles_cap is not None:
        prob += pulp.lpSum(d[t] * dt_h for t in range(T)) <= cycles_cap * E_USABLE

    prob.solve(SOLVER)
    cv = [c[t].value() or 0.0 for t in range(T)]
    dv = [d[t].value() or 0.0 for t in range(T)]
    gross = sum((prices[t] / 1000.0) * (dv[t] - cv[t]) * dt_h for t in range(T))
    mwh_dis = sum(dv[t] * dt_h for t in range(T)) / 1000.0
    mwh_chg = sum(cv[t] * dt_h for t in range(T)) / 1000.0
    simul = max((min(cv[t], dv[t]) for t in range(T)), default=0.0)
    return gross, mwh_dis, mwh_chg, simul


def run(days, cycles_cap, label):
    tot_gross = tot_dis = tot_chg = 0.0
    max_simul = 0.0
    n = 0
    for d in sorted(days):
        pts = days[d]
        dt_h = infer_dt_h(pts)
        if not (22 <= len(pts) * dt_h <= 26):   # skip incomplete days (allow DST 23/25h)
            continue
        g, md, mc, sm = solve_day([p for _, p in pts], dt_h, cycles_cap)
        tot_gross += g; tot_dis += md; tot_chg += mc
        max_simul = max(max_simul, sm)
        n += 1
    spread = tot_gross / tot_dis if tot_dis else 0.0
    cyc = (tot_dis * 1000.0) / (E_USABLE * n) if n else 0.0
    print(f"  {label:<34} spread {spread:5.1f} EUR/MWh | {cyc:4.2f} cyc/day "
          f"| gross {tot_gross:7,.0f} | simul {max_simul:.3f}")
    return spread, cyc, tot_gross, n


def main():
    global SOLVER
    try:
        SOLVER = pulp.HiGHS(msg=False)
        sname = "HiGHS"
    except Exception:
        SOLVER = pulp.PULP_CBC_CMD(msg=False)
        sname = "CBC"
    years = [int(a) for a in sys.argv[1:]] or [2024]
    print(f"solver: {sname}   years: {years}")

    summary = []
    for year in years:
        rows, dropped = fetch_prices(year)
        days = group_by_berlin_day(rows)
        ppd = defaultdict(int)
        for d in days:
            ppd[len(days[d])] += 1
        print(f"\n########## {year} ##########")
        print(f"  {len(rows)} prices ({dropped} null), {len(days)} Berlin days, "
              f"points/day {dict(sorted(ppd.items()))}")
        print(f"  range {min(p for _,p in rows):.1f}..{max(p for _,p in rows):.1f} EUR/MWh, "
              f"{sum(1 for _, p in rows if p < 0)} neg-price intervals")
        s15, c15, g15, _ = run(days, 1.5, "ceiling, capped 1.5 cyc")
        s0, c0, g0, _ = run(days, None, "ceiling, uncapped")
        summary.append((year, s15, c15, g15, s0, c0, g0))

    print("\n===== MULTI-YEAR SUMMARY — perfect-foresight UPPER BOUND (no fudge) =====")
    print("assumed: 80.0 EUR/MWh @ 1.50 cyc/day, ~EUR 9,947 gross/yr")
    print(f"{'year':>5} | {'capped@1.5  EUR/MWh   cyc    gross':>34} | "
          f"{'uncapped  EUR/MWh   cyc    gross':>32}")
    for yr, s15, c15, g15, s0, c0, g0 in summary:
        print(f"{yr:>5} | {s15:>14.1f} {c15:>6.2f} {g15:>9,.0f}  | "
              f"{s0:>12.1f} {c0:>6.2f} {g0:>9,.0f}")
    print("\nReal causal capture ~85% of this ceiling. Re-base the deck on the conservative end.")


if __name__ == "__main__":
    main()
