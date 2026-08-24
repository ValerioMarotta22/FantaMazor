"""Role-specific FantaScore models (§12). Each role shares the same
normalize-then-weight engine (see fanta_score.py) but a different feature
set/weighting from model_config.py — a midfielder and a goalkeeper should
never be scored on the same curve.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerFeatures:
    """Whatever inputs are actually available for a player. Any field left
    as None is excluded from scoring, never treated as 0 (§55)."""

    fantasy_average: float | None = None
    average_rating: float | None = None
    goals: float | None = None
    assists: float | None = None
    appearances: float | None = None
    fvm: float | None = None


ROLE_MODELS = {"POR", "DIF", "CEN", "ATT"}


def validate_role(role: str) -> str:
    role = role.strip().upper()
    if role not in ROLE_MODELS:
        raise ValueError(f"unknown role '{role}', expected one of {sorted(ROLE_MODELS)}")
    return role
