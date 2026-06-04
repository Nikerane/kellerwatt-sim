# KellerWatt Battery-Arbitrage Simulation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Streamlit dashboard that backtests a 200 kWh basement battery on real German day-ahead prices and reconciles the result against the business-plan assumptions (implied €/MWh & cycles/day vs the assumed €80/1.5), with judge-draggable stress-test sliders.

**Architecture:** Pure functions in `src/` with one job each. Both dispatch strategies return the same `Schedule`, so everything downstream is strategy-agnostic. The **expensive LP dispatch is computed once and cached**; the **cheap economics layer** recomputes instantly on every econ-slider change. Data is pre-downloaded to Parquet — the app never hits the network.

**Tech Stack:** Python 3.12 · pandas · numpy · numpy-financial · pulp[highs] · plotly · streamlit · requests (data-prep) · entsoe-py (cross-check only) · pytest.

**Design source of truth:** `docs/superpowers/specs/2026-06-04-kellerwatt-arbitrage-sim-design.md`.

**Refinements over the spec (intentional):**
- Keep prices at **native resolution** (hourly before 2025-10-01, 15-min after) and infer `dt_h` per day, rather than upsampling. Cleaner and avoids fabricating intra-hour granularity.
- **Dispatch ↔ economics split:** `run_backtest` returns per-day dispatch aggregates (independent of econ sliders); `compute_metrics` applies the economics. This is what makes the sliders responsive.

---

### Task 1: Project scaffolding & dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Write `requirements.txt`**

```
pandas>=2.2
numpy>=1.26
numpy-financial>=1.0
pulp[highs]>=2.8
plotly>=5.20
streamlit>=1.33
requests>=2.31
pyarrow>=15.0
entsoe-py>=0.7.8
pytest>=8.0
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.streamlit/secrets.toml
# real-numbers config must never be committed/deployed
src/params_real.py
.DS_Store
```

- [ ] **Step 3: Write `README.md` (skeleton)**

```markdown
# KellerWatt Arbitrage Simulation

Backtests a 200 kWh basement battery on real German (DE-LU) day-ahead prices and
reconciles the result against the business-plan assumptions.

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt

## Data (one-time)
    python -m src.fetch_prices --start 2024-01-01 --out data/prices_de_lu.parquet

## Run
    streamlit run app/streamlit_app.py            # baseline (real) preset
    KW_PRESET=sanitized streamlit run app/streamlit_app.py   # public/sanitized preset

## Test
    pytest -q
```

- [ ] **Step 4: Create empty `src/__init__.py` and `tests/__init__.py`**

Both files are empty.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore README.md src/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding and dependencies"
```

---

### Task 2: Parameters and presets (`src/params.py`)

**Files:**
- Create: `src/params.py`
- Test: `tests/test_params.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_params.py
import math
from src.params import BatteryParams, EconParams, AssumedBaseline, BASELINE, SANITIZED, get_preset


def test_battery_derived_values():
    b = BatteryParams()  # 200 kWh, 50 kW, 10-100%, RTE 0.90
    assert b.e_usable_kwh == 180.0                      # 200 * (1.0 - 0.10)
    assert math.isclose(b.eta_chg, 0.9 ** 0.5)
    assert math.isclose(b.eta_dis, 0.9 ** 0.5)
    assert b.soc_min_kwh == 20.0
    assert b.soc_max_kwh == 200.0


def test_baseline_preset_has_assumed_figures():
    assert BASELINE.assumed.gross_eur == 9947
    assert BASELINE.assumed.cycles_day == 1.5
    assert BASELINE.econ.bkv_fee_pct == 0.12


def test_get_preset_selects_by_name():
    assert get_preset("baseline") is BASELINE
    assert get_preset("sanitized") is SANITIZED
    assert get_preset("BASELINE") is BASELINE  # case-insensitive
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_params.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.params'`.

- [ ] **Step 3: Write `src/params.py`**

```python
# src/params.py
"""Battery + economic parameters and the BASELINE / SANITIZED presets.

Swap in real business-plan numbers by editing BASELINE below (this file is the
single source of truth for the "Spreadsheet assumed" column). SANITIZED holds
placeholder figures for the public deployment.
"""
from dataclasses import dataclass, field


@dataclass
class BatteryParams:
    capacity_kwh: float = 200.0
    power_kw: float = 50.0          # 200 / 50 = 4-hour battery
    soc_min_frac: float = 0.10
    soc_max_frac: float = 1.0
    eta_rt: float = 0.90            # round-trip; applied ONCE in the SoC balance
    cycles_cap: float = 1.5         # per-day discharge throughput cap (cycles)
    degradation_eur_mwh: float = 0.0

    @property
    def e_usable_kwh(self) -> float:
        return self.capacity_kwh * (self.soc_max_frac - self.soc_min_frac)

    @property
    def eta_chg(self) -> float:
        return self.eta_rt ** 0.5

    @property
    def eta_dis(self) -> float:
        return self.eta_rt ** 0.5

    @property
    def soc_min_kwh(self) -> float:
        return self.capacity_kwh * self.soc_min_frac

    @property
    def soc_max_kwh(self) -> float:
        return self.capacity_kwh * self.soc_max_frac


@dataclass
class EconParams:
    capex_eur: float = 140_000.0
    opex_eur_yr: float = 2_000.0
    owner_lease_eur_yr: float = 1_000.0
    bkv_fee_pct: float = 0.12             # aggregator fee on gross trading revenue
    grid_fee_on_charge_eur_mwh: float = 0.0   # downside scenario slider
    fcr_afrr_eur_yr: float = 0.0          # capped, partitioned ancillary line
    capture_pct: float = 0.85             # live vs perfect-foresight haircut
    asset_life_yr: int = 15


@dataclass(frozen=True)
class AssumedBaseline:
    """The 'Spreadsheet assumed' figures shown for comparison (display only)."""
    spread_eur_mwh: float
    cycles_day: float
    gross_eur: float
    ebitda_eur: float
    irr: float
    payback_yr: float


@dataclass
class Preset:
    name: str
    battery: BatteryParams
    econ: EconParams
    assumed: AssumedBaseline


# --- EDIT THESE with the real spreadsheet numbers for the live pitch ---
BASELINE = Preset(
    name="baseline",
    battery=BatteryParams(),
    econ=EconParams(capex_eur=140_000.0),
    assumed=AssumedBaseline(
        spread_eur_mwh=80.0, cycles_day=1.5,
        gross_eur=9947, ebitda_eur=6758, irr=0.187, payback_yr=5.0,
    ),
)

# Placeholder figures for the public deployment — NOT the real economics.
SANITIZED = Preset(
    name="sanitized",
    battery=BatteryParams(),
    econ=EconParams(capex_eur=150_000.0),
    assumed=AssumedBaseline(
        spread_eur_mwh=75.0, cycles_day=1.3,
        gross_eur=8500, ebitda_eur=5500, irr=0.150, payback_yr=6.0,
    ),
)

_PRESETS = {"baseline": BASELINE, "sanitized": SANITIZED}


def get_preset(name: str) -> Preset:
    return _PRESETS[name.lower()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_params.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/params.py tests/test_params.py
git commit -m "feat: battery/econ parameters and BASELINE/SANITIZED presets"
```

