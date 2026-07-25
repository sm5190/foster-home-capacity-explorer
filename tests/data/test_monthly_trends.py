from scripts.etl.aggregate_counties import (
    derive_county_aggregates,
)
from scripts.etl.aggregate_monthly_trends import (
    build_trend_snapshot_dates,
    derive_county_monthly_trends,
)
from scripts.etl.config import (
    DEFAULT_RAW_DATA_DIR,
    REPORTING_CUTOFF_DATE,
    TREND_SNAPSHOT_COUNT,
)
from scripts.etl.load_sources import load_sources


def test_monthly_trends_have_complete_county_grid() -> None:
    data = load_sources(DEFAULT_RAW_DATA_DIR)
    counties = derive_county_aggregates(data)

    trends = derive_county_monthly_trends(
        data,
        counties,
    )

    assert len(build_trend_snapshot_dates()) == TREND_SNAPSHOT_COUNT
    assert len(trends) == len(counties) * TREND_SNAPSHOT_COUNT

    for county in counties:
        county_trends = [
            trend for trend in trends if trend.county_slug == county.county_slug
        ]

        assert len(county_trends) == TREND_SNAPSHOT_COUNT

        current = next(
            trend
            for trend in county_trends
            if trend.snapshot_date == REPORTING_CUTOFF_DATE
        )

        assert current.children_currently_in_care == county.children_currently_in_care

        assert current.current_foster_homes == county.current_foster_homes

        assert current.children_per_current_home == county.children_per_current_home
