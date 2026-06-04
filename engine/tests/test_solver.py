"""A1 — solver. Pinned HiGHS, deterministic, **optimal-or-fail** (no CBC fallback,
unlike the throwaway spike). A non-optimal status must raise, never be silently used.
"""
import pulp
import pytest

from engine import solver


def test_make_solver_is_highs():
    s = solver.make_solver()
    # PuLP's HiGHS wrapper; name varies by version but must reference HiGHS.
    assert "HiGHS" in type(s).__name__ or "HiGHS" in getattr(s, "name", "")


def test_solver_metadata_reports_name_and_version():
    meta = solver.solver_metadata()
    assert meta["name"] == "HiGHS"
    assert isinstance(meta["version"], str) and meta["version"]
    assert "mip_gap_tolerance" in meta


def test_solve_or_raise_returns_optimal_value():
    prob = pulp.LpProblem("feasible", pulp.LpMaximize)
    x = pulp.LpVariable("x", lowBound=0, upBound=3)
    prob += x
    prob += x <= 2
    solver.solve_or_raise(prob)
    assert pulp.LpStatus[prob.status] == "Optimal"
    assert abs(pulp.value(prob.objective) - 2.0) < 1e-9


def test_solve_or_raise_raises_on_infeasible():
    prob = pulp.LpProblem("infeasible", pulp.LpMaximize)
    x = pulp.LpVariable("x", lowBound=0)
    prob += x
    prob += x <= 1
    prob += x >= 2  # contradiction
    with pytest.raises(solver.SolverError):
        solver.solve_or_raise(prob)
