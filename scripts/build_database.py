"""Create the immutable aggregate SQLite database."""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from scripts.etl.aggregate_counties import derive_county_aggregates
from scripts.etl.classify_opportunities import (
    CountySignal,
    classify_counties,
)
from scripts.etl.config import DEFAULT_RAW_DATA_DIR
from scripts.etl.derive_snapshot import derive_statewide_snapshot
from scripts.etl.load_sources import load_sources
from scripts.etl.write_database import (
    insert_county_signals,
    insert_county_summaries,
    insert_statewide_summary,
    record_classification_metadata,
    record_source_metadata,
    upsert_metadata,
)


PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]

DEFAULT_SCHEMA_PATH: Final = PROJECT_ROOT / "db" / "schema.sql"

DEFAULT_DATABASE_PATH: Final = (
    PROJECT_ROOT / "data" / "generated" / "foster_capacity.db"
)

SCHEMA_VERSION: Final = "1.1"

EXPECTED_COUNTY_ROWS: Final = 103

REQUIRED_TABLES: Final = {
    "metadata",
    "statewide_summary",
    "county_summary",
    "county_age_alignment",
    "county_placement_flow",
    "county_signal",
    "county_investigation_question",
}

REQUIRED_INDEXES: Final = {
    "idx_county_recruitment_priority",
    "idx_county_engagement_priority",
    "idx_county_flow_origin_count",
    "idx_county_age_band",
}

REQUIRED_METADATA_KEYS: Final = {
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
    "county_summary_rows",
    "county_signal_rows",
    "percentile_method",
    "threshold_children_per_current_home_p75",
    "threshold_out_of_county_foster_rate_p75",
    "threshold_homes_without_recent_activity_share_p75",
    "threshold_median_observed_active_day_rate_p25",
    "threshold_renewals_within_90_days_share_p75",
    "eligible_children_per_current_home_count",
    "eligible_out_of_county_foster_rate_count",
    "eligible_engagement_count",
}


def get_git_commit_sha() -> str:
    """Return the current Git commit SHA when available."""

    environment_sha = os.getenv("GIT_COMMIT_SHA")

    if environment_sha:
        return environment_sha.strip()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return "unknown"

    return result.stdout.strip() or "unknown"


def get_schema_object_names(
    connection: sqlite3.Connection,
    object_type: str,
) -> set[str]:
    """Return non-internal SQLite schema objects of a given type."""

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


def validate_county_signal_foreign_key_schema(
    connection: sqlite3.Connection,
) -> None:
    """Verify the county-signal foreign key targets county_summary.slug."""

    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(county_signal)"
    ).fetchall()

    expected_relationship_exists = any(
        str(row[2]) == "county_summary"
        and str(row[3]) == "county_slug"
        and str(row[4]) == "county_slug"
        for row in foreign_keys
    )

    if not expected_relationship_exists:
        raise RuntimeError(
            "db/schema.sql must define county_signal.county_slug as "
            "FOREIGN KEY (county_slug) REFERENCES "
            "county_summary(county_slug). "
            f"Current county_signal foreign keys: {foreign_keys}"
        )


def validate_database(
    connection: sqlite3.Connection,
) -> None:
    """Validate database structure, indexes, and integrity."""

    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()

    if integrity_result != ("ok",):
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")

    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()

    if foreign_key_violations:
        raise RuntimeError(
            f"SQLite foreign-key validation failed: {foreign_key_violations}"
        )

    tables = get_schema_object_names(connection, "table")
    missing_tables = REQUIRED_TABLES - tables

    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Required tables are missing: {missing}")

    indexes = get_schema_object_names(connection, "index")
    missing_indexes = REQUIRED_INDEXES - indexes

    if missing_indexes:
        missing = ", ".join(sorted(missing_indexes))
        raise RuntimeError(f"Required indexes are missing: {missing}")

    validate_county_signal_foreign_key_schema(connection)


