"""Create deterministic county investigation questions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Final

from scripts.etl.aggregate_age_alignment import (
    CountyAgeAlignment,
)
from scripts.etl.aggregate_counties import CountyAggregate
from scripts.etl.aggregate_placement_flows import (
    CountyPlacementFlow,
)
from scripts.etl.classify_opportunities import CountySignal
from scripts.etl.aggregate_monthly_trends import CountyMonthlyTrend
from scripts.etl.config import TREND_STABLE_PERCENT_CHANGE


MINIMUM_QUESTIONS_PER_COUNTY: Final = 3
MAXIMUM_QUESTIONS_PER_COUNTY: Final = 5
MAXIMUM_CONTEXTUAL_QUESTIONS: Final = 3

AGE_BAND_LABELS: Final = {
    "0-5": "0 to 5",
    "6-12": "6 to 12",
    "13-17": "13 to 17",
}


@dataclass(frozen=True, slots=True)
class CountyInvestigationQuestion:
    """Represent one ordered county investigation question."""

    county_slug: str
    display_order: int
    question_text: str


def format_age_band_list(
    age_bands: tuple[str, ...],
) -> str:
    """Format age bands for plain-language question text."""

    labels = [AGE_BAND_LABELS[age_band] for age_band in age_bands]

    if len(labels) == 1:
        return labels[0]

    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"

    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def group_signal_codes(
    signals: tuple[CountySignal, ...],
) -> dict[str, set[str]]:
    """Group county classification signal codes by county."""

    grouped: defaultdict[str, set[str]] = defaultdict(set)

    for signal in signals:
        grouped[signal.county_slug].add(signal.signal_code)

    return dict(grouped)


def group_age_evidence(
    alignments: tuple[CountyAgeAlignment, ...],
) -> dict[str, tuple[str, ...]]:
    """Group age bands with recruitment evidence by county."""

    grouped: defaultdict[str, list[str]] = defaultdict(list)

    for alignment in alignments:
        if not alignment.recruitment_evidence:
            continue

        if alignment.age_band not in AGE_BAND_LABELS:
            continue

        grouped[alignment.county_slug].append(alignment.age_band)

    age_band_order = {age_band: index for index, age_band in enumerate(AGE_BAND_LABELS)}

    return {
        county_slug: tuple(
            sorted(
                age_bands,
                key=age_band_order.__getitem__,
            )
        )
        for county_slug, age_bands in grouped.items()
    }


def group_monthly_trends(
    trends: tuple[CountyMonthlyTrend, ...],
) -> dict[str, tuple[CountyMonthlyTrend, ...]]:
    """Group monthly trend points by county."""

    grouped: defaultdict[str, list[CountyMonthlyTrend]] = defaultdict(list)

    for trend in trends:
        grouped[trend.county_slug].append(trend)

    return {
        county_slug: tuple(
            sorted(
                county_trends,
                key=lambda trend: trend.snapshot_date,
            )
        )
        for county_slug, county_trends in grouped.items()
    }


def calculate_trend_change(
    trends: tuple[CountyMonthlyTrend, ...],
) -> tuple[float, float, float] | None:
    """Return previous ratio, current ratio, and percent change."""

    if len(trends) < 2:
        return None

    previous_ratio = trends[0].children_per_current_home
    current_ratio = trends[-1].children_per_current_home

    if previous_ratio is None or current_ratio is None or previous_ratio <= 0:
        return None

    percent_change = (current_ratio - previous_ratio) / previous_ratio

    return (
        previous_ratio,
        current_ratio,
        percent_change,
    )


def calculate_cross_county_counts(
    flows: tuple[CountyPlacementFlow, ...],
    county_name_by_slug: dict[str, str],
) -> tuple[dict[str, int], dict[str, int]]:
    """Calculate non-local outbound and inbound flow counts."""

    outbound_counts: defaultdict[str, int] = defaultdict(int)
    inbound_counts_by_name: defaultdict[str, int] = defaultdict(int)

    for flow in flows:
        if flow.origin_county_slug not in county_name_by_slug:
            raise ValueError(
                "Placement flow references an unknown origin "
                f"county slug: {flow.origin_county_slug!r}"
            )

        if flow.is_local:
            continue

        outbound_counts[flow.origin_county_slug] += flow.placement_count

        inbound_counts_by_name[flow.destination_county_name] += flow.placement_count

    inbound_counts = {
        county_slug: inbound_counts_by_name.get(
            county_name,
            0,
        )
        for county_slug, county_name in county_name_by_slug.items()
    }

    return dict(outbound_counts), inbound_counts


def select_contextual_questions(
    *,
    county: CountyAggregate,
    signal_codes: set[str],
    age_evidence: tuple[str, ...],
    outbound_count: int,
    inbound_count: int,
    monthly_trends: tuple[CountyMonthlyTrend, ...],
) -> list[str]:
    """Select up to three pattern-specific questions."""

    recruitment_questions: list[str] = []
    engagement_questions: list[str] = []
    coordination_questions: list[str] = []
    context_questions: list[str] = []

    if age_evidence:
        age_description = format_age_band_list(age_evidence)

        recruitment_questions.append(
            "What local factors should be reviewed to "
            "understand the number of current homes whose "
            "preferences include children ages "
            f"{age_description}?"
        )

    if "high_out_of_county_foster_rate" in signal_codes:
        recruitment_questions.append(
            "What circumstances should be reviewed to "
            f"understand why children from {county.county_name} "
            "are placed outside their removal county?"
        )

    if "high_children_per_current_home" in signal_codes:
        recruitment_questions.append(
            "What local factors should be reviewed to "
            "understand the number of children currently in "
            "care relative to currently licensed foster homes "
            f"in {county.county_name}?"
        )
    if county.renewals_without_recent_activity > 0:
        engagement_questions.append(
            f"{county.renewals_without_recent_activity} currently "
            f"licensed homes in {county.county_name} County have "
            "both a renewal date within 90 days and no recorded "
            "foster-home placement activity during the previous "
            "90 days. What renewal outreach or provider support "
            "is already planned for these homes?"
        )

    if "high_share_without_recent_activity" in signal_codes:
        engagement_questions.append(
            "What factors may explain why some currently "
            "licensed homes have no recorded foster-home "
            "placement activity in the previous 90 days?"
        )

    if "low_median_observed_active_day_rate" in signal_codes:
        engagement_questions.append(
            "What local information could help explain the "
            "observed active-day pattern among currently "
            f"licensed homes in {county.county_name}?"
        )

    if "high_renewal_share_90_days" in signal_codes:
        engagement_questions.append(
            "What renewal-related outreach or administrative "
            "questions should be reviewed for homes with "
            "renewal dates in the next 90 days?"
        )

    if outbound_count > 0 and inbound_count > 0:
        coordination_questions.append(
            "What coordination issues should be investigated "
            f"where children from {county.county_name} are "
            "placed elsewhere while homes in the county serve "
            "children from other counties?"
        )

    if county.limited_data:
        context_questions.append(
            "What additional local information would help "
            "interpret measures that have limited or unstable "
            f"denominators in {county.county_name}?"
        )

    trend_change = calculate_trend_change(monthly_trends)

    if trend_change is not None:
        previous_ratio, current_ratio, percent_change = trend_change

        if abs(percent_change) >= TREND_STABLE_PERCENT_CHANGE:
            direction = "increased" if percent_change > 0 else "decreased"

            recruitment_questions.append(
                f"{county.county_name} County's children-per-home "
                f"ratio {direction} from {previous_ratio:.1f} to "
                f"{current_ratio:.1f} over the previous 12 months. "
                "Was the change driven primarily by the number of "
                "children in care, the number of licensed homes, "
                "or both?"
            )

    selected: list[str] = []

    # Preserve representation from recruitment, engagement,
    # and coordination when all are applicable.
    for question_group in (
        recruitment_questions,
        engagement_questions,
        coordination_questions,
    ):
        if question_group and len(selected) < MAXIMUM_CONTEXTUAL_QUESTIONS:
            selected.append(question_group[0])

    remaining_questions = (
        recruitment_questions[1:]
        + engagement_questions[1:]
        + coordination_questions[1:]
        + context_questions
    )

    for question in remaining_questions:
        if len(selected) >= MAXIMUM_CONTEXTUAL_QUESTIONS:
            break

        if question not in selected:
            selected.append(question)

    if not selected:
        selected.append(
            "What local factors should be reviewed to "
            "understand the current foster-home capacity "
            f"pattern in {county.county_name}?"
        )

    return selected


def build_county_questions(
    *,
    county: CountyAggregate,
    signal_codes: set[str],
    age_evidence: tuple[str, ...],
    outbound_count: int,
    inbound_count: int,
    monthly_trends: tuple[CountyMonthlyTrend, ...],
) -> tuple[CountyInvestigationQuestion, ...]:
    """Create the complete ordered question set for one county."""

    contextual_questions = select_contextual_questions(
        county=county,
        signal_codes=signal_codes,
        age_evidence=age_evidence,
        outbound_count=outbound_count,
        inbound_count=inbound_count,
        monthly_trends=monthly_trends,
    )

    question_texts = [
        *contextual_questions,
        (
            "What local information is not represented in "
            "these aggregate records and should be reviewed "
            f"before drawing conclusions about "
            f"{county.county_name}?"
        ),
        (
            "Which area warrants the next discussion in "
            f"{county.county_name}: recruitment, support for "
            "existing homes, or cross-county coordination?"
        ),
    ]

    return tuple(
        CountyInvestigationQuestion(
            county_slug=county.county_slug,
            display_order=index,
            question_text=question_text,
        )
        for index, question_text in enumerate(
            question_texts,
            start=1,
        )
    )


def validate_investigation_questions(
    questions: tuple[CountyInvestigationQuestion, ...],
    counties: tuple[CountyAggregate, ...],
) -> None:
    """Validate question counts, ordering, and county coverage."""

    known_county_slugs = {county.county_slug for county in counties}

    questions_by_county: defaultdict[
        str,
        list[CountyInvestigationQuestion],
    ] = defaultdict(list)

    for question in questions:
        if question.county_slug not in known_county_slugs:
            raise ValueError(
                "Investigation question references an unknown "
                f"county slug: {question.county_slug!r}"
            )

        if not question.question_text.strip():
            raise ValueError("Investigation question text cannot be empty.")

        if not (1 <= question.display_order <= MAXIMUM_QUESTIONS_PER_COUNTY):
            raise ValueError(
                "Investigation-question display order must be "
                "between 1 and "
                f"{MAXIMUM_QUESTIONS_PER_COUNTY}."
            )

        questions_by_county[question.county_slug].append(question)

    if set(questions_by_county) != known_county_slugs:
        missing_counties = known_county_slugs - set(questions_by_county)

        raise ValueError(
            "Investigation questions were not created for every "
            f"county. Missing: {sorted(missing_counties)}."
        )

    for county_slug, county_questions in questions_by_county.items():
        ordered_questions = sorted(
            county_questions,
            key=lambda question: question.display_order,
        )

        question_count = len(ordered_questions)

        if not (
            MINIMUM_QUESTIONS_PER_COUNTY
            <= question_count
            <= MAXIMUM_QUESTIONS_PER_COUNTY
        ):
            raise ValueError(
                "Each county must have between "
                f"{MINIMUM_QUESTIONS_PER_COUNTY} and "
                f"{MAXIMUM_QUESTIONS_PER_COUNTY} questions. "
                f"County: {county_slug}; "
                f"count: {question_count}."
            )

        expected_orders = list(range(1, question_count + 1))

        actual_orders = [question.display_order for question in ordered_questions]

        if actual_orders != expected_orders:
            raise ValueError(
                "Investigation-question display order must be "
                f"contiguous for {county_slug}. "
                f"Received: {actual_orders}."
            )

        question_texts = [question.question_text for question in ordered_questions]

        if len(question_texts) != len(set(question_texts)):
            raise ValueError(
                "A county cannot contain duplicate "
                f"investigation questions: {county_slug}."
            )


def derive_county_investigation_questions(
    counties: tuple[CountyAggregate, ...],
    age_alignments: tuple[CountyAgeAlignment, ...],
    placement_flows: tuple[CountyPlacementFlow, ...],
    signals: tuple[CountySignal, ...],
    monthly_trends: tuple[CountyMonthlyTrend, ...],
) -> tuple[CountyInvestigationQuestion, ...]:
    """Derive deterministic questions for every county."""

    county_name_by_slug = {
        county.county_slug: county.county_name for county in counties
    }

    if len(county_name_by_slug) != len(counties):
        raise ValueError("County aggregates contain duplicate county slugs.")

    known_county_slugs = set(county_name_by_slug)

    unknown_age_counties = {
        alignment.county_slug
        for alignment in age_alignments
        if alignment.county_slug not in known_county_slugs
    }

    if unknown_age_counties:
        raise ValueError(
            "Age alignments reference unknown counties: "
            f"{sorted(unknown_age_counties)}."
        )

    unknown_signal_counties = {
        signal.county_slug
        for signal in signals
        if signal.county_slug not in known_county_slugs
    }

    if unknown_signal_counties:
        raise ValueError(
            "County signals reference unknown counties: "
            f"{sorted(unknown_signal_counties)}."
        )

    signal_codes_by_county = group_signal_codes(signals)

    age_evidence_by_county = group_age_evidence(age_alignments)

    (
        outbound_counts,
        inbound_counts,
    ) = calculate_cross_county_counts(
        placement_flows,
        county_name_by_slug,
    )

    questions: list[CountyInvestigationQuestion] = []
    monthly_trends_by_county = group_monthly_trends(monthly_trends)

    for county in sorted(
        counties,
        key=lambda item: item.county_slug,
    ):
        questions.extend(
            build_county_questions(
                county=county,
                signal_codes=signal_codes_by_county.get(
                    county.county_slug,
                    set(),
                ),
                age_evidence=age_evidence_by_county.get(
                    county.county_slug,
                    (),
                ),
                outbound_count=outbound_counts.get(
                    county.county_slug,
                    0,
                ),
                inbound_count=inbound_counts.get(
                    county.county_slug,
                    0,
                ),
                monthly_trends=monthly_trends_by_county.get(
                    county.county_slug,
                    (),
                ),
            )
        )

    result = tuple(questions)

    validate_investigation_questions(
        result,
        counties,
    )

    return result
