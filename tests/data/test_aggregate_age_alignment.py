"""Tests for county age-preference alignment."""

from __future__ import annotations

from datetime import date

import pytest

from scripts.etl.aggregate_age_alignment import (
    CountyAgeAlignment,
    age_band_for_child,
    classify_age_alignments,
    derive_county_age_alignment,
    provider_preference_overlaps_band,
)
from scripts.etl.config import ALL_AGE_BANDS
from scripts.etl.load_sources import SourceData
from tests.data.factories import (
    make_child,
    make_county,
    make_provider,
)


@pytest.mark.parametrize(
    ("age", "expected_band"),
    [
        (0, "0-5"),
        (5, "0-5"),
        (6, "6-12"),
        (12, "6-12"),
        (13, "13-17"),
        (17, "13-17"),
        (None, "unknown"),
    ],
)
def test_age_band_for_child(
    age: int | None,
    expected_band: str,
) -> None:
    """Verify every boundary uses the configured age bands."""

    assert age_band_for_child(age) == expected_band


@pytest.mark.parametrize("age", [-1, 18])
def test_age_band_rejects_out_of_range_age(
    age: int,
) -> None:
    """Reject ages outside the supported child range."""

    with pytest.raises(
        ValueError,
        match="outside the supported range",
    ):
        age_band_for_child(age)


@pytest.mark.parametrize(
    (
        "minimum_age",
        "maximum_age",
        "age_band",
        "expected",
    ),
    [
        (0, 5, "0-5", True),
        (5, 8, "0-5", True),
        (5, 8, "6-12", True),
        (6, 12, "0-5", False),
        (12, 14, "6-12", True),
        (12, 14, "13-17", True),
        (13, 17, "6-12", False),
        (0, 17, "13-17", True),
        (0, 17, "unknown", False),
    ],
)
def test_provider_preference_overlap(
    minimum_age: int,
    maximum_age: int,
    age_band: str,
    expected: bool,
) -> None:
    """Verify inclusive interval-overlap behavior."""

    provider = make_provider(
        "provider-1",
        minimum_age,
        maximum_age,
    )

    assert (
        provider_preference_overlaps_band(
            provider,
            age_band,
        )
        is expected
    )


def test_provider_preference_rejects_unknown_band() -> None:
    """Reject age-band labels outside the configured set."""

    provider = make_provider(
        "provider-1",
        0,
        17,
    )

    with pytest.raises(
        ValueError,
        match="Unexpected age band",
    ):
        provider_preference_overlaps_band(
            provider,
            "18-plus",
        )


def test_derive_county_age_alignment() -> None:
    """Calculate one complete county-by-age-band grid."""

    data = SourceData(
        children=(
            make_child("child-1", 2),
            make_child("child-2", 5),
            make_child("child-3", 6),
            make_child("child-4", 12),
            make_child("child-5", 15),
            make_child("child-6", None),
        ),
        placements=(),
        providers=(
            make_provider("provider-young", 0, 7),
            make_provider("provider-middle", 6, 12),
            make_provider("provider-teen", 13, 17),
            make_provider("provider-all", 0, 17),
        ),
    )

    result = derive_county_age_alignment(
        data,
        (make_county(),),
    )

    assert len(result.alignments) == len(ALL_AGE_BANDS)

    by_band = {alignment.age_band: alignment for alignment in result.alignments}

    assert by_band["0-5"] == CountyAgeAlignment(
        county_slug="example",
        age_band="0-5",
        current_children=2,
        preference_matching_homes=2,
        children_per_matching_home=1.0,
        limited_data=True,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )

    middle = by_band["6-12"]

    assert middle.county_slug == "example"
    assert middle.current_children == 2
    assert middle.preference_matching_homes == 3

    children_per_home = middle.children_per_matching_home

    assert children_per_home is not None
    assert children_per_home == pytest.approx(2 / 3)
    assert middle.limited_data is True
    assert middle.recruitment_evidence is False
    assert middle.statewide_p75_threshold is None

    assert by_band["13-17"] == CountyAgeAlignment(
        county_slug="example",
        age_band="13-17",
        current_children=1,
        preference_matching_homes=2,
        children_per_matching_home=0.5,
        limited_data=True,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )

    assert by_band["unknown"] == CountyAgeAlignment(
        county_slug="example",
        age_band="unknown",
        current_children=1,
        preference_matching_homes=0,
        children_per_matching_home=None,
        limited_data=True,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )

    assert result.thresholds == {
        "0-5": None,
        "6-12": None,
        "13-17": None,
        "unknown": None,
    }

    assert result.eligible_counties == {
        "0-5": 0,
        "6-12": 0,
        "13-17": 0,
        "unknown": 0,
    }


