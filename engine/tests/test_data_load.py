"""A2 — data loading & fail-loud calendar validation (Codex 15).

The validated spike SILENTLY SKIPPED incomplete days. Production must instead
FAIL LOUD on any unexplained missing/duplicate/short day, while still correctly
allowing DST 23/25-hour days and the 2025-10-01 hourly->15-min transition.
Unit tests are synthetic (no network); a separate @network test hits the API.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from engine import data_load as dl

UTC = timezone.utc


# ---- calendar primitives ----------------------------------------------------

def test_berlin_hours_normal_day():
    assert dl.berlin_hours_in_day(date(2024, 6, 15)) == 24


def test_berlin_hours_spring_forward_is_23():
    # Last Sunday of March 2024.
    assert dl.berlin_hours_in_day(date(2024, 3, 31)) == 23


def test_berlin_hours_fall_back_is_25():
    # Last Sunday of October 2024.
    assert dl.berlin_hours_in_day(date(2024, 10, 27)) == 25


def test_expected_resolution_follows_15min_go_live():
    assert dl.expected_points_per_hour(date(2025, 9, 30)) == 1
    assert dl.expected_points_per_hour(date(2025, 10, 1)) == 4
    assert dl.expected_points_per_hour(date(2024, 7, 1)) == 1


# ---- single-day validation --------------------------------------------------

def _day_times(d, points_per_hour):
    """Aware UTC instants spanning Berlin local day `d` at the given resolution."""
    start = datetime(d.year, d.month, d.day, tzinfo=dl.BERLIN).astimezone(UTC)
    n = dl.berlin_hours_in_day(d) * points_per_hour
    step = timedelta(hours=1 / points_per_hour)
    return [start + i * step for i in range(n)]


def test_validate_day_accepts_complete_hourly_day():
    d = date(2024, 6, 15)
    pts = [(t, 50.0) for t in _day_times(d, 1)]
    day = dl.validate_day(d, pts)
    assert day.n_points == 24 and day.points_per_hour == 1


def test_validate_day_accepts_dst_short_day():
    d = date(2024, 3, 31)  # 23 hours
    pts = [(t, 50.0) for t in _day_times(d, 1)]
    assert dl.validate_day(d, pts).n_points == 23


def test_validate_day_accepts_15min_day_after_go_live():
    d = date(2025, 10, 2)
    pts = [(t, 50.0) for t in _day_times(d, 4)]
    day = dl.validate_day(d, pts)
    assert day.n_points == 96 and day.points_per_hour == 4


def test_validate_day_fails_loud_on_missing_point():
    d = date(2024, 6, 15)
    pts = [(t, 50.0) for t in _day_times(d, 1)][:-1]  # drop the last hour
    with pytest.raises(dl.DataValidationError):
        dl.validate_day(d, pts)


def test_validate_day_fails_loud_on_duplicate_timestamp():
    d = date(2024, 6, 15)
    pts = [(t, 50.0) for t in _day_times(d, 1)]
    pts[5] = pts[4]  # duplicate instant
    with pytest.raises(dl.DataValidationError):
        dl.validate_day(d, pts)


def test_validate_day_fails_loud_on_wrong_resolution():
    # An hourly day where 15-min was expected (post go-live).
    d = date(2025, 10, 2)
    pts = [(t, 50.0) for t in _day_times(d, 1)]
    with pytest.raises(dl.DataValidationError):
        dl.validate_day(d, pts)


# ---- full-year assembly -----------------------------------------------------

def _synth_hourly_year(year, price=50.0):
    """Complete synthetic UTC hourly series covering the buffered fetch window
    (prev Dec 31 .. next Jan 1), so every Berlin day of `year` is complete."""
    start = datetime(year - 1, 12, 31, tzinfo=UTC)
    end = datetime(year + 1, 1, 1, 23, tzinfo=UTC)
    rows, t = [], start
    while t <= end:
        rows.append((t, price))
        t += timedelta(hours=1)
    return rows


def test_build_year_happy_path_2024():
    yd = dl.build_year(2024, _synth_hourly_year(2024), nulls_dropped=0)
    assert yd.day_count == 366  # leap year
    assert yd.days[0].day == date(2024, 1, 1)
    assert yd.days[-1].day == date(2024, 12, 31)
    assert 23 in yd.points_per_day_histogram  # spring-forward day present
    assert 25 in yd.points_per_day_histogram  # fall-back day present
    assert yd.resolution_transition is None


def test_build_year_fails_loud_on_missing_day():
    rows = _synth_hourly_year(2024)
    drop = date(2024, 7, 1)
    rows = [(t, p) for (t, p) in rows if t.astimezone(dl.BERLIN).date() != drop]
    with pytest.raises(dl.DataValidationError, match="missing"):
        dl.build_year(2024, rows, nulls_dropped=0)


def test_build_year_reports_negative_intervals_and_range():
    rows = _synth_hourly_year(2024, price=50.0)
    # Make one Berlin day's hours negative.
    flip = date(2024, 5, 5)
    rows = [
        (t, -10.0 if t.astimezone(dl.BERLIN).date() == flip else p)
        for (t, p) in rows
    ]
    yd = dl.build_year(2024, rows, nulls_dropped=0)
    assert yd.negative_intervals == 24
    assert yd.price_min == -10.0 and yd.price_max == 50.0
