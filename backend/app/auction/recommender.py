"""RecommendedPrice bands (§15) and the MinimumCompletionBudget / MaximumBid
hard invariant (§21). This module is the single place responsible for the
rule tested exhaustively in tests/test_budget_constraints.py:

    The system must never suggest a price that makes it mathematically
    impossible to fill every remaining roster slot.

Every band in RecommendedPrice (not just "maximum") is clamped to the hard
cap, so no part of the UI can ever surface a number above what's safe.
"""

from dataclasses import dataclass

BARGAIN_RATIO = 0.80
FAIR_RATIO = 1.00
AGGRESSIVE_RATIO = 1.25


@dataclass(frozen=True)
class RosterState:
    budget_remaining: float
    slots_remaining: dict[str, int]  # role -> empty slots still to fill


@dataclass(frozen=True)
class BudgetConstraint:
    minimum_completion_budget: float
    safe_spendable_budget: float
    # None means the buyer has 0 remaining slots at this role — they cannot bid at all.
    hard_max_bid: float | None


def compute_budget_constraint(roster: RosterState, role: str, base_price: float) -> BudgetConstraint:
    total_remaining_slots = sum(roster.slots_remaining.values())
    minimum_completion_budget = total_remaining_slots * base_price
    safe_spendable_budget = roster.budget_remaining - minimum_completion_budget

    role_slots_remaining = roster.slots_remaining.get(role, 0)
    if role_slots_remaining <= 0:
        return BudgetConstraint(minimum_completion_budget, safe_spendable_budget, None)

    # This pick fills one of the role's slots; every OTHER remaining slot
    # (any role) still needs at least base_price reserved for it.
    other_slots = total_remaining_slots - 1
    hard_max_bid = roster.budget_remaining - other_slots * base_price

    return BudgetConstraint(minimum_completion_budget, safe_spendable_budget, hard_max_bid)


@dataclass(frozen=True)
class RecommendedPrice:
    bargain_max: float
    fair_max: float
    aggressive_max: float
    maximum: float  # hard-capped — never exceeds budget_constraint.hard_max_bid
    hard_capped: bool  # True if the budget constraint, not the model value, set `maximum`


def compute_recommended_price(model_value: float, hard_max_bid: float | None) -> RecommendedPrice:
    def clamp(x: float) -> float:
        capped = x if hard_max_bid is None else min(x, hard_max_bid)
        return round(max(capped, 0.0), 1)

    theoretical_bargain = model_value * BARGAIN_RATIO
    theoretical_fair = model_value * FAIR_RATIO
    theoretical_aggressive = model_value * AGGRESSIVE_RATIO

    aggressive_max = clamp(theoretical_aggressive)
    hard_capped = hard_max_bid is not None and theoretical_aggressive > hard_max_bid

    return RecommendedPrice(
        bargain_max=clamp(theoretical_bargain),
        fair_max=clamp(theoretical_fair),
        aggressive_max=aggressive_max,
        maximum=aggressive_max,
        hard_capped=hard_capped,
    )
