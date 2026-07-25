"""Create the immutable aggregate SQLite database."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from scripts.etl.aggregate_age_alignment import (
    derive_county_age_alignment,
)
from scripts.etl.aggregate_counties import (
    derive_county_aggregates,
)
from scripts.etl.classify_opportunities import classify_counties

from scripts.etl.config import (
    ANALYSIS_START_DATE,
    DEFAULT_COUNTY_EXPORT_PATH,
    DEFAULT_METADATA_EXPORT_PATH,
    DEFAULT_DATABASE_PATH,
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
    EXPECTED_COUNTY_ROWS,
    REPORTING_CUTOFF_DATE,
    SCHEMA_VERSION,
)

from scripts.etl.derive_snapshot import derive_statewide_snapshot
from scripts.etl.load_sources import load_sources
from scripts.etl.metadata import (
    build_age_alignment_metadata,
    build_placement_flow_metadata,
    build_investigation_question_metadata,
    get_git_commit_sha,
)
from scripts.etl.validate_population import (
    validate_population,
    validate_signal_county_references,
)
from scripts.etl.validate_schema import (
    validate_database,
    validate_database_schema,
)


from scripts.etl.write_database import (
    insert_county_age_alignments,
    insert_county_investigation_questions,
    insert_county_monthly_trends,
    insert_county_placement_flows,
    insert_county_signals,
    insert_county_summaries,
    insert_statewide_summary,
    record_classification_metadata,
    record_source_metadata,
    upsert_metadata,
)


from scripts.etl.aggregate_placement_flows import (
    derive_county_placement_flows,
)

from scripts.etl.aggregate_investigation_questions import (
    derive_county_investigation_questions,
)

from scripts.etl.validate_outputs import (
    validate_public_database_privacy,
)

from scripts.export_outputs import export_aggregate_outputs
from scripts.etl.export_outputs import write_metadata_json

from scripts.etl.aggregate_monthly_trends import (
    derive_county_monthly_trends,
)


def read_schema(schema_path: Path) -> str:
    """Read and validate the SQLite schema file."""

    resolved_schema_path = schema_path.resolve()

    if not resolved_schema_path.is_file():
        raise FileNotFoundError(f"SQLite schema was not found: {resolved_schema_path}")

    schema_sql = resolved_schema_path.read_text(encoding="utf-8").strip()

    if not schema_sql:
        raise ValueError(f"SQLite schema is empty: {resolved_schema_path}")

    return schema_sql


def create_temporary_database_path(
    output_path: Path,
) -> Path:
    """Create an empty temporary database path beside the output."""

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

    return Path(temporary_name)


def validate_inserted_county_count(
    connection: sqlite3.Connection,
) -> None:
    """Verify county parent rows exist before detail rows are used."""

    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM county_summary
        """
    ).fetchone()

    if row is None:
        raise RuntimeError("Unable to count inserted county summary rows.")

    inserted_count = int(row[0])

    if inserted_count != EXPECTED_COUNTY_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_COUNTY_ROWS} county rows before "
            f"inserting county details, found {inserted_count}."
        )


