"""Integration tests for the aggregate SQLite schema."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from scripts.etl.config import DEFAULT_SCHEMA_PATH
from scripts.etl.validate_schema import (
    REQUIRED_COLUMNS,
    REQUIRED_FOREIGN_KEYS,
    REQUIRED_INDEXES,
    REQUIRED_TABLES,
    validate_database_schema,
)

from scripts.etl.validate_schema import ForeignKeyExpectation


@pytest.fixture
def schema_connection() -> Generator[
    sqlite3.Connection,
    None,
    None,
]:
    """Create an isolated in-memory database from the production schema."""

    schema_sql = DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")

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
    """Return non-internal SQLite schema-object names."""

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


def insert_county_summary(
    connection: sqlite3.Connection,
    *,
    county_slug: str = "example",
    county_name: str = "Example",
    children_currently_in_care: int = 0,
    current_kin_placements: int = 0,
    current_foster_placements: int = 0,
    current_nonfamily_placements: int = 0,
    local_foster_placements: int = 0,
    out_of_county_foster_placements: int = 0,
) -> None:
    """Insert a valid parent county row for schema tests."""

    connection.execute(
        """
        INSERT INTO county_summary (
            county_slug,
            county_name,
            children_currently_in_care,
            current_kin_placements,
            current_foster_placements,
            current_nonfamily_placements,
            current_foster_homes,
            children_per_current_home,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            median_observed_active_day_rate,
            renewals_within_90_days,
            renewals_without_recent_activity,
            recruitment_level,
            recruitment_signal_count,
            engagement_level,
            engagement_signal_count,
            primary_opportunity,
            limited_data
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            0, NULL, ?, ?, NULL,
            0, 0, 0, NULL, 0, 0,
            'limited', 0,
            'limited', 0,
            'review', 1
        )
        """,
        (
            county_slug,
            county_name,
            children_currently_in_care,
            current_kin_placements,
            current_foster_placements,
            current_nonfamily_placements,
            local_foster_placements,
            out_of_county_foster_placements,
        ),
    )


def test_schema_file_exists() -> None:
    """The version-controlled database schema must exist."""

    assert DEFAULT_SCHEMA_PATH.is_file()


def test_schema_creates_required_tables(
    schema_connection: sqlite3.Connection,
) -> None:
    """Create every required aggregate table."""

    tables = get_schema_object_names(
        schema_connection,
        "table",
    )

    assert REQUIRED_TABLES.issubset(tables)


def test_schema_creates_required_indexes(
    schema_connection: sqlite3.Connection,
) -> None:
    """Create indexes needed by aggregate queries."""

    indexes = get_schema_object_names(
        schema_connection,
        "index",
    )

    assert REQUIRED_INDEXES.issubset(indexes)


@pytest.mark.parametrize(
    ("table_name", "required_columns"),
    sorted(REQUIRED_COLUMNS.items()),
)
def test_schema_creates_required_columns(
    schema_connection: sqlite3.Connection,
    table_name: str,
    required_columns: frozenset[str],
) -> None:
    """Expose every required column on each aggregate table."""

    actual_columns = get_table_columns(
        schema_connection,
        table_name,
    )

    assert required_columns.issubset(actual_columns)


def test_schema_passes_application_validator(
    schema_connection: sqlite3.Connection,
) -> None:
    """Pass the same structural validation used by the builder."""

    validate_database_schema(schema_connection)


def test_foreign_keys_are_enabled(
    schema_connection: sqlite3.Connection,
) -> None:
    """Keep SQLite foreign-key enforcement active."""

    enabled = schema_connection.execute("PRAGMA foreign_keys").fetchone()

    assert enabled is not None
    assert enabled[0] == 1


@pytest.mark.parametrize(
    "expectation",
    REQUIRED_FOREIGN_KEYS,
)
def test_county_detail_foreign_keys_are_defined(
    schema_connection: sqlite3.Connection,
    expectation: ForeignKeyExpectation,
) -> None:
    """Reference county_summary with cascading deletion."""

    child_table = expectation.child_table
    child_column = expectation.child_column
    parent_table = expectation.parent_table
    parent_column = expectation.parent_column
    expected_on_delete = expectation.on_delete

    foreign_keys = schema_connection.execute(
        f"PRAGMA foreign_key_list({child_table})"
    ).fetchall()

    matching_relationships = [
        row
        for row in foreign_keys
        if (
            str(row[2]) == parent_table
            and str(row[3]) == child_column
            and str(row[4]) == parent_column
            and str(row[6]).upper() == expected_on_delete.upper()
        )
    ]

    assert len(matching_relationships) == 1


def test_database_passes_integrity_check(
    schema_connection: sqlite3.Connection,
) -> None:
    """Pass SQLite validation after schema creation."""

    result = schema_connection.execute("PRAGMA integrity_check").fetchone()

    assert result == ("ok",)


def test_count_constraint_rejects_negative_value(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject negative aggregate counts."""

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
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
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject rates outside the zero-to-one range."""

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
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


def test_age_alignment_requires_existing_county(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject age rows that reference a missing county."""

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data,
                recruitment_evidence,
                statewide_p75_threshold
            )
            VALUES (
                'missing-county',
                '0-5',
                10,
                5,
                2.0,
                0,
                0,
                2.5
            )
            """
        )


def test_age_alignment_rejects_invalid_age_band(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject age-band labels outside the configured categories."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data,
                recruitment_evidence,
                statewide_p75_threshold
            )
            VALUES (
                'example',
                '18-plus',
                10,
                5,
                2.0,
                0,
                0,
                2.5
            )
            """
        )


