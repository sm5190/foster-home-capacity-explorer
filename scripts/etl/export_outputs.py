"""Export deterministic public aggregate artifacts."""

from __future__ import annotations

import csv
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final
import json
from contextlib import closing


COUNTY_SUMMARY_EXPORT_COLUMNS: Final[tuple[str, ...]] = (
    "reporting_cutoff",
    "observation_start",
    "county_slug",
    "county_name",
    "primary_opportunity",
    "recruitment_level",
    "recruitment_signal_count",
    "engagement_level",
    "engagement_signal_count",
    "limited_data",
    "children_currently_in_care",
    "current_kin_placements",
    "current_foster_placements",
    "current_nonfamily_placements",
    "current_foster_homes",
    "children_per_current_home",
    "local_foster_placements",
    "out_of_county_foster_placements",
    "local_placement_rate",
    "homes_with_current_placement",
    "homes_with_recent_activity",
    "homes_without_recent_activity",
    "median_observed_active_day_rate",
    "renewals_within_90_days",
    "renewals_without_recent_activity",
)

COUNTY_SUMMARY_EXPORT_QUERY: Final = """
    SELECT
        statewide.reporting_cutoff,
        statewide.observation_start,
        county.county_slug,
        county.county_name,
        county.primary_opportunity,
        county.recruitment_level,
        county.recruitment_signal_count,
        county.engagement_level,
        county.engagement_signal_count,
        county.limited_data,
        county.children_currently_in_care,
        county.current_kin_placements,
        county.current_foster_placements,
        county.current_nonfamily_placements,
        county.current_foster_homes,
        county.children_per_current_home,
        county.local_foster_placements,
        county.out_of_county_foster_placements,
        county.local_placement_rate,
        county.homes_with_current_placement,
        county.homes_with_recent_activity,
        county.homes_without_recent_activity,
        county.median_observed_active_day_rate,
        county.renewals_within_90_days
        county.renewals_without_recent_activity
    FROM county_summary AS county
    CROSS JOIN statewide_summary AS statewide
    WHERE statewide.id = 1
    ORDER BY
        county.county_name COLLATE NOCASE,
        county.county_slug
"""


@dataclass(frozen=True, slots=True)
class CountySummaryExportResult:
    """Describe one completed county-summary CSV export."""

    output_path: Path
    row_count: int
    sha256: str


@dataclass(frozen=True, slots=True)
class MetadataExportResult:
    """Describe one completed metadata JSON export."""

    output_path: Path
    sha256: str


REQUIRED_METADATA_EXPORT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "reporting_cutoff",
        "observation_start",
        "built_at_utc",
        "git_commit_sha",
        "build_status",
        "source_child_filename",
        "source_child_rows",
        "source_child_sha256",
        "source_placement_filename",
        "source_placement_rows",
        "source_placement_sha256",
        "source_provider_filename",
        "source_provider_rows",
        "source_provider_sha256",
    }
)


def write_metadata_json(
    *,
    database_path: Path,
    county_export: CountySummaryExportResult,
    output_path: Path,
) -> MetadataExportResult:
    """Write reproducibility metadata for the public artifacts."""

    resolved_database_path = database_path.resolve()
    resolved_output_path = output_path.resolve()

    if not resolved_database_path.is_file():
        raise FileNotFoundError(
            "Cannot create metadata because the database does "
            f"not exist: {resolved_database_path}"
        )

    database_uri = f"{resolved_database_path.as_uri()}?mode=ro&immutable=1"

    with closing(
        sqlite3.connect(
            database_uri,
            uri=True,
        )
    ) as connection:
        metadata = {
            str(key): str(value)
            for key, value in connection.execute(
                """
                SELECT key, value
                FROM metadata
                ORDER BY key
                """
            ).fetchall()
        }

    missing_keys = REQUIRED_METADATA_EXPORT_KEYS - set(metadata)

    if missing_keys:
        raise RuntimeError(
            "Cannot create metadata JSON because required "
            f"database metadata is missing: {sorted(missing_keys)}"
        )

    payload = {
        "schema_version": metadata["schema_version"],
        "reporting_cutoff": metadata["reporting_cutoff"],
        "observation_start": metadata["observation_start"],
        "built_at_utc": metadata["built_at_utc"],
        "git_commit_sha": metadata["git_commit_sha"],
        "build_status": metadata["build_status"],
        "sources": {
            "child": {
                "filename": metadata["source_child_filename"],
                "rows": int(metadata["source_child_rows"]),
                "sha256": metadata["source_child_sha256"],
            },
            "placement": {
                "filename": metadata["source_placement_filename"],
                "rows": int(metadata["source_placement_rows"]),
                "sha256": metadata["source_placement_sha256"],
            },
            "provider": {
                "filename": metadata["source_provider_filename"],
                "rows": int(metadata["source_provider_rows"]),
                "sha256": metadata["source_provider_sha256"],
            },
        },
        "database": {
            "filename": resolved_database_path.name,
            "sha256": calculate_file_sha256(resolved_database_path),
        },
        "county_export": {
            "filename": county_export.output_path.name,
            "row_count": county_export.row_count,
            "sha256": county_export.sha256,
        },
    }

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resolved_output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return MetadataExportResult(
        output_path=resolved_output_path,
        sha256=calculate_file_sha256(resolved_output_path),
    )


def serialize_csv_value(value: object) -> str:
    """Convert a SQLite value into deterministic CSV text."""

    if value is None:
        return ""

    if isinstance(value, float):
        return format(value, ".17g")

    return str(value)


def calculate_file_sha256(path: Path) -> str:
    """Return the SHA-256 checksum of an exported file."""

    if not path.is_file():
        raise FileNotFoundError(f"Cannot checksum missing output file: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def fetch_county_summary_export_rows(
    connection: sqlite3.Connection,
) -> tuple[dict[str, str], ...]:
    """Return deterministic public county-summary rows."""

    cursor = connection.execute(COUNTY_SUMMARY_EXPORT_QUERY)

    description = cursor.description or ()

    actual_columns = tuple(str(column[0]) for column in description)

    if actual_columns != COUNTY_SUMMARY_EXPORT_COLUMNS:
        raise RuntimeError(
            "County-summary export query does not match the "
            "locked CSV contract. "
            f"Expected: {COUNTY_SUMMARY_EXPORT_COLUMNS}; "
            f"received: {actual_columns}."
        )

    exported_rows: list[dict[str, str]] = []

    for database_row in cursor.fetchall():
        if len(database_row) != len(COUNTY_SUMMARY_EXPORT_COLUMNS):
            raise RuntimeError(
                "County-summary export query returned an unexpected number of values."
            )

        exported_rows.append(
            {
                column_name: serialize_csv_value(value)
                for column_name, value in zip(
                    COUNTY_SUMMARY_EXPORT_COLUMNS,
                    database_row,
                    strict=True,
                )
            }
        )

    return tuple(exported_rows)


def write_county_summary_csv(
    connection: sqlite3.Connection,
    output_path: Path,
) -> CountySummaryExportResult:
    """Write the deterministic aggregate county-summary CSV."""

    resolved_output_path = output_path.resolve()

    rows = fetch_county_summary_export_rows(connection)

    if not rows:
        raise RuntimeError(
            "County-summary CSV cannot be exported because "
            "county_summary contains no rows."
        )

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with resolved_output_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=COUNTY_SUMMARY_EXPORT_COLUMNS,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    return CountySummaryExportResult(
        output_path=resolved_output_path,
        row_count=len(rows),
        sha256=calculate_file_sha256(resolved_output_path),
    )
