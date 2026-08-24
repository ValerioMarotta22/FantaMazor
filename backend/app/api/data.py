from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.db.session import get_db
from app.ingestion.listone_import import import_quotes
from app.ingestion.scoring_pipeline import run_scoring_pipeline
from app.providers.data_quality import get_status, record_sync_failure, record_sync_success
from app.providers.demo_data import SEASON_LABEL as DEMO_SEASON_LABEL
from app.providers.demo_data import DemoDataProvider
from app.providers.manual_import import ListoneValidationError, parse_listone_csv, parse_listone_json
from app.schemas.data import DataSourceStatus, ImportResultResponse

router = APIRouter()


@router.get("/status", response_model=list[DataSourceStatus])
def data_status(db: Session = Depends(get_db), _user: str = CurrentUser):
    return get_status(db)


@router.post("/import/listone", response_model=ImportResultResponse)
async def import_listone(
    season_label: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: str = CurrentUser,
):
    content = await file.read()
    try:
        if file.filename and file.filename.lower().endswith(".json"):
            records = parse_listone_json(content, season_label)
        else:
            records = parse_listone_csv(content, season_label)
    except ListoneValidationError as exc:
        record_sync_failure(db, "manual_import", "; ".join(exc.errors))
        raise HTTPException(422, detail={"errors": exc.errors}) from exc

    result = import_quotes(db, records, season_label)
    record_sync_success(db, "manual_import", result["records_imported"])
    return ImportResultResponse(**result)


@router.post("/import/demo", response_model=ImportResultResponse)
def import_demo(db: Session = Depends(get_db), _user: str = CurrentUser):
    provider = DemoDataProvider()
    records = provider.get_quotes(DEMO_SEASON_LABEL)
    result = import_quotes(db, records, DEMO_SEASON_LABEL)
    record_sync_success(db, "demo", result["records_imported"])
    return ImportResultResponse(**result)


@router.post("/score")
def trigger_scoring(season_label: str, db: Session = Depends(get_db), _user: str = CurrentUser):
    try:
        return run_scoring_pipeline(db, season_label)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
