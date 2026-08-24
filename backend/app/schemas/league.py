from pydantic import BaseModel, ConfigDict


class LeagueSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    config: dict
    is_active: bool


class LeagueSettingsUpdateRequest(BaseModel):
    config: dict


class LeagueMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_admin: bool


class RosterPlayerResponse(BaseModel):
    player_id: int
    name: str
    role: str
    price: float


class MemberRosterResponse(BaseModel):
    member_id: int
    name: str
    budget_remaining: float
    slots_remaining: dict[str, int]
    players: list[RosterPlayerResponse]
