"""Runs FantaScore + tiering (§11-13) for every player quoted in a season.
Triggered explicitly (POST /api/data/score) after an import, rather than on
every request, so the live auction dashboard reads pre-computed values —
recomputing per-request would blow the <500ms budget in §61.
"""

from sqlalchemy.orm import Session

from app.db.models import FantasyQuote, ModelVersion, PlayerScore, PlayerSeasonStats, PlayerTier, Season
from app.scoring.fanta_score import compute_fanta_scores
from app.scoring.model_config import FANTA_SCORE_MODEL_VERSION, FANTA_SCORE_WEIGHTS
from app.scoring.role_models import PlayerFeatures
from app.scoring.tiers import assign_tiers


def _get_or_create_model_version(db: Session) -> ModelVersion:
    model_version = (
        db.query(ModelVersion)
        .filter_by(component="fanta_score", version=FANTA_SCORE_MODEL_VERSION)
        .order_by(ModelVersion.id.desc())
        .first()
    )
    if model_version is None:
        model_version = ModelVersion(
            component="fanta_score",
            version=FANTA_SCORE_MODEL_VERSION,
            description="v1 deterministic weighted score — see app/scoring/model_config.py",
            config=FANTA_SCORE_WEIGHTS,
        )
        db.add(model_version)
        db.flush()
    return model_version


def run_scoring_pipeline(db: Session, season_label: str) -> dict:
    season = db.query(Season).filter_by(label=season_label).one_or_none()
    if season is None:
        raise ValueError(f"season '{season_label}' not found — import a listone for it first")

    model_version = _get_or_create_model_version(db)

    # Recomputing replaces the prior pass for this season/model_version —
    # there is exactly one current score/tier per player per model version.
    db.query(PlayerScore).filter_by(season_id=season.id, model_version_id=model_version.id).delete()
    db.query(PlayerTier).filter_by(season_id=season.id, model_version_id=model_version.id).delete()

    quotes = db.query(FantasyQuote).filter_by(season_id=season.id).all()
    fvm_by_player: dict[int, float] = {}
    players_by_role: dict[str, set[int]] = {}
    for q in quotes:
        players_by_role.setdefault(q.role, set()).add(q.player_id)
        if q.fvm:
            fvm_by_player[q.player_id] = float(q.fvm)

    stats_rows = db.query(PlayerSeasonStats).filter_by(season_id=season.id, scope="current").all()
    stats_by_player = {s.player_id: s for s in stats_rows}

    total_scored = 0
    for role, player_ids in players_by_role.items():
        features: dict[int, PlayerFeatures] = {}
        for pid in player_ids:
            stats = stats_by_player.get(pid)
            features[pid] = PlayerFeatures(
                fantasy_average=float(stats.fantasy_average) if stats and stats.fantasy_average is not None else None,
                average_rating=float(stats.average_rating) if stats and stats.average_rating is not None else None,
                goals=float(stats.goals) if stats and stats.goals is not None else None,
                assists=float(stats.assists) if stats and stats.assists is not None else None,
                appearances=float(stats.appearances) if stats and stats.appearances is not None else None,
                fvm=fvm_by_player.get(pid),
            )

        scores = compute_fanta_scores(role, features)
        tiers = assign_tiers(role, {pid: result.score for pid, result in scores.items()})

        for pid, result in scores.items():
            db.add(
                PlayerScore(
                    player_id=pid,
                    season_id=season.id,
                    model_version_id=model_version.id,
                    fanta_score=result.score,
                    components=result.components,
                )
            )
            tier = tiers.get(pid)
            if tier is not None:
                db.add(
                    PlayerTier(
                        player_id=pid,
                        season_id=season.id,
                        role=role,
                        tier_label=tier.tier_label,
                        tier_rank=tier.tier_rank,
                        model_version_id=model_version.id,
                    )
                )
            total_scored += 1

    db.commit()
    return {"season": season_label, "model_version": FANTA_SCORE_MODEL_VERSION, "players_scored": total_scored}
