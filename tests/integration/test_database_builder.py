"""Integration tests for aggregate database generation."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from scripts.build_database import build_database
from scripts.etl.config import (
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
)


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


def test_builder_creates_database(
    tmp_path: Path,
) -> None:
    """Produce a nonempty SQLite database at the requested path."""

    database_path = tmp_path / "foster_capacity.db"

    result = build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    assert result == database_path.resolve()
    assert database_path.is_file()
    assert database_path.stat().st_size > 0

    with closing(sqlite3.connect(database_path)) as connection:
        integrity_result = connection.execute("PRAGMA integrity_check").fetchone()

        foreign_key_violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    assert integrity_result == ("ok",)
    assert foreign_key_violations == []


def test_builder_creates_missing_output_directories(
    tmp_path: Path,
) -> None:
    """Create parent directories for a nested output path."""

    database_path = tmp_path / "nested" / "generated" / "foster_capacity.db"

    result = build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    assert result == database_path.resolve()
    assert database_path.is_file()


def test_rebuild_replaces_existing_database(
    tmp_path: Path,
) -> None:
    """Replace stale database contents during a successful rebuild."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
        output_path=database_path,
        raw_data_dir=DEFAULT_RAW_DATA_DIR,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            INSERT INTO metadata (
                key,
                value
            )
            VALUES (
                'stale_test_value',
                'remove-me'
            )
            """
        )
        connection.commit()

    build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
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
    """Preserve the valid artifact when a replacement build fails."""

    database_path = tmp_path / "foster_capacity.db"

    build_database(
        schema_path=DEFAULT_SCHEMA_PATH,
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


def test_missing_schema_does_not_create_database(
    tmp_path: Path,
) -> None:
    """Reject a missing schema before creating the output."""

    schema_path = tmp_path / "missing.sql"
    database_path = tmp_path / "foster_capacity.db"

    with pytest.raises(
        FileNotFoundError,
        match="SQLite schema was not found",
    ):
        build_database(
            schema_path=schema_path,
            output_path=database_path,
            raw_data_dir=DEFAULT_RAW_DATA_DIR,
        )

    assert not database_path.exists()


def test_empty_schema_does_not_create_database(
    tmp_path: Path,
) -> None:
    """Reject an empty schema before creating the output."""

    schema_path = tmp_path / "empty.sql"
    database_path = tmp_path / "foster_capacity.db"

    schema_path.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="SQLite schema is empty",
    ):
        build_database(
            schema_path=schema_path,
            output_path=database_path,
            raw_data_dir=DEFAULT_RAW_DATA_DIR,
        )

    assert not database_path.exists()


def test_incomplete_schema_does_not_create_database(
    tmp_path: Path,
) -> None:
    """Reject a valid but incomplete SQLite schema."""

    schema_path = tmp_path / "incomplete.sql"
    database_path = tmp_path / "foster_capacity.db"

    schema_path.write_text(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="Required tables are missing",
    ):
        build_database(
            schema_path=schema_path,
            output_path=database_path,
            raw_data_dir=DEFAULT_RAW_DATA_DIR,
        )

    assert not database_path.exists()
