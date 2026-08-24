"""Scarcity engine (§18): how many players are left in a tier versus how
many slots the whole league still needs at that role."""

from dataclasses import dataclass

HIGH_RATIO_THRESHOLD = 1.5
MEDIUM_RATIO_THRESHOLD = 0.8

SCARCITY_MULTIPLIERS = {"HIGH": 1.15, "MEDIUM": 1.0, "LOW": 0.9, "UNKNOWN": 1.0}


@dataclass(frozen=True)
class ScarcityResult:
    level: str  # LOW | MEDIUM | HIGH | UNKNOWN
    players_remaining_in_tier: int
    slots_still_needed_league_wide: int
    ratio: float


def compute_scarcity(players_remaining_in_tier: int, slots_still_needed_league_wide: int) -> ScarcityResult:
    if players_remaining_in_tier <= 0:
        ratio = float("inf") if slots_still_needed_league_wide > 0 else 0.0
    else:
        ratio = slots_still_needed_league_wide / players_remaining_in_tier

    if ratio >= HIGH_RATIO_THRESHOLD:
        level = "HIGH"
    elif ratio >= MEDIUM_RATIO_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ScarcityResult(level, players_remaining_in_tier, slots_still_needed_league_wide, ratio)
