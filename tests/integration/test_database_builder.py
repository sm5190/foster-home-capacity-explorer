"""Integration tests for aggregate database generation."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from scripts.build_database import (
    REQUIRED_INDEXES,
    REQUIRED_TABLES,
    SCHEMA_VERSION,
    build_database,
)
from scripts.etl.config import DEFAULT_RAW_DATA_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"


def file_checksum(path: Path) -> str:
    """Return a SHA-256 checksum for a file."""

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(8192),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def get_object_names(
    connection: sqlite3.Connection,
    object_type: str,
) -> set[str]:
    """Return SQLite schema-object names."""

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


def test_builder_creates_valid_database(
    tmp_path: Path,
) -> None:
    """The builder must produce a valid database."""

    database_path = tmp_path / "foster_capacity.db"

    result = build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    assert result == database_path.resolve()
    assert database_path.is_file()
    assert database_path.stat().st_size > 0

    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)

        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

        tables = get_object_names(
            connection,
            "table",
        )
        indexes = get_object_names(
            connection,
            "index",
        )

        assert REQUIRED_TABLES.issubset(tables)
        assert REQUIRED_INDEXES.issubset(indexes)


def test_builder_inserts_required_metadata(
    tmp_path: Path,
) -> None:
    """The database must identify its sources and build."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        metadata = dict(
            connection.execute(
                """
                SELECT key, value
                FROM metadata
                """
            ).fetchall()
        )

    assert metadata["schema_version"] == SCHEMA_VERSION
    assert metadata["reporting_cutoff"] == "2026-07-01"
    assert metadata["observation_start"] == "2022-01-01"
    assert metadata["build_status"] == "complete"

    assert metadata["source_child_rows"] == "16139"
    assert metadata["source_placement_rows"] == "51994"
    assert metadata["source_provider_rows"] == "6063"

    assert len(metadata["source_child_sha256"]) == 64
    assert len(metadata["source_placement_sha256"]) == 64
    assert len(metadata["source_provider_sha256"]) == 64
    assert metadata["county_summary_rows"] == "103"

    assert metadata["built_at_utc"]
    assert metadata["git_commit_sha"]

    assert metadata["county_signal_rows"] == "117"

    assert metadata["percentile_method"] == ("linear_interpolation_position_(n-1)*p")

    assert metadata["eligible_children_per_current_home_count"] == "103"

    assert metadata["eligible_out_of_county_foster_rate_count"] == "31"

    assert metadata["eligible_engagement_count"] == "103"


def test_builder_populates_statewide_summary(
    tmp_path: Path,
) -> None:
    """The statewide table must match locked baselines."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT *
            FROM statewide_summary
            WHERE id = 1
            """
        ).fetchone()

    assert row is not None

    assert row["children_currently_in_care"] == 8_071
    assert row["current_kin_placements"] == 3_688
    assert row["current_foster_home_placements"] == 4_343
    assert row["current_nonfamily_placements"] == 40

    assert row["current_foster_homes"] == 3_395
    assert row["homes_with_current_placement"] == 2_733
    assert row["homes_with_recent_activity"] == 3_170
    assert row["homes_without_recent_activity"] == 225

    assert row["local_foster_placements"] == 1_519
    assert row["out_of_county_foster_placements"] == 2_824

    assert row["local_placement_rate"] == pytest.approx(1_519 / 4_343)

    assert row["median_observed_active_day_rate"] == pytest.approx(0.6967113276492083)


def test_rebuild_replaces_existing_database(
    tmp_path: Path,
) -> None:
    """Rebuilding must replace stale database contents."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            INSERT INTO metadata (key, value)
            VALUES ('stale_test_value', 'remove-me')
            """
        )
        connection.commit()
    finally:
        connection.close()

    # No SQLite connection is open when replacement begins.
    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        stale_record = connection.execute(
            """
            SELECT value
            FROM metadata
            WHERE key = 'stale_test_value'
            """
        ).fetchone()

    assert stale_record is None


def test_failed_build_preserves_existing_database(
    tmp_path: Path,
) -> None:
    """A failed build must preserve the valid artifact."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    original_checksum = file_checksum(database_path)

    invalid_schema_path = tmp_path / "invalid_schema.sql"
    invalid_schema_path.write_text(
        "CREATE TABLE incomplete (",
        encoding="utf-8",
    )

    with pytest.raises(sqlite3.Error):
        build_database(
            schema_path=invalid_schema_path,
            output_path=database_path,
            raw_data_dir=DEFAULT_RAW_DATA_DIR,
        )

    assert database_path.is_file()
    assert file_checksum(database_path) == original_checksum


def test_builder_populates_county_summary(
    tmp_path: Path,
) -> None:
    """County rows must be inserted and reconcile statewide."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row

        county_count = connection.execute(
            """
            SELECT COUNT(*) AS county_count
            FROM county_summary
            """
        ).fetchone()

        totals = connection.execute(
            """
            SELECT
                SUM(children_currently_in_care)
                    AS children,
                SUM(current_foster_homes)
                    AS homes,
                SUM(current_foster_placements)
                    AS foster_placements,
                SUM(local_foster_placements)
                    AS local_placements,
                SUM(
                    out_of_county_foster_placements
                ) AS out_of_county_placements,
                SUM(homes_with_recent_activity)
                    AS recent_homes
            FROM county_summary
            """
        ).fetchone()

        cook = connection.execute(
            """
            SELECT *
            FROM county_summary
            WHERE county_slug = 'cook'
            """
        ).fetchone()

    assert county_count is not None
    assert county_count[0] == 103

    assert totals is not None
    assert totals["children"] == 8_071
    assert totals["homes"] == 3_395
    assert totals["foster_placements"] == 4_343
    assert totals["local_placements"] == 1_519
    assert totals["out_of_county_placements"] == 2_824
    assert totals["recent_homes"] == 3_170

    assert cook is not None
    assert cook["county_name"] == "Cook"
    assert cook["current_foster_homes"] == 156
    assert cook["current_foster_placements"] == 1_044


def test_builder_populates_classifications_and_signals(
    tmp_path: Path,
) -> None:
    """The database must store categories and evidence."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row

        signal_count = connection.execute(
            """
            SELECT COUNT(*) AS signal_count
            FROM county_signal
            """
        ).fetchone()

        cook = connection.execute(
            """
            SELECT
                recruitment_level,
                recruitment_signal_count,
                engagement_level,
                engagement_signal_count,
                primary_opportunity
            FROM county_summary
            WHERE county_slug = 'cook'
            """
        ).fetchone()

        cook_signals = connection.execute(
            """
            SELECT signal_code
            FROM county_signal
            WHERE county_slug = 'cook'
            ORDER BY signal_code
            """
        ).fetchall()

        level_counts = connection.execute(
            """
            SELECT
                recruitment_level,
                COUNT(*) AS county_count
            FROM county_summary
            GROUP BY recruitment_level
            """
        ).fetchall()

    assert signal_count is not None
    assert signal_count["signal_count"] == 117

    assert cook is not None
    assert cook["recruitment_level"] == "higher"
    assert cook["recruitment_signal_count"] == 2
    assert cook["engagement_level"] == "possible"
    assert cook["engagement_signal_count"] == 1
    assert cook["primary_opportunity"] == "recruitment"

    assert {row["signal_code"] for row in cook_signals} == {
        "high_children_per_current_home",
        "high_out_of_county_foster_rate",
        "low_median_observed_active_day_rate",
    }

    assert {row["recruitment_level"]: row["county_count"] for row in level_counts} == {
        "limited": 72,
        "possible": 21,
        "higher": 6,
        "review": 4,
    }
