"""Centralized, documented model configuration (§11: "Centralizzare tutti i
pesi in una configurazione: model_config"). Nothing here is buried in
scoring logic — change a weight by editing this file (or, once persisted,
the `model_versions.config` row) rather than the algorithm.

FANTA_SCORE_WEIGHTS v1 rationale: MVP1 only has listone quotations
(quotation/FVM) and season stat lines available (no schedule/injury/context
data yet — those arrive in MVP2 and will add Context/Risk/Trend components
per §11). So v1 only scores Performance + Opportunity + Bonus potential:
  - fantasy_average / average_rating capture realized performance
  - goals / assists capture bonus-driving output, weighted higher for
    attacking roles where they matter more
  - appearances is a crude opportunity proxy (minutes data is often absent
    from listone-only imports)
  - fvm is a small market-prior nudge so scores don't wildly diverge from
    consensus when our own stat sample is thin
Each role's weights sum to 1.0. These are a documented starting point,
meant to be tuned by backtesting (§43/§44) once enough seasons of local
data exist — not asserted as "correct".
"""

FANTA_SCORE_MODEL_VERSION = "fanta-score-v1"

FANTA_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "POR": {
        "fantasy_average": 0.45,
        "average_rating": 0.25,
        "appearances": 0.15,
        "fvm": 0.15,
    },
    "DIF": {
        "fantasy_average": 0.35,
        "average_rating": 0.15,
        "goals": 0.15,
        "assists": 0.15,
        "appearances": 0.10,
        "fvm": 0.10,
    },
    "CEN": {
        "fantasy_average": 0.30,
        "average_rating": 0.10,
        "goals": 0.20,
        "assists": 0.20,
        "appearances": 0.10,
        "fvm": 0.10,
    },
    "ATT": {
        "fantasy_average": 0.25,
        "average_rating": 0.05,
        "goals": 0.35,
        "assists": 0.15,
        "appearances": 0.10,
        "fvm": 0.10,
    },
}

TIER_TARGET_SIZE = 4  # aim for ~4 players per tier before gap-based adjustment
TIER_MIN_COUNT = 3
TIER_MAX_COUNT = 8

# The target league's exact profile (§1), seeded as the default LeagueSettings
# preset. LeagueSettings.config is what the app actually reads at runtime —
# this constant only exists to seed that row; nothing downstream hardcodes it.
DEFAULT_LEAGUE_SETTINGS_CONFIG: dict = {
    "participants": 10,
    "starting_budget": 500,
    "roster_size": 25,
    "roster_slots": {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6},
    "base_price": 1,
    "auction_type": "random_by_role",
    "free_rebids": True,
    "allow_budget_overflow": False,
    "require_full_roster_before_budget_zero": True,
    "no_waivers_during_auction_session": True,
    "no_trades_during_auction_session": True,
    "second_auction_after_transfer_window": True,
    "winter_repair_extra_budget": 50,
    "waivers_per_role": 2,
    "allowed_modules": ["3-5-2", "3-4-3", "4-5-1", "4-4-2", "4-3-3", "5-3-2", "5-4-1"],
    "bench_size_limited": True,
    "max_substitutions": 5,
    "role_priority_substitutions": True,
    "no_default_reserve": True,
    "switch_plus_cross_role_allowed": True,
    "scoring": {
        "goal_scored": 3,
        "goal_conceded": -1,
        "penalty_scored": 3,
        "penalty_missed": -3,
        "penalty_saved": 3,
        "yellow_card": -0.5,
        "red_card": -1,
        "assist": 1,
        "own_goal": -2,
        "clean_sheet_bonus": 1,
        "goal_modifier_thresholds": {"1_goal": 6, "2_goals": 72},
    },
}
