"""Shared configuration for analytical data processing."""

from datetime import date
from pathlib import Path
from typing import Final


PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DATA_DIR: Final = PROJECT_ROOT / "data" / "raw"

ANALYSIS_START_DATE: Final = date(2022, 1, 1)
REPORTING_CUTOFF_DATE: Final = date(2026, 7, 1)

RECENT_ACTIVITY_DAYS: Final = 90
RENEWAL_WINDOW_DAYS: Final = 90

CHILD_FILE_NAME: Final = "child_level.csv"
PLACEMENT_FILE_NAME: Final = "placement_level.csv"
PROVIDER_FILE_NAME: Final = "provider_level_updated.csv"

AGE_BANDS: Final[dict[str, tuple[int, int]]] = {
    "0-5": (0, 5),
    "6-12": (6, 12),
    "13-17": (13, 17),
}