---

### Task 3: Schedule type + data loading (`src/data_load.py`)

**Files:**
- Create: `src/types.py`
- Create: `src/data_load.py`
- Test: `tests/test_data_load.py`

- [ ] **Step 1: Write `src/types.py` (shared dataclass; no test needed — it is a pure container)**

```python
# src/types.py
from dataclasses import dataclass
import numpy as np


@dataclass
class Schedule:
    """AC-side per-step plan. charge_kw/discharge_kw are grid-side powers (>=0);
    soc_kwh is battery state of charge at the END of each step."""
    charge_kw: np.ndarray
    discharge_kw: np.ndarray
    soc_kwh: np.ndarray
    dt_h: float
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_data_load.py
import pandas as pd
from src.data_load import load_prices, infer_dt_h


def _write_fixture(tmp_path):
    ts = pd.to_datetime(
        ["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-02 00:00"], utc=True
    )
    df = pd.DataFrame({"ts": ts, "price_eur_mwh": [10.0, 90.0, 50.0]})
    p = tmp_path / "prices.parquet"
    df.to_parquet(p)
    return p


def test_load_prices_sorted_and_typed(tmp_path):
    p = _write_fixture(tmp_path)
    out = load_prices(p)
    assert list(out.columns) == ["ts", "price_eur_mwh"]
    assert str(out["ts"].dt.tz) == "UTC"
    assert out["ts"].is_monotonic_increasing
    assert len(out) == 3


def test_load_prices_date_filter(tmp_path):
    p = _write_fixture(tmp_path)
    out = load_prices(p, start="2024-01-02", end="2024-01-02")
    assert len(out) == 1
    assert out.iloc[0]["price_eur_mwh"] == 50.0


def test_infer_dt_h_hourly():
    ts = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 02:00"], utc=True)
    day = pd.DataFrame({"ts": ts, "price_eur_mwh": [1.0, 2.0, 3.0]})
    assert infer_dt_h(day) == 1.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_data_load.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data_load'`.

- [ ] **Step 4: Write `src/data_load.py`**

```python
# src/data_load.py
import pandas as pd


def load_prices(path, start=None, end=None) -> pd.DataFrame:
    """Load DE-LU day-ahead prices from Parquet. Returns columns [ts (UTC), price_eur_mwh],
    sorted and de-duplicated. Optional inclusive date filter (YYYY-MM-DD strings)."""
    df = pd.read_parquet(path)[["ts", "price_eur_mwh"]].copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.dropna(subset=["price_eur_mwh"]).drop_duplicates("ts").sort_values("ts")
    if start is not None:
        df = df[df["ts"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        end_excl = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        df = df[df["ts"] < end_excl]
    return df.reset_index(drop=True)


def infer_dt_h(day_df: pd.DataFrame) -> float:
    """Median spacing of a single day's timestamps, in hours (1.0 hourly, 0.25 quarter-hour)."""
    if len(day_df) < 2:
        return 1.0
    diffs = day_df["ts"].diff().dropna()
    return float(diffs.median().total_seconds() / 3600.0)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_data_load.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/types.py src/data_load.py tests/test_data_load.py
git commit -m "feat: Schedule type and price data loading"
```

---

### Task 4: Price download script (`src/fetch_prices.py`)

**Files:**
- Create: `src/fetch_prices.py`
- Test: `tests/test_fetch_prices.py`

The network fetch is not unit-tested; the **JSON parser** is (it is the part that breaks).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_prices.py
from src.fetch_prices import parse_energy_charts


def test_parse_energy_charts_to_dataframe():
    payload = {
        "unix_seconds": [1704067200, 1704070800],  # 2024-01-01 00:00, 01:00 UTC
        "price": [10.5, 92.3],
        "unit": "EUR / MWh",
    }
    df = parse_energy_charts(payload)
    assert list(df.columns) == ["ts", "price_eur_mwh"]
    assert len(df) == 2
    assert str(df["ts"].dt.tz) == "UTC"
    assert df.iloc[1]["price_eur_mwh"] == 92.3
    assert str(df.iloc[0]["ts"]) == "2024-01-01 00:00:00+00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch_prices.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.fetch_prices'`.

- [ ] **Step 3: Write `src/fetch_prices.py`**

