"""AuctionSimulator (§23) — Monte Carlo over a candidate shortlist.

Scope note (v1): this simulates price uncertainty around your OWN target
list (the "what if I go for these players" question), not a full 10-agent
multi-participant auction — modeling nine independent opponents' bidding
behavior realistically needs local-league transaction history this app
hasn't accumulated yet (§7/§44). Full opponent simulation is a natural
MVP2/3 extension once there's enough transaction data to calibrate it.
"""

import random
from dataclasses import dataclass

VALID_ITERATION_COUNTS = (100, 500, 1000)


@dataclass(frozen=True)
class SimulationTarget:
    player_id: int
    role: str
    model_value: float


@dataclass(frozen=True)
class SimulationResult:
    iterations: int
    completion_probability: float
    total_cost_p10: float
    total_cost_p50: float
    total_cost_p90: float
    remaining_budget_p50: float


def run_auction_simulation(
    targets: list[SimulationTarget],
    other_slots_needed: int,
    base_price: float,
    budget: float,
    iterations: int = 500,
    price_noise_pct: float = 0.15,
    seed: int | None = None,
) -> SimulationResult:
    if iterations not in VALID_ITERATION_COUNTS:
        raise ValueError(f"iterations must be one of {VALID_ITERATION_COUNTS}")

    rng = random.Random(seed)
    total_costs: list[float] = []
    completions = 0

    for _ in range(iterations):
        cost = 0.0
        for target in targets:
            noise = rng.gauss(1.0, price_noise_pct)
            price = max(base_price, target.model_value * noise)
            cost += price
        cost += other_slots_needed * base_price
        total_costs.append(cost)
        if cost <= budget:
            completions += 1

    total_costs.sort()

    def percentile(p: float) -> float:
        idx = min(len(total_costs) - 1, int(len(total_costs) * p))
        return round(total_costs[idx], 1)

    p50 = percentile(0.50)
    return SimulationResult(
        iterations=iterations,
        completion_probability=round(completions / iterations, 3),
        total_cost_p10=percentile(0.10),
        total_cost_p50=p50,
        total_cost_p90=percentile(0.90),
        remaining_budget_p50=round(budget - p50, 1),
    )
