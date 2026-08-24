"""ModelAuctionValue (§14) — the theoretical value of a player, distinct
from raw market average or FVM (§6: never treat market average as "the
correct price").

v1 formula: start from a market signal (local league transaction history if
we have it for this tier, otherwise a normalized-FVM heuristic scaled into
this league's actual budget), then apply the tier premium (replacement
level, §17) and scarcity multiplier (§18). Every component is returned in
`components` so the UI/API can show *why*, per §27.
"""

from dataclasses import dataclass

from app.auction.replacement import tier_premium_multiplier
from app.auction.scarcity import SCARCITY_MULTIPLIERS

# Default role budget-share heuristic, used ONLY as a fallback when there is
# no local market-average signal yet for a role/tier. Mirrors the "Balanced"
# strategy example from §16 — a documented starting point, not ground truth.
# It is what fraction of total league budget typically flows to each role.
DEFAULT_ROLE_BUDGET_SHARE = {"POR": 0.07, "DIF": 0.19, "CEN": 0.32, "ATT": 0.42}


@dataclass(frozen=True)
class AuctionValueResult:
    player_id: int
    model_value: float | None
    market_average: float | None
    components: dict


def compute_role_budget_pool(
    total_budget_all_members: float, role: str, role_share: dict[str, float] | None = None
) -> float:
    role_share = role_share or DEFAULT_ROLE_BUDGET_SHARE
    return total_budget_all_members * role_share[role]


def compute_model_auction_value(
    player_id: int,
    role: str,
    tier_rank: int,
    tier_count: int,
    scarcity_level: str,
    total_budget_all_members: float,
    fvm: float | None = None,
    sum_fvm_in_role: float | None = None,
    market_average: float | None = None,
    role_share: dict[str, float] | None = None,
) -> AuctionValueResult:
    if market_average is not None:
        base = market_average
        base_source = "local_market_average"
    elif fvm and sum_fvm_in_role:
        role_budget_pool = compute_role_budget_pool(total_budget_all_members, role, role_share)
        base = (fvm / sum_fvm_in_role) * role_budget_pool
        base_source = "fvm_heuristic"
    else:
        return AuctionValueResult(player_id, None, market_average, {"base_source": "unavailable"})

    tier_premium = tier_premium_multiplier(tier_rank, tier_count)
    scarcity_mult = SCARCITY_MULTIPLIERS.get(scarcity_level, 1.0)
    value = base * tier_premium * scarcity_mult

    return AuctionValueResult(
        player_id=player_id,
        model_value=round(value, 2),
        market_average=market_average,
        components={
            "base_source": base_source,
            "base_value": round(base, 2),
            "tier_premium_multiplier": round(tier_premium, 3),
            "scarcity_level": scarcity_level,
            "scarcity_multiplier": scarcity_mult,
        },
    )