```python
# src/fetch_prices.py
"""One-time price downloader. Pulls DE-LU day-ahead prices from Energy-Charts
(no token, CC BY 4.0 — attribute 'Energy-Charts.info') and writes Parquet.

Usage:
    python -m src.fetch_prices --start 2024-01-01 --out data/prices_de_lu.parquet
"""
import argparse

import pandas as pd
import requests

ENERGY_CHARTS_URL = "https://api.energy-charts.info/price"


def parse_energy_charts(payload: dict) -> pd.DataFrame:
    """Convert an Energy-Charts /price JSON payload to [ts (UTC), price_eur_mwh]."""
    ts = pd.to_datetime(payload["unix_seconds"], unit="s", utc=True)
    df = pd.DataFrame({"ts": ts, "price_eur_mwh": payload["price"]})
    return df.dropna(subset=["price_eur_mwh"]).sort_values("ts").reset_index(drop=True)


def fetch_year(year: int, bzn: str = "DE-LU") -> pd.DataFrame:
    """Fetch one calendar year (Energy-Charts caps each request to a bounded range)."""
    params = {"bzn": bzn, "start": f"{year}-01-01", "end": f"{year}-12-31"}
    resp = requests.get(ENERGY_CHARTS_URL, params=params, timeout=60)
    resp.raise_for_status()
    return parse_energy_charts(resp.json())


def fetch_range(start: str, end: str | None, bzn: str = "DE-LU") -> pd.DataFrame:
    start_year = pd.Timestamp(start).year
    end_year = pd.Timestamp(end).year if end else pd.Timestamp.utcnow().year
    frames = [fetch_year(y, bzn) for y in range(start_year, end_year + 1)]
    out = pd.concat(frames, ignore_index=True).drop_duplicates("ts").sort_values("ts")
    return out.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default="data/prices_de_lu.parquet")
    args = ap.parse_args()
    df = fetch_range(args.start, args.end)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out} ({df['ts'].min()} .. {df['ts'].max()})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch_prices.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Download real data (manual, one-time) and sanity-check**

Run: `python -m src.fetch_prices --start 2024-01-01 --out data/prices_de_lu.parquet`
Expected: prints `Wrote NNNNN rows ...` with min near 2024-01-01 and max near today. If the
network is unavailable, skip — later tasks use synthetic fixtures and do not require this file.

- [ ] **Step 6: Commit (code only; data file is large — keep it but commit separately)**

```bash
git add src/fetch_prices.py tests/test_fetch_prices.py
git commit -m "feat: Energy-Charts price downloader with tested parser"
git add -f data/prices_de_lu.parquet 2>/dev/null && git commit -m "data: DE-LU day-ahead prices 2024->present" || echo "no data file yet — fine"
```

---

### Task 5: Threshold dispatch (`src/dispatch.py`)

**Files:**
- Create: `src/dispatch.py`
- Test: `tests/test_dispatch_threshold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dispatch_threshold.py
import numpy as np
from src.params import BatteryParams
from src.dispatch import dispatch_threshold


def test_threshold_charges_cheap_discharges_dear():
    prices = np.array([10.0, 10.0, 100.0, 100.0])   # EUR/MWh
    batt = BatteryParams(eta_rt=1.0, cycles_cap=10.0)
    s = dispatch_threshold(prices, batt, buy_eur=50.0, sell_eur=80.0, dt_h=0.25)
    assert s.charge_kw[0] > 0 and s.charge_kw[1] > 0     # charged in cheap steps
    assert s.discharge_kw[2] > 0 and s.discharge_kw[3] > 0  # discharged in dear steps
    assert s.charge_kw[2] == 0 and s.discharge_kw[0] == 0


def test_threshold_respects_power_and_soc_bounds():
    prices = np.array([10.0] * 20 + [100.0] * 20)
    batt = BatteryParams(eta_rt=1.0, cycles_cap=10.0)
    s = dispatch_threshold(prices, batt, buy_eur=50.0, sell_eur=80.0, dt_h=0.25)
    assert s.charge_kw.max() <= batt.power_kw + 1e-6
    assert s.discharge_kw.max() <= batt.power_kw + 1e-6
    assert s.soc_kwh.min() >= batt.soc_min_kwh - 1e-6
    assert s.soc_kwh.max() <= batt.soc_max_kwh + 1e-6


def test_threshold_respects_cycle_cap():
    prices = np.array([10.0] * 50 + [100.0] * 50)
    batt = BatteryParams(eta_rt=1.0, cycles_cap=0.5)   # at most 0.5 * 180 = 90 kWh discharged
    s = dispatch_threshold(prices, batt, buy_eur=50.0, sell_eur=80.0, dt_h=0.25)
    discharged_kwh = s.discharge_kw.sum() * 0.25
    assert discharged_kwh <= 0.5 * batt.e_usable_kwh + 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dispatch_threshold.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.dispatch'`.

- [ ] **Step 3: Write the threshold dispatcher in `src/dispatch.py`**

```python
# src/dispatch.py
import numpy as np

from src.params import BatteryParams
from src.types import Schedule


def dispatch_threshold(prices_eur_mwh, batt: BatteryParams,
                       buy_eur: float = 50.0, sell_eur: float = 100.0,
                       dt_h: float = 0.25) -> Schedule:
    """Greedy rule: charge below buy_eur, discharge above sell_eur, within SoC/power/cycle
    bounds. Powers are AC-side (grid); efficiency losses live inside the SoC update."""
    prices = np.asarray(prices_eur_mwh, dtype=float)
    T = len(prices)
    c = np.zeros(T)
    d = np.zeros(T)
    soc_track = np.zeros(T)
    soc = batt.soc_min_kwh
    cap_kwh = batt.cycles_cap * batt.e_usable_kwh
    discharged = 0.0

    for t in range(T):
        if prices[t] <= buy_eur and soc < batt.soc_max_kwh:
            headroom_ac_kw = (batt.soc_max_kwh - soc) / batt.eta_chg / dt_h
            c[t] = min(batt.power_kw, headroom_ac_kw)
            soc += c[t] * batt.eta_chg * dt_h
        elif prices[t] >= sell_eur and soc > batt.soc_min_kwh and discharged < cap_kwh:
            avail_ac_kw = (soc - batt.soc_min_kwh) * batt.eta_dis / dt_h
            cap_left_kw = (cap_kwh - discharged) / dt_h
            d[t] = min(batt.power_kw, avail_ac_kw, cap_left_kw)
            soc -= d[t] / batt.eta_dis * dt_h
            discharged += d[t] * dt_h
        soc_track[t] = soc

    return Schedule(charge_kw=c, discharge_kw=d, soc_kwh=soc_track, dt_h=dt_h)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dispatch_threshold.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/dispatch.py tests/test_dispatch_threshold.py
git commit -m "feat: threshold dispatch strategy"
```

---

### Task 6: LP dispatch (`src/dispatch.py`)

