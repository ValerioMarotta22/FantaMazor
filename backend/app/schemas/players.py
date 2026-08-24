from pydantic import BaseModel


class PlayerResponse(BaseModel):
    id: int
    name: str
    role: str
    team_name: str | None
    status: str


class PlayerScoreResponse(BaseModel):
    player_id: int
    fanta_score: float | None
    tier_label: str | None
    components: dict
    model_version: str | None
    computed_at: str | None


class PlayerValueResponse(BaseModel):
    player_id: int
    model_value: float | None
    market_average: float | None
    components: dict
