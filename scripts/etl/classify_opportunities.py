"""Classify county recruitment and engagement opportunities."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Final

from scripts.etl.aggregate_counties import (
    ENGAGEMENT_MINIMUM_HOMES,
    LOCAL_RATE_MINIMUM_DENOMINATOR,
    CountyAggregate,
)


PERCENTILE_METHOD: Final = "linear_interpolation_position_(n-1)*p"


@dataclass(frozen=True, slots=True)
class OpportunityThresholds:
    """Statewide thresholds used for county classifications."""

    children_per_current_home_p75: float
    out_of_county_foster_rate_p75: float

    homes_without_recent_activity_share_p75: float
    median_observed_active_day_rate_p25: float
    renewals_within_90_days_share_p75: float

    children_per_current_home_eligible_count: int
    out_of_county_foster_rate_eligible_count: int
    engagement_eligible_count: int


@dataclass(frozen=True, slots=True)
class CountySignal:
    """One transparent signal supporting a county classification."""

    county_slug: str
    focus: str
    signal_code: str
    signal_value: float
    threshold_value: float


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Classified counties, evidence rows, and thresholds."""

    counties: tuple[CountyAggregate, ...]
    signals: tuple[CountySignal, ...]
    thresholds: OpportunityThresholds

    def metadata(self) -> dict[str, str]:
        """Return auditable classification metadata."""

        thresholds = self.thresholds

        return {
            "percentile_method": PERCENTILE_METHOD,
            "threshold_children_per_current_home_p75": (
                _format_float(thresholds.children_per_current_home_p75)
            ),
            "threshold_out_of_county_foster_rate_p75": (
                _format_float(thresholds.out_of_county_foster_rate_p75)
            ),
            ("threshold_homes_without_recent_activity_share_p75"): _format_float(
                thresholds.homes_without_recent_activity_share_p75
            ),
            ("threshold_median_observed_active_day_rate_p25"): _format_float(
                thresholds.median_observed_active_day_rate_p25
            ),
            ("threshold_renewals_within_90_days_share_p75"): _format_float(
                thresholds.renewals_within_90_days_share_p75
            ),
            ("eligible_children_per_current_home_count"): str(
                thresholds.children_per_current_home_eligible_count
            ),
            ("eligible_out_of_county_foster_rate_count"): str(
                thresholds.out_of_county_foster_rate_eligible_count
            ),
            "eligible_engagement_count": str(thresholds.engagement_eligible_count),
        }


def _format_float(value: float) -> str:
    """Format a float with enough precision for reproducibility."""

    return format(value, ".17g")


def linear_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """Calculate a percentile with linear interpolation.

    The position is calculated as:

        (number of values - 1) * percentile

    This makes the percentile behavior explicit and reproducible
    without requiring a numerical package.
    """

    if not 0 <= percentile <= 1:
        raise ValueError("Percentile must be between zero and one.")

    if not values:
        raise ValueError("Cannot calculate a percentile from no values.")

    ordered_values = sorted(values)

    if len(ordered_values) == 1:
        return ordered_values[0]

    position = (len(ordered_values) - 1) * percentile

    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered_values[lower_index]

    interpolation_fraction = position - lower_index

    lower_value = ordered_values[lower_index]
    upper_value = ordered_values[upper_index]

    return lower_value + (upper_value - lower_value) * interpolation_fraction


def _out_of_county_rate(
    county: CountyAggregate,
) -> float | None:
    """Return the county's out-of-county placement rate."""

    if county.current_foster_placements == 0:
        return None

    return county.out_of_county_foster_placements / county.current_foster_placements


def _without_recent_activity_share(
    county: CountyAggregate,
) -> float | None:
    """Return the share of current homes without recent activity."""

    if county.current_foster_homes == 0:
        return None

    return county.homes_without_recent_activity / county.current_foster_homes


def _renewal_share(
    county: CountyAggregate,
) -> float | None:
    """Return the share of homes with renewal dates in 90 days."""

    if county.current_foster_homes == 0:
        return None

    return county.renewals_within_90_days / county.current_foster_homes


def _classification_level(
    signal_count: int,
    limited: bool,
) -> str:
    """Convert a signal count into a user-facing category."""

    if limited:
        return "limited"

    if signal_count >= 2:
        return "higher"

    if signal_count == 1:
        return "possible"

    return "review"


def _primary_opportunity(
    recruitment_signal_count: int,
    engagement_signal_count: int,
    recruitment_limited: bool,
    engagement_limited: bool,
) -> str:
    """Select the main area to investigate."""

    if recruitment_limited and engagement_limited:
        return "review"

    if recruitment_limited:
        return "engagement" if engagement_signal_count > 0 else "review"

    if engagement_limited:
        return "recruitment" if recruitment_signal_count > 0 else "review"

    if recruitment_signal_count == 0 and engagement_signal_count == 0:
        return "review"

    if recruitment_signal_count == engagement_signal_count:
        return "both"

    if recruitment_signal_count > engagement_signal_count:
        return "recruitment"

    return "engagement"