**Files:**
- Modify: `src/dispatch.py` (add `dispatch_lp`)
- Test: `tests/test_dispatch_lp.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dispatch_lp.py
import numpy as np
from src.params import BatteryParams
from src.dispatch import dispatch_lp


def test_lp_charges_at_min_discharges_at_max():
    prices = np.array([10.0, 10.0, 100.0, 100.0])
    batt = BatteryParams(eta_rt=1.0, cycles_cap=10.0)
    s = dispatch_lp(prices, batt, dt_h=0.25)
    assert s.charge_kw[0] > 1e-3                      # bought cheap
    assert s.discharge_kw[3] > 1e-3                   # sold dear
    assert s.discharge_kw[0] < 1e-3                   # did not sell cheap


def test_lp_is_cyclic_soc_start_equals_end():
    prices = np.array([10.0, 20.0, 100.0, 90.0, 15.0, 110.0])
    batt = BatteryParams(eta_rt=0.90, cycles_cap=10.0)
    s = dispatch_lp(prices, batt, dt_h=0.25)
    # final SoC returns to the (free) initial SoC -> net daily storage change ~ 0
    soc_init_implied = s.soc_kwh[-1]
    delta = (batt.eta_chg * s.charge_kw - s.discharge_kw / batt.eta_dis) * 0.25
    assert abs(s.soc_kwh[0] - (soc_init_implied + delta[0])) < 1e-4


def test_lp_respects_cycle_cap():
    prices = np.array([10.0, 10.0, 10.0, 100.0, 100.0, 100.0])
    batt = BatteryParams(eta_rt=1.0, cycles_cap=0.25)   # <= 0.25 * 180 = 45 kWh discharged
    s = dispatch_lp(prices, batt, dt_h=0.25)
    assert s.discharge_kw.sum() * 0.25 <= 0.25 * batt.e_usable_kwh + 1e-3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dispatch_lp.py -q`
Expected: FAIL with `ImportError: cannot import name 'dispatch_lp'`.

- [ ] **Step 3: Add `dispatch_lp` to `src/dispatch.py`** (append; keep existing imports, add `import pulp`)

```python
import pulp


def _solver():
    """Prefer HiGHS (bundled via pulp[highs]); fall back to default CBC."""
    try:
        return pulp.HiGHS(msg=False)
    except Exception:
        return pulp.PULP_CBC_CMD(msg=False)


def dispatch_lp(prices_eur_mwh, batt: BatteryParams, dt_h: float = 0.25) -> Schedule:
    """Perfect-day-ahead-foresight LP for one delivery day. Maximises arbitrage revenue
    minus a degradation term, subject to power, SoC, cyclic (SoC_0 = SoC_T) and per-day
    cycle-throughput constraints. Powers are AC-side; RTE applied once in the SoC balance."""
    prices = np.asarray(prices_eur_mwh, dtype=float)
    T = len(prices)
    prob = pulp.LpProblem("arbitrage", pulp.LpMaximize)

    c = [pulp.LpVariable(f"c_{t}", lowBound=0, upBound=batt.power_kw) for t in range(T)]
    d = [pulp.LpVariable(f"d_{t}", lowBound=0, upBound=batt.power_kw) for t in range(T)]
    soc = [pulp.LpVariable(f"soc_{t}", lowBound=batt.soc_min_kwh, upBound=batt.soc_max_kwh)
           for t in range(T)]
    soc_init = pulp.LpVariable("soc_init", lowBound=batt.soc_min_kwh, upBound=batt.soc_max_kwh)

    # price EUR/MWh -> EUR/kWh = price/1000; AC arbitrage revenue minus degradation
    revenue = pulp.lpSum((prices[t] / 1000.0) * (d[t] - c[t]) * dt_h for t in range(T))
    degr = pulp.lpSum((batt.degradation_eur_mwh / 1000.0) * (c[t] + d[t]) * dt_h
                      for t in range(T))
    prob += revenue - degr

    for t in range(T):
        prev = soc_init if t == 0 else soc[t - 1]
        prob += soc[t] == prev + (batt.eta_chg * c[t] - d[t] / batt.eta_dis) * dt_h
    prob += soc[T - 1] == soc_init  # cyclic boundary: end where we began
    prob += pulp.lpSum(d[t] * dt_h for t in range(T)) <= batt.cycles_cap * batt.e_usable_kwh

    prob.solve(_solver())

    val = lambda v: float(v.value() or 0.0)
    return Schedule(
        charge_kw=np.array([val(c[t]) for t in range(T)]),
        discharge_kw=np.array([val(d[t]) for t in range(T)]),
        soc_kwh=np.array([val(soc[t]) for t in range(T)]),
        dt_h=dt_h,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dispatch_lp.py -q`
Expected: PASS (3 passed). If HiGHS is missing, the CBC fallback still passes.

- [ ] **Step 5: Commit**

```bash
git add src/dispatch.py tests/test_dispatch_lp.py
git commit -m "feat: perfect-foresight LP dispatch (PuLP/HiGHS)"
```

---

### Task 7: Economics layer (`src/economics.py`)

**Files:**
- Create: `src/economics.py`
- Test: `tests/test_economics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_economics.py
import numpy as np
from src.params import BatteryParams, EconParams
from src.types import Schedule
from src.economics import compute_day


def test_compute_day_gross_and_mwh():
    # 4 steps dt=0.25h. Charge 50kW at step0 (price 10), discharge 50kW at step2 (price 100).
    c = np.array([50.0, 0.0, 0.0, 0.0])
    d = np.array([0.0, 0.0, 50.0, 0.0])
    soc = np.array([32.0, 32.0, 20.0, 20.0])  # values irrelevant to economics
    sched = Schedule(c, d, soc, dt_h=0.25)
    prices = np.array([10.0, 10.0, 100.0, 100.0])
    batt = BatteryParams(degradation_eur_mwh=0.0)
    econ = EconParams(bkv_fee_pct=0.0, grid_fee_on_charge_eur_mwh=0.0)
    day = compute_day(sched, prices, econ, batt)
    # discharged 50kW*0.25h = 12.5 kWh = 0.0125 MWh; charged the same
    assert abs(day.mwh_discharged - 0.0125) < 1e-9
    assert abs(day.mwh_charged - 0.0125) < 1e-9
    # gross = 100*0.0125 - 10*0.0125 = 1.25 - 0.125 = 1.125 EUR
    assert abs(day.gross_eur - 1.125) < 1e-9


def test_compute_day_applies_bkv_and_grid_fee():
    c = np.array([50.0, 0.0])
    d = np.array([0.0, 50.0])
    sched = Schedule(c, d, np.array([32.0, 20.0]), dt_h=0.25)
    prices = np.array([10.0, 100.0])
    batt = BatteryParams()
    econ = EconParams(bkv_fee_pct=0.10, grid_fee_on_charge_eur_mwh=20.0)
    day = compute_day(sched, prices, econ, batt)
    assert abs(day.bkv_fee_eur - 0.10 * day.gross_eur) < 1e-9
    assert abs(day.grid_fee_eur - 20.0 * day.mwh_charged) < 1e-9


def test_negative_price_revenue_tracked():
    c = np.array([50.0, 0.0])
    d = np.array([0.0, 50.0])
    sched = Schedule(c, d, np.array([32.0, 20.0]), dt_h=0.25)
    prices = np.array([-30.0, 100.0])   # paid to charge in step 0
    day = compute_day(sched, prices, EconParams(), BatteryParams())
    # step 0 revenue = -30 * (-0.0125 MWh) = +0.375 EUR comes from a negative-price hour
    assert abs(day.neg_price_gross_eur - 0.375) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_economics.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.economics'`.

