"""ApiFootballProvider (§4) — real HTTP adapter for API-Football.

Self-reports ProviderUnavailable when no API key is configured, so the rest
of the system degrades gracefully instead of depending on it (§38). When a
key is present: server-side only (§50), retried with exponential backoff on
HTTP 429, and cached in Redis to avoid duplicate requests.
"""

import time

import httpx

from app.core.cache import TTL_HISTORICAL, get_redis
from app.core.config import get_settings
from app.providers.base import PlayerDataProvider, PlayerRecord, ProviderUnavailable

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0


class ApiFootballProvider(PlayerDataProvider):
    source_key = "api_football"

    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._settings.api_football_api_key)

    def _request(self, path: str, params: dict) -> dict:
        if not self.is_configured():
            raise ProviderUnavailable("API_FOOTBALL_API_KEY is not set")

        cache_key = f"api_football:{path}:{sorted(params.items())}"
        redis = get_redis()
        cached = redis.get(cache_key)
        if cached:
            import json

            return json.loads(cached)

        headers = {"x-apisports-key": self._settings.api_football_api_key}
        url = f"{self._settings.api_football_base_url}{path}"

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = httpx.get(url, headers=headers, params=params, timeout=10.0)
                if resp.status_code == 429:
                    wait = BASE_BACKOFF_SECONDS * (2**attempt)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                redis.setex(cache_key, TTL_HISTORICAL, __import__("json").dumps(data))
                return data
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(BASE_BACKOFF_SECONDS * (2**attempt))

        raise ProviderUnavailable(f"API-Football request failed after {MAX_RETRIES} attempts: {last_error}")

    def search_players(self, query: str) -> list[PlayerRecord]:
        data = self._request("/players", {"search": query, "league": 135, "season": 2025})
        records: list[PlayerRecord] = []
        for item in data.get("response", []):
            player = item.get("player", {})
            stats = item.get("statistics", [{}])[0] if item.get("statistics") else {}
            team = stats.get("team", {}) if stats else {}
            records.append(
                PlayerRecord(
                    name=player.get("name"),
                    role=None,
                    team_name=team.get("name"),
                    birth_date=player.get("birth", {}).get("date"),
                    nationality=player.get("nationality"),
                    external_id=str(player.get("id")) if player.get("id") else None,
                    source=self.source_key,
                )
            )
        return records