def test_unknown_age_rejects_numeric_preference_metrics(
    schema_connection: sqlite3.Connection,
) -> None:
    """Prevent unknown ages from being matched to preferences."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data,
                recruitment_evidence,
                statewide_p75_threshold
            )
            VALUES (
                'example',
                'unknown',
                1,
                2,
                0.5,
                1,
                0,
                NULL
            )
            """
        )


def test_known_age_with_zero_matching_homes_requires_null_ratio(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject a ratio when no preference-matching homes exist."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data,
                recruitment_evidence,
                statewide_p75_threshold
            )
            VALUES (
                'example',
                '0-5',
                10,
                0,
                2.0,
                1,
                0,
                NULL
            )
            """
        )


def test_recruitment_evidence_requires_eligible_metrics(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject evidence without a ratio and statewide threshold."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_age_alignment (
                county_slug,
                age_band,
                current_children,
                preference_matching_homes,
                children_per_matching_home,
                limited_data,
                recruitment_evidence,
                statewide_p75_threshold
            )
            VALUES (
                'example',
                '6-12',
                12,
                0,
                NULL,
                1,
                1,
                NULL
            )
            """
        )


def test_valid_age_alignment_row_is_accepted(
    schema_connection: sqlite3.Connection,
) -> None:
    """Accept a complete valid age-alignment record."""

    insert_county_summary(schema_connection)

    schema_connection.execute(
        """
        INSERT INTO county_age_alignment (
            county_slug,
            age_band,
            current_children,
            preference_matching_homes,
            children_per_matching_home,
            limited_data,
            recruitment_evidence,
            statewide_p75_threshold
        )
        VALUES (
            'example',
            '13-17',
            20,
            10,
            2.0,
            0,
            1,
            1.75
        )
        """
    )

    row = schema_connection.execute(
        """
        SELECT
            recruitment_evidence,
            statewide_p75_threshold
        FROM county_age_alignment
        WHERE county_slug = 'example'
          AND age_band = '13-17'
        """
    ).fetchone()

    assert row == (1, 1.75)


def test_deleting_county_cascades_to_age_alignment(
    schema_connection: sqlite3.Connection,
) -> None:
    """Delete county detail rows when their parent is removed."""

    insert_county_summary(schema_connection)

    schema_connection.execute(
        """
        INSERT INTO county_age_alignment (
            county_slug,
            age_band,
            current_children,
            preference_matching_homes,
            children_per_matching_home,
            limited_data,
            recruitment_evidence,
            statewide_p75_threshold
        )
        VALUES (
            'example',
            'unknown',
            1,
            0,
            NULL,
            1,
            0,
            NULL
        )
        """
    )

    schema_connection.execute(
        """
        DELETE FROM county_summary
        WHERE county_slug = 'example'
        """
    )

    remaining_rows = schema_connection.execute(
        """
        SELECT COUNT(*)
        FROM county_age_alignment
        WHERE county_slug = 'example'
        """
    ).fetchone()

    assert remaining_rows == (0,)


def test_placement_flow_table_contains_only_aggregate_fields(
    schema_connection: sqlite3.Connection,
) -> None:
    """Exclude child and provider identifiers from flow output."""

    columns = get_table_columns(
        schema_connection,
        "county_placement_flow",
    )

    assert columns == {
        "origin_county_slug",
        "destination_county_name",
        "placement_count",
        "placement_share",
        "is_local",
    }

    assert "id_child" not in columns
    assert "id_provider" not in columns


def test_placement_flow_rejects_invalid_share(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject placement shares outside zero through one."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_placement_flow (
                origin_county_slug,
                destination_county_name,
                placement_count,
                placement_share,
                is_local
            )
            VALUES (
                'example',
                'Example',
                1,
                1.25,
                1
            )
            """
        )


def test_investigation_question_table_is_aggregate_only(
    schema_connection: sqlite3.Connection,
) -> None:
    """Store only county, ordering, and question text."""

    columns = get_table_columns(
        schema_connection,
        "county_investigation_question",
    )

    assert columns == {
        "county_slug",
        "display_order",
        "question_text",
    }


def test_investigation_question_rejects_blank_text(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject empty deterministic questions."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_investigation_question (
                county_slug,
                display_order,
                question_text
            )
            VALUES (
                'example',
                1,
                '   '
            )
            """
        )


def test_investigation_question_rejects_order_above_five(
    schema_connection: sqlite3.Connection,
) -> None:
    """Limit county briefs to at most five questions."""

    insert_county_summary(schema_connection)

    with pytest.raises(sqlite3.IntegrityError):
        schema_connection.execute(
            """
            INSERT INTO county_investigation_question (
                county_slug,
                display_order,
                question_text
            )
            VALUES (
                'example',
                6,
                'What should staff investigate?'
            )
            """
        )


def test_county_rejects_unreconciled_placement_settings(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject county placement counts that do not sum to children."""

    with pytest.raises(sqlite3.IntegrityError):
        insert_county_summary(
            schema_connection,
            children_currently_in_care=1,
        )


def test_county_rejects_unreconciled_foster_locations(
    schema_connection: sqlite3.Connection,
) -> None:
    """Reject foster counts that do not reconcile by location."""

    with pytest.raises(sqlite3.IntegrityError):
        insert_county_summary(
            schema_connection,
            children_currently_in_care=1,
            current_foster_placements=1,
        )
