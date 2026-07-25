"""Calculate county-level recruitment and engagement aggregates."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from statistics import median

from scripts.etl.config import (
    ANALYSIS_START_DATE,
    RECENT_ACTIVITY_DAYS,
    RENEWAL_WINDOW_DAYS,
    REPORTING_CUTOFF_DATE,
)
from scripts.etl.derive_snapshot import intervals_overlap
from scripts.etl.load_sources import (
    ProviderRecord,
    SourceData,
)


LOCAL_RATE_MINIMUM_DENOMINATOR = 20
ENGAGEMENT_MINIMUM_HOMES = 10


@dataclass(frozen=True, slots=True)
class CountyAggregate:
    """County-level measures stored in county_summary."""

    county_slug: str
    county_name: str

    children_currently_in_care: int

    current_kin_placements: int
    current_foster_placements: int
    current_nonfamily_placements: int

    current_foster_homes: int
    children_per_current_home: float | None

    local_foster_placements: int
    out_of_county_foster_placements: int
    local_placement_rate: float | None

    homes_with_current_placement: int
    homes_with_recent_activity: int
    renewals_within_90_days: int
    renewals_without_recent_activity: int
    homes_without_recent_activity: int
    median_observed_active_day_rate: float | None

    recruitment_level: str
    recruitment_signal_count: int

    engagement_level: str
    engagement_signal_count: int

    primary_opportunity: str
    limited_data: bool


def slugify_county(county_name: str) -> str:
    """Create a stable URL slug without changing the stored label."""

    normalized = unicodedata.normalize(
        "NFKD",
        county_name,
    )

    ascii_name = normalized.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        ascii_name.lower(),
    ).strip("-")

    if not slug:
        raise ValueError(f"Unable to create a slug for county {county_name!r}.")

    return slug


def calculate_observed_active_day_rate(
    provider: ProviderRecord,
) -> float:
    """Calculate activity over the observed license interval."""

    observed_start = max(
        provider.license_start_date,
        ANALYSIS_START_DATE,
    )

    observed_end = min(
        provider.license_end_date,
        REPORTING_CUTOFF_DATE,
    )

    observed_licensed_days = (observed_end - observed_start).days

    if observed_licensed_days <= 0:
        raise ValueError(
            f"Provider has no observed licensed days: {provider.id_provider}"
        )

    if provider.n_days_active > observed_licensed_days:
        raise ValueError(
            "Observed active days exceed observed licensed days "
            f"for provider {provider.id_provider}."
        )

    return provider.n_days_active / observed_licensed_days


def derive_county_aggregates(
    data: SourceData,
) -> tuple[CountyAggregate, ...]:
    """Calculate county-level metrics from the current snapshot."""

    cutoff = REPORTING_CUTOFF_DATE

    recent_window_start = cutoff - timedelta(days=RECENT_ACTIVITY_DAYS)

    renewal_window_end = cutoff + timedelta(days=RENEWAL_WINDOW_DAYS)

    current_children = tuple(
        child for child in data.children if child.discharge_date is None
    )

    current_placements = tuple(
        placement
        for placement in data.placements
        if placement.placement_end_date == cutoff
    )

    current_foster_placements = tuple(
        placement
        for placement in current_placements
        if placement.resource_type == "foster_home"
    )

    current_providers = tuple(
        provider
        for provider in data.providers
        if (provider.license_start_date <= cutoff <= provider.license_end_date)
    )

    current_provider_by_id = {
        provider.id_provider: provider for provider in current_providers
    }

    children_by_county = Counter(child.removal_county for child in current_children)

    kin_placements_by_county = Counter(
        placement.removal_county
        for placement in current_placements
        if placement.resource_type == "kin"
    )

    nonfamily_placements_by_county = Counter(
        placement.removal_county
        for placement in current_placements
        if placement.resource_type == "nonfamily"
    )

    current_homes_by_county = Counter(
        provider.county_provider for provider in current_providers
    )

    foster_placements_by_county = Counter(
        placement.removal_county for placement in current_foster_placements
    )

    local_placements_by_county = Counter(
        placement.removal_county
        for placement in current_foster_placements
        if (placement.removal_county == placement.placement_county)
    )

    out_of_county_placements_by_county = Counter(
        placement.removal_county
        for placement in current_foster_placements
        if (placement.removal_county != placement.placement_county)
    )

    homes_with_current_placement: defaultdict[
        str,
        set[str],
    ] = defaultdict(set)

    for placement in current_foster_placements:
        provider_id = placement.id_provider

        if provider_id is None:
            raise ValueError(
                "Current foster-home placement is missing a provider identifier."
            )

        provider = current_provider_by_id.get(provider_id)

        if provider is None:
            raise ValueError(
                "Current foster-home placement references "
                "a provider that is not currently licensed: "
                f"{provider_id}"
            )

        homes_with_current_placement[provider.county_provider].add(provider_id)

    homes_with_recent_activity: defaultdict[
        str,
        set[str],
    ] = defaultdict(set)

    for placement in data.placements:
        if placement.resource_type != "foster_home":
            continue

        provider_id = placement.id_provider

        if provider_id is None:
            continue

        provider = current_provider_by_id.get(provider_id)

        if provider is None:
            continue

        if intervals_overlap(
            placement.placement_start_date,
            placement.placement_end_date,
            recent_window_start,
            cutoff,
        ):
            homes_with_recent_activity[provider.county_provider].add(provider_id)

    active_day_rates: defaultdict[
        str,
        list[float],
    ] = defaultdict(list)

    renewals_by_county: Counter[str] = Counter()
    renewals_without_recent_activity_by_county: Counter[str] = Counter()

    for provider in current_providers:
        county_name = provider.county_provider

        active_day_rates[county_name].append(
            calculate_observed_active_day_rate(provider)
        )

        if cutoff <= provider.license_end_date <= renewal_window_end:
            renewals_by_county[county_name] += 1

            if provider.id_provider not in homes_with_recent_activity[county_name]:
                renewals_without_recent_activity_by_county[county_name] += 1

    county_names = {child.removal_county for child in current_children}

    county_names.update(provider.county_provider for provider in current_providers)

    county_names.update(placement.removal_county for placement in current_placements)

    county_names.update(placement.placement_county for placement in current_placements)

    aggregates: list[CountyAggregate] = []

    for county_name in sorted(county_names):
        current_children_count = children_by_county[county_name]

        current_kin_placement_count = kin_placements_by_county[county_name]

        current_foster_placement_count = foster_placements_by_county[county_name]

        current_nonfamily_placement_count = nonfamily_placements_by_county[county_name]

        current_homes_count = current_homes_by_county[county_name]

        current_placement_setting_total = (
            current_kin_placement_count
            + current_foster_placement_count
            + current_nonfamily_placement_count
        )

        if current_placement_setting_total != current_children_count:
            raise ValueError(
                "Current placement-setting counts do not reconcile "
                f"with current children for {county_name}. "
                f"Children: {current_children_count}; "
                f"placements: {current_placement_setting_total}."
            )

        # current_foster_placement_count = foster_placements_by_county[county_name]

        local_placement_count = local_placements_by_county[county_name]

        out_of_county_placement_count = out_of_county_placements_by_county[county_name]

        if (
            local_placement_count + out_of_county_placement_count
            != current_foster_placement_count
        ):
            raise ValueError(
                "Local and out-of-county foster placements do not "
                f"reconcile for {county_name}."
            )

        recent_home_count = len(homes_with_recent_activity[county_name])

        current_placement_home_count = len(homes_with_current_placement[county_name])

        if recent_home_count > current_homes_count:
            raise ValueError(
                "Recent active-home count exceeds current "
                f"home count for {county_name}."
            )

        if current_placement_home_count > current_homes_count:
            raise ValueError(
                "Homes with a current placement exceed "
                f"current homes for {county_name}."
            )

        children_per_home = (
            current_children_count / current_homes_count
            if current_homes_count
            else None
        )

        local_placement_rate = (
            local_placement_count / current_foster_placement_count
            if current_foster_placement_count
            else None
        )

        county_active_rates = active_day_rates[county_name]

        median_active_day_rate = (
            median(county_active_rates) if county_active_rates else None
        )

        recruitment_limited = (
            current_foster_placement_count < LOCAL_RATE_MINIMUM_DENOMINATOR
        )

        engagement_limited = current_homes_count < ENGAGEMENT_MINIMUM_HOMES

        renewal_count = renewals_by_county[county_name]
        renewal_without_activity_count = renewals_without_recent_activity_by_county[
            county_name
        ]
        homes_without_recent_activity_count = current_homes_count - recent_home_count

        if renewal_without_activity_count > renewal_count:
            raise ValueError(
                "Renewing homes without recent activity exceed all "
                f"renewing homes for {county_name}."
            )

        if renewal_without_activity_count > homes_without_recent_activity_count:
            raise ValueError(
                "Renewing homes without recent activity exceed all "
                f"homes without recent activity for {county_name}."
            )

        aggregates.append(
            CountyAggregate(
                county_slug=slugify_county(county_name),
                county_name=county_name,
                children_currently_in_care=current_children_count,
                current_kin_placements=current_kin_placement_count,
                current_foster_placements=current_foster_placement_count,
                current_nonfamily_placements=(current_nonfamily_placement_count),
                current_foster_homes=current_homes_count,
                children_per_current_home=children_per_home,
                # current_foster_placements=(current_foster_placement_count),
                local_foster_placements=(local_placement_count),
                out_of_county_foster_placements=(out_of_county_placement_count),
                local_placement_rate=(local_placement_rate),
                homes_with_current_placement=(current_placement_home_count),
                homes_with_recent_activity=(recent_home_count),
                homes_without_recent_activity=(homes_without_recent_activity_count),
                median_observed_active_day_rate=(median_active_day_rate),
                renewals_within_90_days=renewal_count,
                renewals_without_recent_activity=(renewal_without_activity_count),
                # Percentile-based classifications are added
                # during the next ETL stage.
                recruitment_level=("limited" if recruitment_limited else "review"),
                recruitment_signal_count=0,
                engagement_level=("limited" if engagement_limited else "review"),
                engagement_signal_count=0,
                primary_opportunity="review",
                limited_data=(recruitment_limited or engagement_limited),
            )
        )

    county_slugs = [aggregate.county_slug for aggregate in aggregates]

    if len(county_slugs) != len(set(county_slugs)):
        raise ValueError("County slug generation produced a collision.")

    return tuple(aggregates)
