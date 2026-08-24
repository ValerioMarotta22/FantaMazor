"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "league_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )

    op.create_table(
        "league_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_settings_id", sa.Integer(), sa.ForeignKey("league_settings.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("short_name", sa.String(16), nullable=True),
        sa.Column("api_football_team_id", sa.Integer(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(16), nullable=False, unique=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("normalized_name", sa.String(128), nullable=False),
        sa.Column("first_name", sa.String(64), nullable=True),
        sa.Column("last_name", sa.String(64), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("role", sa.String(4), nullable=False),
        sa.Column("fantasy_role", sa.String(8), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="unknown"),
        *_timestamps(),
    )
    op.create_index("ix_players_name", "players", ["name"])
    op.create_index("ix_players_normalized_name", "players", ["normalized_name"])

    op.create_table(
        "player_external_ids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("player_id", "source", name="uq_player_source"),
    )

    op.create_table(
        "fantasy_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("role", sa.String(4), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("quotation", sa.Integer(), nullable=True),
        sa.Column("fvm", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "player_season_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("starts", sa.Integer(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("fantasy_points", sa.Numeric(8, 2), nullable=True),
        sa.Column("average_rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("fantasy_average", sa.Numeric(4, 2), nullable=True),
        sa.Column("penalties_scored", sa.Integer(), nullable=True),
        sa.Column("penalties_missed", sa.Integer(), nullable=True),
        sa.Column("yellow_cards", sa.Integer(), nullable=True),
        sa.Column("red_cards", sa.Integer(), nullable=True),
        sa.Column("shots", sa.Integer(), nullable=True),
        sa.Column("shots_on_target", sa.Integer(), nullable=True),
        sa.Column("key_passes", sa.Integer(), nullable=True),
        sa.Column("xg", sa.Numeric(6, 3), nullable=True),
        sa.Column("xa", sa.Numeric(6, 3), nullable=True),
        sa.Column("npxg", sa.Numeric(6, 3), nullable=True),
        sa.Column("xg_chain", sa.Numeric(6, 3), nullable=True),
        sa.Column("xg_buildup", sa.Numeric(6, 3), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_successful_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "data_sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("data_source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component", sa.String(32), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "player_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("fanta_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "player_tiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("role", sa.String(4), nullable=False),
        sa.Column("tier_label", sa.String(8), nullable=False),
        sa.Column("tier_rank", sa.Integer(), nullable=False),
        sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "auction_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_settings_id", sa.Integer(), sa.ForeignKey("league_settings.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="setup"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "auction_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auction_session_id", sa.Integer(), sa.ForeignKey("auction_sessions.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("role", sa.String(4), nullable=False),
        sa.Column("buyer_league_member_id", sa.Integer(), sa.ForeignKey("league_members.id"), nullable=False),
        sa.Column("price", sa.Numeric(6, 2), nullable=False),
        sa.Column("budget_before", sa.Numeric(6, 2), nullable=False),
        sa.Column("budget_after", sa.Numeric(6, 2), nullable=False),
        sa.Column("remaining_slots", postgresql.JSONB(), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "league_rosters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auction_session_id", sa.Integer(), sa.ForeignKey("auction_sessions.id"), nullable=False),
        sa.Column("league_member_id", sa.Integer(), sa.ForeignKey("league_members.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("role", sa.String(4), nullable=False),
        sa.Column("price", sa.Numeric(6, 2), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("auction_session_id", "player_id", name="uq_session_player"),
    )


def downgrade() -> None:
    op.drop_table("league_rosters")
    op.drop_table("auction_transactions")
    op.drop_table("auction_sessions")
    op.drop_table("player_tiers")
    op.drop_table("player_scores")
    op.drop_table("model_versions")
    op.drop_table("data_sync_logs")
    op.drop_table("data_sources")
    op.drop_table("player_season_stats")
    op.drop_table("fantasy_quotes")
    op.drop_table("player_external_ids")
    op.drop_index("ix_players_normalized_name", table_name="players")
    op.drop_index("ix_players_name", table_name="players")
    op.drop_table("players")
    op.drop_table("seasons")
    op.drop_table("teams")
    op.drop_table("league_members")
    op.drop_table("league_settings")
    op.drop_table("users")
