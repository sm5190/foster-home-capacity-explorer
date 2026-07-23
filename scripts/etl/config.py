from datetime import date

ANALYSIS_START_DATE = date(2022, 1, 1)
REPORTING_CUTOFF_DATE = date(2026, 7, 1)

RECENT_ACTIVITY_DAYS = 90
RENEWAL_WINDOW_DAYS = 90
MIN_PLACEMENTS_FOR_RANKING = 20

AGE_BANDS: dict[str, tuple[int, int]] = {
    "0-5": (0, 5),
    "6-12": (6, 12),
    "13-17": (13, 17),
}
