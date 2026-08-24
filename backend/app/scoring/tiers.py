"""Dynamic per-role tiering (§13). Tier count/boundaries are NOT fixed —
they come from where the real gaps in FantaScore fall, targeting roughly
TIER_TARGET_SIZE players per tier as a starting point. This is a v1
heuristic; §17/§18 (replacement level, scarcity) will later feed back into
where boundaries should sit, not just raw score gaps.
"""

from dataclasses import dataclass

from app.scoring.model_config import TIER_MAX_COUNT, TIER_MIN_COUNT, TIER_TARGET_SIZE
from app.scoring.role_models import validate_role

ROLE_PREFIX = {"POR": "P", "DIF": "D", "CEN": "C", "ATT": "A"}


@dataclass(frozen=True)
class TierResult:
    player_id: int
    tier_label: str
    tier_rank: int  # 1 = best tier in the role


def assign_tiers(role: str, scores: dict[int, float]) -> dict[int, TierResult]:
    role = validate_role(role)
    prefix = ROLE_PREFIX[role]

    if not scores:
        return {}

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)  # [(player_id, score), ...] desc
    n = len(ranked)

    if n == 1:
        return {ranked[0][0]: TierResult(ranked[0][0], f"{prefix}1", 1)}

    target_tier_count = max(TIER_MIN_COUNT, min(TIER_MAX_COUNT, round(n / TIER_TARGET_SIZE)))
    target_tier_count = min(target_tier_count, n)  # never more tiers than players
    boundary_count = target_tier_count - 1

    # Gaps between consecutive (sorted desc) scores; larger gap = more
    # natural break point. Index i is the gap AFTER ranked[i].
    gaps = [(ranked[i][1] - ranked[i + 1][1], i) for i in range(n - 1)]
    chosen_boundaries = sorted(idx for _, idx in sorted(gaps, reverse=True)[:boundary_count])

    results: dict[int, TierResult] = {}
    tier_rank = 1
    start = 0
    boundaries = chosen_boundaries + [n - 1]
    for boundary in boundaries:
        for i in range(start, boundary + 1):
            pid = ranked[i][0]
            results[pid] = TierResult(pid, f"{prefix}{tier_rank}", tier_rank)
        start = boundary + 1
        tier_rank += 1

    return results
