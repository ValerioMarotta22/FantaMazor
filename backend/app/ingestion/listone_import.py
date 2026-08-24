"""Persists parsed QuoteRecords (from ManualImportProvider or
DemoDataProvider) into `fantasy_quotes`, resolving each row to a stable
internal Player via player_resolution.py."""

from sqlalchemy.orm import Session

from app.db.models import FantasyQuote, Season
from app.ingestion.player_resolution import find_or_create_player
from app.providers.base import QuoteRecord


def _get_or_create_season(db: Session, season_label: str) -> Season:
    season = db.query(Season).filter_by(label=season_label).one_or_none()
    if season is None:
        season = Season(label=season_label, is_current=True)
        db.add(season)
        db.flush()
    return season


def import_quotes(db: Session, records: list[QuoteRecord], season_label: str) -> dict:
    season = _get_or_create_season(db, season_label)

    created = matched = 0
    for record in records:
        player, was_created = find_or_create_player(db, record.player_name, record.role, record.team_name)
        created += int(was_created)
        matched += int(not was_created)

        db.add(
            FantasyQuote(
                player_id=player.id,
                season_id=season.id,
                role=record.role,
                team_id=player.team_id,
                quotation=record.quotation,
                fvm=record.fvm,
                source=record.source,
                raw_data=None,
            )
        )

    db.commit()
    return {
        "source": records[0].source if records else "unknown",
        "records_imported": len(records),
        "players_created": created,
        "players_matched": matched,
        "warnings": [],
    }