def test_excludes_discharged_children_and_expired_providers() -> None:
    """Use only children in care and homes licensed at cutoff."""

    data = SourceData(
        children=(
            make_child("current", 4),
            make_child(
                "discharged",
                4,
                discharge_date=date(2026, 6, 1),
            ),
        ),
        placements=(),
        providers=(
            make_provider(
                "current-provider",
                0,
                5,
            ),
            make_provider(
                "expired-provider",
                0,
                17,
                license_end_date=date(2026, 6, 30),
            ),
        ),
    )

    result = derive_county_age_alignment(
        data,
        (make_county(),),
    )

    young = next(
        alignment for alignment in result.alignments if alignment.age_band == "0-5"
    )

    assert young.current_children == 1
    assert young.preference_matching_homes == 1


def test_license_cutoff_is_inclusive() -> None:
    """Include a provider whose license ends on the cutoff."""

    data = SourceData(
        children=(make_child("child-1", 4),),
        placements=(),
        providers=(
            make_provider(
                "cutoff-provider",
                0,
                5,
                license_end_date=date(2026, 7, 1),
            ),
        ),
    )

    result = derive_county_age_alignment(
        data,
        (make_county(),),
    )

    young = next(
        alignment for alignment in result.alignments if alignment.age_band == "0-5"
    )

    assert young.preference_matching_homes == 1


def test_age_alignment_reconciles_multiple_counties() -> None:
    """Produce every band when a county has zero children."""

    counties = (
        make_county(),
        make_county(
            county_slug="second",
            county_name="Second",
        ),
    )

    data = SourceData(
        children=(
            make_child(
                "child-1",
                10,
                "Example",
            ),
        ),
        placements=(),
        providers=(
            make_provider(
                "second-provider",
                6,
                12,
                "Second",
            ),
        ),
    )

    result = derive_county_age_alignment(
        data,
        counties,
    )

    assert len(result.alignments) == (len(counties) * len(ALL_AGE_BANDS))

    second_middle = next(
        alignment
        for alignment in result.alignments
        if (alignment.county_slug == "second" and alignment.age_band == "6-12")
    )

    assert second_middle.current_children == 0
    assert second_middle.preference_matching_homes == 1
    assert second_middle.children_per_matching_home == 0.0
    assert second_middle.limited_data is True


def test_classifies_age_recruitment_evidence_at_p75() -> None:
    """Flag eligible county ratios at or above the p75 threshold."""

    alignments = (
        CountyAgeAlignment(
            county_slug="one",
            age_band="0-5",
            current_children=10,
            preference_matching_homes=10,
            children_per_matching_home=1.0,
            limited_data=False,
            recruitment_evidence=False,
            statewide_p75_threshold=None,
        ),
        CountyAgeAlignment(
            county_slug="two",
            age_band="0-5",
            current_children=20,
            preference_matching_homes=10,
            children_per_matching_home=2.0,
            limited_data=False,
            recruitment_evidence=False,
            statewide_p75_threshold=None,
        ),
        CountyAgeAlignment(
            county_slug="three",
            age_band="0-5",
            current_children=30,
            preference_matching_homes=10,
            children_per_matching_home=3.0,
            limited_data=False,
            recruitment_evidence=False,
            statewide_p75_threshold=None,
        ),
        CountyAgeAlignment(
            county_slug="four",
            age_band="0-5",
            current_children=40,
            preference_matching_homes=10,
            children_per_matching_home=4.0,
            limited_data=False,
            recruitment_evidence=False,
            statewide_p75_threshold=None,
        ),
    )

    result = classify_age_alignments(alignments)

    threshold = result.thresholds["0-5"]

    assert threshold is not None
    assert threshold == pytest.approx(3.25)
    assert result.eligible_counties["0-5"] == 4

    by_county = {alignment.county_slug: alignment for alignment in result.alignments}

    assert by_county["one"].recruitment_evidence is False
    assert by_county["two"].recruitment_evidence is False
    assert by_county["three"].recruitment_evidence is False
    assert by_county["four"].recruitment_evidence is True

    for alignment in result.alignments:
        stored_threshold = alignment.statewide_p75_threshold

        assert stored_threshold is not None
        assert stored_threshold == pytest.approx(3.25)


def test_limited_rows_do_not_affect_age_threshold() -> None:
    """Exclude small-denominator rows from percentile calculation."""

    eligible = CountyAgeAlignment(
        county_slug="eligible",
        age_band="6-12",
        current_children=20,
        preference_matching_homes=10,
        children_per_matching_home=2.0,
        limited_data=False,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )

    limited = CountyAgeAlignment(
        county_slug="limited",
        age_band="6-12",
        current_children=9,
        preference_matching_homes=1,
        children_per_matching_home=9.0,
        limited_data=True,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )

    result = classify_age_alignments((eligible, limited))

    threshold = result.thresholds["6-12"]

    assert threshold == 2.0
    assert result.eligible_counties["6-12"] == 1

    by_county = {alignment.county_slug: alignment for alignment in result.alignments}

    assert by_county["eligible"].recruitment_evidence is True
    assert by_county["limited"].recruitment_evidence is False
