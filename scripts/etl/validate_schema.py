"""Validate the aggregate SQLite schema and database integrity."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ForeignKeyExpectation:
    """Describe one required SQLite foreign-key relationship."""

    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    on_delete: str = "CASCADE"


REQUIRED_TABLES: Final[frozenset[str]] = frozenset(
    {
        "metadata",
        "statewide_summary",
        "county_summary",
        "county_age_alignment",
        "county_placement_flow",
        "county_signal",
        "county_investigation_question",
    }
)

REQUIRED_INDEXES: Final[frozenset[str]] = frozenset(
    {
        "idx_county_recruitment_priority",
        "idx_county_engagement_priority",
        "idx_county_flow_origin_count",
        "idx_county_age_band",
    }
)

REQUIRED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "metadata": frozenset(
        {
            "key",
            "value",
        }
    ),
    "statewide_summary": frozenset(
        {
            "id",
            "reporting_cutoff",
            "observation_start",
            "children_currently_in_care",
            "current_kin_placements",
            "current_foster_home_placements",
            "current_nonfamily_placements",
            "current_foster_homes",
            "homes_with_current_placement",
            "homes_with_recent_activity",
            "homes_without_recent_activity",
            "local_foster_placements",
            "out_of_county_foster_placements",
            "local_placement_rate",
            "median_observed_active_day_rate",
        }
    ),
    "county_summary": frozenset(
        {
            "county_slug",
            "county_name",
            "children_currently_in_care",
            "current_foster_homes",
            "children_per_current_home",
            "current_foster_placements",
            "local_foster_placements",
            "out_of_county_foster_placements",
            "local_placement_rate",
            "homes_with_current_placement",
            "homes_with_recent_activity",
            "homes_without_recent_activity",
            "median_observed_active_day_rate",
            "renewals_within_90_days",
            "recruitment_level",
            "recruitment_signal_count",
            "engagement_level",
            "engagement_signal_count",
            "primary_opportunity",
            "limited_data",
            "current_kin_placements",
            "current_nonfamily_placements",
        }
    ),
    "county_age_alignment": frozenset(
        {
            "county_slug",
            "age_band",
            "current_children",
            "preference_matching_homes",
            "children_per_matching_home",
            "limited_data",
            "recruitment_evidence",
            "statewide_p75_threshold",
        }
    ),
    "county_placement_flow": frozenset(
        {
            "origin_county_slug",
            "destination_county_name",
            "placement_count",
            "placement_share",
            "is_local",
        }
    ),
    "county_signal": frozenset(
        {
            "county_slug",
            "focus",
            "signal_code",
            "signal_value",
            "threshold_value",
        }
    ),
    "county_investigation_question": frozenset(
        {
            "county_slug",
            "display_order",
            "question_text",
        }
    ),
}

REQUIRED_FOREIGN_KEYS: Final[tuple[ForeignKeyExpectation, ...]] = (
    ForeignKeyExpectation(
        child_table="county_age_alignment",
        child_column="county_slug",
        parent_table="county_summary",
        parent_column="county_slug",
    ),
    ForeignKeyExpectation(
        child_table="county_placement_flow",
        child_column="origin_county_slug",
        parent_table="county_summary",
        parent_column="county_slug",
    ),
    ForeignKeyExpectation(
        child_table="county_signal",
        child_column="county_slug",
        parent_table="county_summary",
        parent_column="county_slug",
    ),
    ForeignKeyExpectation(
        child_table="county_investigation_question",
        child_column="county_slug",
        parent_table="county_summary",
        parent_column="county_slug",
    ),
)


def get_schema_object_names(
    connection: sqlite3.Connection,
    object_type: str,
) -> set[str]:
    """Return non-internal SQLite objects of the requested type."""

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


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    """Return the column names for one SQLite table."""

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {str(row[1]) for row in rows}


def get_foreign_keys(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[sqlite3.Row | tuple[object, ...]]:
    """Return the foreign-key definitions for one table."""

    return list(connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall())


def validate_foreign_key_enforcement(
    connection: sqlite3.Connection,
) -> None:
    """Verify foreign-key enforcement is enabled."""

    row = connection.execute("PRAGMA foreign_keys").fetchone()

    if row is None or int(row[0]) != 1:
        raise RuntimeError("SQLite foreign-key enforcement must be enabled.")


def validate_required_tables(
    connection: sqlite3.Connection,
) -> None:
    """Verify all required aggregate tables exist."""

    actual_tables = get_schema_object_names(
        connection,
        "table",
    )

    missing_tables = REQUIRED_TABLES - actual_tables

    if missing_tables:
        missing = ", ".join(sorted(missing_tables))

        raise RuntimeError(f"Required tables are missing: {missing}")


def validate_required_indexes(
    connection: sqlite3.Connection,
) -> None:
    """Verify indexes required by aggregate queries exist."""

    actual_indexes = get_schema_object_names(
        connection,
        "index",
    )

    missing_indexes = REQUIRED_INDEXES - actual_indexes

    if missing_indexes:
        missing = ", ".join(sorted(missing_indexes))

        raise RuntimeError(f"Required indexes are missing: {missing}")


def validate_required_columns(
    connection: sqlite3.Connection,
) -> None:
    """Verify required tables expose their expected columns."""

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        actual_columns = get_table_columns(
            connection,
            table_name,
        )

        missing_columns = required_columns - actual_columns

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))

            raise RuntimeError(
                f"Table {table_name!r} is missing required columns: {missing}"
            )


def validate_foreign_key_reference(
    connection: sqlite3.Connection,
    expectation: ForeignKeyExpectation,
) -> None:
    """Verify one required foreign-key relationship exists."""

    foreign_keys = get_foreign_keys(
        connection,
        expectation.child_table,
    )

    relationship_exists = any(
        str(row[2]) == expectation.parent_table
        and str(row[3]) == expectation.child_column
        and str(row[4]) == expectation.parent_column
        and str(row[6]).upper() == expectation.on_delete.upper()
        for row in foreign_keys
    )

    if relationship_exists:
        return

    raise RuntimeError(
        f"Table {expectation.child_table!r} must define "
        f"FOREIGN KEY ({expectation.child_column}) REFERENCES "
        f"{expectation.parent_table}"
        f"({expectation.parent_column}) "
        f"ON DELETE {expectation.on_delete}. "
        f"Current foreign keys: {foreign_keys}"
    )


def validate_county_detail_foreign_keys(
    connection: sqlite3.Connection,
) -> None:
    """Verify county-detail tables reference county_summary."""

    for expectation in REQUIRED_FOREIGN_KEYS:
        validate_foreign_key_reference(
            connection,
            expectation,
        )


def validate_database_integrity(
    connection: sqlite3.Connection,
) -> None:
    """Run SQLite integrity and foreign-key checks."""

    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()

    if integrity_result is None or str(integrity_result[0]).lower() != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")

    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()

    if foreign_key_violations:
        raise RuntimeError(
            f"SQLite foreign-key validation failed: {foreign_key_violations}"
        )


def validate_database_schema(
    connection: sqlite3.Connection,
) -> None:
    """Validate tables, columns, indexes, and relationships."""

    validate_foreign_key_enforcement(connection)
    validate_required_tables(connection)
    validate_required_indexes(connection)
    validate_required_columns(connection)
    validate_county_detail_foreign_keys(connection)


def validate_database(
    connection: sqlite3.Connection,
) -> None:
    """Validate both database structure and integrity."""

    validate_database_schema(connection)
    validate_database_integrity(connection)
