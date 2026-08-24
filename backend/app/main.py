from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auction, auth, data, league, players
from app.core.config import get_settings
from app.db import models  # noqa: F401 -- registers all models on Base.metadata
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.startup import seed_defaults

settings = get_settings()

app = FastAPI(title="FantaMazor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(league.router, prefix="/api/league", tags=["league"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(auction.router, prefix="/api/auction", tags=["auction"])


@app.on_event("startup")
def on_startup() -> None:
    if settings.database_url.startswith("sqlite"):
        # Local single-user mode: no Alembic/Postgres required, just create
        # the schema directly. Production (Postgres) always uses
        # `alembic upgrade head` instead -- see README.
        Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
