"""FantaScore v1 (§11) — deterministic, explainable, not ML (§42: start
simple, earn the right to add ML later via backtesting).

For a role's player pool: each feature is min-max normalized across players
who have that feature (missing values are simply excluded from that
player's weighted sum, and the remaining weights renormalize to still sum
to 1 — a player scored on 3 of 4 features is never penalized for the 4th
being unknown). The result is scaled to 0-100 and is *relative to the role
pool it was computed over*, matching §11's definition of FantaScore as
"how useful/convenient this player is versus others at the same role", not
an absolute strength rating.
"""

from dataclasses import dataclass, field

from app.scoring.model_config import FANTA_SCORE_WEIGHTS
from app.scoring.role_models import PlayerFeatures, validate_role


@dataclass(frozen=True)
class FantaScoreResult:
    player_id: int
    score: float
    components: dict = field(default_factory=dict)


def _minmax_normalize(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return dict.fromkeys(values, 0.5)
    return {pid: (v - lo) / (hi - lo) for pid, v in values.items()}


def compute_fanta_scores(role: str, players: dict[int, PlayerFeatures]) -> dict[int, FantaScoreResult]:
    role = validate_role(role)
    weights = FANTA_SCORE_WEIGHTS[role]

    # Gather raw values per feature across the pool, normalize independently.
    normalized_by_feature: dict[str, dict[int, float]] = {}
    for feature_name in weights:
        raw = {
            pid: getattr(feats, feature_name)
            for pid, feats in players.items()
            if getattr(feats, feature_name) is not None
        }
        normalized_by_feature[feature_name] = _minmax_normalize(raw)

    results: dict[int, FantaScoreResult] = {}
    for pid in players:
        present_weights = {
            f: w for f, w in weights.items() if pid in normalized_by_feature[f]
        }
        weight_sum = sum(present_weights.values())
        components: dict[str, float] = {}
        if weight_sum == 0:
            # No usable data at all for this player: score stays at the
            # pool midpoint rather than being fabricated.
            results[pid] = FantaScoreResult(pid, 50.0, {"note": "insufficient data"})
            continue

        weighted_sum = 0.0
        for feature_name, weight in present_weights.items():
            normalized_value = normalized_by_feature[feature_name][pid]
            renormalized_weight = weight / weight_sum
            contribution = normalized_value * renormalized_weight
            weighted_sum += contribution
            components[feature_name] = round(contribution * 100, 2)

        results[pid] = FantaScoreResult(pid, round(weighted_sum * 100, 2), components)

    return results
