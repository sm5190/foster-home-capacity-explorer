"""Tests for county opportunity classification."""

from __future__ import annotations

from collections import Counter

import pytest

from scripts.etl.aggregate_counties import (
    derive_county_aggregates,
)
from scripts.etl.classify_opportunities import (
    classify_counties,
    linear_percentile,
)
from scripts.etl.load_sources import load_sources


@pytest.fixture(scope="module")
def classification():
    """Build the county classification once."""

    counties = derive_county_aggregates(load_sources())

    return classify_counties(counties)


def test_linear_percentile_interpolates() -> None:
    """The percentile calculation must be deterministic."""

    assert linear_percentile(
        [0.0, 10.0],
        0.25,
    ) == pytest.approx(2.5)

    assert linear_percentile(
        [1.0, 2.0, 3.0, 4.0],
        0.75,
    ) == pytest.approx(3.25)


def test_thresholds_match_current_sources(
    classification,
) -> None:
    """Thresholds must remain stable for the supplied snapshot."""

    thresholds = classification.thresholds

    assert thresholds.children_per_current_home_p75 == pytest.approx(1.669761273209549)

    assert thresholds.out_of_county_foster_rate_p75 == pytest.approx(0.7788220551378446)

    assert thresholds.homes_without_recent_activity_share_p75 == pytest.approx(
        0.09032634032634032
    )

    assert thresholds.median_observed_active_day_rate_p25 == pytest.approx(
        0.6394640682095005
    )

    assert thresholds.renewals_within_90_days_share_p75 == pytest.approx(0.5)

    assert thresholds.children_per_current_home_eligible_count == 103

    assert thresholds.out_of_county_foster_rate_eligible_count == 31

    assert thresholds.engagement_eligible_count == 103


def test_classification_counts(
    classification,
) -> None:
    """County category counts must match the snapshot."""

    recruitment_levels = Counter(
        county.recruitment_level for county in classification.counties
    )

    engagement_levels = Counter(
        county.engagement_level for county in classification.counties
    )

    primary_opportunities = Counter(
        county.primary_opportunity for county in classification.counties
    )

    assert recruitment_levels == {
        "limited": 72,
        "possible": 21,
        "higher": 6,
        "review": 4,
    }

    assert engagement_levels == {
        "review": 42,
        "possible": 40,
        "higher": 21,
    }

    assert primary_opportunities == {
        "engagement": 51,
        "review": 28,
        "recruitment": 16,
        "both": 8,
    }


def test_signal_counts_match_county_rows(
    classification,
) -> None:
    """Evidence rows must reconcile with summary counts."""

    stored_signal_count = sum(
        county.recruitment_signal_count + county.engagement_signal_count
        for county in classification.counties
    )

    assert len(classification.signals) == 117
    assert stored_signal_count == 117

    signal_codes = Counter(signal.signal_code for signal in classification.signals)

    assert signal_codes == {
        "high_children_per_current_home": 26,
        "high_out_of_county_foster_rate": 8,
        "high_share_without_recent_activity": 26,
        "low_median_observed_active_day_rate": 26,
        "high_renewal_share_90_days": 31,
    }


def test_cook_has_higher_recruitment_opportunity(
    classification,
) -> None:
    """Cook protects the primary recruitment workflow."""

    cook = next(
        county for county in classification.counties if county.county_name == "Cook"
    )

    assert cook.recruitment_level == "higher"
    assert cook.recruitment_signal_count == 2

    assert cook.engagement_level == "possible"
    assert cook.engagement_signal_count == 1

    assert cook.primary_opportunity == "recruitment"

    cook_signal_codes = {
        signal.signal_code
        for signal in classification.signals
        if signal.county_slug == "cook"
    }

    assert cook_signal_codes == {
        "high_children_per_current_home",
        "high_out_of_county_foster_rate",
        "low_median_observed_active_day_rate",
    }


def test_schuyler_retains_limited_recruitment_label(
    classification,
) -> None:
    """A zero placement denominator must stay limited."""

    schuyler = next(
        county for county in classification.counties if county.county_name == "Schuyler"
    )

    assert schuyler.current_foster_placements == 0
    assert schuyler.recruitment_level == "limited"
    assert schuyler.recruitment_signal_count == 0
    assert schuyler.primary_opportunity == "review"


def test_vermillion_is_engagement_led(
    classification,
) -> None:
    """The preserved alternate county label remains classifiable."""

    vermillion = next(
        county
        for county in classification.counties
        if county.county_name == "Vermillion"
    )

    assert vermillion.recruitment_level == "limited"
    assert vermillion.engagement_level == "higher"
    assert vermillion.engagement_signal_count == 2
    assert vermillion.primary_opportunity == "engagement"
