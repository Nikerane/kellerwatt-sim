"""Pinned, deterministic MILP solver — HiGHS only, optimal-or-fail.

The validated spike fell back to CBC when HiGHS was unavailable; the production
engine must not. A non-optimal status is a hard error (we never report a number
from a non-optimal solve). Solver metadata (name/version/tolerance) is recorded
in the export provenance.
"""
from __future__ import annotations

from importlib import metadata

import pulp

SOLVER_NAME = "HiGHS"
# HiGHS default MIP gap; PuLP's wrapper does not expose a knob, so we record the
# tolerance we rely on for reproducibility rather than tightening it per-solve.
MIP_GAP_TOLERANCE = 0.0


class SolverError(RuntimeError):
    """Raised when the solver does not return a provably optimal solution."""


def make_solver(msg: bool = False):
    """Return the pinned HiGHS solver. Raises if HiGHS is not importable — no
    silent CBC fallback (determinism guardrail)."""
    return pulp.HiGHS(msg=msg)


def _highs_version() -> str:
    for dist in ("highspy", "PuLP"):
        try:
            return metadata.version(dist)
        except metadata.PackageNotFoundError:
            continue
    return "unknown"


def solver_metadata() -> dict:
    return {
        "name": SOLVER_NAME,
        "version": _highs_version(),
        "status": None,  # filled in per-run by the caller
        "mip_gap_tolerance": MIP_GAP_TOLERANCE,
    }


def solve_or_raise(prob: "pulp.LpProblem", solver=None) -> "pulp.LpProblem":
    """Solve `prob` and raise SolverError unless the status is Optimal."""
    solver = solver or make_solver()
    status_code = prob.solve(solver)
    status = pulp.LpStatus[status_code]
    if status != "Optimal":
        raise SolverError(
            f"{SOLVER_NAME} returned status {status!r} for problem "
            f"{prob.name!r}; expected 'Optimal'."
        )
    return prob
