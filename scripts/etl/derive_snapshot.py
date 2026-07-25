"""Derive the statewide current foster-care snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from scripts.etl.config import (
    ANALYSIS_START_DATE,
    RECENT_ACTIVITY_DAYS,
    RENEWAL_WINDOW_DAYS,
    REPORTING_CUTOFF_DATE,
)
from scripts.etl.load_sources import SourceData


@dataclass(frozen=True, slots=True)
class StatewideSnapshot:
    """Validated statewide aggregate values."""

    source_children: int
    source_placements: int
    source_providers: int

    children_currently_in_care: int
    current_placements: int

    current_kin_placements: int
    current_foster_home_placements: int
    current_nonfamily_placements: int

    current_foster_homes: int
    homes_with_current_placement: int
    homes_with_recent_activity: int
    homes_without_recent_activity: int
    renewals_within_90_days: int
    renewals_without_recent_activity: int
    local_foster_placements: int
    out_of_county_foster_placements: int
    local_placement_rate: float | None

    median_observed_active_day_rate: float | None


def intervals_overlap(
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
) -> bool:
    """Return whether two inclusive date intervals overlap."""

    return first_start <= second_end and first_end >= second_start


def derive_statewide_snapshot(
    data: SourceData,
) -> StatewideSnapshot:
    """Calculate and reconcile the current statewide snapshot."""

    cutoff = REPORTING_CUTOFF_DATE
    recent_window_start = cutoff - timedelta(days=RECENT_ACTIVITY_DAYS)

    current_children = tuple(
        child for child in data.children if child.discharge_date is None
    )

    current_placements = tuple(
        placement
        for placement in data.placements
        if placement.placement_end_date == cutoff
    )

    current_providers = tuple(
        provider
        for provider in data.providers
        if (provider.license_start_date <= cutoff <= provider.license_end_date)
    )

    current_child_ids = {child.id_child for child in current_children}
    current_placement_child_ids = {
        placement.id_child for placement in current_placements
    }

    if len(current_placements) != len(current_placement_child_ids):
        raise ValueError("A current child has more than one current placement.")

    if current_child_ids != current_placement_child_ids:
        raise ValueError(
            "Current child and current placement records do not reconcile."
        )

    current_foster_placements = tuple(
        placement
        for placement in current_placements
        if placement.resource_type == "foster_home"
    )

    local_foster_placements = tuple(
        placement
        for placement in current_foster_placements
        if (placement.removal_county == placement.placement_county)
    )

    out_of_county_foster_placements = tuple(
        placement
        for placement in current_foster_placements
        if (placement.removal_county != placement.placement_county)
    )

    current_provider_ids = {provider.id_provider for provider in current_providers}

    homes_with_current_placement = {
        placement.id_provider
        for placement in current_foster_placements
        if placement.id_provider in current_provider_ids
    }

    homes_with_recent_activity = {
        placement.id_provider
        for placement in data.placements
        if (
            placement.resource_type == "foster_home"
            and placement.id_provider in current_provider_ids
            and intervals_overlap(
                placement.placement_start_date,
                placement.placement_end_date,
                recent_window_start,
                cutoff,
            )
        )
    }

    renewal_window_end = cutoff + timedelta(days=RENEWAL_WINDOW_DAYS)

    renewing_provider_ids = {
        provider.id_provider
        for provider in current_providers
        if cutoff <= provider.license_end_date <= renewal_window_end
    }

    renewing_without_recent_activity_ids = (
        renewing_provider_ids - homes_with_recent_activity
    )

    if len(renewing_without_recent_activity_ids) > len(renewing_provider_ids):
        raise ValueError(
            "Renewing homes without recent activity exceed all renewing homes."
        )

    observed_active_day_rates: list[float] = []

    for provider in current_providers:
        observed_start = max(
            provider.license_start_date,
            ANALYSIS_START_DATE,
        )
        observed_end = min(
            provider.license_end_date,
            cutoff,
        )

        observed_licensed_days = (observed_end - observed_start).days

        if observed_licensed_days <= 0:
            raise ValueError(
                "Current provider has no observed licensed "
                f"days: {provider.id_provider}"
            )

        if provider.n_days_active > observed_licensed_days:
            raise ValueError(
                "Observed active days exceed observed licensed "
                f"days for provider {provider.id_provider}."
            )

        observed_active_day_rates.append(
            provider.n_days_active / observed_licensed_days
        )

    foster_placement_count = len(current_foster_placements)
    local_placement_count = len(local_foster_placements)

    return StatewideSnapshot(
        source_children=len(data.children),
        source_placements=len(data.placements),
        source_providers=len(data.providers),
        children_currently_in_care=len(current_children),
        current_placements=len(current_placements),
        current_kin_placements=sum(
            placement.resource_type == "kin" for placement in current_placements
        ),
        current_foster_home_placements=(foster_placement_count),
        current_nonfamily_placements=sum(
            placement.resource_type == "nonfamily" for placement in current_placements
        ),
        current_foster_homes=len(current_providers),
        homes_with_current_placement=len(homes_with_current_placement),
        homes_with_recent_activity=len(homes_with_recent_activity),
        renewals_within_90_days=len(renewing_provider_ids),
        renewals_without_recent_activity=(len(renewing_without_recent_activity_ids)),
        homes_without_recent_activity=(
            len(current_providers) - len(homes_with_recent_activity)
        ),
        local_foster_placements=(local_placement_count),
        out_of_county_foster_placements=len(out_of_county_foster_placements),
        local_placement_rate=(
            local_placement_count / foster_placement_count
            if foster_placement_count
            else None
        ),
        median_observed_active_day_rate=(
            median(observed_active_day_rates) if observed_active_day_rates else None
        ),
    )
