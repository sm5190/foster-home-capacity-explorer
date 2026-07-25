from scripts.etl.aggregate_counties import (
    derive_county_aggregates,
)
from scripts.etl.config import DEFAULT_RAW_DATA_DIR
from scripts.etl.derive_snapshot import (
    derive_statewide_snapshot,
)
from scripts.etl.load_sources import load_sources


def test_retention_intersection_reconciles() -> None:
    data = load_sources(DEFAULT_RAW_DATA_DIR)

    statewide = derive_statewide_snapshot(data)
    counties = derive_county_aggregates(data)

    assert (
        sum(county.renewals_within_90_days for county in counties)
        == statewide.renewals_within_90_days
    )

    assert (
        sum(county.renewals_without_recent_activity for county in counties)
        == statewide.renewals_without_recent_activity
    )

    for county in counties:
        assert county.renewals_without_recent_activity <= county.renewals_within_90_days

        assert (
            county.renewals_without_recent_activity
            <= county.homes_without_recent_activity
        )
