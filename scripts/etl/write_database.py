"""Write validated aggregate metrics into SQLite."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from pathlib import Path

from scripts.etl.config import (
    ANALYSIS_START_DATE,
    CHILD_FILE_NAME,
    PLACEMENT_FILE_NAME,
    PROVIDER_FILE_NAME,
    REPORTING_CUTOFF_DATE,
)
from scripts.etl.derive_snapshot import StatewideSnapshot
from scripts.etl.aggregate_counties import CountyAggregate

from scripts.etl.classify_opportunities import (
    ClassificationResult,
    CountySignal,
)


def calculate_sha256(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""

    if not path.is_file():
        raise FileNotFoundError(
            f"Cannot calculate checksum because the file does not exist: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def upsert_metadata(
    connection: sqlite3.Connection,
    metadata: Mapping[str, str],
) -> None:
    """Insert or update database metadata values."""

    connection.executemany(
        """
        INSERT INTO metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value
        """,
        sorted(metadata.items()),
    )


def insert_statewide_summary(
    connection: sqlite3.Connection,
    snapshot: StatewideSnapshot,
) -> None:
    """Insert the current statewide analytical snapshot."""

    connection.execute(
        """
        INSERT INTO statewide_summary (
            id,
            reporting_cutoff,
            observation_start,
            children_currently_in_care,
            current_kin_placements,
            current_foster_home_placements,
            current_nonfamily_placements,
            current_foster_homes,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            median_observed_active_day_rate
        )
        VALUES (
            1,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            REPORTING_CUTOFF_DATE.isoformat(),
            ANALYSIS_START_DATE.isoformat(),
            snapshot.children_currently_in_care,
            snapshot.current_kin_placements,
            snapshot.current_foster_home_placements,
            snapshot.current_nonfamily_placements,
            snapshot.current_foster_homes,
            snapshot.homes_with_current_placement,
            snapshot.homes_with_recent_activity,
            snapshot.homes_without_recent_activity,
            snapshot.local_foster_placements,
            snapshot.out_of_county_foster_placements,
            snapshot.local_placement_rate,
            snapshot.median_observed_active_day_rate,
        ),
    )


def record_source_metadata(
    connection: sqlite3.Connection,
    raw_data_dir: Path,
    snapshot: StatewideSnapshot,
) -> None:
    """Record source filenames, row counts, and checksums."""

    raw_data_dir = raw_data_dir.resolve()

    child_path = raw_data_dir / CHILD_FILE_NAME
    placement_path = raw_data_dir / PLACEMENT_FILE_NAME
    provider_path = raw_data_dir / PROVIDER_FILE_NAME

    metadata = {
        "source_child_filename": CHILD_FILE_NAME,
        "source_child_rows": str(snapshot.source_children),
        "source_child_sha256": calculate_sha256(child_path),
        "source_placement_filename": PLACEMENT_FILE_NAME,
        "source_placement_rows": str(snapshot.source_placements),
        "source_placement_sha256": calculate_sha256(placement_path),
        "source_provider_filename": PROVIDER_FILE_NAME,
        "source_provider_rows": str(snapshot.source_providers),
        "source_provider_sha256": calculate_sha256(provider_path),
    }

    upsert_metadata(connection, metadata)


def insert_county_summaries(
    connection: sqlite3.Connection,
    counties: tuple[CountyAggregate, ...],
) -> None:
    """Insert all county-level aggregate rows."""

    connection.executemany(
        """
        INSERT INTO county_summary (
            county_slug,
            county_name,
            children_currently_in_care,
            current_foster_homes,
            children_per_current_home,
            current_foster_placements,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            median_observed_active_day_rate,
            renewals_within_90_days,
            recruitment_level,
            recruitment_signal_count,
            engagement_level,
            engagement_signal_count,
            primary_opportunity,
            limited_data
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                county.county_slug,
                county.county_name,
                county.children_currently_in_care,
                county.current_foster_homes,
                county.children_per_current_home,
                county.current_foster_placements,
                county.local_foster_placements,
                county.out_of_county_foster_placements,
                county.local_placement_rate,
                county.homes_with_current_placement,
                county.homes_with_recent_activity,
                county.homes_without_recent_activity,
                county.median_observed_active_day_rate,
                county.renewals_within_90_days,
                county.recruitment_level,
                county.recruitment_signal_count,
                county.engagement_level,
                county.engagement_signal_count,
                county.primary_opportunity,
                int(county.limited_data),
            )
            for county in counties
        ],
    )


def insert_county_signals(
    connection: sqlite3.Connection,
    signals: tuple[CountySignal, ...],
) -> None:
    """Insert the evidence supporting county classifications."""

    connection.executemany(
        """
        INSERT INTO county_signal (
            county_slug,
            focus,
            signal_code,
            signal_value,
            threshold_value
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                signal.county_slug,
                signal.focus,
                signal.signal_code,
                signal.signal_value,
                signal.threshold_value,
            )
            for signal in signals
        ],
    )


def record_classification_metadata(
    connection: sqlite3.Connection,
    classification: ClassificationResult,
) -> None:
    """Record thresholds and percentile methodology."""

    upsert_metadata(
        connection,
        classification.metadata(),
    )
