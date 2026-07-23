"""Integration tests for the aggregate SQLite schema."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"

EXPECTED_TABLES = {
    "metadata",
    "statewide_summary",
    "county_summary",
    "county_age_alignment",
    "county_placement_flow",
    "county_signal",
    "county_investigation_question",
}

EXPECTED_INDEXES = {
    "idx_county_recruitment_priority",
    "idx_county_engagement_priority",
    "idx_county_flow_origin_count",
    "idx_county_age_band",
}


@pytest.fixture
def database_connection() -> Generator[sqlite3.Connection, None, None]:
    """Create an isolated in-memory database from the production schema."""

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema_sql)

    try:
        yield connection
    finally:
        connection.close()


def get_schema_object_names(
    connection: sqlite3.Connection,
    object_type: str,
) -> set[str]:
    """Return non-internal SQLite schema objects of the requested type."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = ?
          AND name NOT LIKE 'sqlite_%'
        """,
        (object_type,),
    ).fetchall()

    return {str(row[0]) for row in rows}


def test_schema_file_exists() -> None:
    """The version-controlled database schema must exist."""

    assert SCHEMA_PATH.is_file()


def test_schema_creates_expected_tables(
    database_connection: sqlite3.Connection,
) -> None:
    """The schema must create every required aggregate table."""

    tables = get_schema_object_names(database_connection, "table")

    assert EXPECTED_TABLES.issubset(tables)


def test_schema_creates_expected_indexes(
    database_connection: sqlite3.Connection,
) -> None:
    """The schema must create indexes needed by application queries."""

    indexes = get_schema_object_names(database_connection, "index")

    assert EXPECTED_INDEXES.issubset(indexes)


def test_foreign_keys_are_enabled(
    database_connection: sqlite3.Connection,
) -> None:
    """Foreign-key enforcement must be active."""

    enabled = database_connection.execute("PRAGMA foreign_keys").fetchone()

    assert enabled is not None
    assert enabled[0] == 1


def test_database_passes_integrity_check(
    database_connection: sqlite3.Connection,
) -> None:
    """A database created from the schema must pass SQLite validation."""

    result = database_connection.execute("PRAGMA integrity_check").fetchone()

    assert result == ("ok",)


def test_count_constraint_rejects_negative_value(
    database_connection: sqlite3.Connection,
) -> None:
    """Nonnegative-count constraints must reject invalid records."""

    with pytest.raises(sqlite3.IntegrityError):
        database_connection.execute(
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
                '2026-07-01',
                '2022-01-01',
                -1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                NULL,
                NULL
            )
            """
        )


def test_rate_constraint_rejects_value_above_one(
    database_connection: sqlite3.Connection,
) -> None:
    """Rate constraints must reject values outside the zero-to-one range."""

    with pytest.raises(sqlite3.IntegrityError):
        database_connection.execute(
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
                '2026-07-01',
                '2022-01-01',
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                1.25,
                NULL
            )
            """
        )


def test_child_table_requires_existing_county(
    database_connection: sqlite3.Connection,
) -> None:
    """County-detail records must reference an existing county summary."""

    with pytest.raises(sqlite3.IntegrityError):
        database_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data
            )
            VALUES (
                'missing-county',
                '0-5',
                10,
                5,
                2.0,
                0
            )
            """
        )
