"""Export validated public artifacts from the aggregate database."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from collections.abc import Sequence
from pathlib import Path

from scripts.etl.config import (
    DEFAULT_COUNTY_EXPORT_PATH,
    DEFAULT_DATABASE_PATH,
)
from scripts.etl.export_outputs import (
    CountySummaryExportResult,
    write_county_summary_csv,
)
from scripts.etl.validate_outputs import (
    validate_county_summary_csv,
    validate_public_database_privacy,
)


def create_temporary_export_path(
    output_path: Path,
) -> Path:
    """Create a temporary CSV beside the final output."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}.",
        suffix=".tmp.csv",
        dir=output_path.parent,
    )

    os.close(file_descriptor)

    return Path(temporary_name)


def open_read_only_database(
    database_path: Path,
) -> sqlite3.Connection:
    """Open the immutable aggregate database read-only."""

    resolved_database_path = database_path.resolve()

    if not resolved_database_path.is_file():
        raise FileNotFoundError(
            f"Aggregate SQLite database was not found: {resolved_database_path}"
        )

    database_uri = f"{resolved_database_path.as_uri()}?mode=ro&immutable=1"

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    connection.execute("PRAGMA query_only = ON")

    return connection


def export_aggregate_outputs(
    database_path: Path = DEFAULT_DATABASE_PATH,
    county_csv_path: Path = DEFAULT_COUNTY_EXPORT_PATH,
) -> CountySummaryExportResult:
    """Create and validate the public aggregate CSV export."""

    resolved_county_csv_path = county_csv_path.resolve()

    temporary_path = create_temporary_export_path(resolved_county_csv_path)

    connection: sqlite3.Connection | None = None

    try:
        connection = open_read_only_database(database_path)

        validate_public_database_privacy(connection)

        temporary_result = write_county_summary_csv(
            connection,
            temporary_path,
        )

        validate_county_summary_csv(
            connection,
            temporary_path,
        )

        connection.close()
        connection = None

        os.replace(
            temporary_path,
            resolved_county_csv_path,
        )

        return CountySummaryExportResult(
            output_path=resolved_county_csv_path,
            row_count=temporary_result.row_count,
            sha256=temporary_result.sha256,
        )

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    finally:
        if connection is not None:
            connection.close()


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse output-export arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Export validated public aggregate artifacts "
            "from the Foster Home Capacity Explorer database."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="Path to the aggregate SQLite database.",
    )

    parser.add_argument(
        "--county-csv",
        type=Path,
        default=DEFAULT_COUNTY_EXPORT_PATH,
        help="Path for the aggregate county CSV.",
    )

    return parser.parse_args(arguments)


def main(
    arguments: Sequence[str] | None = None,
) -> int:
    """Export all public aggregate artifacts."""

    parsed_arguments = parse_arguments(arguments)

    result = export_aggregate_outputs(
        database_path=parsed_arguments.database,
        county_csv_path=parsed_arguments.county_csv,
    )

    print(f"Created validated aggregate county export: {result.output_path}")
    print(f"Rows: {result.row_count}")
    print(f"SHA-256: {result.sha256}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
