"""Create monthly county foster-home capacity-pressure snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

from scripts.etl.aggregate_counties import CountyAggregate
from scripts.etl.config import (
    REPORTING_CUTOFF_DATE,
    TREND_SNAPSHOT_COUNT,
    TREND_START_DATE,
)
from scripts.etl.load_sources import SourceData


@dataclass(frozen=True, slots=True)
class CountyMonthlyTrend:
    """One county-level historical snapshot."""

    county_slug: str
    snapshot_date: date
    children_currently_in_care: int
    current_foster_homes: int
    children_per_current_home: float | None


def next_month_start(value: date) -> date:
    """Return the first day of the next month."""

    if value.month == 12:
        return date(value.year + 1, 1, 1)

    return date(value.year, value.month + 1, 1)


def build_trend_snapshot_dates() -> tuple[date, ...]:
    """Return all monthly snapshot dates in the trend window."""

    snapshot_dates: list[date] = []
    current_date = TREND_START_DATE

    while current_date <= REPORTING_CUTOFF_DATE:
        snapshot_dates.append(current_date)
        current_date = next_month_start(current_date)

    result = tuple(snapshot_dates)

    if len(result) != TREND_SNAPSHOT_COUNT:
        raise ValueError(
            "Historical trend snapshot count is invalid. "
            f"Expected {TREND_SNAPSHOT_COUNT}; found {len(result)}."
        )

    if result[-1] != REPORTING_CUTOFF_DATE:
        raise ValueError(
            "The final historical trend snapshot must equal the reporting cutoff."
        )

    return result


def child_is_in_care_on_snapshot(
    *,
    removal_date: date,
    discharge_date: date | None,
    snapshot_date: date,
) -> bool:
    """Return whether a child is in care on a historical snapshot."""

    if removal_date > snapshot_date:
        return False

    # The locked current-child definition treats a null
    # discharge date as currently in care at the reporting cutoff.
    if snapshot_date == REPORTING_CUTOFF_DATE:
        return discharge_date is None

    return discharge_date is None or discharge_date > snapshot_date


def derive_county_monthly_trends(
    data: SourceData,
    counties: tuple[CountyAggregate, ...],
) -> tuple[CountyMonthlyTrend, ...]:
    """Build a complete county-by-month trend grid."""

    snapshot_dates = build_trend_snapshot_dates()
    results: list[CountyMonthlyTrend] = []

    for snapshot_date in snapshot_dates:
        children_by_county: Counter[str] = Counter(
            child.removal_county
            for child in data.children
            if child_is_in_care_on_snapshot(
                removal_date=child.removal_date,
                discharge_date=child.discharge_date,
                snapshot_date=snapshot_date,
            )
        )

        homes_by_county: Counter[str] = Counter(
            provider.county_provider
            for provider in data.providers
            if (
                provider.license_start_date
                <= snapshot_date
                <= provider.license_end_date
            )
        )

        for county in counties:
            child_count = children_by_county[county.county_name]
            home_count = homes_by_county[county.county_name]

            ratio = child_count / home_count if home_count > 0 else None

            results.append(
                CountyMonthlyTrend(
                    county_slug=county.county_slug,
                    snapshot_date=snapshot_date,
                    children_currently_in_care=child_count,
                    current_foster_homes=home_count,
                    children_per_current_home=ratio,
                )
            )

    result = tuple(results)

    validate_county_monthly_trends(
        trends=result,
        counties=counties,
        snapshot_dates=snapshot_dates,
    )

    return result


def validate_county_monthly_trends(
    *,
    trends: tuple[CountyMonthlyTrend, ...],
    counties: tuple[CountyAggregate, ...],
    snapshot_dates: tuple[date, ...],
) -> None:
    """Validate trend coverage and current-snapshot reconciliation."""

    expected_row_count = len(counties) * len(snapshot_dates)

    if len(trends) != expected_row_count:
        raise ValueError(
            "County monthly trend row count is invalid. "
            f"Expected {expected_row_count}; found {len(trends)}."
        )

    keys = {(trend.county_slug, trend.snapshot_date) for trend in trends}

    if len(keys) != len(trends):
        raise ValueError("County monthly trends contain duplicate county-date keys.")

    trends_by_county: defaultdict[
        str,
        list[CountyMonthlyTrend],
    ] = defaultdict(list)

    for trend in trends:
        trends_by_county[trend.county_slug].append(trend)

        if (
            trend.current_foster_homes == 0
            and trend.children_per_current_home is not None
        ):
            raise ValueError(
                "A county trend ratio must be null when the home denominator is zero."
            )

        if trend.current_foster_homes > 0 and trend.children_per_current_home is None:
            raise ValueError(
                "A county trend ratio cannot be null when the "
                "home denominator is positive."
            )

    expected_dates = set(snapshot_dates)

    for county in counties:
        county_trends = trends_by_county[county.county_slug]

        actual_dates = {trend.snapshot_date for trend in county_trends}

        if actual_dates != expected_dates:
            raise ValueError(
                f"County monthly trend dates are incomplete for {county.county_name}."
            )

        current_trend = next(
            trend
            for trend in county_trends
            if trend.snapshot_date == REPORTING_CUTOFF_DATE
        )

        if (
            current_trend.children_currently_in_care
            != county.children_currently_in_care
        ):
            raise ValueError(
                "Current trend child count does not reconcile for "
                f"{county.county_name}."
            )

        if current_trend.current_foster_homes != county.current_foster_homes:
            raise ValueError(
                f"Current trend home count does not reconcile for {county.county_name}."
            )

        expected_ratio = county.children_per_current_home
        actual_ratio = current_trend.children_per_current_home

        if expected_ratio is None or actual_ratio is None:
            if expected_ratio != actual_ratio:
                raise ValueError(
                    "Current trend ratio nullability does not "
                    f"reconcile for {county.county_name}."
                )
        elif abs(expected_ratio - actual_ratio) > 0.000000001:
            raise ValueError(
                f"Current trend ratio does not reconcile for {county.county_name}."
            )
