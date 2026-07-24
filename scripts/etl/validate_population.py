"""Validate populated aggregate SQLite tables and reconciliations."""

from __future__ import annotations

import math
import sqlite3
from typing import Final

from scripts.etl.classify_opportunities import CountySignal
from scripts.etl.config import (
    AGE_SIGNAL_MINIMUM_CHILDREN,
    ALL_AGE_BANDS,
    EXPECTED_COUNTY_ROWS,
)
from scripts.etl.metadata import normalize_age_band_for_metadata


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
    "county_age_alignment_rows",
    "percentile_method",
    "threshold_children_per_current_home_p75",
    "threshold_out_of_county_foster_rate_p75",
    "threshold_homes_without_recent_activity_share_p75",
    "threshold_median_observed_active_day_rate_p25",
    "threshold_renewals_within_90_days_share_p75",
    "eligible_children_per_current_home_count",
    "eligible_out_of_county_foster_rate_count",
    "eligible_engagement_count",
    "age_0_5_eligible_counties",
    "age_0_5_p75_threshold",
    "age_6_12_eligible_counties",
    "age_6_12_p75_threshold",
    "age_13_17_eligible_counties",
    "age_13_17_p75_threshold",
    "age_unknown_eligible_counties",
    "age_unknown_p75_threshold",
    "county_placement_flow_rows",
    "county_placement_flow_placements",
    "county_investigation_question_rows",
}


def get_metadata_value(
    connection: sqlite3.Connection,
    key: str,
) -> str | None:
    """Return one metadata value when present."""

    row = connection.execute(
        """
        SELECT value
        FROM metadata
        WHERE key = ?
        """,
        (key,),
    ).fetchone()

    if row is None:
        return None

    return str(row[0])


def require_metadata_value(
    connection: sqlite3.Connection,
    key: str,
) -> str:
    """Return a required metadata value or raise an error."""

    value = get_metadata_value(
        connection,
        key,
    )

    if value is None:
        raise RuntimeError(f"Required metadata value is missing: {key}")

    return value


def fetch_required_integer(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[object, ...] = (),
) -> int:
    """Execute a scalar query and return its integer value."""

    row = connection.execute(
        query,
        parameters,
    ).fetchone()

    if row is None or row[0] is None:
        raise RuntimeError("A required integer database query returned no value.")

    return int(row[0])


def validate_required_metadata(
    connection: sqlite3.Connection,
) -> None:
    """Verify all required build and analytical metadata exists."""

    actual_keys = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT key
            FROM metadata
            """
        ).fetchall()
    }

    missing_keys = REQUIRED_METADATA_KEYS - actual_keys

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))

        raise RuntimeError(f"Required metadata is missing: {missing}")

    build_status = require_metadata_value(
        connection,
        "build_status",
    )

    if build_status != "complete":
        raise RuntimeError(
            "Database build status was not marked complete. "
            f"Current value: {build_status!r}"
        )


def validate_statewide_population(
    connection: sqlite3.Connection,
) -> None:
    """Verify the database contains one valid statewide row."""

    statewide_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM statewide_summary
        """,
    )

    if statewide_count != 1:
        raise RuntimeError(
            "The database must contain exactly one statewide "
            f"summary row. Found {statewide_count}."
        )


