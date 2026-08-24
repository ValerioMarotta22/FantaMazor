"""ManualImportProvider — the primary MVP1 data path (§1, §48).

Parses a user-supplied listone CSV or JSON into validated QuoteRecords.
Nothing is guessed: a row missing a required field is rejected with a clear
error rather than silently defaulted, per §55.
"""

import csv
import io
import json

from app.providers.base import FantasyDataProvider, ProviderUnavailable, QuoteRecord

VALID_ROLES = {"POR", "DIF", "CEN", "ATT"}

REQUIRED_CSV_COLUMNS = {"name", "role"}


class ListoneValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s): {errors[:5]}")


def _normalize_role(raw: str) -> str:
    role = raw.strip().upper()
    if role not in VALID_ROLES:
        raise ValueError(f"invalid role '{raw}' (expected one of {sorted(VALID_ROLES)})")
    return role


def _parse_int(raw: str | int | None) -> int | None:
    if raw is None or raw == "":
        return None
    return int(raw)


def parse_listone_csv(content: bytes, season_label: str, source: str = "manual_import") -> list[QuoteRecord]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ListoneValidationError(["file has no header row"])
    missing_cols = REQUIRED_CSV_COLUMNS - {c.strip().lower() for c in reader.fieldnames}
    if missing_cols:
        raise ListoneValidationError([f"missing required column(s): {sorted(missing_cols)}"])

    records: list[QuoteRecord] = []
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):  # header is row 1
        row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
        try:
            name = row["name"]
            if not name:
                raise ValueError("empty name")
            role = _normalize_role(row["role"])
            records.append(
                QuoteRecord(
                    player_name=name,
                    role=role,
                    team_name=row.get("team") or None,
                    quotation=_parse_int(row.get("quotation")),
                    fvm=_parse_int(row.get("fvm")),
                    season_label=season_label,
                    source=source,
                )
            )
        except (ValueError, KeyError) as exc:
            errors.append(f"row {i}: {exc}")

    if errors:
        raise ListoneValidationError(errors)
    return records


def parse_listone_json(content: bytes, season_label: str, source: str = "manual_import") -> list[QuoteRecord]:
    try:
        rows = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ListoneValidationError([f"invalid JSON: {exc}"]) from exc
    if not isinstance(rows, list):
        raise ListoneValidationError(["JSON root must be an array of player objects"])

    records: list[QuoteRecord] = []
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        try:
            name = row["name"]
            if not name:
                raise ValueError("empty name")
            role = _normalize_role(row["role"])
            records.append(
                QuoteRecord(
                    player_name=name,
                    role=role,
                    team_name=row.get("team") or None,
                    quotation=_parse_int(row.get("quotation")),
                    fvm=_parse_int(row.get("fvm")),
                    season_label=season_label,
                    source=source,
                )
            )
        except (ValueError, KeyError) as exc:
            errors.append(f"item {i}: {exc}")

    if errors:
        raise ListoneValidationError(errors)
    return records


class ManualImportProvider(FantasyDataProvider):
    """Holds the most recently imported batch in memory for this process;
    the API layer is responsible for persisting parsed records to
    `fantasy_quotes` immediately after a successful import."""

    source_key = "manual_import"

    def __init__(self) -> None:
        self._last_import: list[QuoteRecord] = []

    def load(self, records: list[QuoteRecord]) -> None:
        self._last_import = records

    def get_quotes(self, season_label: str) -> list[QuoteRecord]:
        if not self._last_import:
            raise ProviderUnavailable("no listone has been imported yet")
        return [r for r in self._last_import if r.season_label == season_label]
