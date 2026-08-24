from datetime import datetime

from pydantic import BaseModel


class DataSourceStatus(BaseModel):
    key: str
    display_name: str
    is_enabled: bool
    last_successful_sync: datetime | None
    last_failed_sync: datetime | None
    last_error: str | None


class ImportResultResponse(BaseModel):
    source: str
    records_imported: int
    players_created: int
    players_matched: int
    warnings: list[str]
