from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auction.scarcity import compute_scarcity
from app.auction.value import compute_model_auction_value
from app.core.security import CurrentUser
from app.db.models import FantasyQuote, LeagueSettings, ModelVersion, Player, PlayerScore, PlayerTier, Season
from app.db.session import get_db
from app.schemas.players import PlayerResponse, PlayerScoreResponse, PlayerValueResponse
from app.scoring.model_config import FANTA_SCORE_MODEL_VERSION

router = APIRouter()


def _to_player_response(player: Player) -> PlayerResponse:
    return PlayerResponse(
        id=player.id,
        name=player.name,
        role=player.role,
        team_name=player.team.name if player.team else None,
        status=player.status,
    )


@router.get("", response_model=list[PlayerResponse])
def list_players(
    role: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _user: str = CurrentUser,
):
    query = db.query(Player)
    if role:
        query = query.filter(Player.role == role.upper())
    if search:
        query = query.filter(Player.normalized_name.ilike(f"%{search.lower()}%"))
    # A full Serie A listone is ~500-550 players; 2000 leaves headroom
    # without turning into an unbounded response.
    players = query.order_by(Player.name).limit(2000).all()
    return [_to_player_response(p) for p in players]


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(404, "player not found")
    return _to_player_response(player)


def _current_model_version(db: Session) -> ModelVersion | None:
    return (
        db.query(ModelVersion)
        .filter_by(component="fanta_score", version=FANTA_SCORE_MODEL_VERSION)
        .order_by(ModelVersion.id.desc())
        .first()
    )


@router.get("/{player_id}/score", response_model=PlayerScoreResponse)
def get_player_score(player_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    season = db.query(Season).filter_by(is_current=True).one_or_none()
    model_version = _current_model_version(db) if season else None
    empty = PlayerScoreResponse(
        player_id=player_id, fanta_score=None, tier_label=None, components={}, model_version=None, computed_at=None
    )
    if season is None or model_version is None:
        return empty

    score = (
        db.query(PlayerScore)
        .filter_by(player_id=player_id, season_id=season.id, model_version_id=model_version.id)
        .one_or_none()
    )
    tier = (
        db.query(PlayerTier)
        .filter_by(player_id=player_id, season_id=season.id, model_version_id=model_version.id)
        .one_or_none()
    )
    if score is None:
        return empty
    return PlayerScoreResponse(
        player_id=player_id,
        fanta_score=float(score.fanta_score),
        tier_label=tier.tier_label if tier else None,
        components=score.components,
        model_version=FANTA_SCORE_MODEL_VERSION,
        computed_at=score.computed_at.isoformat(),
    )


@router.get("/{player_id}/value", response_model=PlayerValueResponse)
def get_player_value(player_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    """Pre-auction browsing value: league-wide scarcity (nothing purchased
    yet assumed) rather than a specific auction session's live state. For
    the in-session number, use GET /api/auction/recommendation/{id}."""

    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(404, "player not found")

    season = db.query(Season).filter_by(is_current=True).one_or_none()
    league_settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    empty = PlayerValueResponse(player_id=player_id, model_value=None, market_average=None, components={})
    if season is None or league_settings is None:
        return empty

    model_version = _current_model_version(db)
    tier_row = (
        db.query(PlayerTier)
        .filter_by(player_id=player_id, season_id=season.id, model_version_id=model_version.id)
        .one_or_none()
        if model_version
        else None
    )
    if tier_row is None:
        return PlayerValueResponse(
            player_id=player_id, model_value=None, market_average=None, components={"note": "tier not yet computed"}
        )

    tier_player_ids = [
        r.player_id
        for r in db.query(PlayerTier)
        .filter_by(role=player.role, tier_label=tier_row.tier_label, season_id=season.id, model_version_id=model_version.id)
        .all()
    ]
    tier_count = (
        db.query(PlayerTier.tier_rank)
        .filter_by(role=player.role, season_id=season.id, model_version_id=model_version.id)
        .distinct()
        .count()
    ) or 1

    roster_slots = league_settings.config["roster_slots"]
    participants = league_settings.config["participants"]
    slots_needed_league_wide = roster_slots[player.role] * participants
    scarcity = compute_scarcity(len(tier_player_ids), slots_needed_league_wide)

    quote = (
        db.query(FantasyQuote)
        .filter_by(player_id=player_id, season_id=season.id)
        .order_by(FantasyQuote.imported_at.desc())
        .first()
    )
    role_quotes = db.query(FantasyQuote).filter_by(role=player.role, season_id=season.id).all()
    fvm_values = [float(q.fvm) for q in role_quotes if q.fvm]
    sum_fvm_in_role = sum(fvm_values) if fvm_values else None
    total_budget_all_members = league_settings.config["starting_budget"] * participants

    result = compute_model_auction_value(
        player_id=player_id,
        role=player.role,
        tier_rank=tier_row.tier_rank,
        tier_count=tier_count,
        scarcity_level=scarcity.level,
        total_budget_all_members=total_budget_all_members,
        fvm=float(quote.fvm) if quote and quote.fvm else None,
        sum_fvm_in_role=sum_fvm_in_role,
    )
    return PlayerValueResponse(
        player_id=player_id, model_value=result.model_value, market_average=result.market_average,
        components=result.components,
    )