def calculate_thresholds(
    counties: tuple[CountyAggregate, ...],
) -> OpportunityThresholds:
    """Calculate statewide thresholds from eligible counties."""

    if not counties:
        raise ValueError("At least one county is required.")

    children_per_home_values = [
        county.children_per_current_home
        for county in counties
        if county.children_per_current_home is not None
    ]

    out_of_county_rate_values = [
        rate
        for county in counties
        if (county.current_foster_placements >= LOCAL_RATE_MINIMUM_DENOMINATOR)
        if (rate := _out_of_county_rate(county)) is not None
    ]

    engagement_counties = [
        county
        for county in counties
        if (
            county.current_foster_homes >= ENGAGEMENT_MINIMUM_HOMES
            and county.median_observed_active_day_rate is not None
        )
    ]

    without_recent_activity_values = [
        share
        for county in engagement_counties
        if (share := _without_recent_activity_share(county)) is not None
    ]

    median_active_day_rate_values = [
        county.median_observed_active_day_rate
        for county in engagement_counties
        if (county.median_observed_active_day_rate is not None)
    ]

    renewal_share_values = [
        share
        for county in engagement_counties
        if (share := _renewal_share(county)) is not None
    ]

    return OpportunityThresholds(
        children_per_current_home_p75=(
            linear_percentile(
                children_per_home_values,
                0.75,
            )
        ),
        out_of_county_foster_rate_p75=(
            linear_percentile(
                out_of_county_rate_values,
                0.75,
            )
        ),
        homes_without_recent_activity_share_p75=(
            linear_percentile(
                without_recent_activity_values,
                0.75,
            )
        ),
        median_observed_active_day_rate_p25=(
            linear_percentile(
                median_active_day_rate_values,
                0.25,
            )
        ),
        renewals_within_90_days_share_p75=(
            linear_percentile(
                renewal_share_values,
                0.75,
            )
        ),
        children_per_current_home_eligible_count=len(children_per_home_values),
        out_of_county_foster_rate_eligible_count=len(out_of_county_rate_values),
        engagement_eligible_count=len(engagement_counties),
    )


def classify_counties(
    counties: tuple[CountyAggregate, ...],
) -> ClassificationResult:
    """Assign county opportunity categories and reason codes."""

    thresholds = calculate_thresholds(counties)

    classified_counties: list[CountyAggregate] = []
    signals: list[CountySignal] = []

    for county in counties:
        recruitment_signals: list[CountySignal] = []
        engagement_signals: list[CountySignal] = []

        recruitment_limited = (
            county.current_foster_placements < LOCAL_RATE_MINIMUM_DENOMINATOR
        )

        engagement_limited = county.current_foster_homes < ENGAGEMENT_MINIMUM_HOMES

        if (
            county.children_per_current_home is not None
            and county.children_per_current_home
            >= thresholds.children_per_current_home_p75
        ):
            recruitment_signals.append(
                CountySignal(
                    county_slug=county.county_slug,
                    focus="recruitment",
                    signal_code=("high_children_per_current_home"),
                    signal_value=(county.children_per_current_home),
                    threshold_value=(thresholds.children_per_current_home_p75),
                )
            )

        out_of_county_rate = _out_of_county_rate(county)

        if (
            not recruitment_limited
            and out_of_county_rate is not None
            and out_of_county_rate >= thresholds.out_of_county_foster_rate_p75
        ):
            recruitment_signals.append(
                CountySignal(
                    county_slug=county.county_slug,
                    focus="recruitment",
                    signal_code=("high_out_of_county_foster_rate"),
                    signal_value=out_of_county_rate,
                    threshold_value=(thresholds.out_of_county_foster_rate_p75),
                )
            )

        without_recent_share = _without_recent_activity_share(county)

        renewal_share = _renewal_share(county)

        if not engagement_limited:
            if (
                without_recent_share is not None
                and without_recent_share
                >= thresholds.homes_without_recent_activity_share_p75
            ):
                engagement_signals.append(
                    CountySignal(
                        county_slug=county.county_slug,
                        focus="engagement",
                        signal_code=("high_share_without_recent_activity"),
                        signal_value=(without_recent_share),
                        threshold_value=(
                            thresholds.homes_without_recent_activity_share_p75
                        ),
                    )
                )

            if (
                county.median_observed_active_day_rate is not None
                and county.median_observed_active_day_rate
                <= thresholds.median_observed_active_day_rate_p25
            ):
                engagement_signals.append(
                    CountySignal(
                        county_slug=county.county_slug,
                        focus="engagement",
                        signal_code=("low_median_observed_active_day_rate"),
                        signal_value=(county.median_observed_active_day_rate),
                        threshold_value=(
                            thresholds.median_observed_active_day_rate_p25
                        ),
                    )
                )

            if (
                renewal_share is not None
                and renewal_share >= thresholds.renewals_within_90_days_share_p75
            ):
                engagement_signals.append(
                    CountySignal(
                        county_slug=county.county_slug,
                        focus="engagement",
                        signal_code=("high_renewal_share_90_days"),
                        signal_value=renewal_share,
                        threshold_value=(thresholds.renewals_within_90_days_share_p75),
                    )
                )

        recruitment_signal_count = len(recruitment_signals)
        engagement_signal_count = len(engagement_signals)

        recruitment_level = _classification_level(
            recruitment_signal_count,
            recruitment_limited,
        )

        engagement_level = _classification_level(
            engagement_signal_count,
            engagement_limited,
        )

        primary_opportunity = _primary_opportunity(
            recruitment_signal_count=(recruitment_signal_count),
            engagement_signal_count=(engagement_signal_count),
            recruitment_limited=(recruitment_limited),
            engagement_limited=(engagement_limited),
        )

        classified_counties.append(
            replace(
                county,
                recruitment_level=(recruitment_level),
                recruitment_signal_count=(recruitment_signal_count),
                engagement_level=engagement_level,
                engagement_signal_count=(engagement_signal_count),
                primary_opportunity=(primary_opportunity),
                limited_data=(recruitment_limited or engagement_limited),
            )
        )

        signals.extend(recruitment_signals)
        signals.extend(engagement_signals)

    return ClassificationResult(
        counties=tuple(classified_counties),
        signals=tuple(signals),
        thresholds=thresholds,
    )
