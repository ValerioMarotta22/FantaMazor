from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auction.live_engine import get_roster_state
from app.core.security import CurrentUser
from app.db.models import LeagueMember, LeagueRoster, LeagueSettings
from app.db.session import get_db
from app.schemas.league import (
    LeagueMemberResponse,
    LeagueMemberUpdateRequest,
    LeagueSettingsResponse,
    LeagueSettingsUpdateRequest,
    MemberRosterResponse,
    RosterPlayerResponse,
)

router = APIRouter()


@router.get("/settings", response_model=LeagueSettingsResponse)
def get_league_settings(db: Session = Depends(get_db), _user: str = CurrentUser):
    settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    if settings is None:
        raise HTTPException(404, "no active league settings")
    return settings


@router.put("/settings", response_model=LeagueSettingsResponse)
def update_league_settings(
    payload: LeagueSettingsUpdateRequest, db: Session = Depends(get_db), _user: str = CurrentUser
):
    settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    if settings is None:
        raise HTTPException(404, "no active league settings")
    settings.config = payload.config
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/members", response_model=list[LeagueMemberResponse])
def list_members(db: Session = Depends(get_db), _user: str = CurrentUser):
    settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    if settings is None:
        return []
    return db.query(LeagueMember).filter_by(league_settings_id=settings.id).order_by(LeagueMember.id).all()


@router.put("/members/{member_id}", response_model=LeagueMemberResponse)
def update_member(
    member_id: int, payload: LeagueMemberUpdateRequest, db: Session = Depends(get_db), _user: str = CurrentUser
):
    member = db.get(LeagueMember, member_id)
    if member is None:
        raise HTTPException(404, "member not found")
    member.name = payload.name
    db.commit()
    db.refresh(member)
    return member


@router.get("/members/{member_id}/roster", response_model=MemberRosterResponse)
def member_roster(member_id: int, session_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    member = db.get(LeagueMember, member_id)
    if member is None:
        raise HTTPException(404, "member not found")

    state = get_roster_state(db, session_id, member_id)
    rosters = (
        db.query(LeagueRoster).filter_by(auction_session_id=session_id, league_member_id=member_id).all()
    )
    players = [
        RosterPlayerResponse(player_id=r.player_id, name=r.player.name, role=r.role, price=float(r.price))
        for r in rosters
    ]
    return MemberRosterResponse(
        member_id=member.id,
        name=member.name,
        budget_remaining=state.budget_remaining,
        slots_remaining=state.slots_remaining,
        players=players,
    )
