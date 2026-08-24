"""Player entity resolution (§8/§9), v1.

MVP1 only ingests one source at a time (manual import or demo data), so
there's no cross-source reconciliation to do yet — matching is a plain
normalized-name + role exact match. Real fuzzy matching with a confidence
score and a manual-review queue for low-confidence auto-matches becomes
necessary once a second source (e.g. API-Football) needs to be reconciled
against the same player_id, which is MVP2 scope.
"""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.db.models import Player, Team


def normalize_name(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower().strip()
    return re.sub(r"\s+", " ", ascii_name)


def find_or_create_team(db: Session, team_name: str) -> Team:
    team = db.query(Team).filter_by(name=team_name).one_or_none()
    if team is None:
        team = Team(name=team_name)
        db.add(team)
        db.flush()
    return team


def find_or_create_player(db: Session, name: str, role: str, team_name: str | None) -> tuple[Player, bool]:
    """Returns (player, was_created)."""
    normalized = normalize_name(name)
    existing = db.query(Player).filter_by(normalized_name=normalized, role=role).one_or_none()

    team = find_or_create_team(db, team_name) if team_name else None

    if existing is not None:
        if team is not None:
            existing.team_id = team.id
        return existing, False

    player = Player(
        name=name,
        normalized_name=normalized,
        role=role,
        team_id=team.id if team else None,
        status="unknown",
    )
    db.add(player)
    db.flush()
    return player, True
