"""First-run seeding: the single admin user, the default LeagueSettings
preset matching the target 10-participant / 500 FM league (§1), its 10
LeagueMembers, and the known data source rows for the /settings/data page."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import LeagueMember, LeagueSettings, User
from app.providers.data_quality import ensure_sources_seeded
from app.scoring.model_config import DEFAULT_LEAGUE_SETTINGS_CONFIG


def seed_defaults(db: Session) -> None:
    settings = get_settings()

    if db.query(User).filter_by(username=settings.admin_username).one_or_none() is None:
        db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))

    league_settings = db.query(LeagueSettings).filter_by(is_active=True).one_or_none()
    if league_settings is None:
        league_settings = LeagueSettings(
            name="Lega Titolare (10 partecipanti, 500 FM)",
            config=DEFAULT_LEAGUE_SETTINGS_CONFIG,
            is_active=True,
        )
        db.add(league_settings)
        db.flush()

        db.add(LeagueMember(league_settings_id=league_settings.id, name=settings.admin_username, is_admin=True))
        for i in range(2, DEFAULT_LEAGUE_SETTINGS_CONFIG["participants"] + 1):
            db.add(LeagueMember(league_settings_id=league_settings.id, name=f"Partecipante {i}", is_admin=False))

    db.commit()
    ensure_sources_seeded(db)