def validate_placement_flow_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate current foster-home placement-flow aggregates."""

    flow_row_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_placement_flow
        """,
    )

    metadata_row_count = int(
        require_metadata_value(
            connection,
            "county_placement_flow_rows",
        )
    )

    if metadata_row_count != flow_row_count:
        raise RuntimeError(
            "Placement-flow row-count metadata does not match "
            "the populated table. "
            f"Metadata: {metadata_row_count}; "
            f"table: {flow_row_count}."
        )

    flow_placement_count = fetch_required_integer(
        connection,
        """
        SELECT COALESCE(
            SUM(placement_count),
            0
        )
        FROM county_placement_flow
        """,
    )

    metadata_placement_count = int(
        require_metadata_value(
            connection,
            "county_placement_flow_placements",
        )
    )

    if metadata_placement_count != flow_placement_count:
        raise RuntimeError(
            "Placement-flow placement metadata does not match "
            "the populated table. "
            f"Metadata: {metadata_placement_count}; "
            f"table: {flow_placement_count}."
        )

    flow_totals = connection.execute(
        """
        SELECT
            COALESCE(
                SUM(placement_count),
                0
            ),
            COALESCE(
                SUM(
                    CASE
                        WHEN is_local = 1
                        THEN placement_count
                        ELSE 0
                    END
                ),
                0
            ),
            COALESCE(
                SUM(
                    CASE
                        WHEN is_local = 0
                        THEN placement_count
                        ELSE 0
                    END
                ),
                0
            )
        FROM county_placement_flow
        """
    ).fetchone()

    statewide_totals = connection.execute(
        """
        SELECT
            current_foster_home_placements,
            local_foster_placements,
            out_of_county_foster_placements
        FROM statewide_summary
        WHERE id = 1
        """
    ).fetchone()

    if flow_totals is None or statewide_totals is None:
        raise RuntimeError("Unable to reconcile placement-flow statewide totals.")

    if flow_totals != statewide_totals:
        raise RuntimeError(
            "Placement-flow totals do not reconcile with the "
            "statewide summary. "
            f"Flow totals: {flow_totals}; "
            f"statewide totals: {statewide_totals}."
        )

    county_mismatches = connection.execute(
        """
        SELECT
            summary.county_slug,
            summary.current_foster_placements,
            COALESCE(
                SUM(flow.placement_count),
                0
            ) AS flow_placements,
            summary.local_foster_placements,
            COALESCE(
                SUM(
                    CASE
                        WHEN flow.is_local = 1
                        THEN flow.placement_count
                        ELSE 0
                    END
                ),
                0
            ) AS flow_local,
            summary.out_of_county_foster_placements,
            COALESCE(
                SUM(
                    CASE
                        WHEN flow.is_local = 0
                        THEN flow.placement_count
                        ELSE 0
                    END
                ),
                0
            ) AS flow_out_of_county
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
        """
    ).fetchall()

    if county_mismatches:
        raise RuntimeError(
            "Placement flows do not reconcile with county "
            f"placement totals: {county_mismatches}"
        )

    invalid_share_totals = connection.execute(
        """
        SELECT
            summary.county_slug,
            summary.current_foster_placements,
            COUNT(
                flow.destination_county_name
            ) AS flow_rows,
            COALESCE(
                SUM(flow.placement_share),
                0
            ) AS share_total
        FROM county_summary AS summary
        LEFT JOIN county_placement_flow AS flow
            ON flow.origin_county_slug
               = summary.county_slug
        GROUP BY
            summary.county_slug,
            summary.current_foster_placements
        HAVING
            (
                summary.current_foster_placements = 0
                AND COUNT(
                    flow.destination_county_name
                ) != 0
            )
            OR (
                summary.current_foster_placements > 0
                AND ABS(
                    COALESCE(
                        SUM(flow.placement_share),
                        0
                    ) - 1.0
                ) > 0.000000001
            )
        """
    ).fetchall()

    if invalid_share_totals:
        raise RuntimeError(
            "Placement-flow shares do not sum to one within "
            f"their origin counties: {invalid_share_totals}"
        )

    invalid_flow_rows = connection.execute(
        """
        SELECT
            flow.origin_county_slug,
            flow.destination_county_name,
            flow.placement_count,
            flow.placement_share
        FROM county_placement_flow AS flow
        JOIN county_summary AS summary
            ON summary.county_slug
               = flow.origin_county_slug
        WHERE
            flow.placement_count <= 0
            OR flow.placement_share <= 0
            OR summary.current_foster_placements <= 0
            OR (
                summary.current_foster_placements > 0
                AND ABS(
                    flow.placement_share
                    -
                    (
                        CAST(
                            flow.placement_count
                            AS REAL
                        )
                        /
                        summary.current_foster_placements
                    )
                ) > 0.000000001
            )
        """
    ).fetchall()

    if invalid_flow_rows:
        raise RuntimeError(
            "Placement-flow row shares do not match their "
            f"origin placement totals: {invalid_flow_rows}"
        )

    invalid_local_flags = connection.execute(
        """
        SELECT
            flow.origin_county_slug,
            summary.county_name,
            flow.destination_county_name,
            flow.is_local
        FROM county_placement_flow AS flow
        JOIN county_summary AS summary
            ON summary.county_slug
               = flow.origin_county_slug
        WHERE flow.is_local != CASE
            WHEN flow.destination_county_name
                 = summary.county_name
            THEN 1
            ELSE 0
        END
        """
    ).fetchall()

    if invalid_local_flags:
        raise RuntimeError(
            "Placement-flow local indicators do not match the "
            f"origin and destination counties: {invalid_local_flags}"
        )


