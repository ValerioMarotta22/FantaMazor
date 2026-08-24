"""DemoDataProvider — clearly-marked seed data for local development with no
external calls and no manual import (§57). Every record carries
source="demo" so it can never be mistaken for real data downstream (the
frontend must render a visible "Demo data" badge whenever a response is
sourced from here).
"""

DEMO_DATA = True

from app.providers.base import FantasyDataProvider, QuoteRecord

SEASON_LABEL = "2025-26"

# A small, deliberately fictional-looking roster: real club names (public
# domain facts), invented quotations, so nobody mistakes this for a live feed.
_DEMO_PLAYERS: list[tuple[str, str, str, int, int]] = [
    # name, role, team, quotation, fvm
    ("A. Demo Goalkeeper 1", "POR", "Inter", 18, 22),
    ("B. Demo Goalkeeper 2", "POR", "Milan", 16, 19),
    ("C. Demo Goalkeeper 3", "POR", "Juventus", 14, 16),
    ("D. Demo Goalkeeper 4", "POR", "Napoli", 12, 14),
    ("E. Demo Defender 1", "DIF", "Inter", 20, 24),
    ("F. Demo Defender 2", "DIF", "Milan", 18, 21),
    ("G. Demo Defender 3", "DIF", "Juventus", 16, 18),
    ("H. Demo Defender 4", "DIF", "Napoli", 14, 16),
    ("I. Demo Defender 5", "DIF", "Roma", 12, 14),
    ("J. Demo Defender 6", "DIF", "Atalanta", 10, 12),
    ("K. Demo Defender 7", "DIF", "Fiorentina", 8, 9),
    ("L. Demo Defender 8", "DIF", "Bologna", 6, 7),
    ("M. Demo Midfielder 1", "CEN", "Inter", 28, 34),
    ("N. Demo Midfielder 2", "CEN", "Milan", 26, 31),
    ("O. Demo Midfielder 3", "CEN", "Juventus", 22, 26),
    ("P. Demo Midfielder 4", "CEN", "Napoli", 20, 24),
    ("Q. Demo Midfielder 5", "CEN", "Roma", 18, 21),
    ("R. Demo Midfielder 6", "CEN", "Atalanta", 15, 18),
    ("S. Demo Midfielder 7", "CEN", "Lazio", 12, 14),
    ("T. Demo Midfielder 8", "CEN", "Fiorentina", 9, 11),
    ("U. Demo Forward 1", "ATT", "Inter", 45, 55),
    ("V. Demo Forward 2", "ATT", "Napoli", 40, 49),
    ("W. Demo Forward 3", "ATT", "Milan", 34, 41),
    ("X. Demo Forward 4", "ATT", "Juventus", 28, 34),
    ("Y. Demo Forward 5", "ATT", "Roma", 20, 24),
    ("Z. Demo Forward 6", "ATT", "Atalanta", 14, 17),
]


class DemoDataProvider(FantasyDataProvider):
    source_key = "demo"

    def get_quotes(self, season_label: str) -> list[QuoteRecord]:
        return [
            QuoteRecord(
                player_name=name,
                role=role,
                team_name=team,
                quotation=quotation,
                fvm=fvm,
                season_label=season_label,
                source=self.source_key,
            )
            for name, role, team, quotation, fvm in _DEMO_PLAYERS
        ]
