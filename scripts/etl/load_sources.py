from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

CHILD_COLUMNS = (
    "id_child",
    "removal_date",
    "discharge_date",
    "age_at_removal",
    "most_recent_age",
    "removal_county",
)

PLACEMENT_COLUMNS = (
    "id_child",
    "placement_start_date",
    "placement_end_date",
    "resource_type_on_this_placement",
    "placement_index",
    "removal_county",
    "placement_county",
    "id_provider",
    "placement_length",
)

PROVIDER_COLUMNS = (
    "id_provider",
    "license_start_date",
    "license_end_date",
    "county_provider",
    "n_days_licensed",
    "n_days_active",
    "min_age",
    "max_age",
)


@dataclass(frozen=True, slots=True)
class ChildRecord:
    id_child: str
    removal_date: date
    discharge_date: date | None
    age_at_removal: int | None
    most_recent_age: int | None
    removal_county: str


@dataclass(frozen=True, slots=True)
class PlacementRecord:
    id_child: str
    placement_start_date: date
    placement_end_date: date
    resource_type: str
    placement_index: int
    removal_county: str
    placement_county: str
    id_provider: str | None
    placement_length: int


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    id_provider: str
    license_start_date: date
    license_end_date: date
    county_provider: str
    n_days_licensed: int
    n_days_active: int
    min_age: int
    max_age: int


@dataclass(frozen=True, slots=True)
class SourceData:
    children: tuple[ChildRecord, ...]
    placements: tuple[PlacementRecord, ...]
    providers: tuple[ProviderRecord, ...]


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%m/%d/%y").date()


def _optional_date(value: str) -> date | None:
    return None if value == "NA" else _parse_date(value)


def _optional_int(value: str) -> int | None:
    return None if value == "NA" else int(value)


def _optional_string(value: str) -> str | None:
    return None if value == "NA" else value


def _read_rows(
    path: Path,
    expected_columns: tuple[str, ...],
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required source file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as source_file:
        reader = csv.DictReader(source_file)
        actual_columns = tuple(reader.fieldnames or ())

        if actual_columns != expected_columns:
            raise ValueError(
                f"Unexpected columns in {path.name}. "
                f"Expected {expected_columns}, received {actual_columns}."
            )

        return list(reader)


def load_sources(raw_data_dir: Path | None = None) -> SourceData:
    data_dir = raw_data_dir or DEFAULT_RAW_DATA_DIR

    child_rows = _read_rows(data_dir / "child_level.csv", CHILD_COLUMNS)
    placement_rows = _read_rows(
        data_dir / "placement_level.csv",
        PLACEMENT_COLUMNS,
    )
    provider_rows = _read_rows(
        data_dir / "provider_level_updated.csv",
        PROVIDER_COLUMNS,
    )

    children = tuple(
        ChildRecord(
            id_child=row["id_child"],
            removal_date=_parse_date(row["removal_date"]),
            discharge_date=_optional_date(row["discharge_date"]),
            age_at_removal=_optional_int(row["age_at_removal"]),
            most_recent_age=_optional_int(row["most_recent_age"]),
            removal_county=row["removal_county"],
        )
        for row in child_rows
    )

    placements = tuple(
        PlacementRecord(
            id_child=row["id_child"],
            placement_start_date=_parse_date(row["placement_start_date"]),
            placement_end_date=_parse_date(row["placement_end_date"]),
            resource_type=row["resource_type_on_this_placement"],
            placement_index=int(row["placement_index"]),
            removal_county=row["removal_county"],
            placement_county=row["placement_county"],
            id_provider=_optional_string(row["id_provider"]),
            placement_length=int(row["placement_length"]),
        )
        for row in placement_rows
    )

    providers = tuple(
        ProviderRecord(
            id_provider=row["id_provider"],
            license_start_date=_parse_date(row["license_start_date"]),
            license_end_date=_parse_date(row["license_end_date"]),
            county_provider=row["county_provider"],
            n_days_licensed=int(row["n_days_licensed"]),
            n_days_active=int(row["n_days_active"]),
            min_age=int(row["min_age"]),
            max_age=int(row["max_age"]),
        )
        for row in provider_rows
    )

    return SourceData(
        children=children,
        placements=placements,
        providers=providers,
    )
