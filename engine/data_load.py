"""Real DE-LU day-ahead price loading with FAIL-LOUD calendar validation.

Reuses the validated spike's grouping (Europe/Berlin delivery days, DST 23/25-h
handled, AC-side prices) but, unlike the spike, NEVER silently skips an incomplete
day (Codex 15). Any missing day, duplicate timestamp, short/long day, or wrong
resolution raises DataValidationError.

To make every Berlin delivery day complete we *buffer* the UTC fetch by one day
each side, then select exactly the Berlin dates in [Jan 1 .. Dec 31]. Resolution
is validated per day against the known 2025-10-01 hourly->15-min go-live.
"""
from __future__ import annotations

import json
import statistics
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
UTC = timezone.utc

PRICE_ZONE = "DE-LU"
DATA_SOURCE = "Energy-Charts"
SOURCE_URL = "https://api.energy-charts.info/price"
# DE-LU day-ahead moved to 15-minute MTUs at this delivery day.
FIFTEEN_MIN_GO_LIVE = date(2025, 10, 1)
CACHE_DIR = Path(__file__).resolve().parent / "data" / "cache"

_SPACING_TOL_H = 1e-6


class DataValidationError(Exception):
    """Raised on any unexplained gap, duplicate, short/long day, or bad resolution."""


@dataclass(frozen=True)
class DayPrices:
    day: date
    dt_h: float
    prices: tuple[float, ...]

    @property
    def n_points(self) -> int:
        return len(self.prices)

    @property
    def points_per_hour(self) -> int:
        return int(round(1.0 / self.dt_h))

    @property
    def hours(self) -> int:
        return berlin_hours_in_day(self.day)


@dataclass(frozen=True)
class YearData:
    year: int
    days: tuple[DayPrices, ...]
    nulls_dropped: int
    points_per_day_histogram: dict
    price_min: float
    price_max: float
    negative_intervals: int
    resolution_transition: date | None

    @property
    def day_count(self) -> int:
        return len(self.days)


# ---- calendar primitives ----------------------------------------------------

