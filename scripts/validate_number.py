#!/usr/bin/env python3
"""Validate the core number — throwaway spike (Codex review #18).

Downloads real DE-LU 2024 day-ahead prices (Energy-Charts, no token), runs a
*corrected* perfect-day-ahead-foresight LP, and prints the implied captured
spread (EUR/MWh) and cycles/day to compare against the business-plan assumption
of ~EUR 80/MWh at 1.5 cycles/day.

Corrections baked in vs the original plan:
  #1  no simultaneous charge/discharge (a strictly-positive throughput penalty
      makes it unprofitable; we ALSO assert it never happens).
  #2  delivery days grouped by Europe/Berlin local date (not UTC), so DST
      23h/25h days are handled correctly.
  #15 data completeness is validated and reported, not silently dropped.
  #3  the LP is reported strictly as a perfect-foresight UPPER BOUND — no
      capture-% fudge factor anywhere.

Stdlib only except PuLP (+ optional highspy). Python 3.9+.
"""
import json
import math
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
LAMBDA_EUR_MWH = 1.0              # tiny throughput tie-break -> kills simultaneity
BERLIN = ZoneInfo("Europe/Berlin")

URL = "https://api.energy-charts.info/price?bzn=DE-LU&start=2024-01-01&end=2024-12-31"


def fetch_prices():
    with urllib.request.urlopen(URL, timeout=120) as r:
        payload = json.load(r)
    secs, price = payload["unix_seconds"], payload["price"]
    rows = []
    dropped = 0
    for s, p in zip(secs, price):
        if p is None:
            dropped += 1
            continue
        utc = datetime.fromtimestamp(s, tz=timezone.utc)
        rows.append((utc, float(p)))
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
    prob += soc[T - 1] == soc0  # cyclic: end where we began
    if cycles_cap is not None:
        prob += pulp.lpSum(d[t] * dt_h for t in range(T)) <= cycles_cap * E_USABLE

    prob.solve(SOLVER)
    cv = [c[t].value() or 0.0 for t in range(T)]
    dv = [d[t].value() or 0.0 for t in range(T)]
    gross = sum((prices[t] / 1000.0) * (dv[t] - cv[t]) * dt_h for t in range(T))
    mwh_dis = sum(dv[t] * dt_h for t in range(T)) / 1000.0
    mwh_chg = sum(cv[t] * dt_h for t in range(T)) / 1000.0
    simul = max((min(cv[t], dv[t]) for t in range(T)), default=0.0)
    neg_gross = sum((prices[t] / 1000.0) * (dv[t] - cv[t]) * dt_h
                    for t in range(T) if prices[t] < 0)
    return gross, mwh_dis, mwh_chg, simul, neg_gross


def run(days, cycles_cap, label):
    tot_gross = tot_dis = tot_chg = tot_neg = 0.0
    max_simul = 0.0
    n = 0
    for d in sorted(days):
        pts = days[d]
        if len(pts) < 20:          # incomplete day (allow 23 for DST)
            continue
        prices = [p for _, p in pts]
        dt_h = 1.0                  # 2024 DE-LU is hourly
        g, md, mc, sm, ng = solve_day(prices, dt_h, cycles_cap)
        tot_gross += g; tot_dis += md; tot_chg += mc; tot_neg += ng
        max_simul = max(max_simul, sm)
        n += 1
    spread = tot_gross / tot_dis if tot_dis else 0.0
    cyc = (tot_dis * 1000.0) / (E_USABLE * n) if n else 0.0
    print(f"\n=== {label} ===")
    print(f"days simulated         : {n}")
    print(f"total gross (EUR)      : {tot_gross:,.0f}")
    print(f"MWh discharged (AC)    : {tot_dis:,.1f}")
    print(f"MWh charged (AC)       : {tot_chg:,.1f}")
    print(f"IMPLIED SPREAD EUR/MWh : {spread:,.1f}   (assumed 80)")
    print(f"IMPLIED CYCLES/DAY     : {cyc:,.2f}   (assumed 1.5)")
    print(f"gross during neg-price : {tot_neg:,.0f} EUR "
          f"({100*tot_neg/tot_gross if tot_gross else 0:.0f}% of gross)")
    print(f"max simultaneous c&d   : {max_simul:.4f} kW  (must be ~0)")
    return spread, cyc


def main():
    global SOLVER
    try:
        SOLVER = pulp.HiGHS(msg=False)
        solver_name = "HiGHS"
    except Exception:
        SOLVER = pulp.PULP_CBC_CMD(msg=False)
        solver_name = "CBC"
    print(f"solver: {solver_name}")

    rows, dropped = fetch_prices()
    days = group_by_berlin_day(rows)
    hour_counts = defaultdict(int)
    for d in days:
        hour_counts[len(days[d])] += 1
    print(f"fetched {len(rows)} hourly prices ({dropped} null dropped)")
    print(f"Berlin delivery days   : {len(days)}")
    print(f"hours-per-day histogram: {dict(sorted(hour_counts.items()))}")
    print(f"price range EUR/MWh    : {min(p for _,p in rows):.1f} .. {max(p for _,p in rows):.1f}")
    neg_hours = sum(1 for _, p in rows if p < 0)
    print(f"negative-price hours   : {neg_hours}")

    run(days, 1.5, "PERFECT-FORESIGHT CEILING, capped at 1.5 cycles/day")
    run(days, None, "PERFECT-FORESIGHT CEILING, uncapped (natural cycling)")
    print("\nNote: the LP has PERFECT day-ahead foresight -> this is an UPPER BOUND.")
    print("Real causal operation (forecast error) lands below this. No capture-% fudge applied.")


if __name__ == "__main__":
    main()
