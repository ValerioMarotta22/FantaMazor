"""Replacement level (§17): a player in a higher tier is worth a premium
proportional to how far the drop to the next tier would hurt the squad.
v1 approximates this with a simple per-tier step multiplier rather than a
full marginal-value calculation — see value.py for how it's applied."""

TIER_PREMIUM_STEP = 0.08
TIER_PREMIUM_CAP = 0.40


def tier_premium_multiplier(tier_rank: int, tier_count: int) -> float:
    """tier_rank=1 is the best tier. Being in the top tier of a role with
    many tiers below it carries the largest premium; the bottom tier gets
    none."""
    if tier_count <= 1:
        return 1.0
    tiers_above_bottom = tier_count - tier_rank
    premium = min(TIER_PREMIUM_CAP, tiers_above_bottom * TIER_PREMIUM_STEP)
    return 1 + premium
