"""Dispatch engines — the validated LP ceiling and the causal walk-forward benchmark.

(a) solve_day_ceiling: perfect-foresight day-ahead LP (the spike, hardened). Binary
    no-simultaneity, AC-side cashflows, RTE applied once (eta both ways), cyclic SoC,
    cycle cap, marginal charges (grid fee on charge, degradation) inside the objective
    (Codex 4). Reported gross is pure AC arbitrage from the solved dispatch; the
    tie-break and marginal charges only SHAPE the dispatch. Optimal-or-fail.

(b) run_causal_walkforward: a causal benchmark that uses NO foresight. Buy/sell price
    thresholds are quantiles of the trailing `trailing_days` complete Berlin days,
    fixed for the whole day (no current-day recalibration). SoC is carried continuously
    across days from a fixed initial SoC; a deterministic terminal restoration values
    the net horizon energy change at a causal reference price so it is comparable to the
    cyclic LP (Codex 10). Reported as a benchmark-vs-ceiling bracket, NOT a floor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import numpy as np
import pulp

from engine.params import Battery
from engine.solver import solve_or_raise

DEFAULT_TIEBREAK_EUR_MWH = 1.0  # tiny throughput tie-break (matches the spike's lambda)
_EPS = 1e-9


# ===== (a) LP perfect-foresight ceiling ======================================

@dataclass(frozen=True)
class DayDispatch:
    gross_eur: float          # pure AC arbitrage revenue of the solved dispatch
    mwh_discharged: float     # AC energy delivered
    mwh_charged: float        # AC energy drawn
    simul_max: float          # max simultaneous charge & discharge (must be ~0)
    status: str
    charge_kw: tuple
    discharge_kw: tuple
    soc_kwh: tuple
    soc_init_kwh: float


def solve_day_ceiling(
    prices: Sequence[float],
    dt_h: float,
    battery: Battery,
    *,
    cycle_cap: float | None,
    grid_fee_charge: float = 0.0,
    degradation_discharge: float = 0.0,
    tiebreak: float = DEFAULT_TIEBREAK_EUR_MWH,
    solver=None,
) -> DayDispatch:
    """Perfect-foresight LP for one delivery day. €/MWh charges; kW powers; kWh SoC."""
    T = len(prices)
    P = battery.power_kw
    eta = battery.eta_one_way
    smin, smax = battery.soc_min_kwh, battery.soc_max_kwh

    prob = pulp.LpProblem("ceiling", pulp.LpMaximize)
    c = [pulp.LpVariable(f"c{t}", lowBound=0, upBound=P) for t in range(T)]
    d = [pulp.LpVariable(f"d{t}", lowBound=0, upBound=P) for t in range(T)]
    soc = [pulp.LpVariable(f"s{t}", lowBound=smin, upBound=smax) for t in range(T)]
    s0 = pulp.LpVariable("s_init", lowBound=smin, upBound=smax)
    y = [pulp.LpVariable(f"y{t}", cat="Binary") for t in range(T)]  # 1 = charge mode

    revenue = pulp.lpSum((prices[t] / 1000.0) * (d[t] - c[t]) * dt_h for t in range(T))
    tie = pulp.lpSum((tiebreak / 1000.0) * (c[t] + d[t]) * dt_h for t in range(T))
    grid = pulp.lpSum((grid_fee_charge / 1000.0) * c[t] * dt_h for t in range(T))
    deg = pulp.lpSum((degradation_discharge / 1000.0) * d[t] * dt_h for t in range(T))
    prob += revenue - tie - grid - deg

    for t in range(T):
        prev = s0 if t == 0 else soc[t - 1]
        prob += soc[t] == prev + (eta * c[t] - d[t] / eta) * dt_h
        prob += c[t] <= P * y[t]          # no simultaneous charge & discharge
        prob += d[t] <= P * (1 - y[t])
    prob += soc[T - 1] == s0              # cyclic SoC
    if cycle_cap is not None:
        prob += pulp.lpSum(d[t] * dt_h for t in range(T)) <= cycle_cap * battery.usable_kwh

    solve_or_raise(prob, solver)

    cv = [c[t].value() or 0.0 for t in range(T)]
    dv = [d[t].value() or 0.0 for t in range(T)]
    socv = [soc[t].value() for t in range(T)]
    gross = sum((prices[t] / 1000.0) * (dv[t] - cv[t]) * dt_h for t in range(T))
    mwh_dis = sum(dv[t] * dt_h for t in range(T)) / 1000.0
    mwh_chg = sum(cv[t] * dt_h for t in range(T)) / 1000.0
    simul = max((min(cv[t], dv[t]) for t in range(T)), default=0.0)
    return DayDispatch(
        gross_eur=gross,
        mwh_discharged=mwh_dis,
        mwh_charged=mwh_chg,
        simul_max=simul,
        status="Optimal",
        charge_kw=tuple(cv),
        discharge_kw=tuple(dv),
        soc_kwh=tuple(socv),
        soc_init_kwh=s0.value(),
    )


# ===== (b) causal walk-forward benchmark =====================================

@dataclass(frozen=True)
class CausalParams:
    trailing_days: int = 28
    charge_quantile: float = 0.25    # charge when price <= 25th pct of trailing window
    discharge_quantile: float = 0.75  # discharge when price >= 75th pct


@dataclass(frozen=True)
class CausalDay:
    day: date
    gross_eur: float          # pure AC arbitrage realized that day
    net_eur: float            # after marginal grid fee / degradation
    mwh_discharged: float
    mwh_charged: float
    soc_start_kwh: float
    soc_end_kwh: float
    traded: bool


@dataclass(frozen=True)
class CausalResult:
    days: tuple
    soc_init_kwh: float
    soc_final_kwh: float
    terminal_value_eur: float
    terminal_ref_price: float

    @property
    def gross_eur(self) -> float:
        return sum(d.gross_eur for d in self.days) + self.terminal_value_eur

    @property
    def net_eur(self) -> float:
        return sum(d.net_eur for d in self.days) + self.terminal_value_eur

    @property
    def mwh_discharged(self) -> float:
        return sum(d.mwh_discharged for d in self.days)

    @property
    def mwh_charged(self) -> float:
        return sum(d.mwh_charged for d in self.days)

    @property
    def implied_spread(self) -> float:
        m = self.mwh_discharged
        return self.gross_eur / m if m else 0.0

    def per_year(self) -> dict:
        """Aggregate gross/discharge/charge by calendar year of the delivery day."""
        agg: dict[int, dict] = {}
        for d in self.days:
            y = agg.setdefault(d.day.year, {"gross": 0.0, "net": 0.0, "dis": 0.0, "chg": 0.0})
            y["gross"] += d.gross_eur
            y["net"] += d.net_eur
            y["dis"] += d.mwh_discharged
            y["chg"] += d.mwh_charged
        return agg


def run_causal_walkforward(
    days: Sequence,
    battery: Battery,
    *,
    cycle_cap: float | None,
    params: CausalParams = CausalParams(),
    grid_fee_charge: float = 0.0,
    degradation_discharge: float = 0.0,
    soc_init: float | None = None,
) -> CausalResult:
    """Walk a chronological sequence of DayPrices with a causal threshold policy."""
    days = sorted(days, key=lambda x: x.day)
    P = battery.power_kw
    eta = battery.eta_one_way
    rte = eta * eta
    smin, smax = battery.soc_min_kwh, battery.soc_max_kwh
    budget_cap = cycle_cap * battery.usable_kwh if cycle_cap is not None else float("inf")

    soc = battery.soc_min_kwh if soc_init is None else soc_init
    soc_init_val = soc
    results: list[CausalDay] = []
    last_window: np.ndarray | None = None

    for i, day in enumerate(days):
        dt = day.dt_h
        traded = i >= params.trailing_days
        if traded:
            window = np.fromiter(
                (p for dd in days[i - params.trailing_days:i] for p in dd.prices),
                dtype=float,
            )
            last_window = window
            ch_thr = float(np.quantile(window, params.charge_quantile))
            dis_thr = float(np.quantile(window, params.discharge_quantile))
        else:
            ch_thr = dis_thr = None

        soc_start = soc
        day_dis_ac = 0.0
        g = net = mdis = mchg = 0.0

        for price in day.prices:
            # Charge on cheap intervals, only if a positive round-trip is expected
            # after the marginal grid fee (marginal charge inside the policy, Codex 4).
            if traded and price <= ch_thr and soc < smax - _EPS \
                    and (price + grid_fee_charge) < dis_thr * rte:
                c_kw = min(P, (smax - soc) / (eta * dt))
                if c_kw > _EPS:
                    e_ac = c_kw * dt
                    soc += eta * c_kw * dt
                    g -= (price / 1000.0) * e_ac
                    net -= ((price + grid_fee_charge) / 1000.0) * e_ac
                    mchg += e_ac / 1000.0
                    continue
            # Discharge on expensive intervals, within SoC and the daily cycle cap.
            if traded and price >= dis_thr and soc > smin + _EPS \
                    and day_dis_ac < budget_cap - _EPS \
                    and (price - degradation_discharge) > ch_thr / rte:
                d_kw = min(P, (soc - smin) * eta / dt, (budget_cap - day_dis_ac) / dt)
                if d_kw > _EPS:
                    e_ac = d_kw * dt
                    soc -= d_kw / eta * dt
                    g += (price / 1000.0) * e_ac
                    net += ((price - degradation_discharge) / 1000.0) * e_ac
                    mdis += e_ac / 1000.0
                    day_dis_ac += e_ac
                    continue
            # else idle

        results.append(CausalDay(day.day, g, net, mdis, mchg, soc_start, soc, traded))

    # Deterministic terminal restoration: value the net horizon energy change at a
    # causal reference (median of the last trailing window), discounted through eta,
    # so the continuous-SoC strategy is comparable to the cyclic LP (Codex 10).
    soc_final = soc
    ref = float(np.median(last_window)) if last_window is not None else 0.0
    terminal_value = ref * ((soc_final - soc_init_val) * eta / 1000.0)
    return CausalResult(
        days=tuple(results),
        soc_init_kwh=soc_init_val,
        soc_final_kwh=soc_final,
        terminal_value_eur=terminal_value,
        terminal_ref_price=ref,
    )
