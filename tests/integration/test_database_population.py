"""Integration tests for populated aggregate database values."""

from __future__ import annotations

import sqlite3

import pytest

from scripts.etl.config import (
    AGE_SIGNAL_MINIMUM_CHILDREN,
    ALL_AGE_BANDS,
    ANALYSIS_START_DATE,
    EXPECTED_COUNTY_ROWS,
    KNOWN_AGE_BANDS,
    REPORTING_CUTOFF_DATE,
    SCHEMA_VERSION,
)
from scripts.etl.metadata import (
    normalize_age_band_for_metadata,
)


def read_metadata(
    connection: sqlite3.Connection,
) -> dict[str, str]:
    """Return all stored database metadata."""

    rows = connection.execute(
        """
        SELECT
            key,
            value
        FROM metadata
        """
    ).fetchall()

    return {str(row["key"]): str(row["value"]) for row in rows}


def test_database_contains_required_metadata(
    database_connection: sqlite3.Connection,
) -> None:
    """Identify the build, source files, and methodology."""

    metadata = read_metadata(database_connection)

    assert metadata["schema_version"] == SCHEMA_VERSION
    assert metadata["reporting_cutoff"] == (REPORTING_CUTOFF_DATE.isoformat())
    assert metadata["observation_start"] == (ANALYSIS_START_DATE.isoformat())
    assert metadata["build_status"] == "complete"

    assert metadata["source_child_rows"] == "16139"
    assert metadata["source_placement_rows"] == "51994"
    assert metadata["source_provider_rows"] == "6063"

    assert len(metadata["source_child_sha256"]) == 64
    assert len(metadata["source_placement_sha256"]) == 64
    assert len(metadata["source_provider_sha256"]) == 64

    assert metadata["county_summary_rows"] == str(EXPECTED_COUNTY_ROWS)
    assert metadata["county_signal_rows"] == "117"
    assert metadata["county_age_alignment_rows"] == str(
        EXPECTED_COUNTY_ROWS * len(ALL_AGE_BANDS)
    )

    assert metadata["built_at_utc"]
    assert metadata["git_commit_sha"]

    assert metadata["percentile_method"] == ("linear_interpolation_position_(n-1)*p")

    assert metadata["eligible_children_per_current_home_count"] == "103"
    assert metadata["eligible_out_of_county_foster_rate_count"] == "31"
    assert metadata["eligible_engagement_count"] == "103"

    assert metadata["age_unknown_eligible_counties"] == "0"
    assert metadata["age_unknown_p75_threshold"] == "not_applicable"

    assert metadata["county_placement_flow_rows"] == "1376"

    assert metadata["county_placement_flow_placements"] == "4343"

    question_count = database_connection.execute(
        """
        SELECT COUNT(*)
        FROM county_investigation_question
        """
    ).fetchone()

    assert question_count is not None

    assert metadata["county_investigation_question_rows"] == str(question_count[0])


