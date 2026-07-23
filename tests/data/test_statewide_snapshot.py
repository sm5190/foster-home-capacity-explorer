"""Tests for source loading and statewide derivation."""

from datetime import date

import pytest

from scripts.etl.derive_snapshot import (
    derive_statewide_snapshot,
    intervals_overlap,
)

from scripts.etl.load_sources import load_sources


def test_interval_overlap_includes_long_placement() -> None:
    """A placement spanning the window counts as recent."""

    assert intervals_overlap(
        date(2025, 12, 1),
        date(2026, 7, 1),
        date(2026, 4, 2),
        date(2026, 7, 1),
    )


def test_interval_overlap_excludes_old_placement() -> None:
    """A placement ending before the window is excluded."""

    assert not intervals_overlap(
        date(2026, 1, 1),
        date(2026, 4, 1),
        date(2026, 4, 2),
        date(2026, 7, 1),
    )


def test_source_null_semantics() -> None:
    """Meaningful source NA values must remain null."""

    data = load_sources()

    assert sum(child.discharge_date is None for child in data.children) == 8_071

    assert sum(child.age_at_removal is None for child in data.children) == 6

    assert sum(child.most_recent_age is None for child in data.children) == 6

    assert sum(placement.id_provider is None for placement in data.placements) == 16_926


def test_statewide_snapshot_matches_locked_baselines() -> None:
    """All statewide values must reconcile to the SRS."""

    snapshot = derive_statewide_snapshot(load_sources())

    assert snapshot.source_children == 16_139
    assert snapshot.source_placements == 51_994
    assert snapshot.source_providers == 6_063

    assert snapshot.children_currently_in_care == 8_071
    assert snapshot.current_placements == 8_071

    assert snapshot.current_kin_placements == 3_688
    assert snapshot.current_foster_home_placements == 4_343
    assert snapshot.current_nonfamily_placements == 40

    assert snapshot.current_foster_homes == 3_395
    assert snapshot.homes_with_current_placement == 2_733
    assert snapshot.homes_with_recent_activity == 3_170
    assert snapshot.homes_without_recent_activity == 225

    assert snapshot.local_foster_placements == 1_519
    assert snapshot.out_of_county_foster_placements == 2_824

    assert snapshot.local_placement_rate == pytest.approx(1_519 / 4_343)

    assert snapshot.median_observed_active_day_rate == pytest.approx(0.6967113276492083)
