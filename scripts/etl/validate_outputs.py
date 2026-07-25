"""Validate public aggregate database and export artifacts."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Final

from scripts.etl.export_outputs import (
    COUNTY_SUMMARY_EXPORT_COLUMNS,
    fetch_county_summary_export_rows,
)


ALLOWED_PUBLIC_TABLES: Final[frozenset[str]] = frozenset(
    {
        "metadata",
        "statewide_summary",
        "county_summary",
        "county_monthly_trend",
        "county_age_alignment",
        "county_placement_flow",
        "county_signal",
        "county_investigation_question",
    }
)
FORBIDDEN_PUBLIC_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "id_child",
        "child_id",
        "id_provider",
        "provider_id",
    }
)


def get_public_table_names(
    connection: sqlite3.Connection,
) -> set[str]:
    """Return non-internal SQLite table names."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()

    return {str(row[0]) for row in rows}


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    """Return lowercase column names for one table."""

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {str(row[1]).lower() for row in rows}


def validate_public_database_privacy(
    connection: sqlite3.Connection,
) -> None:
    """Ensure the serving database contains aggregates only."""

    actual_tables = get_public_table_names(connection)

    missing_tables = ALLOWED_PUBLIC_TABLES - actual_tables

    if missing_tables:
        raise RuntimeError(
            "Public database is missing required aggregate "
            f"tables: {sorted(missing_tables)}"
        )

    unexpected_tables = actual_tables - ALLOWED_PUBLIC_TABLES

    if unexpected_tables:
        raise RuntimeError(
            "Public database contains unexpected tables that "
            "may expose nonaggregate data: "
            f"{sorted(unexpected_tables)}"
        )

    for table_name in sorted(actual_tables):
        table_columns = get_table_columns(
            connection,
            table_name,
        )

        forbidden_columns = table_columns & FORBIDDEN_PUBLIC_COLUMNS

        if forbidden_columns:
            raise RuntimeError(
                f"Public table {table_name!r} contains "
                "forbidden source identifiers: "
                f"{sorted(forbidden_columns)}"
            )

    identifier_mentions = connection.execute(
        """
        SELECT
            county_slug,
            display_order
        FROM county_investigation_question
        WHERE
            LOWER(question_text) LIKE '%id_child%'
            OR LOWER(question_text) LIKE '%child_id%'
            OR LOWER(question_text) LIKE '%id_provider%'
            OR LOWER(question_text) LIKE '%provider_id%'
        """
    ).fetchall()

    if identifier_mentions:
        raise RuntimeError(
            "Investigation questions expose source identifier "
            f"terminology: {identifier_mentions}"
        )


def read_county_summary_csv(
    csv_path: Path,
) -> tuple[
    tuple[str, ...],
    tuple[dict[str, str], ...],
]:
    """Read the aggregate county CSV and preserve column order."""

    resolved_csv_path = csv_path.resolve()

    if not resolved_csv_path.is_file():
        raise FileNotFoundError(
            f"County-summary CSV was not found: {resolved_csv_path}"
        )

    if resolved_csv_path.stat().st_size == 0:
        raise RuntimeError(f"County-summary CSV is empty: {resolved_csv_path}")

    with resolved_csv_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        fieldnames = tuple(reader.fieldnames or ())

        rows: list[dict[str, str]] = []

        for raw_row in reader:
            if None in raw_row:
                raise RuntimeError(
                    "County-summary CSV contains values outside the declared header."
                )

            normalized_row: dict[str, str] = {}

            for column_name in fieldnames:
                value = raw_row.get(column_name)

                if value is None:
                    raise RuntimeError(
                        "County-summary CSV contains a row with "
                        f"a missing {column_name!r} column."
                    )

                normalized_row[column_name] = value

            rows.append(normalized_row)

    return fieldnames, tuple(rows)


def validate_county_summary_csv(
    connection: sqlite3.Connection,
    csv_path: Path,
) -> None:
    """Validate the CSV contract against the SQLite source."""

    actual_columns, actual_rows = read_county_summary_csv(csv_path)

    if actual_columns != COUNTY_SUMMARY_EXPORT_COLUMNS:
        raise RuntimeError(
            "County-summary CSV header does not match the "
            "locked public export contract. "
            f"Expected: {COUNTY_SUMMARY_EXPORT_COLUMNS}; "
            f"received: {actual_columns}."
        )

    forbidden_columns = {
        column.lower() for column in actual_columns
    } & FORBIDDEN_PUBLIC_COLUMNS

    if forbidden_columns:
        raise RuntimeError(
            "County-summary CSV contains forbidden source "
            f"identifier columns: {sorted(forbidden_columns)}"
        )

    expected_rows = fetch_county_summary_export_rows(connection)

    if len(actual_rows) != len(expected_rows):
        raise RuntimeError(
            "County-summary CSV row count does not match "
            "county_summary. "
            f"Expected: {len(expected_rows)}; "
            f"received: {len(actual_rows)}."
        )

    actual_slugs = [row["county_slug"] for row in actual_rows]

    if len(actual_slugs) != len(set(actual_slugs)):
        raise RuntimeError("County-summary CSV contains duplicate county slugs.")

    for row_index, (
        actual_row,
        expected_row,
    ) in enumerate(
        zip(
            actual_rows,
            expected_rows,
            strict=True,
        ),
        start=2,
    ):
        if actual_row != expected_row:
            raise RuntimeError(
                "County-summary CSV does not match the "
                "aggregate database at CSV row "
                f"{row_index}. "
                f"Expected: {expected_row}; "
                f"received: {actual_row}."
            )