- [ ] **Step 3: Write `src/economics.py`**

```python
# src/economics.py
from dataclasses import dataclass

import numpy as np

from src.params import BatteryParams, EconParams
from src.types import Schedule


@dataclass
class DayPnL:
    gross_eur: float          # AC arbitrage revenue at capture=1.0 (pre-fee)
    bkv_fee_eur: float
    grid_fee_eur: float
    degradation_eur: float
    mwh_discharged: float
    mwh_charged: float
    neg_price_gross_eur: float


def compute_day(sched: Schedule, prices_eur_mwh, econ: EconParams,
                batt: BatteryParams) -> DayPnL:
    """Per-day P&L primitives from a dispatch Schedule. capture_pct and annual lines
    (FCR, OpEx, lease, CapEx) are applied later in metrics — this stays per-day and cheap."""
    prices = np.asarray(prices_eur_mwh, dtype=float)
    dt = sched.dt_h
    mwh_dis = float(sched.discharge_kw.sum() * dt / 1000.0)
    mwh_chg = float(sched.charge_kw.sum() * dt / 1000.0)

    step_rev = (prices / 1000.0) * (sched.discharge_kw - sched.charge_kw) * dt
    gross = float(step_rev.sum())
    neg = float(step_rev[prices < 0].sum())

    bkv = max(gross, 0.0) * econ.bkv_fee_pct
    grid_fee = mwh_chg * econ.grid_fee_on_charge_eur_mwh
    degr = (mwh_dis + mwh_chg) * batt.degradation_eur_mwh
    return DayPnL(gross, bkv, grid_fee, degr, mwh_dis, mwh_chg, neg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_economics.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/economics.py tests/test_economics.py
git commit -m "feat: per-day economics primitives"
```

---

### Task 8: Backtest orchestration (`src/backtest.py`)

**Files:**
- Create: `src/backtest.py`
- Test: `tests/test_backtest.py`

The backtest computes **dispatch-level aggregates only** (independent of capture %, fees,
CapEx) so the economics sliders stay instant downstream.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backtest.py
import numpy as np
import pandas as pd
from src.params import BatteryParams, EconParams
from src.backtest import run_backtest


def _two_day_prices():
    # day 1: cheap morning, dear evening; day 2: same shape
    rows = []
    for day in ["2024-01-01", "2024-01-02"]:
        for hour, price in zip(range(4), [10.0, 10.0, 100.0, 100.0]):
            rows.append({"ts": pd.Timestamp(f"{day} 0{hour}:00", tz="UTC"),
                         "price_eur_mwh": price})
    return pd.DataFrame(rows)


def test_run_backtest_aggregates_days():
    prices = _two_day_prices()
    batt = BatteryParams(eta_rt=1.0, cycles_cap=10.0)
    res = run_backtest(prices, batt, EconParams(), strategy="lp")
    assert res.n_days == 2
    assert res.total_mwh_discharged > 0
    assert res.total_gross_eur > 0
    assert len(res.daily) == 2
    assert res.sample_week is not None       # a Schedule stored for the animation


def test_run_backtest_threshold_strategy_runs():
    prices = _two_day_prices()
    batt = BatteryParams(eta_rt=1.0, cycles_cap=10.0)
    res = run_backtest(prices, batt, EconParams(), strategy="threshold",
                       buy_eur=50.0, sell_eur=80.0)
    assert res.total_gross_eur > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backtest.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.backtest'`.

- [ ] **Step 3: Write `src/backtest.py`**

```python
# src/backtest.py
from dataclasses import dataclass

import pandas as pd

from src.data_load import infer_dt_h
from src.dispatch import dispatch_lp, dispatch_threshold
from src.economics import compute_day, DayPnL
from src.params import BatteryParams, EconParams
from src.types import Schedule


@dataclass
class BacktestResult:
    n_days: int
    total_gross_eur: float
    total_mwh_discharged: float
    total_mwh_charged: float
    total_neg_price_gross_eur: float
    daily: pd.DataFrame              # columns: date, gross_eur, mwh_discharged, neg_price_gross_eur
    sample_week: Schedule | None     # one representative stretch for the animation
    sample_prices: list              # prices aligned to sample_week (for plotting)


def run_backtest(prices_df: pd.DataFrame, batt: BatteryParams, econ: EconParams,
                 strategy: str = "lp", buy_eur: float = 50.0,
                 sell_eur: float = 100.0) -> BacktestResult:
    rows = []
    sample_week = None
    sample_prices = []
    day_count = 0

    for date, day in prices_df.groupby(prices_df["ts"].dt.date):
        pv = day["price_eur_mwh"].to_numpy(dtype=float)
        dt_h = infer_dt_h(day)
        if strategy == "lp":
            sched = dispatch_lp(pv, batt, dt_h=dt_h)
        else:
            sched = dispatch_threshold(pv, batt, buy_eur=buy_eur, sell_eur=sell_eur, dt_h=dt_h)
        pnl: DayPnL = compute_day(sched, pv, econ, batt)
        rows.append({"date": date, "gross_eur": pnl.gross_eur,
                     "mwh_discharged": pnl.mwh_discharged,
                     "mwh_charged": pnl.mwh_charged,
                     "neg_price_gross_eur": pnl.neg_price_gross_eur})
        if day_count < 7:   # keep first 7 days as the animation sample
            if sample_week is None:
                sample_week = sched
                sample_prices = list(pv)
        day_count += 1

    daily = pd.DataFrame(rows)
    return BacktestResult(
        n_days=len(daily),
        total_gross_eur=float(daily["gross_eur"].sum()),
        total_mwh_discharged=float(daily["mwh_discharged"].sum()),
        total_mwh_charged=float(daily["mwh_charged"].sum()),
        total_neg_price_gross_eur=float(daily["neg_price_gross_eur"].sum()),
        daily=daily,
        sample_week=sample_week,
        sample_prices=sample_prices,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backtest.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/backtest.py tests/test_backtest.py
git commit -m "feat: day-by-day backtest orchestration"
```

