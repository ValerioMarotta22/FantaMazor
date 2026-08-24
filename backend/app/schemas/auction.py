from pydantic import BaseModel, ConfigDict


class CreateSessionRequest(BaseModel):
    name: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str


class TransactionRequest(BaseModel):
    player_id: int
    buyer_member_id: int
    price: float


class TransactionResponse(BaseModel):
    id: int
    player_id: int
    player_name: str
    role: str
    buyer_member_id: int
    buyer_name: str
    price: float
    budget_before: float
    budget_after: float
    remaining_slots: dict[str, int]


class BudgetConstraintResponse(BaseModel):
    minimum_completion_budget: float
    safe_spendable_budget: float
    hard_max_bid: float | None


class ScarcityResponse(BaseModel):
    level: str
    players_remaining_in_tier: int
    slots_still_needed_league_wide: int
    ratio: float


class RecommendedPriceResponse(BaseModel):
    bargain_max: float
    fair_max: float
    aggressive_max: float
    maximum: float
    hard_capped: bool


class RecommendationResponse(BaseModel):
    player_id: int
    role: str
    fanta_score: float | None
    tier_label: str | None
    model_value: float | None
    market_average: float | None
    recommended_price: RecommendedPriceResponse | None
    budget_constraint: BudgetConstraintResponse
    scarcity: ScarcityResponse
    warnings: list[str]


class MemberStateResponse(BaseModel):
    member_id: int
    name: str
    is_admin: bool
    budget_remaining: float
    slots_remaining: dict[str, int]


class SessionStateResponse(BaseModel):
    session_id: int
    status: str
    members: list[MemberStateResponse]


class SimulationTargetRequest(BaseModel):
    player_id: int
    role: str
    model_value: float


class SimulationRequest(BaseModel):
    targets: list[SimulationTargetRequest]
    other_slots_needed: int
    base_price: float
    budget: float
    iterations: int = 500
    price_noise_pct: float = 0.15


class SimulationResponse(BaseModel):
    iterations: int
    completion_probability: float
    total_cost_p10: float
    total_cost_p50: float
    total_cost_p90: float
    remaining_budget_p50: float
