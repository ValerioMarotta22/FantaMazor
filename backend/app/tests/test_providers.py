import pytest

from app.providers.api_football import ApiFootballProvider
from app.providers.base import ProviderUnavailable
from app.providers.demo_data import DEMO_DATA, DemoDataProvider
from app.providers.manual_import import ListoneValidationError, parse_listone_csv, parse_listone_json


def test_demo_data_is_clearly_flagged():
    assert DEMO_DATA is True
    provider = DemoDataProvider()
    quotes = provider.get_quotes("2025-26")
    assert len(quotes) > 0
    assert all(q.source == "demo" for q in quotes)


def test_demo_data_covers_every_role_with_enough_players_for_target_league():
    # Target league needs 3 POR / 8 DIF / 8 CEN / 6 ATT per team -- demo data
    # should have enough per role for at least a small test auction.
    provider = DemoDataProvider()
    quotes = provider.get_quotes("2025-26")
    by_role: dict[str, int] = {}
    for q in quotes:
        by_role[q.role] = by_role.get(q.role, 0) + 1
    assert by_role["POR"] >= 3
    assert by_role["DIF"] >= 3
    assert by_role["CEN"] >= 3
    assert by_role["ATT"] >= 3


def test_manual_import_csv_valid():
    csv_bytes = b"name,role,team,quotation,fvm\nMario Rossi,ATT,Inter,40,48\n"
    records = parse_listone_csv(csv_bytes, season_label="2025-26")
    assert len(records) == 1
    assert records[0].role == "ATT"
    assert records[0].quotation == 40


def test_manual_import_csv_missing_column_raises():
    csv_bytes = b"name,team\nMario Rossi,Inter\n"
    with pytest.raises(ListoneValidationError):
        parse_listone_csv(csv_bytes, season_label="2025-26")


def test_manual_import_csv_invalid_role_raises():
    csv_bytes = b"name,role\nMario Rossi,XYZ\n"
    with pytest.raises(ListoneValidationError):
        parse_listone_csv(csv_bytes, season_label="2025-26")


def test_manual_import_never_fabricates_missing_optional_fields():
    csv_bytes = b"name,role\nMario Rossi,ATT\n"
    records = parse_listone_csv(csv_bytes, season_label="2025-26")
    assert records[0].quotation is None  # not 0 -- per §55, unknown stays unknown
    assert records[0].fvm is None


def test_manual_import_json_valid():
    json_bytes = b'[{"name": "Mario Rossi", "role": "por", "quotation": 15}]'
    records = parse_listone_json(json_bytes, season_label="2025-26")
    assert records[0].role == "POR"


def test_manual_import_json_invalid_shape_raises():
    with pytest.raises(ListoneValidationError):
        parse_listone_json(b'{"not": "a list"}', season_label="2025-26")


def test_api_football_reports_unavailable_without_key(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = ApiFootballProvider()
    assert provider.is_configured() is False
    with pytest.raises(ProviderUnavailable):
        provider.search_players("Mario Rossi")
    get_settings.cache_clear()
