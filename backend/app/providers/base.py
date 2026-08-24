"""Provider interfaces (§39). Neither the database nor the frontend talks to
an external API directly — everything goes through one of these. Swapping a
real integration in later means writing a new class here, not touching
callers.

MatchDataProvider / InjuryDataProvider / LineupDataProvider /
AdvancedStatsProvider are declared for MVP2+ and intentionally left
unimplemented in MVP1.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderUnavailable(Exception):
    """Raised when a provider cannot currently serve data — missing API key,
    network failure, rate limit exhausted, etc. Callers must catch this and
    fall back (cache -> secondary provider -> visible warning), per §38.
    Never let this crash a request or silently produce fabricated data."""


@dataclass(frozen=True)
class QuoteRecord:
    """One listone entry, as delivered by a FantasyDataProvider."""

    player_name: str
    role: str  # POR | DIF | CEN | ATT
    team_name: str | None
    quotation: int | None
    fvm: int | None
    season_label: str
    source: str


@dataclass(frozen=True)
class PlayerRecord:
    """A player as delivered by a PlayerDataProvider."""

    name: str
    role: str | None
    team_name: str | None
    birth_date: str | None
    nationality: str | None
    external_id: str | None
    source: str


@dataclass(frozen=True)
class MarketAverageRecord:
    """A market-average price signal, per §6/§7 — a benchmark, never "the
    correct price"."""

    player_name: str
    role: str
    avg_price: float
    sample_size: int
    season_label: str
    source: str


class FantasyDataProvider(ABC):
    """Listone / quotations / FVM — primary conceptual source is
    Fantacalcio.it (§1), delivered via CSV/JSON import or demo seed in MVP1."""

    source_key: str

    @abstractmethod
    def get_quotes(self, season_label: str) -> list[QuoteRecord]: ...


class PlayerDataProvider(ABC):
    """Structured player/team data — API-Football in production (§4)."""

    source_key: str

    @abstractmethod
    def search_players(self, query: str) -> list[PlayerRecord]: ...


class AuctionDataProvider(ABC):
    """Market-average benchmark data — local league history or an external
    aggregate (§6/§7)."""

    source_key: str

    @abstractmethod
    def get_market_averages(self, season_label: str) -> list[MarketAverageRecord]: ...


class MatchDataProvider(ABC):
    """Deferred to MVP2 — fixtures/results/lineups/match stats."""


class InjuryDataProvider(ABC):
    """Deferred to MVP2 — injury/suspension status."""


class LineupDataProvider(ABC):
    """Deferred to MVP2 — probable lineups / starting probability."""


class AdvancedStatsProvider(ABC):
    """Deferred to MVP2 — xG/xA/npxG etc. (Understat-equivalent)."""
