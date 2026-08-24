from app.scoring.fanta_score import compute_fanta_scores
from app.scoring.model_config import FANTA_SCORE_WEIGHTS
from app.scoring.role_models import PlayerFeatures
from app.scoring.tiers import assign_tiers


def test_weights_are_centralized_and_sum_to_one_per_role():
    for role, weights in FANTA_SCORE_WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, f"{role} weights must sum to 1.0"


def test_missing_features_are_excluded_not_treated_as_zero():
    players = {
        1: PlayerFeatures(fantasy_average=7.0, average_rating=6.5, goals=5, assists=3, appearances=30, fvm=45),
        # Player 2 has only fvm, but it's the BEST fvm in the pool -- if
        # missing stats were silently treated as 0 instead of excluded,
        # this player would incorrectly score near the bottom despite
        # having the top value on the one feature we actually know about.
        2: PlayerFeatures(fvm=50),
    }
    results = compute_fanta_scores("ATT", players)
    assert results[2].score > results[1].score
    # Only the fvm component should be present in player 2's breakdown.
    assert set(results[2].components.keys()) <= {"fvm"}


def test_player_with_no_data_gets_pool_midpoint_not_a_fabricated_score():
    players = {1: PlayerFeatures(fantasy_average=7.0), 2: PlayerFeatures()}
    results = compute_fanta_scores("CEN", players)
    assert results[2].score == 50.0
    assert results[2].components.get("note") == "insufficient data"


def test_normalization_puts_best_player_at_top_of_range():
    players = {
        1: PlayerFeatures(fantasy_average=8.0, goals=20, assists=10, appearances=38, average_rating=7.5, fvm=100),
        2: PlayerFeatures(fantasy_average=6.0, goals=2, assists=1, appearances=15, average_rating=5.8, fvm=20),
    }
    results = compute_fanta_scores("ATT", players)
    assert results[1].score > results[2].score


def test_tiers_are_gap_based_not_fixed_bucket_size():
    # A clear gap between a cluster of strong scores and one much weaker score.
    scores = {1: 90.0, 2: 88.0, 3: 87.0, 4: 40.0}
    tiers = assign_tiers("ATT", scores)
    assert tiers[4].tier_label != tiers[1].tier_label
    assert tiers[1].tier_rank < tiers[4].tier_rank


def test_tiers_handle_single_player():
    tiers = assign_tiers("POR", {1: 75.0})
    assert tiers[1].tier_label == "P1"
    assert tiers[1].tier_rank == 1


def test_tiers_use_role_specific_prefix():
    tiers = assign_tiers("DIF", {1: 70.0, 2: 60.0})
    assert all(t.tier_label.startswith("D") for t in tiers.values())
