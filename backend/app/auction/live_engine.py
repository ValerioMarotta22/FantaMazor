"""LiveAuctionEngine (§19/§20/§22) — orchestrates everything else in this
package against real session state. This is the module the API layer
actually calls: it reads league_settings/league_rosters to build each
member's RosterState, pulls FantaScore/tier/market data, and is the one
place that both *recommends* a maximum bid and *enforces* it when a
transaction is recorded (§60 — the invariant is not just advisory).
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auction.recommender import (
    BudgetConstraint,
    RecommendedPrice,
    RosterState,
    compute_budget_constraint,
    compute_recommended_price,
)
from app.auction.scarcity import ScarcityResult, compute_scarcity
from app.auction.value import compute_model_auction_value
from app.db.models import (
    AuctionSession,
    AuctionTransaction,
    FantasyQuote,
    LeagueMember,
    LeagueRoster,
    ModelVersion,
    Player,
    PlayerScore,
    PlayerTier,
    Season,
)
from app.scoring.model_config import FANTA_SCORE_MODEL_VERSION


class AuctionEngineError(ValueError):
    """Raised for any invalid auction operation — including an attempt to
    record a transaction that would violate the budget-completion invariant."""


@dataclass(frozen=True)
class Recommendation:
    player_id: int
    role: str
    fanta_score: float | None
    tier_label: str | None
    model_value: float | None
    market_average: float | None
    recommended_price: RecommendedPrice | None
    budget_constraint: BudgetConstraint
    scarcity: ScarcityResult
    warnings: list[str] = field(default_factory=list)


def _league_settings_config(session: AuctionSession) -> dict:
    return session.league_settings.config


def get_roster_state(db: Session, session_id: int, member_id: int) -> RosterState:
    session = db.get(AuctionSession, session_id)
    if session is None:
        raise AuctionEngineError(f"auction session {session_id} not found")
    config = _league_settings_config(session)
    roster_slots: dict[str, int] = config["roster_slots"]
    starting_budget: float = config["starting_budget"]

    rosters = (
        db.query(LeagueRoster)
        .filter_by(auction_session_id=session_id, league_member_id=member_id)
        .all()
    )
    spent = sum(float(r.price) for r in rosters)
    filled_by_role = Counter(r.role for r in rosters)
    slots_remaining = {
        role: max(0, count - filled_by_role.get(role, 0)) for role, count in roster_slots.items()
    }
    return RosterState(budget_remaining=starting_budget - spent, slots_remaining=slots_remaining)


def get_scarcity_for_player(db: Session, session_id: int, player: Player, season_id: int, model_version_id: int) -> ScarcityResult:
    tier_row = (
        db.query(PlayerTier)
        .filter_by(player_id=player.id, season_id=season_id, model_version_id=model_version_id)
        .one_or_none()
    )
    if tier_row is None:
        return ScarcityResult("UNKNOWN", 0, 0, 0.0)

    tier_player_ids = [
        r.player_id
        for r in db.query(PlayerTier)
        .filter_by(role=player.role, tier_label=tier_row.tier_label, season_id=season_id, model_version_id=model_version_id)
        .all()
    ]
    purchased_count = (
        db.query(LeagueRoster)
        .filter(LeagueRoster.auction_session_id == session_id, LeagueRoster.player_id.in_(tier_player_ids))
        .count()
    )
    remaining_in_tier = len(tier_player_ids) - purchased_count

    session = db.get(AuctionSession, session_id)
    config = _league_settings_config(session)
    roster_slots: dict[str, int] = config["roster_slots"]
    members = db.query(LeagueMember).filter_by(league_settings_id=session.league_settings_id).all()

    total_needed = 0
    for member in members:
        filled = (
            db.query(LeagueRoster)
            .filter_by(auction_session_id=session_id, league_member_id=member.id, role=player.role)
            .count()
        )
        total_needed += max(0, roster_slots[player.role] - filled)

    return compute_scarcity(remaining_in_tier, total_needed)


def _get_admin_member(db: Session, session: AuctionSession) -> LeagueMember:
    admin_member = (
        db.query(LeagueMember)
        .filter_by(league_settings_id=session.league_settings_id, is_admin=True)
        .one_or_none()
    )
    if admin_member is None:
        raise AuctionEngineError("no admin league member configured for this league")
    return admin_member


def get_recommendation(db: Session, session_id: int, player_id: int, for_member_id: int | None = None) -> Recommendation:
    session = db.get(AuctionSession, session_id)
    if session is None:
        raise AuctionEngineError(f"auction session {session_id} not found")
    player = db.get(Player, player_id)
    if player is None:
        raise AuctionEngineError(f"player {player_id} not found")

    member = db.get(LeagueMember, for_member_id) if for_member_id else _get_admin_member(db, session)

    roster_state = get_roster_state(db, session_id, member.id)
    base_price = _league_settings_config(session)["base_price"]
    budget_constraint = compute_budget_constraint(roster_state, player.role, base_price)

    warnings: list[str] = []
    if budget_constraint.hard_max_bid is None:
        warnings.append(f"No remaining {player.role} slots — this buyer cannot bid on this player")

    current_season = db.query(Season).filter_by(is_current=True).one_or_none()
    model_version = (
        db.query(ModelVersion)
        .filter_by(component="fanta_score", version=FANTA_SCORE_MODEL_VERSION)
        .order_by(ModelVersion.id.desc())
        .first()
    )

    fanta_score = tier_label = model_value = market_average = None
    recommended_price = None
    scarcity = ScarcityResult("UNKNOWN", 0, 0, 0.0)

    if current_season is None or model_version is None:
        warnings.append("No current season / scored model version yet — scores unavailable")
    else:
        score_row = (
            db.query(PlayerScore)
            .filter_by(player_id=player.id, season_id=current_season.id, model_version_id=model_version.id)
            .one_or_none()
        )
        tier_row = (
            db.query(PlayerTier)
            .filter_by(player_id=player.id, season_id=current_season.id, model_version_id=model_version.id)
            .one_or_none()
        )
        if score_row is not None:
            fanta_score = float(score_row.fanta_score)
        else:
            warnings.append("FantaScore not yet computed for this player")

        if tier_row is not None:
            tier_label = tier_row.tier_label
            scarcity = get_scarcity_for_player(db, session_id, player, current_season.id, model_version.id)

            tier_player_ids = [
                r.player_id
                for r in db.query(PlayerTier)
                .filter_by(role=player.role, tier_label=tier_row.tier_label, season_id=current_season.id, model_version_id=model_version.id)
                .all()
            ]
            paid_prices = [
                float(t.price)
                for t in db.query(AuctionTransaction)
                .filter(AuctionTransaction.auction_session_id == session_id, AuctionTransaction.player_id.in_(tier_player_ids))
                .all()
            ]
            if paid_prices:
                market_average = round(sum(paid_prices) / len(paid_prices), 2)

            quote = (
                db.query(FantasyQuote)
                .filter_by(player_id=player.id, season_id=current_season.id)
                .order_by(FantasyQuote.imported_at.desc())
                .first()
            )
            role_quotes = db.query(FantasyQuote).filter_by(role=player.role, season_id=current_season.id).all()
            fvm_values = [float(q.fvm) for q in role_quotes if q.fvm]
            sum_fvm_in_role = sum(fvm_values) if fvm_values else None

            total_budget_all_members = (
                _league_settings_config(session)["starting_budget"]
                * _league_settings_config(session)["participants"]
            )
            tier_count = (
                db.query(PlayerTier.tier_rank)
                .filter_by(role=player.role, season_id=current_season.id, model_version_id=model_version.id)
                .distinct()
                .count()
            ) or 1

            value_result = compute_model_auction_value(
                player_id=player.id,
                role=player.role,
                tier_rank=tier_row.tier_rank,
                tier_count=tier_count,
                scarcity_level=scarcity.level,
                total_budget_all_members=total_budget_all_members,
                fvm=float(quote.fvm) if quote and quote.fvm else None,
                sum_fvm_in_role=sum_fvm_in_role,
                market_average=market_average,
            )
            model_value = value_result.model_value
            if model_value is not None:
                recommended_price = compute_recommended_price(model_value, budget_constraint.hard_max_bid)
        else:
            warnings.append("Tier not yet computed for this player")

    return Recommendation(
        player_id=player.id,
        role=player.role,
        fanta_score=fanta_score,
        tier_label=tier_label,
        model_value=model_value,
        market_average=market_average,
        recommended_price=recommended_price,
        budget_constraint=budget_constraint,
        scarcity=scarcity,
        warnings=warnings,
    )


def record_transaction(db: Session, session_id: int, player_id: int, buyer_member_id: int, price: float) -> AuctionTransaction:
    """Persists a completed sale. Re-validates the budget-completion
    invariant server-side — this is the actual enforcement point, not just
    an advisory number shown in the UI (§60)."""

    session = db.get(AuctionSession, session_id)
    if session is None:
        raise AuctionEngineError(f"auction session {session_id} not found")
    player = db.get(Player, player_id)
    if player is None:
        raise AuctionEngineError(f"player {player_id} not found")
    buyer = db.get(LeagueMember, buyer_member_id)
    if buyer is None:
        raise AuctionEngineError(f"league member {buyer_member_id} not found")

    already_sold = (
        db.query(LeagueRoster).filter_by(auction_session_id=session_id, player_id=player_id).one_or_none()
    )
    if already_sold is not None:
        raise AuctionEngineError(f"player {player_id} was already sold in this session")

    roster_state = get_roster_state(db, session_id, buyer_member_id)
    base_price = _league_settings_config(session)["base_price"]

    if roster_state.slots_remaining.get(player.role, 0) <= 0:
        raise AuctionEngineError(f"{buyer.name} has no remaining {player.role} slots")

    constraint = compute_budget_constraint(roster_state, player.role, base_price)
    if constraint.hard_max_bid is not None and price > constraint.hard_max_bid + 1e-6:
        raise AuctionEngineError(
            f"price {price} exceeds the maximum safe bid ({constraint.hard_max_bid}) for {buyer.name} at "
            f"{player.role} — paying this would make completing the roster impossible"
        )
    if price < base_price:
        raise AuctionEngineError(f"price must be at least the base price ({base_price})")

    budget_before = roster_state.budget_remaining
    budget_after = budget_before - price
    new_slots_remaining = dict(roster_state.slots_remaining)
    new_slots_remaining[player.role] = max(0, new_slots_remaining.get(player.role, 0) - 1)

    txn = AuctionTransaction(
        auction_session_id=session_id,
        player_id=player_id,
        role=player.role,
        buyer_league_member_id=buyer_member_id,
        price=price,
        budget_before=budget_before,
        budget_after=budget_after,
        remaining_slots=new_slots_remaining,
        purchased_at=datetime.now(timezone.utc),
    )
    db.add(txn)
    db.add(
        LeagueRoster(
            auction_session_id=session_id,
            league_member_id=buyer_member_id,
            player_id=player_id,
            role=player.role,
            price=price,
        )
    )
    db.commit()
    db.refresh(txn)
    return txn


def get_session_state(db: Session, session_id: int) -> dict:
    session = db.get(AuctionSession, session_id)
    if session is None:
        raise AuctionEngineError(f"auction session {session_id} not found")

    members = db.query(LeagueMember).filter_by(league_settings_id=session.league_settings_id).all()
    member_states = []
    for member in members:
        state = get_roster_state(db, session_id, member.id)
        member_states.append(
            {
                "member_id": member.id,
                "name": member.name,
                "is_admin": member.is_admin,
                "budget_remaining": state.budget_remaining,
                "slots_remaining": state.slots_remaining,
            }
        )

    return {"session_id": session_id, "status": session.status, "members": member_states}