def validate_county_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate county rows and statewide reconciliation."""

    county_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_summary
        """,
    )

    if county_count != EXPECTED_COUNTY_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_COUNTY_ROWS} county summary rows, "
            f"found {county_count}."
        )

    metadata_count = int(
        require_metadata_value(
            connection,
            "county_summary_rows",
        )
    )

    if metadata_count != county_count:
        raise RuntimeError(
            "County summary metadata does not match the inserted "
            f"row count. Metadata: {metadata_count}; "
            f"table: {county_count}."
        )

    county_totals = connection.execute(
        """
        SELECT
            COALESCE(
                SUM(children_currently_in_care),
                0
            ),
            COALESCE(
                SUM(current_kin_placements),
                0
            ),
            COALESCE(
                SUM(current_foster_placements),
                0
            ),
            COALESCE(
                SUM(current_nonfamily_placements),
                0
            ),
            COALESCE(
                SUM(current_foster_homes),
                0
            ),
            COALESCE(
                SUM(local_foster_placements),
                0
            ),
            COALESCE(
                SUM(out_of_county_foster_placements),
                0
            ),
            COALESCE(
                SUM(homes_with_current_placement),
                0
            ),
            COALESCE(
                SUM(homes_with_recent_activity),
                0
            ),
            COALESCE(
                SUM(homes_without_recent_activity),
                0
            )
        FROM county_summary
        """
    ).fetchone()

    statewide_totals = connection.execute(
        """
        SELECT
            children_currently_in_care,
            current_kin_placements,
            current_foster_home_placements,
            current_nonfamily_placements,
            current_foster_homes,
            local_foster_placements,
            out_of_county_foster_placements,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity
        FROM statewide_summary
        WHERE id = 1
        """
    ).fetchone()

    if county_totals is None or statewide_totals is None:
        raise RuntimeError("Unable to reconcile county and statewide totals.")

    if county_totals != statewide_totals:
        raise RuntimeError(
            "County aggregates do not reconcile with the "
            "statewide summary. "
            f"County totals: {county_totals}; "
            f"statewide totals: {statewide_totals}."
        )

    county_mismatches = connection.execute(
        """
        SELECT
            county_slug,
            children_currently_in_care,
            current_kin_placements,
            current_foster_placements,
            current_nonfamily_placements,
            local_foster_placements,
            out_of_county_foster_placements
        FROM county_summary
        WHERE
            children_currently_in_care
            != (
                current_kin_placements
                + current_foster_placements
                + current_nonfamily_placements
            )
            OR current_foster_placements
            != (
                local_foster_placements
                + out_of_county_foster_placements
            )
        """
    ).fetchall()

    if county_mismatches:
        raise RuntimeError(
            f"County placement-setting counts do not reconcile: {county_mismatches}"
        )


def validate_signal_county_references(
    connection: sqlite3.Connection,
    signals: tuple[CountySignal, ...],
) -> None:
    """Ensure every signal references an inserted county row."""

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

    if not missing_county_slugs:
        return

    missing = ", ".join(sorted(missing_county_slugs))

    raise RuntimeError(
        "County signals reference slugs that were not inserted "
        f"into county_summary: {missing}"
    )


