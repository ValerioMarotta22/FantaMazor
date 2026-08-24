"""SQLAlchemy models for MVP1.

Only the tables MVP1 actually needs are here (see plan doc / README "Database"
section for the full §40 list and what's deferred to MVP2/3). Nothing about
league rules is hardcoded — `LeagueSettings.config` is the single source of
truth the scoring/auction engines read from.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# JSONB on Postgres (production), plain JSON everywhere else (e.g. SQLite in
# tests) -- keeps the ORM layer testable without requiring a live Postgres.
PortableJSON = JSON().with_variant(JSONB, "postgresql")


class User(Base, TimestampMixin):
    """The single MVP1 admin/commissioner account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class LeagueSettings(Base, TimestampMixin):
    """Configurable league rules. `config` holds budget, roster slots per
    role, allowed modules, scoring rules, bench/sub limits — see
    app/scoring/model_config.py for the schema and the seeded default preset
    that matches the target 10-participant / 500 FM league."""

    __tablename__ = "league_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    config: Mapped[dict] = mapped_column(PortableJSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    members: Mapped[list["LeagueMember"]] = relationship(back_populates="league_settings")


class LeagueMember(Base, TimestampMixin):
    """A participant in the league. MVP1 has no per-member login — the admin
    tracks all 10 members' budgets/rosters themselves."""

    __tablename__ = "league_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_settings_id: Mapped[int] = mapped_column(ForeignKey("league_settings.id"))
    name: Mapped[str] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    league_settings: Mapped["LeagueSettings"] = relationship(back_populates="members")


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    short_name: Mapped[str | None] = mapped_column(String(16), nullable=True)
    api_football_team_id: Mapped[int | None] = mapped_column(nullable=True)


class Season(Base, TimestampMixin):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(16), unique=True)  # e.g. "2025-26"
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Player(Base, TimestampMixin):
    """The stable internal player entity. `id` is the `player_id` referenced
    everywhere else in the system — never the player's name (§9)."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    normalized_name: Mapped[str] = mapped_column(String(128), index=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(4))  # POR | DIF | CEN | ATT
    fantasy_role: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # active | injured | suspended | unknown — never inferred silently, see §55
    status: Mapped[str] = mapped_column(String(16), default="unknown")

    team: Mapped["Team | None"] = relationship()
    external_ids: Mapped[list["PlayerExternalId"]] = relationship(back_populates="player")


class PlayerExternalId(Base, TimestampMixin):
    """Maps our internal player_id to IDs in external sources, with a
    confidence score — see §8. Low-confidence auto-matches should be routed
    to manual review rather than trusted outright."""

    __tablename__ = "player_external_ids"
    __table_args__ = (UniqueConstraint("player_id", "source", name="uq_player_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    source: Mapped[str] = mapped_column(String(32))  # fantacalcio | api_football | understat | ...
    external_id: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(default=1.0)
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    player: Mapped["Player"] = relationship(back_populates="external_ids")


class FantasyQuote(Base, TimestampMixin):
    """One listone row: quotation/FVM for a player in a season, from
    whichever source it was imported from (§1 primary source: Fantacalcio.it,
    via manual import in MVP1)."""

    __tablename__ = "fantasy_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    role: Mapped[str] = mapped_column(String(4))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    quotation: Mapped[int | None] = mapped_column(nullable=True)
    fvm: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_data: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    player: Mapped["Player"] = relationship()


class PlayerSeasonStats(Base, TimestampMixin):
    """Per-season stat line. `scope` distinguishes historical vs current vs
    projected data (§10) — never conflate them. Any field that isn't
    available from the source stays NULL, never 0 (§55)."""

    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    scope: Mapped[str] = mapped_column(String(16))  # historical | current | projected

    appearances: Mapped[int | None] = mapped_column(nullable=True)
    starts: Mapped[int | None] = mapped_column(nullable=True)
    minutes: Mapped[int | None] = mapped_column(nullable=True)
    goals: Mapped[int | None] = mapped_column(nullable=True)
    assists: Mapped[int | None] = mapped_column(nullable=True)
    fantasy_points: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    fantasy_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    penalties_scored: Mapped[int | None] = mapped_column(nullable=True)
    penalties_missed: Mapped[int | None] = mapped_column(nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(nullable=True)
    red_cards: Mapped[int | None] = mapped_column(nullable=True)
    shots: Mapped[int | None] = mapped_column(nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(nullable=True)
    key_passes: Mapped[int | None] = mapped_column(nullable=True)
    xg: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    xa: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    npxg: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    xg_chain: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    xg_buildup: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)

    source: Mapped[str] = mapped_column(String(32))
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship()


class DataSource(Base, TimestampMixin):
    """Tracks provider health for the /settings/data freshness page (§37/§38)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_successful_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataSyncLog(Base, TimestampMixin):
    __tablename__ = "data_sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # success | failure | partial
    records_processed: Mapped[int | None] = mapped_column(nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelVersion(Base, TimestampMixin):
    """Records which model/version produced a given score or value (§41)."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    component: Mapped[str] = mapped_column(String(32))  # fanta_score | auction_value | tiers
    version: Mapped[str] = mapped_column(String(32))  # e.g. "fanta-score-v1"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)


class PlayerScore(Base, TimestampMixin):
    __tablename__ = "player_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"))
    fanta_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    components: Mapped[dict] = mapped_column(PortableJSON)  # explainability breakdown
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship()


class PlayerTier(Base, TimestampMixin):
    __tablename__ = "player_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    role: Mapped[str] = mapped_column(String(4))
    tier_label: Mapped[str] = mapped_column(String(8))  # e.g. "A1"
    tier_rank: Mapped[int] = mapped_column()  # 1 = best tier in role
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship()


class AuctionSession(Base, TimestampMixin):
    __tablename__ = "auction_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_settings_id: Mapped[int] = mapped_column(ForeignKey("league_settings.id"))
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="setup")  # setup | in_progress | completed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    league_settings: Mapped["LeagueSettings"] = relationship()


class AuctionTransaction(Base, TimestampMixin):
    """The full transaction log — every single sale, per §7. This is the
    ground truth the local-market statistics and future auctions learn from."""

    __tablename__ = "auction_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_session_id: Mapped[int] = mapped_column(ForeignKey("auction_sessions.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    role: Mapped[str] = mapped_column(String(4))
    buyer_league_member_id: Mapped[int] = mapped_column(ForeignKey("league_members.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    budget_before: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    budget_after: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    remaining_slots: Mapped[dict] = mapped_column(PortableJSON)  # {"POR": 2, "DIF": 6, ...} after this buy
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship()
    buyer: Mapped["LeagueMember"] = relationship()


class LeagueRoster(Base, TimestampMixin):
    """Current-state ownership view, kept in sync with `auction_transactions`
    as each purchase is recorded. A player can only be owned once per
    session."""

    __tablename__ = "league_rosters"
    __table_args__ = (UniqueConstraint("auction_session_id", "player_id", name="uq_session_player"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_session_id: Mapped[int] = mapped_column(ForeignKey("auction_sessions.id"))
    league_member_id: Mapped[int] = mapped_column(ForeignKey("league_members.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    role: Mapped[str] = mapped_column(String(4))
    price: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship()
    member: Mapped["LeagueMember"] = relationship()
