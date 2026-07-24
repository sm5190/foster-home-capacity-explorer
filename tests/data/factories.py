"""Shared record factories for ETL data tests."""

from __future__ import annotations

from datetime import date

from scripts.etl.aggregate_counties import CountyAggregate
from scripts.etl.config import REPORTING_CUTOFF_DATE
from scripts.etl.load_sources import (
    ChildRecord,
    PlacementRecord,
    ProviderRecord,
)


def make_county(
    *,
    county_slug: str = "example",
    county_name: str = "Example",
    children_currently_in_care: int = 0,
    current_kin_placements: int = 0,
    current_foster_placements: int = 0,
    current_nonfamily_placements: int = 0,
    current_foster_homes: int = 0,
    local_foster_placements: int = 0,
    out_of_county_foster_placements: int = 0,
) -> CountyAggregate:
    """Create a county aggregate for ETL data tests."""

    children_per_current_home = (
        children_currently_in_care / current_foster_homes
        if current_foster_homes > 0
        else None
    )

    local_placement_rate = (
        local_foster_placements / current_foster_placements
        if current_foster_placements > 0
        else None
    )

    return CountyAggregate(
        county_slug=county_slug,
        county_name=county_name,
        children_currently_in_care=(children_currently_in_care),
        current_kin_placements=current_kin_placements,
        current_foster_placements=(current_foster_placements),
        current_nonfamily_placements=(current_nonfamily_placements),
        current_foster_homes=current_foster_homes,
        children_per_current_home=children_per_current_home,
        # current_foster_placements=current_foster_placements,
        local_foster_placements=local_foster_placements,
        out_of_county_foster_placements=(out_of_county_foster_placements),
        local_placement_rate=local_placement_rate,
        homes_with_current_placement=0,
        homes_with_recent_activity=0,
        homes_without_recent_activity=0,
        median_observed_active_day_rate=None,
        renewals_within_90_days=0,
        recruitment_level="limited",
        recruitment_signal_count=0,
        engagement_level="limited",
        engagement_signal_count=0,
        primary_opportunity="review",
        limited_data=True,
    )


def make_child(
    child_id: str,
    age: int | None,
    county: str = "Example",
    *,
    discharge_date: date | None = None,
) -> ChildRecord:
    """Create a child record for ETL data tests."""

    return ChildRecord(
        id_child=child_id,
        removal_date=date(2025, 1, 1),
        discharge_date=discharge_date,
        age_at_removal=age,
        most_recent_age=age,
        removal_county=county,
    )


def make_placement(
    child_id: str,
    *,
    removal_county: str = "Example",
    placement_county: str = "Example",
    resource_type: str = "foster_home",
    placement_start_date: date = date(2025, 1, 1),
    placement_end_date: date = REPORTING_CUTOFF_DATE,
    placement_index: int = 1,
    provider_id: str | None = "provider-1",
    placement_length: int = 546,
) -> PlacementRecord:
    """Create a placement record for ETL data tests."""

    return PlacementRecord(
        id_child=child_id,
        placement_start_date=placement_start_date,
        placement_end_date=placement_end_date,
        resource_type=resource_type,
        placement_index=placement_index,
        removal_county=removal_county,
        placement_county=placement_county,
        id_provider=provider_id,
        placement_length=placement_length,
    )


def make_provider(
    provider_id: str,
    minimum_age: int,
    maximum_age: int,
    county: str = "Example",
    *,
    license_start_date: date = date(2025, 1, 1),
    license_end_date: date = date(2027, 1, 1),
) -> ProviderRecord:
    """Create a provider record for ETL data tests."""

    return ProviderRecord(
        id_provider=provider_id,
        license_start_date=license_start_date,
        license_end_date=license_end_date,
        county_provider=county,
        n_days_licensed=730,
        n_days_active=100,
        min_age=minimum_age,
        max_age=maximum_age,
    )