def validate_signal_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate signal rows and stored county classifications."""

    signal_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_signal
        """,
    )

    metadata_signal_count = int(
        require_metadata_value(
            connection,
            "county_signal_rows",
        )
    )

    if metadata_signal_count != signal_count:
        raise RuntimeError(
            "County signal metadata does not match the inserted "
            f"signal count. Metadata: {metadata_signal_count}; "
            f"table: {signal_count}."
        )

    aggregate_signal_count = fetch_required_integer(
        connection,
        """
        SELECT COALESCE(
            SUM(
                recruitment_signal_count
                + engagement_signal_count
            ),
            0
        )
        FROM county_summary
        """,
    )

    if aggregate_signal_count != signal_count:
        raise RuntimeError(
            "County signal rows do not match the signal counts "
            "stored in county_summary. "
            f"Summary count: {aggregate_signal_count}; "
            f"signal rows: {signal_count}."
        )

    invalid_level_count = fetch_required_integer(
        connection,
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
        """,
    )

    if invalid_level_count != 0:
        raise RuntimeError(
            "One or more county classifications do not match "
            f"their signal counts. Invalid rows: "
            f"{invalid_level_count}."
        )


def validate_age_alignment_grid(
    connection: sqlite3.Connection,
) -> int:
    """Validate the complete county-by-age-band row grid."""

    county_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_summary
        """,
    )

    age_row_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_age_alignment
        """,
    )

    expected_row_count = county_count * len(ALL_AGE_BANDS)

    if age_row_count != expected_row_count:
        raise RuntimeError(
            "County age-alignment row count is invalid. "
            f"Expected {expected_row_count}, "
            f"found {age_row_count}."
        )

    invalid_counties = connection.execute(
        """
        SELECT
            county_summary.county_slug,
            COUNT(county_age_alignment.age_band)
        FROM county_summary
        LEFT JOIN county_age_alignment
            ON county_age_alignment.county_slug
               = county_summary.county_slug
        GROUP BY county_summary.county_slug
        HAVING COUNT(county_age_alignment.age_band) != ?
        """,
        (len(ALL_AGE_BANDS),),
    ).fetchall()

    if invalid_counties:
        raise RuntimeError(
            "One or more counties do not contain exactly one row "
            "for every age band: "
            f"{invalid_counties}"
        )

    duplicate_rows = connection.execute(
        """
        SELECT
            county_slug,
            age_band,
            COUNT(*)
        FROM county_age_alignment
        GROUP BY county_slug, age_band
        HAVING COUNT(*) != 1
        """
    ).fetchall()

    if duplicate_rows:
        raise RuntimeError(
            f"County age-alignment contains duplicate keys: {duplicate_rows}"
        )

    metadata_row_count = int(
        require_metadata_value(
            connection,
            "county_age_alignment_rows",
        )
    )

    if metadata_row_count != age_row_count:
        raise RuntimeError(
            "Age-alignment metadata does not match the inserted "
            f"row count. Metadata: {metadata_row_count}; "
            f"table: {age_row_count}."
        )

    return age_row_count


def validate_age_alignment_semantics(
    connection: sqlite3.Connection,
) -> None:
    """Validate age ratios, guardrails, and evidence flags."""

    invalid_unknown_rows = connection.execute(
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

    if invalid_unknown_rows:
        raise RuntimeError(
            "Unknown-age rows contain invalid preference metrics: "
            f"{invalid_unknown_rows}"
        )

    invalid_known_ratios = connection.execute(
        """
        SELECT
            county_slug,
            age_band,
            current_children,
            preference_matching_homes,
            children_per_matching_home
        FROM county_age_alignment
        WHERE age_band != 'unknown'
          AND (
              (
                  preference_matching_homes = 0
                  AND children_per_matching_home IS NOT NULL
              )
              OR
              (
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

    if invalid_known_ratios:
        raise RuntimeError(
            "Age-alignment ratios do not reconcile with children "
            "divided by matching homes: "
            f"{invalid_known_ratios}"
        )

    invalid_limited_rows = connection.execute(
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

    if invalid_limited_rows:
        raise RuntimeError(
            f"Age-alignment limited-data flags are invalid: {invalid_limited_rows}"
        )

    invalid_evidence_rows = connection.execute(
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

    if invalid_evidence_rows:
        raise RuntimeError(
            "Age-specific recruitment evidence does not match "
            "the stored ratios and thresholds: "
            f"{invalid_evidence_rows}"
        )


def validate_age_alignment_totals(
    connection: sqlite3.Connection,
) -> None:
    """Reconcile age-band children statewide and by county."""

    age_child_total = fetch_required_integer(
        connection,
        """
        SELECT COALESCE(SUM(current_children), 0)
        FROM county_age_alignment
        """,
    )

    statewide_child_total = fetch_required_integer(
        connection,
        """
        SELECT children_currently_in_care
        FROM statewide_summary
        WHERE id = 1
        """,
    )

    if age_child_total != statewide_child_total:
        raise RuntimeError(
            "Age-band child totals do not reconcile with "
            "statewide current children. "
            f"Age total: {age_child_total}; "
            f"statewide total: {statewide_child_total}."
        )

    county_mismatches = connection.execute(
        """
        SELECT
            summary.county_slug,
            summary.children_currently_in_care,
            COALESCE(SUM(age.current_children), 0)
        FROM county_summary AS summary
        LEFT JOIN county_age_alignment AS age
            ON age.county_slug = summary.county_slug
        GROUP BY
            summary.county_slug,
            summary.children_currently_in_care
        HAVING
            summary.children_currently_in_care
            != COALESCE(SUM(age.current_children), 0)
        """
    ).fetchall()

    if county_mismatches:
        raise RuntimeError(
            f"Age-band child totals do not reconcile by county: {county_mismatches}"
        )


def validate_age_band_metadata(
    connection: sqlite3.Connection,
    age_band: str,
) -> None:
    """Validate threshold and eligibility metadata for one band."""

    normalized_band = normalize_age_band_for_metadata(age_band)

    eligible_key = f"age_{normalized_band}_eligible_counties"
    threshold_key = f"age_{normalized_band}_p75_threshold"

    metadata_eligible_count = int(
        require_metadata_value(
            connection,
            eligible_key,
        )
    )

    metadata_threshold_value = require_metadata_value(
        connection,
        threshold_key,
    )

    database_eligible_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_age_alignment
        WHERE age_band = ?
          AND limited_data = 0
          AND children_per_matching_home IS NOT NULL
        """,
        (age_band,),
    )

    if metadata_eligible_count != database_eligible_count:
        raise RuntimeError(
            f"Eligible-county metadata for {age_band} does not "
            "match the database rows. "
            f"Metadata: {metadata_eligible_count}; "
            f"database: {database_eligible_count}."
        )

    threshold_rows = connection.execute(
        """
        SELECT DISTINCT statewide_p75_threshold
        FROM county_age_alignment
        WHERE age_band = ?
        """,
        (age_band,),
    ).fetchall()

    threshold_values = {
        (None if row[0] is None else float(row[0])) for row in threshold_rows
    }

    if age_band == "unknown":
        if metadata_eligible_count != 0:
            raise RuntimeError("Unknown age-band eligibility count must be zero.")

        if metadata_threshold_value != "not_applicable":
            raise RuntimeError(
                "Unknown age-band threshold metadata must be 'not_applicable'."
            )

        if threshold_values != {None}:
            raise RuntimeError("Unknown age-band database thresholds must be NULL.")

        return

    if database_eligible_count == 0:
        if metadata_threshold_value != "not_applicable":
            raise RuntimeError(
                f"Age band {age_band} has no eligible counties, "
                "so its threshold must be 'not_applicable'."
            )

        if threshold_values != {None}:
            raise RuntimeError(
                f"Age band {age_band} has no eligible counties, "
                "so all stored thresholds must be NULL."
            )

        return

    if metadata_threshold_value == "not_applicable":
        raise RuntimeError(
            f"Age band {age_band} has eligible counties but no metadata threshold."
        )

    non_null_thresholds = {value for value in threshold_values if value is not None}

    if None in threshold_values or len(non_null_thresholds) != 1:
        raise RuntimeError(
            f"Every row for age band {age_band} must use one "
            "consistent non-null statewide threshold. "
            f"Stored values: {threshold_values}"
        )

    database_threshold = next(iter(non_null_thresholds))
    metadata_threshold = float(metadata_threshold_value)

    if not math.isclose(
        database_threshold,
        metadata_threshold,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise RuntimeError(
            f"Age threshold metadata for {age_band} does not "
            "match the database threshold. "
            f"Metadata: {metadata_threshold}; "
            f"database: {database_threshold}."
        )


def validate_age_alignment_metadata(
    connection: sqlite3.Connection,
) -> None:
    """Validate metadata for every configured age band."""

    for age_band in ALL_AGE_BANDS:
        validate_age_band_metadata(
            connection,
            age_band,
        )


def validate_age_alignment_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate all Step 9 age-alignment outputs."""

    validate_age_alignment_grid(connection)
    validate_age_alignment_semantics(connection)
    validate_age_alignment_totals(connection)
    validate_age_alignment_metadata(connection)


def validate_investigation_question_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate deterministic county investigation questions."""

    question_count = fetch_required_integer(
        connection,
        """
        SELECT COUNT(*)
        FROM county_investigation_question
        """,
    )

    metadata_count = int(
        require_metadata_value(
            connection,
            "county_investigation_question_rows",
        )
    )

    if metadata_count != question_count:
        raise RuntimeError(
            "Investigation-question metadata does not match "
            "the populated table. "
            f"Metadata: {metadata_count}; "
            f"table: {question_count}."
        )

    invalid_counties = connection.execute(
        """
        SELECT
            summary.county_slug,
            COUNT(
                question.display_order
            ) AS question_count
        FROM county_summary AS summary
        LEFT JOIN county_investigation_question AS question
            ON question.county_slug
               = summary.county_slug
        GROUP BY summary.county_slug
        HAVING
            COUNT(question.display_order) < 3
            OR COUNT(question.display_order) > 5
        """
    ).fetchall()

    if invalid_counties:
        raise RuntimeError(
            "Every county must have between three and five "
            "investigation questions. "
            f"Invalid counties: {invalid_counties}"
        )

    invalid_ordering = connection.execute(
        """
        SELECT
            county_slug,
            COUNT(*) AS question_count,
            MIN(display_order) AS minimum_order,
            MAX(display_order) AS maximum_order,
            COUNT(
                DISTINCT display_order
            ) AS distinct_orders
        FROM county_investigation_question
        GROUP BY county_slug
        HAVING
            MIN(display_order) != 1
            OR MAX(display_order) != COUNT(*)
            OR COUNT(DISTINCT display_order)
                != COUNT(*)
        """
    ).fetchall()

    if invalid_ordering:
        raise RuntimeError(
            "Investigation-question display ordering is not "
            f"contiguous: {invalid_ordering}"
        )

    duplicate_questions = connection.execute(
        """
        SELECT
            county_slug,
            question_text,
            COUNT(*)
        FROM county_investigation_question
        GROUP BY
            county_slug,
            question_text
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    if duplicate_questions:
        raise RuntimeError(
            f"Counties contain duplicate investigation questions: {duplicate_questions}"
        )

    empty_questions = connection.execute(
        """
        SELECT
            county_slug,
            display_order
        FROM county_investigation_question
        WHERE LENGTH(TRIM(question_text)) = 0
        """
    ).fetchall()

    if empty_questions:
        raise RuntimeError(
            f"Investigation questions cannot contain empty text: {empty_questions}"
        )


def validate_population(
    connection: sqlite3.Connection,
) -> None:
    """Validate all currently populated aggregate tables."""

    validate_required_metadata(connection)
    validate_statewide_population(connection)
    validate_county_population(connection)
    validate_age_alignment_population(connection)
    validate_placement_flow_population(connection)
    validate_signal_population(connection)
    validate_investigation_question_population(connection)
