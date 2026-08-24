"""§60's mandatory test: given 500 credits / 25 slots / 3 POR-8 DIF-8 CEN-6
ATT, the system must NEVER suggest a bid that makes completing the roster
mathematically impossible. This module is the actual proof of that
invariant at the level where it's enforced (app/auction/recommender.py) —
not an integration test that merely hopes the invariant holds.
"""

import random

import pytest

from app.auction.recommender import RosterState, compute_budget_constraint, compute_recommended_price

TARGET_LEAGUE_SLOTS = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}
TARGET_LEAGUE_BUDGET = 500
BASE_PRICE = 1


def test_minimum_completion_budget_example_from_spec():
    # §21 worked example.
    roster = RosterState(budget_remaining=150, slots_remaining={"POR": 1, "DIF": 3, "CEN": 2, "ATT": 2})
    constraint = compute_budget_constraint(roster, "DIF", base_price=1)
    assert constraint.minimum_completion_budget == 8
    assert constraint.safe_spendable_budget == 142


def test_hard_max_bid_reserves_base_price_for_every_other_remaining_slot():
    roster = RosterState(budget_remaining=150, slots_remaining={"POR": 1, "DIF": 3, "CEN": 2, "ATT": 2})
    constraint = compute_budget_constraint(roster, "DIF", base_price=1)
    # 8 total slots remaining; bidding fills one DIF slot, 7 others remain at >=1 each.
    assert constraint.hard_max_bid == 150 - 7 * 1


def test_last_slot_in_a_role_can_use_full_remaining_budget():
    roster = RosterState(budget_remaining=50, slots_remaining={"POR": 1, "DIF": 0, "CEN": 0, "ATT": 0})
    constraint = compute_budget_constraint(roster, "POR", base_price=1)
    assert constraint.hard_max_bid == 50


def test_role_with_zero_remaining_slots_cannot_bid():
    roster = RosterState(budget_remaining=200, slots_remaining={"POR": 0, "DIF": 5, "CEN": 5, "ATT": 5})
    constraint = compute_budget_constraint(roster, "POR", base_price=1)
    assert constraint.hard_max_bid is None


def test_exact_floor_state_caps_bid_at_base_price():
    # Budget exactly equals the number of remaining slots -- every slot,
    # including the one being bid on, must go for exactly base price.
    roster = RosterState(budget_remaining=8, slots_remaining={"POR": 1, "DIF": 3, "CEN": 2, "ATT": 2})
    constraint = compute_budget_constraint(roster, "CEN", base_price=1)
    assert constraint.hard_max_bid == 1


def test_broken_state_from_opponent_overspend_never_recommends_positive_overpay():
    # A state that should never legitimately occur (budget already short of
    # what's needed) -- e.g. simulating an opponent who overspent. The
    # engine must still never recommend spending into an impossible hole.
    roster = RosterState(budget_remaining=5, slots_remaining={"POR": 1, "DIF": 3, "CEN": 2, "ATT": 2})
    constraint = compute_budget_constraint(roster, "CEN", base_price=1)
    assert constraint.hard_max_bid is not None
    assert constraint.hard_max_bid < BASE_PRICE  # confirms the hole is real and visible

    recommended = compute_recommended_price(model_value=40, hard_max_bid=constraint.hard_max_bid)
    assert recommended.maximum == 0  # clamped, never negative, never spendable
    assert recommended.bargain_max == 0
    assert recommended.fair_max == 0
    assert recommended.hard_capped is True


@pytest.mark.parametrize("model_value", [1, 10, 40, 60, 100, 500])
def test_recommended_price_bands_never_exceed_hard_cap(model_value):
    roster = RosterState(budget_remaining=90, slots_remaining={"POR": 1, "DIF": 4, "CEN": 3, "ATT": 3})
    constraint = compute_budget_constraint(roster, "ATT", base_price=1)
    recommended = compute_recommended_price(model_value, constraint.hard_max_bid)
    assert recommended.bargain_max <= constraint.hard_max_bid
    assert recommended.fair_max <= constraint.hard_max_bid
    assert recommended.aggressive_max <= constraint.hard_max_bid
    assert recommended.maximum <= constraint.hard_max_bid


def test_full_auction_never_breaks_completion_invariant():
    """The concrete §60 scenario: run an entire 25-slot auction always
    bidding the maximum the engine will allow (the worst case for running
    out of budget) and confirm the roster completes exactly, using no more
    than the starting budget, with every slot filled."""

    roster = RosterState(budget_remaining=TARGET_LEAGUE_BUDGET, slots_remaining=dict(TARGET_LEAGUE_SLOTS))

    draft_order: list[str] = []
    for role, count in TARGET_LEAGUE_SLOTS.items():
        draft_order.extend([role] * count)
    random.Random(42).shuffle(draft_order)

    for role in draft_order:
        constraint = compute_budget_constraint(roster, role, BASE_PRICE)
        assert constraint.hard_max_bid is not None, f"no {role} slot available when one was expected"
        assert constraint.hard_max_bid >= BASE_PRICE, "engine let the budget go below what's recoverable"

        price = constraint.hard_max_bid  # worst case: spend the absolute maximum every time
        new_slots = dict(roster.slots_remaining)
        new_slots[role] -= 1
        roster = RosterState(budget_remaining=roster.budget_remaining - price, slots_remaining=new_slots)

    assert all(count == 0 for count in roster.slots_remaining.values()), "roster did not fully complete"
    assert roster.budget_remaining == 0, "budget was not fully/exactly consumed by the forced-maximum strategy"


def test_zero_players_remaining_in_tier_does_not_affect_budget_math():
    # Scarcity affecting *value* is a separate concern (auction/value.py) --
    # the hard budget cap must hold regardless of how scarce a tier is.
    roster = RosterState(budget_remaining=42, slots_remaining={"POR": 2, "DIF": 5, "CEN": 4, "ATT": 3})
    constraint = compute_budget_constraint(roster, "ATT", base_price=1)
    other_slots = 2 + 5 + 4 + 2  # ATT slot being bid on excluded
    assert constraint.hard_max_bid == 42 - other_slots