---

### Task 9: Metrics + the honesty layer (`src/metrics.py`)

**Files:**
- Create: `src/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py
import math
import pandas as pd
from src.params import BatteryParams, EconParams
from src.backtest import BacktestResult
from src.metrics import compute_metrics


def _fake_result():
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]).date,
        "gross_eur": [100.0],
        "mwh_discharged": [1.0],
        "mwh_charged": [1.1],
        "neg_price_gross_eur": [10.0],
    })
    return BacktestResult(
        n_days=1, total_gross_eur=100.0, total_mwh_discharged=1.0,
        total_mwh_charged=1.1, total_neg_price_gross_eur=10.0,
        daily=daily, sample_week=None, sample_prices=[],
    )


def test_implied_spread_and_cycles():
    res = _fake_result()
    batt = BatteryParams()  # E_usable = 180 kWh
    econ = EconParams(capture_pct=1.0, bkv_fee_pct=0.0)
    m = compute_metrics(res, econ, batt)
    # implied spread = gross / MWh discharged = 100 / 1.0 = 100 EUR/MWh
    assert abs(m.implied_spread_eur_mwh - 100.0) < 1e-6
    # implied cycles/day = 1.0 MWh * 1000 / (180 kWh * 1 day) = 5.555.. cycles
    assert abs(m.implied_cycles_day - (1000.0 / 180.0)) < 1e-6
    # negative-price share = 10 / 100 = 10%
    assert abs(m.neg_price_share - 0.10) < 1e-6


def test_capture_pct_scales_gross():
    res = _fake_result()
    m = compute_metrics(res, EconParams(capture_pct=0.5, bkv_fee_pct=0.0), BatteryParams())
    assert abs(m.implied_spread_eur_mwh - 50.0) < 1e-6   # 0.5 * 100


def test_payback_and_irr_signs():
    res = _fake_result()
    econ = EconParams(capex_eur=1000.0, capture_pct=1.0, asset_life_yr=15)
    m = compute_metrics(res, econ, BatteryParams())
    assert m.year1_ebitda_eur != 0
    if m.year1_ebitda_eur > 0:
        assert m.payback_years > 0
        assert math.isfinite(m.irr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.metrics'`.

- [ ] **Step 3: Write `src/metrics.py`**

```python
# src/metrics.py
from dataclasses import dataclass

import numpy_financial as npf

from src.backtest import BacktestResult
from src.params import BatteryParams, EconParams


@dataclass
class Metrics:
    implied_spread_eur_mwh: float
    implied_cycles_day: float
    year1_gross_eur: float
    year1_ebitda_eur: float
    payback_years: float
    irr: float
    neg_price_share: float


def compute_metrics(res: BacktestResult, econ: EconParams, batt: BatteryParams) -> Metrics:
    """Annualise the dispatch backtest into headline metrics. Cheap: re-run on every
    economics-slider change. capture_pct haircuts the (perfect-foresight) gross."""
    days = max(res.n_days, 1)
    scale = 365.0 / days

    captured_gross = res.total_gross_eur * econ.capture_pct
    mwh_dis = res.total_mwh_discharged

    implied_spread = (captured_gross / mwh_dis) if mwh_dis > 0 else 0.0
    implied_cycles = (mwh_dis * 1000.0) / (batt.e_usable_kwh * days) if days else 0.0
    neg_share = (res.total_neg_price_gross_eur / res.total_gross_eur
                 if res.total_gross_eur else 0.0)

    gross_yr = captured_gross * scale
    bkv_yr = max(gross_yr, 0.0) * econ.bkv_fee_pct
    grid_fee_yr = res.total_mwh_charged * scale * econ.grid_fee_on_charge_eur_mwh
    degr_yr = (mwh_dis + res.total_mwh_charged) * scale * batt.degradation_eur_mwh

    revenue_yr = gross_yr + econ.fcr_afrr_eur_yr
    ebitda = (revenue_yr - bkv_yr - grid_fee_yr - degr_yr
              - econ.opex_eur_yr - econ.owner_lease_eur_yr)

    payback = (econ.capex_eur / ebitda) if ebitda > 0 else float("inf")
    cashflows = [-econ.capex_eur] + [ebitda] * econ.asset_life_yr
    try:
        irr = float(npf.irr(cashflows))
    except Exception:
        irr = float("nan")

    return Metrics(implied_spread, implied_cycles, gross_yr, ebitda, payback, irr, neg_share)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/metrics.py tests/test_metrics.py
git commit -m "feat: metrics incl. implied spread/cycles, payback, IRR"
```

---

### Task 10: End-to-end integration test (`tests/test_integration.py`)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_integration.py`

Uses a synthetic full-year price series (no network) to exercise the whole pipeline and
assert plausibility bands.

- [ ] **Step 1: Write `tests/conftest.py` (synthetic year fixture)**

```python
# tests/conftest.py
import math
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_year():
    """One year of hourly DE-LU-like prices: daily sinusoid (trough ~night, peak ~evening)
    with mean ~80 EUR/MWh and ~±60 swing, deterministic (no RNG)."""
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz="UTC")
    hours = idx.hour.to_numpy()
    price = 80.0 + 60.0 * np.sin((hours - 4) / 24.0 * 2 * math.pi)  # min ~04:00, max ~16:00
    return pd.DataFrame({"ts": idx, "price_eur_mwh": price})
```

- [ ] **Step 2: Write the failing integration test**

```python
# tests/test_integration.py
from src.params import BatteryParams, EconParams
from src.backtest import run_backtest
from src.metrics import compute_metrics


def test_full_pipeline_plausible(synthetic_year):
    batt = BatteryParams(cycles_cap=1.5)
    econ = EconParams(capture_pct=1.0, capex_eur=140_000.0)
    res = run_backtest(synthetic_year, batt, econ, strategy="lp")
    m = compute_metrics(res, econ, batt)

    assert res.n_days >= 360
    # implied spread must be positive and below the full daily swing (~120 EUR/MWh)
    assert 0 < m.implied_spread_eur_mwh < 120
    # cycles/day capped at 1.5 by construction
    assert m.implied_cycles_day <= 1.5 + 1e-6
    # IRR should be a finite number for a profitable run
    assert m.year1_gross_eur > 0


def test_threshold_underperforms_lp(synthetic_year):
    batt = BatteryParams(cycles_cap=1.5)
    econ = EconParams(capture_pct=1.0)
    lp = compute_metrics(run_backtest(synthetic_year, batt, econ, "lp"), econ, batt)
    th = compute_metrics(
        run_backtest(synthetic_year, batt, econ, "threshold", buy_eur=40, sell_eur=120),
        econ, batt)
    # the optimiser should capture at least as much spread as a fixed rule
    assert lp.year1_gross_eur >= th.year1_gross_eur - 1e-6
```

