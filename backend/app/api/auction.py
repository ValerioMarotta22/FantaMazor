from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auction.live_engine import (
    AuctionEngineError,
    get_recommendation,
    get_session_state,
    record_transaction,
)
from app.auction.simulator import SimulationTarget, run_auction_simulation
from app.core.security import CurrentUser
from app.db.models import AuctionSession, AuctionTransaction, LeagueSettings
from app.db.session import get_db
from app.schemas.auction import (
    BudgetConstraintResponse,
    CreateSessionRequest,
    RecommendationResponse,
    RecommendedPriceResponse,
    ScarcityResponse,
    SessionResponse,
    SessionStateResponse,
    SimulationRequest,
    SimulationResponse,
    TransactionRequest,
    TransactionResponse,
)

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db), _user: str = CurrentUser):
    league_settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    if league_settings is None:
        raise HTTPException(400, "no active league settings")
    session = AuctionSession(league_settings_id=league_settings.id, name=payload.name, status="in_progress")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_db), _user: str = CurrentUser):
    return db.query(AuctionSession).order_by(AuctionSession.id.desc()).limit(20).all()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    session = db.get(AuctionSession, session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return session


@router.get("/sessions/{session_id}/state", response_model=SessionStateResponse)
def session_state(session_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    try:
        return get_session_state(db, session_id)
    except AuctionEngineError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/recommendation/{player_id}", response_model=RecommendationResponse)
def recommendation(player_id: int, session_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    try:
        rec = get_recommendation(db, session_id, player_id)
    except AuctionEngineError as exc:
        raise HTTPException(400, str(exc)) from exc
    return RecommendationResponse(
        player_id=rec.player_id,
        role=rec.role,
        fanta_score=rec.fanta_score,
        tier_label=rec.tier_label,
        model_value=rec.model_value,
        market_average=rec.market_average,
        recommended_price=RecommendedPriceResponse(**asdict(rec.recommended_price)) if rec.recommended_price else None,
        budget_constraint=BudgetConstraintResponse(**asdict(rec.budget_constraint)),
        scarcity=ScarcityResponse(**asdict(rec.scarcity)),
        warnings=rec.warnings,
    )


@router.post("/sessions/{session_id}/transactions", response_model=TransactionResponse)
def create_transaction(
    session_id: int, payload: TransactionRequest, db: Session = Depends(get_db), _user: str = CurrentUser
):
    try:
        txn = record_transaction(db, session_id, payload.player_id, payload.buyer_member_id, payload.price)
    except AuctionEngineError as exc:
        raise HTTPException(400, str(exc)) from exc
    return TransactionResponse(
        id=txn.id,
        player_id=txn.player_id,
        player_name=txn.player.name,
        role=txn.role,
        buyer_member_id=txn.buyer_league_member_id,
        buyer_name=txn.buyer.name,
        price=float(txn.price),
        budget_before=float(txn.budget_before),
        budget_after=float(txn.budget_after),
        remaining_slots=txn.remaining_slots,
    )


@router.get("/sessions/{session_id}/transactions", response_model=list[TransactionResponse])
def list_transactions(session_id: int, db: Session = Depends(get_db), _user: str = CurrentUser):
    txns = (
        db.query(AuctionTransaction)
        .filter_by(auction_session_id=session_id)
        .order_by(AuctionTransaction.purchased_at.desc())
        .all()
    )
    return [
        TransactionResponse(
            id=t.id,
            player_id=t.player_id,
            player_name=t.player.name,
            role=t.role,
            buyer_member_id=t.buyer_league_member_id,
            buyer_name=t.buyer.name,
            price=float(t.price),
            budget_before=float(t.budget_before),
            budget_after=float(t.budget_after),
            remaining_slots=t.remaining_slots,
        )
        for t in txns
    ]


@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, _user: str = CurrentUser):
    targets = [
        SimulationTarget(player_id=t.player_id, role=t.role, model_value=t.model_value) for t in payload.targets
    ]
    try:
        result = run_auction_simulation(
            targets=targets,
            other_slots_needed=payload.other_slots_needed,
            base_price=payload.base_price,
            budget=payload.budget,
            iterations=payload.iterations,
            price_noise_pct=payload.price_noise_pct,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return SimulationResponse(**asdict(result))
