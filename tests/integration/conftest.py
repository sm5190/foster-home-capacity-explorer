"""Shared fixtures for SQLite integration tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.build_database import build_database
from scripts.etl.config import (
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
)


@pytest.fixture(scope="session")
def built_database_path(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Build one validated database for read-only integration tests."""

    output_directory = tmp_path_factory.mktemp("built_database")

    database_path = output_directory / "foster_capacity.db"

    built_path = build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    if not built_path.is_file():
        raise RuntimeError(
            f"The integration-test database was not created: {built_path}"
        )

    return built_path


@pytest.fixture
def database_connection(
    built_database_path: Path,
) -> Iterator[sqlite3.Connection]:
    """Open a read-only connection to the built test database."""

    database_uri = f"{built_database_path.resolve().as_uri()}?mode=ro&immutable=1"

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
    finally:
        connection.close()
