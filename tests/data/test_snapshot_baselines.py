from scripts.etl.derive_snapshot import derive_snapshot_baselines
from scripts.etl.load_sources import load_sources


def test_source_identifiers_are_unique_and_foster_providers_join() -> None:
    data = load_sources()

    child_ids = [child.id_child for child in data.children]
    provider_ids = [provider.id_provider for provider in data.providers]
    known_provider_ids = set(provider_ids)
    foster_provider_ids = {
        placement.id_provider
        for placement in data.placements
        if placement.resource_type == "foster_home"
        and placement.id_provider is not None
    }

    assert len(child_ids) == len(set(child_ids))
    assert len(provider_ids) == len(set(provider_ids))
    assert foster_provider_ids <= known_provider_ids


def test_current_snapshot_reconciles_to_locked_baselines() -> None:
    baselines = derive_snapshot_baselines(load_sources())

    assert baselines.source_children == 16_139
    assert baselines.source_placements == 51_994
    assert baselines.source_providers == 6_063
    assert baselines.current_children == 8_071
    assert baselines.current_placements == 8_071
    assert baselines.current_kin_placements == 3_688
    assert baselines.current_foster_home_placements == 4_343
    assert baselines.current_nonfamily_placements == 40
    assert baselines.current_foster_homes == 3_395
    assert baselines.homes_supporting_current_placement == 2_733
    assert baselines.homes_with_recent_activity == 3_170
    assert baselines.homes_without_recent_activity == 225
    assert baselines.local_current_foster_placements == 1_519
    assert baselines.out_of_county_current_foster_placements == 2_824
    assert baselines.local_current_foster_placement_rate == 1_519 / 4_343
    assert baselines.median_observed_active_day_rate == 0.6967113276492083
