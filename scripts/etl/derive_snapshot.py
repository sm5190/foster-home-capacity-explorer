from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import median

from scripts.etl.config import (
    ANALYSIS_START_DATE,
    RECENT_ACTIVITY_DAYS,
    REPORTING_CUTOFF_DATE,
)
from scripts.etl.load_sources import SourceData


@dataclass(frozen=True, slots=True)
class SnapshotBaselines:
    source_children: int
    source_placements: int
    source_providers: int
    current_children: int
    current_placements: int
    current_kin_placements: int
    current_foster_home_placements: int
    current_nonfamily_placements: int
    current_foster_homes: int
    homes_supporting_current_placement: int
    homes_with_recent_activity: int
    homes_without_recent_activity: int
    local_current_foster_placements: int
    out_of_county_current_foster_placements: int
    local_current_foster_placement_rate: float
    median_observed_active_day_rate: float


def derive_snapshot_baselines(data: SourceData) -> SnapshotBaselines:
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
        if provider.license_start_date <= cutoff <= provider.license_end_date
    )

    current_foster_placements = tuple(
        placement
        for placement in current_placements
        if placement.resource_type == "foster_home"
    )
    local_current_foster_placements = tuple(
        placement
        for placement in current_foster_placements
        if placement.removal_county == placement.placement_county
    )
    out_of_county_current_foster_placements = tuple(
        placement
        for placement in current_foster_placements
        if placement.removal_county != placement.placement_county
    )

    current_provider_ids = {
        provider.id_provider for provider in current_providers
    }
    homes_supporting_current_placement = {
        placement.id_provider
        for placement in current_foster_placements
        if placement.id_provider is not None
    }
    homes_with_recent_activity = {
        placement.id_provider
        for placement in data.placements
        if placement.resource_type == "foster_home"
        and placement.id_provider in current_provider_ids
        and placement.placement_start_date <= cutoff
        and placement.placement_end_date >= recent_window_start
    }

    observed_active_day_rates: list[float] = []
    for provider in current_providers:
        observed_start = max(provider.license_start_date, ANALYSIS_START_DATE)
        observed_end = min(provider.license_end_date, cutoff)
        observed_days = (observed_end - observed_start).days

        if observed_days <= 0:
            raise ValueError(
                "Current providers must have at least one observed licensed day."
            )
        if provider.n_days_active > observed_days:
            raise ValueError(
                "Observed active days cannot exceed observed licensed days."
            )

        observed_active_day_rates.append(
            provider.n_days_active / observed_days
        )

    foster_count = len(current_foster_placements)
    local_count = len(local_current_foster_placements)

    return SnapshotBaselines(
        source_children=len(data.children),
        source_placements=len(data.placements),
        source_providers=len(data.providers),
        current_children=len(current_children),
        current_placements=len(current_placements),
        current_kin_placements=sum(
            placement.resource_type == "kin"
            for placement in current_placements
        ),
        current_foster_home_placements=foster_count,
        current_nonfamily_placements=sum(
            placement.resource_type == "nonfamily"
            for placement in current_placements
        ),
        current_foster_homes=len(current_providers),
        homes_supporting_current_placement=len(
            homes_supporting_current_placement
        ),
        homes_with_recent_activity=len(homes_with_recent_activity),
        homes_without_recent_activity=(
            len(current_providers) - len(homes_with_recent_activity)
        ),
        local_current_foster_placements=local_count,
        out_of_county_current_foster_placements=len(
            out_of_county_current_foster_placements
        ),
        local_current_foster_placement_rate=local_count / foster_count,
        median_observed_active_day_rate=median(
            observed_active_day_rates
        ),
    )
