"""Integration tests for public aggregate output exports."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from scripts.export_outputs import (
    export_aggregate_outputs,
)
from scripts.etl.config import EXPECTED_COUNTY_ROWS
from scripts.etl.export_outputs import (
    COUNTY_SUMMARY_EXPORT_COLUMNS,
)
from scripts.etl.validate_outputs import (
    FORBIDDEN_PUBLIC_COLUMNS,
    validate_county_summary_csv,
    validate_public_database_privacy,
)


def read_export_rows(
    csv_path: Path,
) -> tuple[
    tuple[str, ...],
    list[dict[str, str]],
]:
    """Read exported county rows for integration assertions."""

    with csv_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        fieldnames = tuple(reader.fieldnames or ())

        rows = [
            {
                str(key): str(value)
                for key, value in row.items()
                if key is not None and value is not None
            }
            for row in reader
        ]

    return fieldnames, rows


def test_export_creates_valid_county_summary_csv(
    built_database_path: Path,
    tmp_path: Path,
) -> None:
    """Create one deterministic aggregate row per county."""

    csv_path = tmp_path / "county-summary.csv"

    result = export_aggregate_outputs(
        database_path=built_database_path,
        county_csv_path=csv_path,
    )

    assert result.output_path == csv_path.resolve()
    assert result.row_count == EXPECTED_COUNTY_ROWS
    assert len(result.sha256) == 64

    assert csv_path.is_file()
    assert csv_path.stat().st_size > 0

    fieldnames, rows = read_export_rows(csv_path)

    assert fieldnames == (COUNTY_SUMMARY_EXPORT_COLUMNS)

    assert len(rows) == EXPECTED_COUNTY_ROWS

    county_slugs = [row["county_slug"] for row in rows]

    assert len(county_slugs) == len(set(county_slugs))

    cook = next(row for row in rows if row["county_slug"] == "cook")

    assert cook["county_name"] == "Cook"
    assert cook["current_foster_homes"] == "156"
    assert cook["current_foster_placements"] == "1044"
    assert cook["reporting_cutoff"] == ("2026-07-01")
    assert cook["observation_start"] == ("2022-01-01")


def test_county_export_contains_no_source_identifier_columns(
    built_database_path: Path,
    tmp_path: Path,
) -> None:
    """Exclude child and provider identifiers from the CSV."""

    csv_path = tmp_path / "county-summary.csv"

    export_aggregate_outputs(
        database_path=built_database_path,
        county_csv_path=csv_path,
    )

    fieldnames, _ = read_export_rows(csv_path)

    actual_columns = {column.lower() for column in fieldnames}

    assert (actual_columns & FORBIDDEN_PUBLIC_COLUMNS) == set()


def test_county_export_is_deterministic(
    built_database_path: Path,
    tmp_path: Path,
) -> None:
    """Produce the same checksum from the same database."""

    first_result = export_aggregate_outputs(
        database_path=built_database_path,
        county_csv_path=(tmp_path / "first-county-summary.csv"),
    )

    second_result = export_aggregate_outputs(
        database_path=built_database_path,
        county_csv_path=(tmp_path / "second-county-summary.csv"),
    )

    assert first_result.row_count == second_result.row_count

    assert first_result.sha256 == second_result.sha256


def test_public_database_contains_only_aggregate_tables(
    built_database_path: Path,
) -> None:
    """Reject raw or unexpected tables in the serving database."""

    connection = sqlite3.connect(built_database_path)

    try:
        validate_public_database_privacy(connection)
    finally:
        connection.close()


def test_csv_validator_rejects_tampered_value(
    built_database_path: Path,
    database_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    """Reject an export that no longer matches SQLite."""

    csv_path = tmp_path / "county-summary.csv"

    export_aggregate_outputs(
        database_path=built_database_path,
        county_csv_path=csv_path,
    )

    fieldnames, rows = read_export_rows(csv_path)

    cook = next(row for row in rows if row["county_slug"] == "cook")

    cook["current_foster_homes"] = "999999"

    with csv_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(
        RuntimeError,
        match="does not match the aggregate database",
    ):
        validate_county_summary_csv(
            database_connection,
            csv_path,
        )


def test_export_rejects_missing_database(
    tmp_path: Path,
) -> None:
    """Fail before creating a CSV when SQLite is missing."""

    missing_database = tmp_path / "missing.db"

    csv_path = tmp_path / "county-summary.csv"

    with pytest.raises(
        FileNotFoundError,
        match="Aggregate SQLite database was not found",
    ):
        export_aggregate_outputs(
            database_path=missing_database,
            county_csv_path=csv_path,
        )

    assert not csv_path.exists()
