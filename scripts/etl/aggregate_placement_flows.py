"""Calculate county-level current foster-home placement flows."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

from scripts.etl.aggregate_counties import CountyAggregate
from scripts.etl.config import REPORTING_CUTOFF_DATE
from scripts.etl.load_sources import (
    PlacementRecord,
    SourceData,
)


@dataclass(frozen=True, slots=True)
class CountyPlacementFlow:
    """Represent one origin-to-destination placement flow."""

    origin_county_slug: str
    destination_county_name: str
    placement_count: int
    placement_share: float
    is_local: bool


def is_current_foster_home_placement(
    placement: PlacementRecord,
) -> bool:
    """Return whether a placement belongs in the current flow analysis."""

    return (
        placement.resource_type == "foster_home"
        and placement.placement_end_date == REPORTING_CUTOFF_DATE
    )


def get_current_foster_home_placements(
    data: SourceData,
) -> tuple[PlacementRecord, ...]:
    """Return current foster-home placements at the reporting cutoff."""

    return tuple(
        placement
        for placement in data.placements
        if is_current_foster_home_placement(placement)
    )


def build_county_name_to_slug(
    counties: tuple[CountyAggregate, ...],
) -> dict[str, str]:
    """Build and validate the county-name-to-slug lookup."""

    county_names = [county.county_name for county in counties]

    county_slugs = [county.county_slug for county in counties]

    if len(set(county_names)) != len(county_names):
        raise ValueError("County aggregates contain duplicate county names.")

    if len(set(county_slugs)) != len(county_slugs):
        raise ValueError("County aggregates contain duplicate county slugs.")

    return {county.county_name: county.county_slug for county in counties}


def count_placement_flows(
    placements: tuple[PlacementRecord, ...],
    county_slug_by_name: dict[str, str],
) -> tuple[
    Counter[tuple[str, str]],
    Counter[str],
]:
    """Count placements by origin and destination county."""

    flow_counts: Counter[tuple[str, str]] = Counter()
    origin_totals: Counter[str] = Counter()

    for placement in placements:
        origin_county_name = placement.removal_county
        destination_county_name = placement.placement_county

        if origin_county_name not in county_slug_by_name:
            raise ValueError(
                "Current foster-home placement references an "
                "origin county that is missing from county "
                f"aggregates: {origin_county_name!r}"
            )

        if not destination_county_name:
            raise ValueError(
                "Current foster-home placement contains an empty destination county."
            )

        flow_counts[
            (
                origin_county_name,
                destination_county_name,
            )
        ] += 1

        origin_totals[origin_county_name] += 1

    return flow_counts, origin_totals


def create_placement_flow_rows(
    flow_counts: Counter[tuple[str, str]],
    origin_totals: Counter[str],
    county_slug_by_name: dict[str, str],
) -> tuple[CountyPlacementFlow, ...]:
    """Convert placement counts into deterministic aggregate rows."""

    destinations_by_origin: defaultdict[
        str,
        list[tuple[str, int]],
    ] = defaultdict(list)

    for (
        origin_county_name,
        destination_county_name,
    ), placement_count in flow_counts.items():
        destinations_by_origin[origin_county_name].append(
            (
                destination_county_name,
                placement_count,
            )
        )

    rows: list[CountyPlacementFlow] = []

    origins = sorted(
        destinations_by_origin,
        key=lambda county_name: county_slug_by_name[county_name],
    )

    for origin_county_name in origins:
        origin_total = origin_totals[origin_county_name]

        if origin_total <= 0:
            raise ValueError(
                "Placement-flow origin totals must be positive. "
                f"County: {origin_county_name!r}; "
                f"total: {origin_total}."
            )

        destinations = sorted(
            destinations_by_origin[origin_county_name],
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )

        for (
            destination_county_name,
            placement_count,
        ) in destinations:
            rows.append(
                CountyPlacementFlow(
                    origin_county_slug=(county_slug_by_name[origin_county_name]),
                    destination_county_name=(destination_county_name),
                    placement_count=placement_count,
                    placement_share=(placement_count / origin_total),
                    is_local=(destination_county_name == origin_county_name),
                )
            )

    return tuple(rows)


def validate_placement_flow_rows(
    flows: tuple[CountyPlacementFlow, ...],
    placements: tuple[PlacementRecord, ...],
    counties: tuple[CountyAggregate, ...],
) -> None:
    """Validate placement-flow counts, shares, and reconciliations."""

    expected_keys = {
        (
            placement.removal_county,
            placement.placement_county,
        )
        for placement in placements
    }

    county_name_by_slug = {
        county.county_slug: county.county_name for county in counties
    }

    actual_keys = {
        (
            county_name_by_slug[flow.origin_county_slug],
            flow.destination_county_name,
        )
        for flow in flows
    }

    if actual_keys != expected_keys:
        missing_keys = expected_keys - actual_keys
        unexpected_keys = actual_keys - expected_keys

        raise ValueError(
            "Placement-flow rows do not match the current "
            "origin-destination pairs. "
            f"Missing: {sorted(missing_keys)}; "
            f"unexpected: {sorted(unexpected_keys)}."
        )

    total_flow_count = sum(flow.placement_count for flow in flows)

    if total_flow_count != len(placements):
        raise ValueError(
            "Placement-flow counts do not reconcile with current "
            "foster-home placements. "
            f"Flow total: {total_flow_count}; "
            f"placement total: {len(placements)}."
        )

    flows_by_origin: defaultdict[
        str,
        list[CountyPlacementFlow],
    ] = defaultdict(list)

    for flow in flows:
        if flow.placement_count <= 0:
            raise ValueError(
                f"Placement-flow rows must contain positive counts. Flow: {flow}"
            )

        expected_local = (
            flow.destination_county_name == county_name_by_slug[flow.origin_county_slug]
        )

        if flow.is_local != expected_local:
            raise ValueError(
                "Placement-flow local flag does not match the "
                f"origin and destination counties: {flow}"
            )

        flows_by_origin[flow.origin_county_slug].append(flow)

    for county in counties:
        county_flows = flows_by_origin.get(
            county.county_slug,
            [],
        )

        flow_count = sum(flow.placement_count for flow in county_flows)

        local_flow_count = sum(
            flow.placement_count for flow in county_flows if flow.is_local
        )

        out_of_county_flow_count = sum(
            flow.placement_count for flow in county_flows if not flow.is_local
        )

        if flow_count != county.current_foster_placements:
            raise ValueError(
                "Placement-flow total does not reconcile with the "
                "county current foster-placement count. "
                f"County: {county.county_name}; "
                f"flow count: {flow_count}; "
                "county aggregate: "
                f"{county.current_foster_placements}."
            )

        if local_flow_count != county.local_foster_placements:
            raise ValueError(
                "Local placement-flow count does not reconcile "
                "with the county aggregate. "
                f"County: {county.county_name}; "
                f"flow count: {local_flow_count}; "
                "county aggregate: "
                f"{county.local_foster_placements}."
            )

        if out_of_county_flow_count != county.out_of_county_foster_placements:
            raise ValueError(
                "Out-of-county placement-flow count does not "
                "reconcile with the county aggregate. "
                f"County: {county.county_name}; "
                f"flow count: {out_of_county_flow_count}; "
                "county aggregate: "
                f"{county.out_of_county_foster_placements}."
            )

        if county.current_foster_placements == 0:
            if county_flows:
                raise ValueError(
                    "A county with no current foster placements "
                    "must not have placement-flow rows. "
                    f"County: {county.county_name}."
                )

            continue

        placement_share_total = math.fsum(flow.placement_share for flow in county_flows)

        if not math.isclose(
            placement_share_total,
            1.0,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "Placement-flow shares do not sum to one for "
                f"{county.county_name}. "
                f"Share total: {placement_share_total}."
            )


def derive_county_placement_flows(
    data: SourceData,
    counties: tuple[CountyAggregate, ...],
) -> tuple[CountyPlacementFlow, ...]:
    """Derive current foster-home flows by origin and destination."""

    county_slug_by_name = build_county_name_to_slug(counties)

    current_placements = get_current_foster_home_placements(data)

    flow_counts, origin_totals = count_placement_flows(
        current_placements,
        county_slug_by_name,
    )

    flows = create_placement_flow_rows(
        flow_counts,
        origin_totals,
        county_slug_by_name,
    )

    validate_placement_flow_rows(
        flows,
        current_placements,
        counties,
    )

    return flows
