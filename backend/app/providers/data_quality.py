"""DataQualityService (§38) — tracks per-source availability so the app can
fall back sanely instead of treating a dead provider as a single point of
failure, and so /settings/data can show an honest status (§37/§53)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import DataSource, DataSyncLog

KNOWN_SOURCES = [
    ("demo", "Demo Data"),
    ("manual_import", "Manual Import"),
    ("api_football", "API-Football"),
    ("understat", "Understat"),
    ("fantacalcio", "Fantacalcio.it"),
]


def ensure_sources_seeded(db: Session) -> None:
    existing = {s.key for s in db.query(DataSource).all()}
    for key, display_name in KNOWN_SOURCES:
        if key not in existing:
            db.add(DataSource(key=key, display_name=display_name, is_enabled=True))
    db.commit()


def record_sync_success(db: Session, source_key: str, records_processed: int, message: str | None = None) -> None:
    source = db.query(DataSource).filter(DataSource.key == source_key).one_or_none()
    if source is None:
        return
    now = datetime.now(timezone.utc)
    source.last_successful_sync = now
    source.last_error = None
    db.add(
        DataSyncLog(
            data_source_id=source.id,
            started_at=now,
            finished_at=now,
            status="success",
            records_processed=records_processed,
            message=message,
        )
    )
    db.commit()


def record_sync_failure(db: Session, source_key: str, error: str) -> None:
    source = db.query(DataSource).filter(DataSource.key == source_key).one_or_none()
    if source is None:
        return
    now = datetime.now(timezone.utc)
    source.last_failed_sync = now
    source.last_error = error
    db.add(
        DataSyncLog(
            data_source_id=source.id,
            started_at=now,
            finished_at=now,
            status="failure",
            records_processed=None,
            message=error,
        )
    )
    db.commit()


def get_status(db: Session) -> list[dict]:
    sources = db.query(DataSource).all()
    return [
        {
            "key": s.key,
            "display_name": s.display_name,
            "is_enabled": s.is_enabled,
            "last_successful_sync": s.last_successful_sync,
            "last_failed_sync": s.last_failed_sync,
            "last_error": s.last_error,
        }
        for s in sources
    ]