def populate_database(
    connection: sqlite3.Connection,
    *,
    raw_data_dir: Path,
) -> None:
    """Run ETL derivation and populate all completed aggregate tables."""

    source_data = load_sources(raw_data_dir)

    statewide_snapshot = derive_statewide_snapshot(source_data)

    base_county_aggregates = derive_county_aggregates(source_data)

    classification = classify_counties(base_county_aggregates)

    monthly_trends = derive_county_monthly_trends(
        source_data,
        classification.counties,
    )

    age_alignment_result = derive_county_age_alignment(
        source_data,
        base_county_aggregates,
    )

    placement_flows = derive_county_placement_flows(
        source_data,
        base_county_aggregates,
    )

    investigation_questions = derive_county_investigation_questions(
        classification.counties,
        age_alignment_result.alignments,
        placement_flows,
        classification.signals,
        monthly_trends=monthly_trends,
    )

    built_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()

    upsert_metadata(
        connection,
        {
            "schema_version": SCHEMA_VERSION,
            "reporting_cutoff": (REPORTING_CUTOFF_DATE.isoformat()),
            "observation_start": (ANALYSIS_START_DATE.isoformat()),
            "built_at_utc": built_at_utc,
            "git_commit_sha": get_git_commit_sha(),
            "build_status": "building",
        },
    )

    insert_statewide_summary(
        connection,
        statewide_snapshot,
    )

    # Parent county rows must exist before county detail rows.
    insert_county_summaries(
        connection,
        classification.counties,
    )

    validate_inserted_county_count(connection)

    insert_county_monthly_trends(
        connection,
        monthly_trends,
    )

    insert_county_age_alignments(
        connection,
        age_alignment_result.alignments,
    )

    insert_county_placement_flows(
        connection,
        placement_flows,
    )

    validate_signal_county_references(
        connection,
        classification.signals,
    )

    insert_county_signals(
        connection,
        classification.signals,
    )

    insert_county_investigation_questions(
        connection,
        investigation_questions,
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

    age_metadata = build_age_alignment_metadata(age_alignment_result)

    placement_flow_metadata = build_placement_flow_metadata(placement_flows)

    investigation_question_metadata = build_investigation_question_metadata(
        investigation_questions
    )

    upsert_metadata(
        connection,
        {
            "build_status": "complete",
            "county_summary_rows": str(len(classification.counties)),
            "county_signal_rows": str(len(classification.signals)),
            "county_monthly_trend_rows": str(len(monthly_trends)),
            **age_metadata,
            **placement_flow_metadata,
            **investigation_question_metadata,
        },
    )


def build_database(
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    output_path: Path = DEFAULT_DATABASE_PATH,
    raw_data_dir: Path = DEFAULT_RAW_DATA_DIR,
) -> Path:
    """Build and validate the immutable aggregate SQLite database.

    The database is created at a temporary path. The final artifact
    is replaced only after schema creation, ETL population, complete
    validation, commit, and explicit connection closure.
    """

    resolved_output_path = output_path.resolve()
    resolved_raw_data_dir = raw_data_dir.resolve()

    schema_sql = read_schema(schema_path)

    temporary_path = create_temporary_database_path(resolved_output_path)

    connection: sqlite3.Connection | None = None

    try:
        try:
            connection = sqlite3.connect(temporary_path)

            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = DELETE")

            connection.executescript(schema_sql)

            # Fail before ETL if the versioned schema is incomplete.
            validate_database_schema(connection)

            connection.execute("BEGIN IMMEDIATE")

            populate_database(
                connection,
                raw_data_dir=resolved_raw_data_dir,
            )

            validate_population(connection)
            validate_database(connection)
            validate_public_database_privacy(connection)

            connection.commit()

        except Exception:
            if connection is not None:
                connection.rollback()

            raise

        finally:
            # SQLite must be explicitly closed before replacing or
            # deleting files on Windows.
            if connection is not None:
                connection.close()

        os.replace(
            temporary_path,
            resolved_output_path,
        )

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return resolved_output_path


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
        "--county-export",
        type=Path,
        default=DEFAULT_COUNTY_EXPORT_PATH,
        help="Path for the aggregate county CSV export.",
    )
    parser.add_argument(
        "--metadata-export",
        type=Path,
        default=DEFAULT_METADATA_EXPORT_PATH,
        help="Path for the public build metadata JSON.",
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
    """Build the database and aggregate county export."""

    parsed_arguments = parse_arguments(arguments)

    database_path = build_database(
        schema_path=parsed_arguments.schema,
        output_path=parsed_arguments.output,
        raw_data_dir=parsed_arguments.raw_data_dir,
    )

    export_result = export_aggregate_outputs(
        database_path=database_path,
        county_csv_path=parsed_arguments.county_export,
    )

    metadata_result = write_metadata_json(
        database_path=database_path,
        county_export=export_result,
        output_path=parsed_arguments.metadata_export,
    )

    print(f"Created validated aggregate database: {database_path}")

    print(f"Created validated aggregate county export: {export_result.output_path}")

    print(f"County export rows: {export_result.row_count}")

    print(f"County export SHA-256: {export_result.sha256}")

    print(f"Created validated build metadata: {metadata_result.output_path}")

    print(f"Metadata SHA-256: {metadata_result.sha256}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