- [ ] **Step 3: Run test to verify it fails, then passes**

Run: `pytest tests/test_integration.py -q`
Expected: initially this should already pass if Tasks 1-9 are complete (no new src). If it
fails, fix the offending module. This task's value is the **plausibility gate**.

- [ ] **Step 4: Run the full suite**

Run: `pytest -q`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_integration.py
git commit -m "test: end-to-end plausibility integration tests"
```

---

### Task 11: Streamlit dashboard (`app/streamlit_app.py`)

**Files:**
- Create: `app/streamlit_app.py`
- Create: `app/charts.py`

UI is verified manually (Step 5). The expensive backtest is cached on
`(battery params, strategy, date range)`; econ sliders recompute metrics only.

- [ ] **Step 1: Write `app/charts.py` (Plotly builders — pure functions)**

```python
# app/charts.py
import numpy as np
import plotly.graph_objects as go


def dispatch_figure(prices, sched):
    """Price line with charge (green) / discharge (red) bars and a SoC trace."""
    t = list(range(len(prices)))
    charge = np.asarray(sched.charge_kw)
    discharge = np.asarray(sched.discharge_kw)
    fig = go.Figure()
    fig.add_bar(x=t, y=charge, name="Charge (kW)", marker_color="seagreen", opacity=0.6)
    fig.add_bar(x=t, y=-discharge, name="Discharge (kW)", marker_color="crimson", opacity=0.6)
    fig.add_scatter(x=t, y=prices, name="Price (€/MWh)", yaxis="y2",
                    line=dict(color="#333", width=2))
    fig.add_scatter(x=t, y=sched.soc_kwh, name="SoC (kWh)", yaxis="y3",
                    line=dict(color="royalblue", width=1, dash="dot"))
    fig.update_layout(
        barmode="relative", height=420, legend_orientation="h",
        yaxis=dict(title="Power (kW)"),
        yaxis2=dict(title="€/MWh", overlaying="y", side="right"),
        yaxis3=dict(overlaying="y", side="right", position=0.97, showgrid=False,
                    showticklabels=False),
        margin=dict(l=40, r=40, t=20, b=20),
    )
    return fig


def cumulative_pnl_figure(daily):
    cum = daily["gross_eur"].cumsum()
    fig = go.Figure(go.Scatter(x=list(daily["date"]), y=cum, fill="tozeroy",
                               line=dict(color="seagreen")))
    fig.update_layout(height=260, title="Cumulative gross trading revenue (€)",
                      margin=dict(l=40, r=20, t=40, b=20))
    return fig
```

- [ ] **Step 2: Write `app/streamlit_app.py`**

```python
# app/streamlit_app.py
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on path

from src.data_load import load_prices
from src.params import BatteryParams, EconParams, get_preset
from src.backtest import run_backtest
from src.metrics import compute_metrics
from app.charts import dispatch_figure, cumulative_pnl_figure

DATA_PATH = "data/prices_de_lu.parquet"

st.set_page_config(page_title="KellerWatt Arbitrage Simulation", layout="wide")
preset = get_preset(os.environ.get("KW_PRESET", "baseline"))

st.title("KellerWatt — Basement Battery Arbitrage Simulation")
st.caption("Backtested on real German (DE-LU) day-ahead prices · Energy-Charts.info (CC BY 4.0)")


@st.cache_data(show_spinner="Running LP dispatch over real prices…")
def _dispatch(strategy, cycles_cap, start, end, buy, sell):
    prices = load_prices(DATA_PATH, start=start, end=end)
    batt = BatteryParams(cycles_cap=cycles_cap)
    res = run_backtest(prices, batt, EconParams(), strategy=strategy,
                       buy_eur=buy, sell_eur=sell)
    return res, batt


with st.sidebar:
    st.header("Dispatch")
    strategy = st.radio("Strategy", ["lp", "threshold"],
                        format_func=lambda s: "Perfect-foresight LP" if s == "lp"
                        else "Threshold rule")
    cycles_cap = st.slider("Cycles/day cap", 0.5, 2.5, preset.battery.cycles_cap, 0.1)
    buy = st.slider("Threshold: buy below (€/MWh)", -50, 150, 50)
    sell = st.slider("Threshold: sell above (€/MWh)", 0, 400, 100)
    year = st.selectbox("Year", ["2024", "2025", "all"], index=0)

    st.header("Economics (instant)")
    capture = st.slider("Capture % (live vs perfect foresight)", 0.5, 1.0,
                        preset.econ.capture_pct, 0.01)
    bkv = st.slider("BKV / aggregator fee %", 0.0, 0.30, preset.econ.bkv_fee_pct, 0.01)
    capex = st.slider("CapEx (€)", 80_000, 250_000, int(preset.econ.capex_eur), 5_000)
    grid_fee = st.slider("Grid fee on charged energy (€/MWh) — downside", 0, 80, 0)

start = None if year == "all" else f"{year}-01-01"
end = None if year == "all" else f"{year}-12-31"

if not Path(DATA_PATH).exists():
    st.error("No price data found. Run: python -m src.fetch_prices --start 2024-01-01")
    st.stop()

res, batt = _dispatch(strategy, cycles_cap, start, end, buy, sell)
econ = EconParams(capex_eur=capex, bkv_fee_pct=bkv, grid_fee_on_charge_eur_mwh=grid_fee,
                  capture_pct=capture, fcr_afrr_eur_yr=preset.econ.fcr_afrr_eur_yr,
                  opex_eur_yr=preset.econ.opex_eur_yr,
                  owner_lease_eur_yr=preset.econ.owner_lease_eur_yr)
m = compute_metrics(res, econ, batt)
a = preset.assumed

# --- honesty panel ---
st.subheader("Spreadsheet assumed  vs  Simulation produced")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Spreadsheet assumed**")
    st.metric("Captured spread", f"€{a.spread_eur_mwh:.0f}/MWh")
    st.metric("Cycles/day", f"{a.cycles_day:.2f}")
    st.metric("Year-1 gross", f"€{a.gross_eur:,.0f}")
    st.metric("Unlevered IRR", f"{a.irr*100:.1f}%")
