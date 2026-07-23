"""Calculate county-level age-preference alignment aggregates."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace

from scripts.etl.aggregate_counties import CountyAggregate
from scripts.etl.statistics import linear_percentile
from scripts.etl.config import (
    AGE_BANDS,
    AGE_RECRUITMENT_PERCENTILE,
    AGE_SIGNAL_MINIMUM_CHILDREN,
    ALL_AGE_BANDS,
    KNOWN_AGE_BANDS,
    REPORTING_CUTOFF_DATE,
)
from scripts.etl.load_sources import ProviderRecord, SourceData


@dataclass(frozen=True, slots=True)
class CountyAgeAlignment:
    """Represent one county and age-band alignment aggregate."""

    county_slug: str
    age_band: str
    current_children: int
    preference_matching_homes: int
    children_per_matching_home: float | None
    limited_data: bool
    recruitment_evidence: bool
    statewide_p75_threshold: float | None


@dataclass(frozen=True, slots=True)
class AgeAlignmentResult:
    """Contain classified age alignments and statewide thresholds."""

    alignments: tuple[CountyAgeAlignment, ...]
    thresholds: dict[str, float | None]
    eligible_counties: dict[str, int]


def age_band_for_child(age: int | None) -> str:
    """Assign a child's current age to a configured age band."""

    if age is None:
        return "unknown"

    for age_band in KNOWN_AGE_BANDS:
        band_range = AGE_BANDS[age_band]

        if band_range is None:
            continue

        minimum_age, maximum_age = band_range

        if minimum_age <= age <= maximum_age:
            return age_band

    raise ValueError(
        f"Current child age falls outside the supported range of 0 through 17: {age}"
    )


def provider_preference_overlaps_band(
    provider: ProviderRecord,
    age_band: str,
) -> bool:
    """Return whether a provider preference overlaps an age band."""

    if age_band not in AGE_BANDS:
        raise ValueError(f"Unexpected age band: {age_band!r}")

    band_range = AGE_BANDS[age_band]

    # Unknown child ages cannot be compared with numeric provider
    # preference ranges.
    if band_range is None:
        return False

    band_minimum, band_maximum = band_range

    return provider.min_age <= band_maximum and provider.max_age >= band_minimum


def get_current_providers(
    data: SourceData,
) -> tuple[ProviderRecord, ...]:
    """Return providers licensed at the reporting cutoff."""

    return tuple(
        provider
        for provider in data.providers
        if (
            provider.license_start_date
            <= REPORTING_CUTOFF_DATE
            <= provider.license_end_date
        )
    )


def count_current_children_by_county_and_band(
    data: SourceData,
) -> tuple[
    Counter[tuple[str, str]],
    int,
]:
    """Count current children by removal county and age band."""

    counts: Counter[tuple[str, str]] = Counter()
    current_child_count = 0

    for child in data.children:
        if child.discharge_date is not None:
            continue

        age_band = age_band_for_child(child.most_recent_age)

        counts[(child.removal_county, age_band)] += 1
        current_child_count += 1

    return counts, current_child_count


def group_current_providers_by_county(
    providers: tuple[ProviderRecord, ...],
) -> dict[str, tuple[ProviderRecord, ...]]:
    """Group current foster homes by provider county."""

    grouped: defaultdict[str, list[ProviderRecord]] = defaultdict(list)

    for provider in providers:
        grouped[provider.county_provider].append(provider)

    return {
        county_name: tuple(county_providers)
        for county_name, county_providers in grouped.items()
    }


def count_preference_matching_homes(
    providers: tuple[ProviderRecord, ...],
    age_band: str,
) -> int:
    """Count homes whose preferences overlap the age band."""

    return sum(
        provider_preference_overlaps_band(
            provider,
            age_band,
        )
        for provider in providers
    )


def create_base_alignment(
    *,
    county_slug: str,
    age_band: str,
    current_children: int,
    county_providers: tuple[ProviderRecord, ...],
) -> CountyAgeAlignment:
    """Create one unclassified county age-alignment row."""

    if age_band == "unknown":
        return CountyAgeAlignment(
            county_slug=county_slug,
            age_band=age_band,
            current_children=current_children,
            # Zero is the database placeholder for not evaluated.
            # It must not be interpreted as no compatible homes.
            preference_matching_homes=0,
            children_per_matching_home=None,
            limited_data=True,
            recruitment_evidence=False,
            statewide_p75_threshold=None,
        )

    matching_home_count = count_preference_matching_homes(
        county_providers,
        age_band,
    )

    children_per_matching_home = (
        current_children / matching_home_count if matching_home_count > 0 else None
    )

    limited_data = (
        current_children < AGE_SIGNAL_MINIMUM_CHILDREN or matching_home_count == 0
    )

    return CountyAgeAlignment(
        county_slug=county_slug,
        age_band=age_band,
        current_children=current_children,
        preference_matching_homes=matching_home_count,
        children_per_matching_home=children_per_matching_home,
        limited_data=limited_data,
        recruitment_evidence=False,
        statewide_p75_threshold=None,
    )


