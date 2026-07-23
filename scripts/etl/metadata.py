"""Build reproducibility and analytical metadata helpers."""

from __future__ import annotations

import os
import subprocess

from scripts.etl.aggregate_age_alignment import AgeAlignmentResult
from scripts.etl.config import ALL_AGE_BANDS, PROJECT_ROOT
from scripts.etl.aggregate_placement_flows import (
    CountyPlacementFlow,
)

from scripts.etl.aggregate_investigation_questions import (
    CountyInvestigationQuestion,
)


def get_git_commit_sha() -> str:
    """Return the current Git commit SHA when available.

    A deployment-provided value takes precedence over invoking Git.
    This supports container builds where the repository metadata may
    not be present in the final runtime image.
    """

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


def normalize_age_band_for_metadata(age_band: str) -> str:
    """Convert an age-band label into a metadata-key fragment."""

    return age_band.replace("-", "_")


def build_age_alignment_metadata(
    result: AgeAlignmentResult,
) -> dict[str, str]:
    """Create metadata for age-alignment rows and thresholds."""

    expected_bands = set(ALL_AGE_BANDS)

    threshold_bands = set(result.thresholds)
    eligibility_bands = set(result.eligible_counties)

    if threshold_bands != expected_bands:
        missing = expected_bands - threshold_bands
        unexpected = threshold_bands - expected_bands

        raise ValueError(
            "Age-alignment thresholds do not contain the configured "
            "age bands. "
            f"Missing: {sorted(missing)}; "
            f"unexpected: {sorted(unexpected)}."
        )

    if eligibility_bands != expected_bands:
        missing = expected_bands - eligibility_bands
        unexpected = eligibility_bands - expected_bands

        raise ValueError(
            "Age-alignment eligibility counts do not contain the "
            "configured age bands. "
            f"Missing: {sorted(missing)}; "
            f"unexpected: {sorted(unexpected)}."
        )

    metadata: dict[str, str] = {
        "county_age_alignment_rows": str(len(result.alignments)),
    }

    for age_band in ALL_AGE_BANDS:
        normalized_band = normalize_age_band_for_metadata(age_band)

        eligible_count = result.eligible_counties[age_band]
        threshold = result.thresholds[age_band]

        if eligible_count < 0:
            raise ValueError(
                "Age-band eligible-county counts cannot be negative. "
                f"Age band: {age_band}; count: {eligible_count}."
            )

        if threshold is not None and threshold < 0:
            raise ValueError(
                "Age-band percentile thresholds cannot be negative. "
                f"Age band: {age_band}; threshold: {threshold}."
            )

        metadata[f"age_{normalized_band}_eligible_counties"] = str(eligible_count)

        metadata[f"age_{normalized_band}_p75_threshold"] = (
            repr(threshold) if threshold is not None else "not_applicable"
        )

    return metadata


def build_placement_flow_metadata(
    flows: tuple[CountyPlacementFlow, ...],
) -> dict[str, str]:
    """Create metadata for county placement-flow aggregates."""

    total_placements = sum(flow.placement_count for flow in flows)

    if any(flow.placement_count <= 0 for flow in flows):
        raise ValueError(
            "Placement-flow metadata cannot be created from "
            "rows with nonpositive placement counts."
        )

    return {
        "county_placement_flow_rows": str(len(flows)),
        "county_placement_flow_placements": str(total_placements),
    }


def build_investigation_question_metadata(
    questions: tuple[CountyInvestigationQuestion, ...],
) -> dict[str, str]:
    """Create metadata for investigation questions."""

    return {
        "county_investigation_question_rows": str(len(questions)),
    }
