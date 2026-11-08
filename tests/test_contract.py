import pytest

from data_platform_lab.contract import (
    COLUMNS,
    ContractError,
    csv_bytes,
    parse_day,
    raw_metrics,
    validate_csv,
)


def test_public_source_and_exact_sums(source):
    rows = validate_csv(source.read_bytes())
    assert len(rows) == 7
    assert raw_metrics(rows)["sums"]["precipitation"] == "35.8"
    assert validate_csv(csv_bytes(rows)) == rows
    assert parse_day("2012-02-29") == "2012-02-29"


@pytest.mark.parametrize("day", ["20120101", "2012-1-1", "2012-02-30", None])
def test_bad_days(day):
    with pytest.raises(ContractError, match="invalid ISO"):
        parse_day(day)


@pytest.mark.parametrize("kind", ["missing", "renamed", "extra", "order", "empty", "unicode",
                                  "duplicate", "blank", "wrong_day", "nan", "range", "scale",
                                  "category", "temperature", "short_row", "long_row", "quoted"])
def test_broken_schema_and_values(source, kind):
    payload = source.read_bytes()
    rows = validate_csv(payload)
    if kind == "missing":
        payload = payload.replace(b",wind,", b",")
    elif kind == "renamed":
        payload = payload.replace(b"wind", b"gust")
    elif kind == "extra":
        payload = payload.replace(b",weather\n", b",weather,extra\n")
    elif kind == "order":
        payload = payload.replace(b"temp_max,temp_min", b"temp_min,temp_max")
    elif kind == "empty":
        payload = (",".join(COLUMNS) + "\n").encode()
    elif kind == "unicode":
        payload = b"\xff"
    elif kind == "duplicate":
        payload = csv_bytes([rows[0], rows[0]])
    elif kind == "blank":
        rows[0]["wind"] = ""
        payload = csv_bytes(rows)
    elif kind == "wrong_day":
        with pytest.raises(ContractError, match="partition"):
            validate_csv(csv_bytes([rows[0]]), "2012-01-02")
        return
    elif kind in {"nan", "range", "scale"}:
        rows[0]["precipitation"] = {"nan": "NaN", "range": "501", "scale": "0.11"}[kind]
        payload = csv_bytes(rows)
    elif kind == "category":
        rows[0]["weather"] = "unknown"
        payload = csv_bytes(rows)
    elif kind == "temperature":
        rows[0]["temp_min"] = "50.0"
        payload = csv_bytes(rows)
    elif kind == "short_row":
        payload = (",".join(COLUMNS) + "\n2012-01-01,0.0\n").encode()
    elif kind == "long_row":
        payload = csv_bytes([rows[0]]).rstrip(b"\n") + b",extra\n"
    else:
        payload = (",".join(COLUMNS) + '\n"unterminated').encode()
    with pytest.raises(ContractError):
        validate_csv(payload)