def validate_base_alignment_grid(
    alignments: tuple[CountyAgeAlignment, ...],
    counties: tuple[CountyAggregate, ...],
    expected_current_child_count: int,
) -> None:
    """Validate the complete county-by-age-band output grid."""

    expected_row_count = len(counties) * len(ALL_AGE_BANDS)

    if len(alignments) != expected_row_count:
        raise ValueError(
            "Age-alignment row count does not match the expected "
            "county-by-band grid. "
            f"Expected {expected_row_count}, "
            f"received {len(alignments)}."
        )

    expected_keys = {
        (county.county_slug, age_band)
        for county in counties
        for age_band in ALL_AGE_BANDS
    }

    actual_keys = {
        (alignment.county_slug, alignment.age_band) for alignment in alignments
    }

    if actual_keys != expected_keys:
        missing_keys = expected_keys - actual_keys
        unexpected_keys = actual_keys - expected_keys

        raise ValueError(
            "Age-alignment output does not contain exactly one row "
            "for every county and age band. "
            f"Missing keys: {sorted(missing_keys)}; "
            f"unexpected keys: {sorted(unexpected_keys)}."
        )

    aligned_child_total = sum(alignment.current_children for alignment in alignments)

    if aligned_child_total != expected_current_child_count:
        raise ValueError(
            "Age-band child totals do not reconcile with current "
            "children. "
            f"Age rows total {aligned_child_total}; "
            f"current children total "
            f"{expected_current_child_count}."
        )


def derive_base_age_alignments(
    data: SourceData,
    counties: tuple[CountyAggregate, ...],
) -> tuple[CountyAgeAlignment, ...]:
    """Calculate county age metrics before classification."""

    county_slugs = [county.county_slug for county in counties]

    if len(set(county_slugs)) != len(county_slugs):
        raise ValueError("County aggregates contain duplicate county slugs.")

    (
        children_by_county_and_band,
        current_child_count,
    ) = count_current_children_by_county_and_band(data)

    providers_by_county = group_current_providers_by_county(get_current_providers(data))

    alignments: list[CountyAgeAlignment] = []

    for county in counties:
        county_providers = providers_by_county.get(
            county.county_name,
            (),
        )

        for age_band in ALL_AGE_BANDS:
            current_children = children_by_county_and_band[
                (county.county_name, age_band)
            ]

            alignments.append(
                create_base_alignment(
                    county_slug=county.county_slug,
                    age_band=age_band,
                    current_children=current_children,
                    county_providers=county_providers,
                )
            )

    result = tuple(alignments)

    validate_base_alignment_grid(
        result,
        counties,
        current_child_count,
    )

    return result


def get_eligible_age_ratio_values(
    alignments: tuple[CountyAgeAlignment, ...],
    age_band: str,
) -> list[float]:
    """Return stable county ratios used for one age threshold."""

    eligible_values: list[float] = []

    for alignment in alignments:
        if alignment.age_band != age_band:
            continue

        if alignment.limited_data:
            continue

        ratio = alignment.children_per_matching_home

        if ratio is not None:
            eligible_values.append(ratio)

    return eligible_values


def calculate_age_thresholds(
    alignments: tuple[CountyAgeAlignment, ...],
) -> tuple[
    dict[str, float | None],
    dict[str, int],
]:
    """Calculate a p75 ratio threshold for each known age band."""

    thresholds: dict[str, float | None] = {}
    eligible_counties: dict[str, int] = {}

    for age_band in ALL_AGE_BANDS:
        if age_band == "unknown":
            thresholds[age_band] = None
            eligible_counties[age_band] = 0
            continue

        eligible_values = get_eligible_age_ratio_values(
            alignments,
            age_band,
        )

        eligible_counties[age_band] = len(eligible_values)

        if not eligible_values:
            thresholds[age_band] = None
            continue

        thresholds[age_band] = linear_percentile(
            eligible_values,
            AGE_RECRUITMENT_PERCENTILE,
        )
    return thresholds, eligible_counties


def classify_age_alignments(
    alignments: tuple[CountyAgeAlignment, ...],
) -> AgeAlignmentResult:
    """Apply age-band thresholds and recruitment evidence."""

    thresholds, eligible_counties = calculate_age_thresholds(alignments)

    classified: list[CountyAgeAlignment] = []

    for alignment in alignments:
        threshold = thresholds[alignment.age_band]
        ratio = alignment.children_per_matching_home

        recruitment_evidence = (
            alignment.age_band != "unknown"
            and not alignment.limited_data
            and ratio is not None
            and threshold is not None
            and ratio >= threshold
        )

        classified.append(
            replace(
                alignment,
                recruitment_evidence=recruitment_evidence,
                statewide_p75_threshold=threshold,
            )
        )

    return AgeAlignmentResult(
        alignments=tuple(classified),
        thresholds=thresholds,
        eligible_counties=eligible_counties,
    )


def derive_county_age_alignment(
    data: SourceData,
    counties: tuple[CountyAggregate, ...],
) -> AgeAlignmentResult:
    """Derive and classify county age-preference alignment."""

    base_alignments = derive_base_age_alignments(
        data,
        counties,
    )

    return classify_age_alignments(base_alignments)
