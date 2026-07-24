"""Shared configuration for analytical data processing."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final, TypeAlias


AgeBandRange: TypeAlias = tuple[int, int] | None


# Repository paths
PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]

DEFAULT_RAW_DATA_DIR: Final = PROJECT_ROOT / "data" / "raw"
DEFAULT_GENERATED_DATA_DIR: Final = PROJECT_ROOT / "data" / "generated"

DEFAULT_SCHEMA_PATH: Final = PROJECT_ROOT / "db" / "schema.sql"
DEFAULT_DATABASE_PATH: Final = DEFAULT_GENERATED_DATA_DIR / "foster_capacity.db"

DEFAULT_COUNTY_EXPORT_PATH: Final = DEFAULT_GENERATED_DATA_DIR / "county-summary.csv"
DEFAULT_METADATA_EXPORT_PATH: Final = DEFAULT_GENERATED_DATA_DIR / "metadata.json"


# Database build configuration
SCHEMA_VERSION: Final = "1.2"
EXPECTED_COUNTY_ROWS: Final = 103


# Analytical reporting period
ANALYSIS_START_DATE: Final = date(2022, 1, 1)
REPORTING_CUTOFF_DATE: Final = date(2026, 7, 1)


# Provider engagement windows
RECENT_ACTIVITY_DAYS: Final = 90
RENEWAL_WINDOW_DAYS: Final = 90


# Source files
CHILD_FILE_NAME: Final = "child_level.csv"
PLACEMENT_FILE_NAME: Final = "placement_level.csv"
PROVIDER_FILE_NAME: Final = "provider_level_updated.csv"


# Shared analytical guardrails
SMALL_PERCENTAGE_DENOMINATOR: Final = 20
MINIMUM_ENGAGEMENT_HOMES: Final = 10


# Age-preference alignment
AGE_SIGNAL_MINIMUM_CHILDREN: Final = 10
AGE_RECRUITMENT_PERCENTILE: Final = 0.75

AGE_BANDS: Final[dict[str, AgeBandRange]] = {
    "0-5": (0, 5),
    "6-12": (6, 12),
    "13-17": (13, 17),
    "unknown": None,
}

KNOWN_AGE_BANDS: Final[tuple[str, ...]] = (
    "0-5",
    "6-12",
    "13-17",
)

ALL_AGE_BANDS: Final[tuple[str, ...]] = tuple(AGE_BANDS)
