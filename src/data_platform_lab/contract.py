"""Exact CSV schema and value checks driven by the committed YAML contract."""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

CONTRACT = yaml.safe_load((Path(__file__).parent / "contracts/weather.yaml").read_text())
COLUMNS = list(CONTRACT["columns"])
SUM_COLUMNS = CONTRACT["reconcile_sums"]


class ContractError(ValueError):
    """Input changed or violates the dataset contract."""


def parse_day(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise ContractError(f"invalid ISO day: {value}") from exc
    return value


def validate_csv(payload: bytes, expected_day: str | None = None) -> list[dict]:
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8")), strict=True)
        if reader.fieldnames != COLUMNS:
            raise ContractError(f"schema columns changed: expected {COLUMNS}, got {reader.fieldnames}")
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise ContractError(f"invalid CSV: {exc}") from exc
    if not rows:
        raise ContractError("empty CSV is not a complete daily partition")
    seen = set()
    for index, row in enumerate(rows, start=1):
        if None in row or any(value is None or value == "" for value in row.values()):
            raise ContractError(f"row {index}: missing or extra values")
        day = parse_day(row["date"])
        if expected_day is not None and day != expected_day:
            raise ContractError(f"row {index}: date {day} does not match partition {expected_day}")
        if day in seen:
            raise ContractError(f"row {index}: duplicate primary key date {day}")
        seen.add(day)
        for name, spec in CONTRACT["columns"].items():
            value = row[name]
            if spec["type"] == "decimal":
                try:
                    number = Decimal(value)
                    if not number.is_finite() or not Decimal(str(spec["min"])) <= number <= Decimal(
                        str(spec["max"])
                    ) or number != number.quantize(Decimal("0.1")):
                        raise InvalidOperation
                except InvalidOperation as exc:
                    raise ContractError(f"row {index}: {name} violates decimal range or scale") from exc
            elif spec["type"] == "string" and value not in spec["enum"]:
                raise ContractError(f"row {index}: unknown {name}: {value}")
        if Decimal(row["temp_min"]) > Decimal(row["temp_max"]):
            raise ContractError(f"row {index}: temp_min is above temp_max")
    return rows


def csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def raw_metrics(rows: list[dict]) -> dict:
    return dict(rows=len(rows), sums={name: str(sum((Decimal(row[name]) for row in rows), Decimal(0)))
                                     for name in SUM_COLUMNS})
