"""Load and type the authoritative Foster Insights CSV sources."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Final

from scripts.etl.config import (
    CHILD_FILE_NAME,
    DEFAULT_RAW_DATA_DIR,
    PLACEMENT_FILE_NAME,
    PROVIDER_FILE_NAME,
)


CHILD_COLUMNS: Final = (
    "id_child",
    "removal_date",
    "discharge_date",
    "age_at_removal",
    "most_recent_age",
    "removal_county",
)

PLACEMENT_COLUMNS: Final = (
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

PROVIDER_COLUMNS: Final = (
    "id_provider",
    "license_start_date",
    "license_end_date",
    "county_provider",
    "n_days_licensed",
    "n_days_active",
    "min_age",
    "max_age",
)

RESOURCE_TYPES: Final = {
    "kin",
    "foster_home",
    "nonfamily",
}

COUNTY_NAME_ALIASES: Final[dict[str, str]] = {
    "Vermillion": "Vermilion",
}


def canonicalize_county_name(value: str) -> str:
    """Return a validated canonical Illinois county name."""

    stripped_value = value.strip()

    if not stripped_value:
        raise ValueError("County name cannot be blank.")

    return COUNTY_NAME_ALIASES.get(
        stripped_value,
        stripped_value,
    )


@dataclass(frozen=True, slots=True)
class ChildRecord:
    """One child-level source record."""

    id_child: str
    removal_date: date
    discharge_date: date | None
    age_at_removal: int | None
    most_recent_age: int | None
    removal_county: str


@dataclass(frozen=True, slots=True)
class PlacementRecord:
    """One placement-level source record."""

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
    """One foster-home provider source record."""

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
    """All typed project source records."""

    children: tuple[ChildRecord, ...]
    placements: tuple[PlacementRecord, ...]
    providers: tuple[ProviderRecord, ...]


def _parse_date(value: str, field_name: str) -> date:
    """Parse the M/D/YY date format used in the source files."""

    try:
        return datetime.strptime(value, "%m/%d/%y").date()
    except ValueError as error:
        raise ValueError(
            f"Invalid date for {field_name}: {value!r}. Expected M/D/YY."
        ) from error


def _parse_int(value: str, field_name: str) -> int:
    """Parse an expected integer source value."""

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer for {field_name}: {value!r}.") from error


def _optional_date(
    value: str,
    field_name: str,
) -> date | None:
    """Convert the source NA sentinel to None."""

    if value == "NA":
        return None

    return _parse_date(value, field_name)


def _optional_int(
    value: str,
    field_name: str,
) -> int | None:
    """Convert the source NA sentinel to None."""

    if value == "NA":
        return None

    return _parse_int(value, field_name)


def _optional_string(value: str) -> str | None:
    """Convert the source NA sentinel to None."""

    return None if value == "NA" else value


def _read_rows(
    path: Path,
    expected_columns: tuple[str, ...],
) -> list[dict[str, str]]:
    """Read a CSV after verifying its exact header."""

    if not path.is_file():
        raise FileNotFoundError(f"Required source file was not found: {path}")

    with path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)
        actual_columns = tuple(reader.fieldnames or ())

        if actual_columns != expected_columns:
            raise ValueError(
                f"Unexpected columns in {path.name}. "
                f"Expected {expected_columns}, "
                f"received {actual_columns}."
            )

        rows = list(reader)

    if not rows:
        raise ValueError(f"Required source file is empty: {path}")

    return rows


def validate_source_relationships(
    data: SourceData,
) -> None:
    """Protect key relationships used by the ETL."""

    child_ids = [child.id_child for child in data.children]
    provider_ids = [provider.id_provider for provider in data.providers]

    if len(child_ids) != len(set(child_ids)):
        raise ValueError("Child source contains duplicate id_child values.")

    if len(provider_ids) != len(set(provider_ids)):
        raise ValueError("Provider source contains duplicate id_provider values.")

    known_child_ids = set(child_ids)
    known_provider_ids = set(provider_ids)

    for placement in data.placements:
        if placement.id_child not in known_child_ids:
            raise ValueError(
                f"Placement references an unknown child: {placement.id_child}"
            )

        # Only foster-home placements participate in foster-home
        # provider metrics. Nonfamily provider identifiers are
        # preserved but are not joined to the foster-home dataset.
        if placement.resource_type == "foster_home":
            if placement.id_provider is None:
                raise ValueError("Foster-home placement is missing id_provider.")

            if placement.id_provider not in known_provider_ids:
                raise ValueError(
                    "Foster-home placement references an "
                    f"unknown provider: {placement.id_provider}"
                )


def load_sources(
    raw_data_dir: Path | None = None,
) -> SourceData:
    """Load, parse, and validate all three source files."""

    data_dir = (raw_data_dir or DEFAULT_RAW_DATA_DIR).resolve()

    child_rows = _read_rows(
        data_dir / CHILD_FILE_NAME,
        CHILD_COLUMNS,
    )
    placement_rows = _read_rows(
        data_dir / PLACEMENT_FILE_NAME,
        PLACEMENT_COLUMNS,
    )
    provider_rows = _read_rows(
        data_dir / PROVIDER_FILE_NAME,
        PROVIDER_COLUMNS,
    )

    children = tuple(
        ChildRecord(
            id_child=row["id_child"],
            removal_date=_parse_date(
                row["removal_date"],
                "child.removal_date",
            ),
            discharge_date=_optional_date(
                row["discharge_date"],
                "child.discharge_date",
            ),
            age_at_removal=_optional_int(
                row["age_at_removal"],
                "child.age_at_removal",
            ),
            most_recent_age=_optional_int(
                row["most_recent_age"],
                "child.most_recent_age",
            ),
            removal_county=canonicalize_county_name(
                row["removal_county"],
            ),
        )
        for row in child_rows
    )

    placements: list[PlacementRecord] = []

    for row in placement_rows:
        resource_type = row["resource_type_on_this_placement"]

        if resource_type not in RESOURCE_TYPES:
            raise ValueError(f"Unexpected placement resource type: {resource_type!r}")

        placements.append(
            PlacementRecord(
                id_child=row["id_child"],
                placement_start_date=_parse_date(
                    row["placement_start_date"],
                    "placement.placement_start_date",
                ),
                placement_end_date=_parse_date(
                    row["placement_end_date"],
                    "placement.placement_end_date",
                ),
                resource_type=resource_type,
                placement_index=_parse_int(
                    row["placement_index"],
                    "placement.placement_index",
                ),
                removal_county=canonicalize_county_name(
                    row["removal_county"],
                ),
                placement_county=canonicalize_county_name(
                    row["placement_county"],
                ),
                id_provider=_optional_string(row["id_provider"]),
                placement_length=_parse_int(
                    row["placement_length"],
                    "placement.placement_length",
                ),
            )
        )

    providers = tuple(
        ProviderRecord(
            id_provider=row["id_provider"],
            license_start_date=_parse_date(
                row["license_start_date"],
                "provider.license_start_date",
            ),
            license_end_date=_parse_date(
                row["license_end_date"],
                "provider.license_end_date",
            ),
            county_provider=canonicalize_county_name(
                row["county_provider"],
            ),
            n_days_licensed=_parse_int(
                row["n_days_licensed"],
                "provider.n_days_licensed",
            ),
            n_days_active=_parse_int(
                row["n_days_active"],
                "provider.n_days_active",
            ),
            min_age=_parse_int(
                row["min_age"],
                "provider.min_age",
            ),
            max_age=_parse_int(
                row["max_age"],
                "provider.max_age",
            ),
        )
        for row in provider_rows
    )

    source_data = SourceData(
        children=children,
        placements=tuple(placements),
        providers=providers,
    )

    validate_source_relationships(source_data)

    return source_data