def test_database_populates_statewide_summary(
    database_connection: sqlite3.Connection,
) -> None:
    """Match the locked statewide analytical baselines."""

    row = database_connection.execute(
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

    assert row["local_placement_rate"] == (pytest.approx(1_519 / 4_343))

    assert row["median_observed_active_day_rate"] == pytest.approx(0.6967113276492083)


def test_database_populates_county_summary(
    database_connection: sqlite3.Connection,
) -> None:
    """Insert county rows and reconcile statewide totals."""

    county_count = database_connection.execute(
        """
        SELECT COUNT(*) AS county_count
        FROM county_summary
        """
    ).fetchone()

    totals = database_connection.execute(
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

    cook = database_connection.execute(
        """
        SELECT *
        FROM county_summary
        WHERE county_slug = 'cook'
        """
    ).fetchone()

    assert county_count is not None
    assert county_count["county_count"] == EXPECTED_COUNTY_ROWS

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


def test_database_populates_classifications_and_signals(
    database_connection: sqlite3.Connection,
) -> None:
    """Store county categories and supporting evidence."""

    signal_count = database_connection.execute(
        """
        SELECT COUNT(*) AS signal_count
        FROM county_signal
        """
    ).fetchone()

    cook = database_connection.execute(
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

    cook_signals = database_connection.execute(
        """
        SELECT signal_code
        FROM county_signal
        WHERE county_slug = 'cook'
        ORDER BY signal_code
        """
    ).fetchall()

    level_counts = database_connection.execute(
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


def test_database_contains_complete_age_alignment_grid(
    database_connection: sqlite3.Connection,
) -> None:
    """Store one row for every county and age band."""

    row_count = database_connection.execute(
        """
        SELECT COUNT(*) AS row_count
        FROM county_age_alignment
        """
    ).fetchone()

    assert row_count is not None
    assert row_count["row_count"] == (EXPECTED_COUNTY_ROWS * len(ALL_AGE_BANDS))

    invalid_counties = database_connection.execute(
        """
        SELECT
            county_slug,
            COUNT(*) AS age_band_count
        FROM county_age_alignment
        GROUP BY county_slug
        HAVING COUNT(*) != ?
        """,
        (len(ALL_AGE_BANDS),),
    ).fetchall()

    assert invalid_counties == []


def test_database_reconciles_age_band_totals(
    database_connection: sqlite3.Connection,
) -> None:
    """Reconcile locked age-band totals with current children."""

    rows = database_connection.execute(
        """
        SELECT
            age_band,
            SUM(current_children) AS child_count
        FROM county_age_alignment
        GROUP BY age_band
        """
    ).fetchall()

    age_totals = {str(row["age_band"]): int(row["child_count"]) for row in rows}

    assert age_totals == {
        "0-5": 1_812,
        "6-12": 3_402,
        "13-17": 2_855,
        "unknown": 2,
    }

    assert sum(age_totals.values()) == 8_071

    county_mismatches = database_connection.execute(
        """
        SELECT
            summary.county_slug,
            summary.children_currently_in_care,
            SUM(age.current_children) AS age_children
        FROM county_summary AS summary
        JOIN county_age_alignment AS age
            ON age.county_slug = summary.county_slug
        GROUP BY
            summary.county_slug,
            summary.children_currently_in_care
        HAVING
            summary.children_currently_in_care
            != SUM(age.current_children)
        """
    ).fetchall()

    assert county_mismatches == []


def test_database_preserves_unknown_age_semantics(
    database_connection: sqlite3.Connection,
) -> None:
    """Never compare unknown ages with numeric preferences."""

    invalid_unknown_rows = database_connection.execute(
        """
        SELECT county_slug
        FROM county_age_alignment
        WHERE age_band = 'unknown'
          AND (
              preference_matching_homes != 0
              OR children_per_matching_home IS NOT NULL
              OR limited_data != 1
              OR recruitment_evidence != 0
              OR statewide_p75_threshold IS NOT NULL
          )
        """
    ).fetchall()

    assert invalid_unknown_rows == []


def test_database_age_ratios_and_evidence_are_consistent(
    database_connection: sqlite3.Connection,
) -> None:
    """Validate ratios, guardrails, and age evidence."""

    invalid_ratios = database_connection.execute(
        """
        SELECT
            county_slug,
            age_band
        FROM county_age_alignment
        WHERE age_band != 'unknown'
          AND (
              (
                  preference_matching_homes = 0
                  AND children_per_matching_home IS NOT NULL
              )
              OR (
                  preference_matching_homes > 0
                  AND (
                      children_per_matching_home IS NULL
                      OR ABS(
                          children_per_matching_home
                          -
                          (
                              CAST(current_children AS REAL)
                              / preference_matching_homes
                          )
                      ) > 0.000000001
                  )
              )
          )
        """
    ).fetchall()

    invalid_limited_flags = database_connection.execute(
        """
        SELECT
            county_slug,
            age_band
        FROM county_age_alignment
        WHERE age_band != 'unknown'
          AND limited_data != CASE
              WHEN current_children < ?
                   OR preference_matching_homes = 0
              THEN 1
              ELSE 0
          END
        """,
        (AGE_SIGNAL_MINIMUM_CHILDREN,),
    ).fetchall()

    invalid_evidence = database_connection.execute(
        """
        SELECT
            county_slug,
            age_band
        FROM county_age_alignment
        WHERE recruitment_evidence != CASE
            WHEN age_band != 'unknown'
                 AND limited_data = 0
                 AND children_per_matching_home IS NOT NULL
                 AND statewide_p75_threshold IS NOT NULL
                 AND children_per_matching_home
                     >= statewide_p75_threshold
            THEN 1
            ELSE 0
        END
        """
    ).fetchall()

    assert invalid_ratios == []
    assert invalid_limited_flags == []
    assert invalid_evidence == []


def test_database_age_threshold_metadata_is_consistent(
    database_connection: sqlite3.Connection,
) -> None:
    """Match age-band threshold metadata to stored rows."""

    metadata = read_metadata(database_connection)

    for age_band in KNOWN_AGE_BANDS:
        normalized_band = normalize_age_band_for_metadata(age_band)

        eligible_key = f"age_{normalized_band}_eligible_counties"
        threshold_key = f"age_{normalized_band}_p75_threshold"

        database_eligible_count = database_connection.execute(
            """
                SELECT COUNT(*)
                FROM county_age_alignment
                WHERE age_band = ?
                  AND limited_data = 0
                  AND children_per_matching_home
                      IS NOT NULL
                """,
            (age_band,),
        ).fetchone()

        assert database_eligible_count is not None

        eligible_count = int(database_eligible_count[0])

        assert int(metadata[eligible_key]) == (eligible_count)

        threshold_rows = database_connection.execute(
            """
                SELECT DISTINCT
                    statewide_p75_threshold
                FROM county_age_alignment
                WHERE age_band = ?
                """,
            (age_band,),
        ).fetchall()

        threshold_values = {row[0] for row in threshold_rows}

        if eligible_count == 0:
            assert metadata[threshold_key] == "not_applicable"
            assert threshold_values == {None}
            continue

        assert None not in threshold_values
        assert len(threshold_values) == 1

        database_threshold = float(next(iter(threshold_values)))
        metadata_threshold = float(metadata[threshold_key])

        assert metadata_threshold == pytest.approx(database_threshold)


def test_database_populates_placement_flows(
    database_connection: sqlite3.Connection,
) -> None:
    """Store all current foster-home origin-destination flows."""

    totals = database_connection.execute(
        """
        SELECT
            COUNT(*) AS flow_rows,
            SUM(placement_count) AS placements,
            SUM(
                CASE
                    WHEN is_local = 1
                    THEN placement_count
                    ELSE 0
                END
            ) AS local_placements,
            SUM(
                CASE
                    WHEN is_local = 0
                    THEN placement_count
                    ELSE 0
                END
            ) AS out_of_county_placements
        FROM county_placement_flow
        """
    ).fetchone()

    assert totals is not None
    assert totals["flow_rows"] == 1_376
    assert totals["placements"] == 4_343
    assert totals["local_placements"] == 1_519
    assert totals["out_of_county_placements"] == 2_824


def test_database_reconciles_placement_flows_by_origin(
    database_connection: sqlite3.Connection,
) -> None:
    """Reconcile flow counts and shares within each origin."""

    mismatches = database_connection.execute(
        """
        SELECT
            summary.county_slug
        FROM county_summary AS summary
        LEFT JOIN county_placement_flow AS flow
            ON flow.origin_county_slug
               = summary.county_slug
        GROUP BY
            summary.county_slug,
            summary.current_foster_placements,
            summary.local_foster_placements,
            summary.out_of_county_foster_placements
        HAVING
            summary.current_foster_placements
                != COALESCE(
                    SUM(flow.placement_count),
                    0
                )
            OR summary.local_foster_placements
                != COALESCE(
                    SUM(
                        CASE
                            WHEN flow.is_local = 1
                            THEN flow.placement_count
                            ELSE 0
                        END
                    ),
                    0
                )
            OR summary.out_of_county_foster_placements
                != COALESCE(
                    SUM(
                        CASE
                            WHEN flow.is_local = 0
                            THEN flow.placement_count
                            ELSE 0
                        END
                    ),
                    0
                )
            OR (
                summary.current_foster_placements > 0
                AND ABS(
                    SUM(flow.placement_share) - 1.0
                ) > 0.000000001
            )
        """
    ).fetchall()

    assert mismatches == []


def test_database_stores_cook_placement_destinations(
    database_connection: sqlite3.Connection,
) -> None:
    """Retain local and out-of-county destinations for Cook."""

    rows = database_connection.execute(
        """
        SELECT
            destination_county_name,
            placement_count,
            placement_share,
            is_local
        FROM county_placement_flow
        WHERE origin_county_slug = 'cook'
        ORDER BY
            placement_count DESC,
            destination_county_name
        LIMIT 5
        """
    ).fetchall()

    assert [
        (
            row["destination_county_name"],
            row["placement_count"],
            row["is_local"],
        )
        for row in rows
    ] == [
        ("Lake", 195, 0),
        ("Cook", 180, 1),
        ("Kane", 167, 0),
        ("DuPage", 163, 0),
        ("Will", 163, 0),
    ]

    cook_row = next(row for row in rows if row["destination_county_name"] == "Cook")

    assert cook_row["placement_share"] == pytest.approx(180 / 1_044)


def test_database_populates_investigation_questions(
    database_connection: sqlite3.Connection,
) -> None:
    """Create three to five ordered questions for every county."""

    county_rows = database_connection.execute(
        """
        SELECT
            summary.county_slug,
            COUNT(
                question.display_order
            ) AS question_count,
            MIN(
                question.display_order
            ) AS first_order,
            MAX(
                question.display_order
            ) AS last_order
        FROM county_summary AS summary
        LEFT JOIN county_investigation_question AS question
            ON question.county_slug
               = summary.county_slug
        GROUP BY summary.county_slug
        ORDER BY summary.county_slug
        """
    ).fetchall()

    assert len(county_rows) == 103

    for row in county_rows:
        question_count = row["question_count"]

        assert 3 <= question_count <= 5
        assert row["first_order"] == 1
        assert row["last_order"] == question_count


def test_investigation_questions_are_aggregate_only(
    database_connection: sqlite3.Connection,
) -> None:
    """Exclude source identifiers from question text."""

    invalid_rows = database_connection.execute(
        """
        SELECT
            county_slug,
            display_order
        FROM county_investigation_question
        WHERE
            LOWER(question_text) LIKE '%id_child%'
            OR LOWER(question_text) LIKE '%id_provider%'
        """
    ).fetchall()

    assert invalid_rows == []


def test_database_metadata_matches_all_aggregate_row_counts(
    database_connection: sqlite3.Connection,
) -> None:
    """Match every aggregate-table row count to metadata."""

    metadata_rows = database_connection.execute(
        """
        SELECT
            key,
            value
        FROM metadata
        """
    ).fetchall()

    metadata = {str(row["key"]): str(row["value"]) for row in metadata_rows}

    table_metadata_pairs = {
        "county_summary": "county_summary_rows",
        "county_age_alignment": ("county_age_alignment_rows"),
        "county_placement_flow": ("county_placement_flow_rows"),
        "county_signal": "county_signal_rows",
        "county_investigation_question": ("county_investigation_question_rows"),
    }

    for (
        table_name,
        metadata_key,
    ) in table_metadata_pairs.items():
        count_row = database_connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()

        assert count_row is not None

        assert int(metadata[metadata_key]) == int(count_row[0])