def berlin_hours_in_day(d: date) -> int:
    """Wall-clock hours in a Berlin local day: 24 normally, 23 spring-forward,
    25 fall-back."""
    start = datetime(d.year, d.month, d.day, tzinfo=BERLIN)
    nxt = d + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=BERLIN)
    seconds = (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds()
    return int(round(seconds / 3600.0))


def expected_points_per_hour(d: date) -> int:
    """1 (hourly) before the 15-min go-live, 4 (quarter-hour) on/after it."""
    return 4 if d >= FIFTEEN_MIN_GO_LIVE else 1


def expected_points(d: date) -> int:
    return berlin_hours_in_day(d) * expected_points_per_hour(d)


def _infer_dt_h(times: list[datetime]) -> float:
    diffs = [
        (times[i + 1] - times[i]).total_seconds() / 3600.0
        for i in range(len(times) - 1)
    ]
    return statistics.median(diffs)


# ---- validation -------------------------------------------------------------

def validate_day(d: date, pts: list[tuple[datetime, float]]) -> DayPrices:
    """Validate one Berlin delivery day; raise DataValidationError on any defect.

    `pts` is a list of (aware-instant, price). The instant may be in any tz; only
    the absolute ordering/spacing matters here.
    """
    pts = sorted(pts, key=lambda x: x[0])
    times = [t for t, _ in pts]

    if len(set(times)) != len(times):
        raise DataValidationError(f"{d}: duplicate timestamps in delivery day")

    pph = expected_points_per_hour(d)
    exp = berlin_hours_in_day(d) * pph
    if len(pts) != exp:
        raise DataValidationError(
            f"{d}: {len(pts)} points, expected {exp} "
            f"({berlin_hours_in_day(d)}h x {pph}/h; 15-min go-live {FIFTEEN_MIN_GO_LIVE})"
        )

    dt_h = _infer_dt_h(times)
    if abs(dt_h - 1.0 / pph) > _SPACING_TOL_H:
        raise DataValidationError(
            f"{d}: median spacing {dt_h:.4f}h, expected {1.0 / pph:.4f}h"
        )
    for i in range(len(times) - 1):
        gap = (times[i + 1] - times[i]).total_seconds() / 3600.0
        if abs(gap - dt_h) > _SPACING_TOL_H:
            raise DataValidationError(
                f"{d}: irregular spacing {gap:.4f}h at index {i} (expected {dt_h:.4f}h)"
            )

    return DayPrices(d, dt_h, tuple(p for _, p in pts))


def build_year(year: int, rows: list[tuple[datetime, float]], nulls_dropped: int) -> YearData:
    """Group rows by Berlin day, validate every day in the inclusive Berlin year,
    and return a YearData. Fail loud on any missing/extra/defective day."""
    by_day: dict[date, list] = defaultdict(list)
    for utc_dt, price in rows:
        local = utc_dt.astimezone(BERLIN)
        by_day[local.date()].append((utc_dt, price))

    first, last = date(year, 1, 1), date(year, 12, 31)
    wanted = [first + timedelta(days=i) for i in range((last - first).days + 1)]

    days: list[DayPrices] = []
    transition: date | None = None
    prev_pph: int | None = None
    for d in wanted:
        if d not in by_day:
            raise DataValidationError(f"{year}: missing Berlin delivery day {d}")
        day = validate_day(d, by_day[d])
        if prev_pph is not None and day.points_per_hour != prev_pph:
            transition = d
        prev_pph = day.points_per_hour
        days.append(day)

    # Resolution transition must match the known go-live exactly (fail loud).
    spans_go_live = first <= FIFTEEN_MIN_GO_LIVE <= last
    if spans_go_live:
        if transition != FIFTEEN_MIN_GO_LIVE:
            raise DataValidationError(
                f"{year}: resolution transition at {transition}, "
                f"expected {FIFTEEN_MIN_GO_LIVE}"
            )
    elif transition is not None:
        raise DataValidationError(
            f"{year}: unexpected resolution change at {transition}"
        )

    histogram: dict[int, int] = defaultdict(int)
    all_prices: list[float] = []
    neg = 0
    for day in days:
        histogram[day.n_points] += 1
        for p in day.prices:
            all_prices.append(p)
            if p < 0:
                neg += 1

    return YearData(
        year=year,
        days=tuple(days),
        nulls_dropped=nulls_dropped,
        points_per_day_histogram=dict(sorted(histogram.items())),
        price_min=min(all_prices),
        price_max=max(all_prices),
        negative_intervals=neg,
        resolution_transition=transition,
    )


# ---- fetch + cache ----------------------------------------------------------

def _fetch_window(year: int) -> tuple[str, str]:
    # Buffer one day each side so Berlin Jan 1 / Dec 31 are complete.
    return f"{year - 1}-12-31", f"{year + 1}-01-01"


def fetch_payload(year: int, timeout: int = 180) -> dict:
    start, end = _fetch_window(year)
    url = f"{SOURCE_URL}?bzn={PRICE_ZONE}&start={start}&end={end}"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        payload = json.load(r)
    payload["_fetch_window"] = [start, end]
    return payload


def parse_payload(payload: dict) -> tuple[list[tuple[datetime, float]], int]:
    rows, dropped = [], 0
    for s, p in zip(payload["unix_seconds"], payload["price"]):
        if p is None:
            dropped += 1
            continue
        rows.append((datetime.fromtimestamp(s, tz=UTC), float(p)))
    rows.sort(key=lambda x: x[0])
    return rows, dropped


def _cache_path(year: int) -> Path:
    return CACHE_DIR / f"price_{PRICE_ZONE}_{year}.json"


def load_year(year: int, *, use_cache: bool = True, allow_fetch: bool = True) -> YearData:
    """Load + validate one year. Reads a local cache if present, otherwise fetches
    from Energy-Charts and caches the raw payload."""
    path = _cache_path(year)
    payload = None
    if use_cache and path.is_file():
        payload = json.loads(path.read_text())
    elif allow_fetch:
        payload = fetch_payload(year)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    else:
        raise DataValidationError(
            f"{year}: no cache at {path} and fetching disabled"
        )
    rows, dropped = parse_payload(payload)
    return build_year(year, rows, dropped)
