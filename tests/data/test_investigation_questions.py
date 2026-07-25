"""Tests for deterministic county investigation questions."""

from __future__ import annotations

from dataclasses import replace

from scripts.etl.aggregate_age_alignment import (
    CountyAgeAlignment,
)
from scripts.etl.aggregate_investigation_questions import (
    derive_county_investigation_questions,
)
from scripts.etl.aggregate_placement_flows import (
    CountyPlacementFlow,
)
from scripts.etl.classify_opportunities import CountySignal
from tests.data.factories import make_county


def test_creates_three_default_questions() -> None:
    """Create a useful minimum set when no signals are present."""

    questions = derive_county_investigation_questions(
        (make_county(),),
        (),
        (),
        (),
        (),
    )

    assert len(questions) == 3

    assert [question.display_order for question in questions] == [
        1,
        2,
        3,
    ]

    assert all(question.county_slug == "example" for question in questions)


def test_combines_recruitment_engagement_and_flow_patterns() -> None:
    """Represent multiple applicable dimensions without exceeding five."""

    counties = (
        replace(
            make_county(),
            limited_data=False,
        ),
        make_county(
            county_slug="second",
            county_name="Second",
        ),
    )

    age_alignments = (
        CountyAgeAlignment(
            county_slug="example",
            age_band="13-17",
            current_children=20,
            preference_matching_homes=5,
            children_per_matching_home=4.0,
            limited_data=False,
            recruitment_evidence=True,
            statewide_p75_threshold=3.5,
        ),
    )

    signals = (
        CountySignal(
            county_slug="example",
            focus="recruitment",
            signal_code="high_out_of_county_foster_rate",
            signal_value=0.8,
            threshold_value=0.6,
        ),
        CountySignal(
            county_slug="example",
            focus="engagement",
            signal_code="high_share_without_recent_activity",
            signal_value=0.3,
            threshold_value=0.2,
        ),
    )

    flows = (
        CountyPlacementFlow(
            origin_county_slug="example",
            destination_county_name="Second",
            placement_count=10,
            placement_share=1.0,
            is_local=False,
        ),
        CountyPlacementFlow(
            origin_county_slug="second",
            destination_county_name="Example",
            placement_count=5,
            placement_share=1.0,
            is_local=False,
        ),
    )

    questions = derive_county_investigation_questions(
        counties,
        age_alignments,
        flows,
        signals,
        (),
    )

    example_questions = [
        question for question in questions if question.county_slug == "example"
    ]

    assert len(example_questions) == 5

    question_text = " ".join(question.question_text for question in example_questions)

    assert "ages 13 to 17" in question_text
    assert "previous 90 days" in question_text
    assert "serve children from other counties" in question_text


def test_questions_are_deterministic() -> None:
    """Return identical ordering for identical aggregate inputs."""

    counties = (
        make_county(
            county_slug="second",
            county_name="Second",
        ),
        make_county(),
    )

    first = derive_county_investigation_questions(
        counties,
        (),
        (),
        (),
        (),
    )

    second = derive_county_investigation_questions(
        counties,
        (),
        (),
        (),
        (),
    )

    assert first == second

    assert [question.county_slug for question in first[:3]] == [
        "example",
        "example",
        "example",
    ]


def test_limited_data_creates_context_question() -> None:
    """Ask for local context when denominators are unstable."""

    questions = derive_county_investigation_questions(
        (make_county(),),
        (),
        (),
        (),
        (),
    )

    assert any(
        "limited or unstable denominators" in question.question_text
        for question in questions
    )


def test_every_county_receives_three_to_five_questions() -> None:
    """Create a complete question set for every county."""

    counties = (
        make_county(),
        make_county(
            county_slug="second",
            county_name="Second",
        ),
        make_county(
            county_slug="third",
            county_name="Third",
        ),
    )

    questions = derive_county_investigation_questions(
        counties,
        (),
        (),
        (),
        (),
    )

    for county in counties:
        county_questions = [
            question
            for question in questions
            if question.county_slug == county.county_slug
        ]

        assert 3 <= len(county_questions) <= 5

        assert [question.display_order for question in county_questions] == list(
            range(
                1,
                len(county_questions) + 1,
            )
        )