with c2:
    st.markdown("**Simulation produced**")
    st.metric("Captured spread", f"€{m.implied_spread_eur_mwh:.0f}/MWh",
              delta=f"{m.implied_spread_eur_mwh - a.spread_eur_mwh:+.0f}")
    st.metric("Cycles/day", f"{m.implied_cycles_day:.2f}",
              delta=f"{m.implied_cycles_day - a.cycles_day:+.2f}")
    st.metric("Year-1 gross", f"€{m.year1_gross_eur:,.0f}")
    st.metric("Unlevered IRR", f"{m.irr*100:.1f}%" if m.irr == m.irr else "n/a")
with c3:
    st.markdown("**Conservative (capture 85%, grid-fee on)**")
    cons_econ = EconParams(capex_eur=capex, bkv_fee_pct=bkv,
                           grid_fee_on_charge_eur_mwh=max(grid_fee, 40),
                           capture_pct=0.85, opex_eur_yr=econ.opex_eur_yr,
                           owner_lease_eur_yr=econ.owner_lease_eur_yr)
    mc = compute_metrics(res, cons_econ, batt)
    st.metric("Captured spread", f"€{mc.implied_spread_eur_mwh:.0f}/MWh")
    st.metric("Year-1 gross", f"€{mc.year1_gross_eur:,.0f}")
    st.metric("Unlevered IRR", f"{mc.irr*100:.1f}%" if mc.irr == mc.irr else "n/a")
    st.caption("Modo anchor: ~13.7% IRR (4h German BESS, utility-scale — directional only)")

st.info(f"€{res.total_neg_price_gross_eur*econ.capture_pct:,.0f} of gross "
        f"({m.neg_price_share*100:.0f}%) comes from negative-price hours.")

# --- demo charts ---
st.subheader("Representative week — charge low, discharge high")
if res.sample_week is not None:
    st.plotly_chart(dispatch_figure(res.sample_prices, res.sample_week),
                    use_container_width=True)
st.plotly_chart(cumulative_pnl_figure(res.daily), use_container_width=True)
```

- [ ] **Step 3: Add a smoke test (`tests/test_app_imports.py`)**

```python
# tests/test_app_imports.py
import importlib


def test_charts_module_imports():
    mod = importlib.import_module("app.charts")
    assert hasattr(mod, "dispatch_figure")
    assert hasattr(mod, "cumulative_pnl_figure")
```

- [ ] **Step 4: Run the smoke test**

Run: `pytest tests/test_app_imports.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Manual verification (the real check for UI)**

Run: `streamlit run app/streamlit_app.py`
Expected: dashboard loads; the three-column honesty panel shows simulation numbers next to
the assumed €80/1.5; moving the **capture/BKV/CapEx/grid-fee** sliders updates metrics
instantly; changing **cycles/day or strategy** re-runs dispatch (brief spinner); the
representative-week chart shows green charging at troughs and red discharging at peaks.
Requires `data/prices_de_lu.parquet` (Task 4 Step 5).

- [ ] **Step 6: Commit**

```bash
git add app/streamlit_app.py app/charts.py tests/test_app_imports.py
git commit -m "feat: Streamlit dashboard with honesty panel and demo charts"
```

---

### Task 12: Sanitized public deployment

**Files:**
- Create: `.streamlit/config.toml`
- Modify: `README.md` (deploy section)

- [ ] **Step 1: Write `.streamlit/config.toml`**

```toml
[theme]
primaryColor = "#2e8b57"
base = "light"

[server]
headless = true
```

- [ ] **Step 2: Add a deploy section to `README.md`**

```markdown
## Deployment

Two builds from one codebase, selected by the `KW_PRESET` env var:

- **Local (real numbers, for the live pitch):** `streamlit run app/streamlit_app.py`
  (uses `BASELINE` in `src/params.py` — never commit real figures to a public remote).
- **Public (sanitized):** deploy this repo to Streamlit Community Cloud with
  `KW_PRESET=sanitized` set in the app's *Advanced settings → Secrets/Env*. This uses the
  `SANITIZED` placeholder preset, so the real economics are never exposed.

Data: commit `data/prices_de_lu.parquet` (public day-ahead prices, CC BY 4.0) so the
deployed app has data without a network call.
```

- [ ] **Step 3: Verify both presets load**

Run: `python -c "from src.params import get_preset; print(get_preset('baseline').name, get_preset('sanitized').name)"`
Expected: `baseline sanitized`

- [ ] **Step 4: Commit**

```bash
git add .streamlit/config.toml README.md
git commit -m "chore: sanitized public deployment config"
```

---

## Verification (end-to-end)

1. `pip install -r requirements.txt`
2. `pytest -q` → all tests pass (params, data_load, fetch parser, threshold, LP, economics, backtest, metrics, integration, app imports).
3. `python -m src.fetch_prices --start 2024-01-01 --out data/prices_de_lu.parquet` → writes the Parquet (needs network; one-time).
4. `streamlit run app/streamlit_app.py` → dashboard loads; honesty panel shows simulation vs assumed €80/1.5; econ sliders are instant, dispatch sliders re-run with a spinner; representative-week chart shows green-low/red-high.
5. **Pitch reality gate:** read the simulation's implied spread for 2024. If it lands below ~€60/MWh, revise the BASELINE assumed figures down in `src/params.py` *before* the pitch.

## Self-review notes (done)

- **Spec coverage:** data layer (T3/T4), LP + threshold dispatch (T5/T6), economics incl. BKV/grid-fee/degradation (T7), implied spread & cycles + IRR/payback + negative-price share (T9), honesty panel + sliders + animated charts + Modo anchor (T11), sanitized/public split (T2/T12), testing (T2-T10). FCR/aFRR is a parameterised capped line (`fcr_afrr_eur_yr`) per the partition rule — not co-optimised (v2).
- **Type consistency:** `Schedule` (charge_kw/discharge_kw/soc_kwh/dt_h) is produced by both dispatchers and consumed by `compute_day`; `DayPnL` → `BacktestResult.daily` columns → `compute_metrics`; `Preset`/`AssumedBaseline` field names match their use in `streamlit_app.py`.
- **Deviation from spec:** native resolution + per-day `dt_h` (no upsampling); documented in the header.