def validate_signal_county_references(
    connection: sqlite3.Connection,
    signals: tuple[CountySignal, ...],
) -> None:
    """Ensure every signal references an inserted county summary row."""

    inserted_county_slugs = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT county_slug
            FROM county_summary
            """
        ).fetchall()
    }

    signal_county_slugs = {signal.county_slug for signal in signals}

    missing_county_slugs = signal_county_slugs - inserted_county_slugs

    if missing_county_slugs:
        missing = ", ".join(sorted(missing_county_slugs))

        raise RuntimeError(
            "County signals reference county slugs that were not "
            f"inserted into county_summary: {missing}"
        )


def validate_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate required aggregate database contents."""

    statewide_count_row = connection.execute(
        """
        SELECT COUNT(*)
        FROM statewide_summary
        """
    ).fetchone()

    if statewide_count_row is None or int(statewide_count_row[0]) != 1:
        raise RuntimeError(
            "The database must contain exactly one statewide summary row."
        )

    build_status_row = connection.execute(
        """
        SELECT value
        FROM metadata
        WHERE key = 'build_status'
        """
    ).fetchone()

    if build_status_row is None or str(build_status_row[0]) != "complete":
        raise RuntimeError("Database build status was not marked complete.")

    metadata_keys = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT key
            FROM metadata
            """
        ).fetchall()
    }

    missing_metadata = REQUIRED_METADATA_KEYS - metadata_keys

    if missing_metadata:
        missing = ", ".join(sorted(missing_metadata))
        raise RuntimeError(f"Required metadata is missing: {missing}")

    county_count_row = connection.execute(
        """
        SELECT COUNT(*)
        FROM county_summary
        """
    ).fetchone()

    if county_count_row is None:
        raise RuntimeError("Unable to count county summary rows.")

    county_count = int(county_count_row[0])

    if county_count != EXPECTED_COUNTY_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_COUNTY_ROWS} county summary rows, "
            f"found {county_count}."
        )

    metadata_county_count_row = connection.execute(
        """
        SELECT value
        FROM metadata
        WHERE key = 'county_summary_rows'
        """
    ).fetchone()

    if metadata_county_count_row is None:
        raise RuntimeError("County summary row-count metadata is missing.")

    if int(metadata_county_count_row[0]) != county_count:
        raise RuntimeError(
            "County summary metadata does not match the inserted row count."
        )

    county_totals = connection.execute(
        """
        SELECT
            COALESCE(SUM(children_currently_in_care), 0),
            COALESCE(SUM(current_foster_homes), 0),
            COALESCE(SUM(current_foster_placements), 0),
            COALESCE(SUM(local_foster_placements), 0),
            COALESCE(SUM(out_of_county_foster_placements), 0),
            COALESCE(SUM(homes_with_current_placement), 0),
            COALESCE(SUM(homes_with_recent_activity), 0),
            COALESCE(SUM(homes_without_recent_activity), 0)
        FROM county_summary
        """
    ).fetchone()

    statewide_totals = connection.execute(
        """
        SELECT
            children_currently_in_care,
            current_foster_homes,
            current_foster_home_placements,
            local_foster_placements,
            out_of_county_foster_placements,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity
        FROM statewide_summary
        WHERE id = 1
        """
    ).fetchone()

    if county_totals != statewide_totals:
        raise RuntimeError(
            "County aggregates do not reconcile with "
            "the statewide summary. "
            f"County totals: {county_totals}; "
            f"statewide totals: {statewide_totals}"
        )

    signal_count_row = connection.execute(
        """
        SELECT COUNT(*)
        FROM county_signal
        """
    ).fetchone()

    if signal_count_row is None:
        raise RuntimeError("Unable to count county signals.")

    signal_count = int(signal_count_row[0])

    metadata_signal_count_row = connection.execute(
        """
        SELECT value
        FROM metadata
        WHERE key = 'county_signal_rows'
        """
    ).fetchone()

    if metadata_signal_count_row is None:
        raise RuntimeError("County signal metadata is missing.")

    if int(metadata_signal_count_row[0]) != signal_count:
        raise RuntimeError(
            "County signal metadata does not match the inserted signal count."
        )

    aggregate_signal_count_row = connection.execute(
        """
        SELECT COALESCE(
            SUM(
                recruitment_signal_count
                + engagement_signal_count
            ),
            0
        )
        FROM county_summary
        """
    ).fetchone()

    if aggregate_signal_count_row is None:
        raise RuntimeError("Unable to reconcile county signal counts.")

    if int(aggregate_signal_count_row[0]) != signal_count:
        raise RuntimeError(
            "County signal rows do not match the signal counts "
            "stored in county_summary."
        )

    invalid_level_count_row = connection.execute(
        """
        SELECT COUNT(*)
        FROM county_summary
        WHERE
            (
                recruitment_level = 'higher'
                AND recruitment_signal_count < 2
            )
            OR (
                recruitment_level = 'possible'
                AND recruitment_signal_count != 1
            )
            OR (
                recruitment_level = 'review'
                AND recruitment_signal_count != 0
            )
            OR (
                engagement_level = 'higher'
                AND engagement_signal_count < 2
            )
            OR (
                engagement_level = 'possible'
                AND engagement_signal_count != 1
            )
            OR (
                engagement_level = 'review'
                AND engagement_signal_count != 0
            )
        """
    ).fetchone()

    if invalid_level_count_row is None or int(invalid_level_count_row[0]) != 0:
        raise RuntimeError(
            "One or more county classifications do not match their signal counts."
        )


def build_database(
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    output_path: Path = DEFAULT_DATABASE_PATH,
    raw_data_dir: Path = DEFAULT_RAW_DATA_DIR,
) -> Path:
    """Build and validate a populated immutable SQLite database.

    The complete database is created at a temporary path. The final
    artifact is replaced only after schema creation, ETL processing,
    insertion, validation, commit, and explicit connection closure.
    """

    schema_path = schema_path.resolve()
    output_path = output_path.resolve()
    raw_data_dir = raw_data_dir.resolve()

    if not schema_path.is_file():
        raise FileNotFoundError(f"SQLite schema was not found: {schema_path}")

    schema_sql = schema_path.read_text(encoding="utf-8").strip()

    if not schema_sql:
        raise ValueError(f"SQLite schema is empty: {schema_path}")

    source_data = load_sources(raw_data_dir)

    statewide_snapshot = derive_statewide_snapshot(source_data)

    base_county_aggregates = derive_county_aggregates(source_data)

    classification = classify_counties(base_county_aggregates)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}.",
        suffix=".tmp.db",
        dir=output_path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)
    connection: sqlite3.Connection | None = None

    try:
        try:
            connection = sqlite3.connect(temporary_path)

            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = DELETE")

            connection.executescript(schema_sql)
            validate_county_signal_foreign_key_schema(connection)

            connection.execute("BEGIN IMMEDIATE")

            built_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()

            upsert_metadata(
                connection,
                {
                    "schema_version": SCHEMA_VERSION,
                    "reporting_cutoff": "2026-07-01",
                    "observation_start": "2022-01-01",
                    "built_at_utc": built_at_utc,
                    "git_commit_sha": get_git_commit_sha(),
                    "build_status": "building",
                },
            )

            insert_statewide_summary(
                connection,
                statewide_snapshot,
            )

            # Insert parent rows before all county child tables.
            insert_county_summaries(
                connection,
                classification.counties,
            )

            inserted_county_count_row = connection.execute(
                """
                SELECT COUNT(*)
                FROM county_summary
                """
            ).fetchone()

            if (
                inserted_county_count_row is None
                or int(inserted_county_count_row[0]) != EXPECTED_COUNTY_ROWS
            ):
                raise RuntimeError(
                    f"Expected {EXPECTED_COUNTY_ROWS} county rows "
                    "before inserting signals, found "
                    f"{inserted_county_count_row}."
                )

            validate_signal_county_references(
                connection,
                classification.signals,
            )

            insert_county_signals(
                connection,
                classification.signals,
            )

            record_classification_metadata(
                connection,
                classification,
            )

            record_source_metadata(
                connection,
                raw_data_dir,
                statewide_snapshot,
            )

            upsert_metadata(
                connection,
                {
                    "build_status": "complete",
                    "county_summary_rows": str(len(classification.counties)),
                    "county_signal_rows": str(len(classification.signals)),
                },
            )

            validate_database(connection)
            validate_population(connection)

            connection.commit()

        except Exception:
            if connection is not None:
                connection.rollback()
            raise

        finally:
            # sqlite3.Connection.__exit__ does not close the file.
            # Explicit closure is required before replace/delete on Windows.
            if connection is not None:
                connection.close()

        # No SQLite handle is open when the temporary file is replaced.
        os.replace(
            temporary_path,
            output_path,
        )

    except Exception:
        # Cleanup is safe because the connection has already been closed.
        temporary_path.unlink(missing_ok=True)
        raise

    return output_path


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Create the Foster Home Capacity Explorer aggregate SQLite database."
        )
    )

    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to the SQLite schema.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="Path for the generated database.",
    )

    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=DEFAULT_RAW_DATA_DIR,
        help=("Directory containing the three authoritative CSV files."),
    )

    return parser.parse_args(arguments)


def main(
    arguments: Sequence[str] | None = None,
) -> int:
    """Run the aggregate database build."""

    parsed_arguments = parse_arguments(arguments)

    database_path = build_database(
        schema_path=parsed_arguments.schema,
        output_path=parsed_arguments.output,
        raw_data_dir=parsed_arguments.raw_data_dir,
    )

    print(f"Created validated aggregate database: {database_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
