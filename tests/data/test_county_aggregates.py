"""Tests for county recruitment and engagement aggregates."""

from __future__ import annotations

import pytest

from scripts.etl.aggregate_counties import (
    derive_county_aggregates,
)
from scripts.etl.load_sources import load_sources


@pytest.fixture(scope="module")
def county_rows():
    """Calculate county aggregates once for this test module."""

    return derive_county_aggregates(load_sources())


def test_county_labels_and_slugs_are_unique(
    county_rows,
) -> None:
    """Every county row must have unique names and URL slugs."""

    county_names = {row.county_name for row in county_rows}

    county_slugs = {row.county_slug for row in county_rows}

    assert len(county_names) == len(county_rows)
    assert len(county_slugs) == len(county_rows)

    # The known source spelling variant is canonicalized
    # before county aggregation.
    assert "Vermilion" in county_names
    assert "Vermillion" not in county_names


def test_county_totals_reconcile_to_statewide_baselines(
    county_rows,
) -> None:
    """County measures must sum to statewide values."""

    assert len(county_rows) == 102

    assert sum(row.children_currently_in_care for row in county_rows) == 8_071

    assert sum(row.current_foster_homes for row in county_rows) == 3_395

    assert sum(row.current_foster_placements for row in county_rows) == 4_343

    assert sum(row.local_foster_placements for row in county_rows) == 1_519

    assert sum(row.out_of_county_foster_placements for row in county_rows) == 2_824

    assert sum(row.homes_with_current_placement for row in county_rows) == 2_733

    assert sum(row.homes_with_recent_activity for row in county_rows) == 3_170

    assert sum(row.homes_without_recent_activity for row in county_rows) == 225

    assert sum(row.current_kin_placements for row in county_rows) == 3_688

    assert sum(row.current_nonfamily_placements for row in county_rows) == 40


def test_cook_county_metrics(
    county_rows,
) -> None:
    """A high-volume county protects core calculations."""

    cook = next(row for row in county_rows if row.county_name == "Cook")

    assert cook.county_slug == "cook"
    assert cook.children_currently_in_care == 1_933
    assert cook.current_foster_homes == 156

    assert cook.children_per_current_home == pytest.approx(1_933 / 156)

    assert cook.current_foster_placements == 1_044
    assert cook.local_foster_placements == 180

    assert cook.out_of_county_foster_placements == 864

    assert cook.local_placement_rate == pytest.approx(180 / 1_044)

    assert cook.homes_with_current_placement == 124
    assert cook.homes_with_recent_activity == 142
    assert cook.homes_without_recent_activity == 14
    assert cook.renewals_within_90_days == 73

    assert cook.current_kin_placements == 879
    assert cook.current_nonfamily_placements == 10

    assert cook.median_observed_active_day_rate == pytest.approx(0.6394640682095005)


def test_zero_placement_denominator_remains_null(
    county_rows,
) -> None:
    """A zero denominator must not become a false zero rate."""

    schuyler = next(row for row in county_rows if row.county_name == "Schuyler")

    assert schuyler.current_foster_placements == 0
    assert schuyler.local_foster_placements == 0
    assert schuyler.local_placement_rate is None
    assert schuyler.recruitment_level == "limited"
    assert schuyler.limited_data is True


def test_recent_activity_never_exceeds_current_homes(
    county_rows,
) -> None:
    """Engagement counts must remain internally consistent."""

    for row in county_rows:
        assert row.homes_with_recent_activity <= row.current_foster_homes

        assert (
            row.homes_without_recent_activity
            == row.current_foster_homes - row.homes_with_recent_activity
        )

        assert row.homes_with_current_placement <= row.current_foster_homes


def test_county_placement_settings_reconcile(
    county_rows,
) -> None:
    """Every county current placement setting must reconcile."""

    for row in county_rows:
        assert (
            row.current_kin_placements
            + row.current_foster_placements
            + row.current_nonfamily_placements
            == row.children_currently_in_care
        )

        assert (
            row.local_foster_placements + row.out_of_county_foster_placements
            == row.current_foster_placements
        )
