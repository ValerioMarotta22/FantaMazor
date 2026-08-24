import pytest

from app.auction.replacement import tier_premium_multiplier
from app.auction.scarcity import compute_scarcity
from app.auction.simulator import SimulationTarget, run_auction_simulation
from app.auction.value import compute_model_auction_value


def test_scarcity_high_when_many_slots_few_players():
    result = compute_scarcity(players_remaining_in_tier=2, slots_still_needed_league_wide=6)
    assert result.level == "HIGH"


def test_scarcity_low_when_many_players_few_slots():
    result = compute_scarcity(players_remaining_in_tier=20, slots_still_needed_league_wide=2)
    assert result.level == "LOW"


def test_scarcity_handles_zero_players_remaining():
    result = compute_scarcity(players_remaining_in_tier=0, slots_still_needed_league_wide=3)
    assert result.level == "HIGH"
    assert result.ratio == float("inf")


def test_tier_premium_top_tier_beats_bottom_tier():
    top = tier_premium_multiplier(tier_rank=1, tier_count=5)
    bottom = tier_premium_multiplier(tier_rank=5, tier_count=5)
    assert top > bottom
    assert bottom == 1.0


def test_model_auction_value_uses_market_average_when_available():
    result = compute_model_auction_value(
        player_id=1,
        role="ATT",
        tier_rank=1,
        tier_count=4,
        scarcity_level="MEDIUM",
        total_budget_all_members=5000,
        market_average=45.0,
    )
    assert result.components["base_source"] == "local_market_average"
    assert result.model_value > 45.0  # tier premium applied on top


def test_model_auction_value_falls_back_to_fvm_heuristic():
    result = compute_model_auction_value(
        player_id=1,
        role="ATT",
        tier_rank=2,
        tier_count=4,
        scarcity_level="LOW",
        total_budget_all_members=5000,
        fvm=100,
        sum_fvm_in_role=1000,
    )
    assert result.components["base_source"] == "fvm_heuristic"
    assert result.model_value is not None


def test_model_auction_value_unavailable_when_no_data():
    result = compute_model_auction_value(
        player_id=1, role="ATT", tier_rank=1, tier_count=1, scarcity_level="UNKNOWN", total_budget_all_members=5000
    )
    assert result.model_value is None
    assert result.components["base_source"] == "unavailable"


def test_simulator_rejects_invalid_iteration_count():
    with pytest.raises(ValueError):
        run_auction_simulation(targets=[], other_slots_needed=0, base_price=1, budget=100, iterations=250)


def test_simulator_is_deterministic_with_seed():
    targets = [SimulationTarget(player_id=1, role="ATT", model_value=40)]
    a = run_auction_simulation(targets, other_slots_needed=5, base_price=1, budget=100, iterations=100, seed=7)
    b = run_auction_simulation(targets, other_slots_needed=5, base_price=1, budget=100, iterations=100, seed=7)
    assert a == b


def test_simulator_completion_probability_drops_with_tighter_budget():
    targets = [SimulationTarget(player_id=1, role="ATT", model_value=40)]
    loose = run_auction_simulation(targets, other_slots_needed=5, base_price=1, budget=100, iterations=500, seed=1)
    tight = run_auction_simulation(targets, other_slots_needed=5, base_price=1, budget=46, iterations=500, seed=1)
    assert tight.completion_probability <= loose.completion_probability
