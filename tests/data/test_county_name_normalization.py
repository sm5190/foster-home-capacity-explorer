"""Tests for canonical Illinois county names."""

from scripts.etl.load_sources import canonicalize_county_name


def test_canonicalizes_vermillion_to_vermilion() -> None:
    """Correct the known county spelling inconsistency."""

    assert canonicalize_county_name("Vermillion") == "Vermilion"


def test_preserves_valid_county_name() -> None:
    """Leave valid Illinois county names unchanged."""

    assert canonicalize_county_name("Cook") == "Cook"


def test_strips_surrounding_whitespace() -> None:
    """Remove accidental surrounding whitespace."""

    assert canonicalize_county_name("  Champaign  ") == "Champaign"
