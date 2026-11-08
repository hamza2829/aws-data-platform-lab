"""Sequential daily commits with validation, reconciliation, and durable run history."""

import hashlib
import json
import re
import tempfile
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

from data_platform_lab.contract import (
    SUM_COLUMNS,
    ContractError,
    csv_bytes,
    parse_day,
    raw_metrics,
    validate_csv,
)
from data_platform_lab.storage import S3Store

STATE_KEY = "_state/watermark.json"
RAW_PATTERN = re.compile(r"weather/date=(\d{4}-\d{2}-\d{2})/source\.csv$")
SQL = (Path(__file__).parent / "sql/transform.sql").read_text()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def ingest(store: S3Store, source: Path) -> list[str]:
    rows = validate_csv(Path(source).read_bytes())
    days = sorted({row["date"] for row in rows})
    for day in days:
        payload = csv_bytes([row for row in rows if row["date"] == day])
        store.put(store.raw_bucket, f"weather/date={day}/source.csv", payload, "text/csv")
    return days


def watermark(store: S3Store) -> str | None:
    state = store.optional_json(STATE_KEY)
    if state is None:
        return None
    if state.get("version") != 1 or "last_good_date" not in state:
        raise ValueError("unsupported or broken watermark state")
    return parse_day(state["last_good_date"])


def raw_days(store: S3Store) -> list[str]:
    days = []
    for key in store.keys(store.raw_bucket, "weather/"):
        match = RAW_PATTERN.fullmatch(key)
        if not match:
            raise ContractError(f"unexpected raw object key: {key}")
        days.append(parse_day(match[1]))
    return days


def transform(payload: bytes, output: Path, break_load: bool = False) -> dict:
    source = output.with_suffix(".csv")
    source.write_bytes(payload)
    with duckdb.connect() as connection:
        relation = connection.read_csv(str(source), header=True, all_varchar=True)
        relation.create_view("raw_input")
        query = SQL if not break_load else "SELECT * FROM (" + SQL + ") WHERE false"
        connection.sql(query).write_parquet(str(output), compression="zstd")
    return parquet_metrics(output)


def parquet_metrics(path: Path) -> dict:
    with duckdb.connect() as connection:
        relation = connection.read_parquet(str(path), hive_partitioning=False)
        relation.create_view("curated_input")
        sums = ", ".join(f"COALESCE(SUM({name}), 0)" for name in SUM_COLUMNS)
        row = connection.execute(f"SELECT COUNT(*), {sums} FROM curated_input").fetchone()
        return dict(rows=row[0], sums={name: str(value)
                                      for name, value in zip(SUM_COLUMNS, row[1:], strict=True)})


def mismatches(raw: dict, curated: dict) -> list[str]:
    differences = []
    if raw["rows"] != curated["rows"]:
        differences.append(f"row count: raw={raw['rows']}, curated={curated['rows']}")
    for name in SUM_COLUMNS:
        if Decimal(raw["sums"][name]) != Decimal(curated["sums"][name]):
            differences.append(
                f"{name} sum: raw={raw['sums'][name]}, curated={curated['sums'][name]}"
            )
    return differences


class PipelineFailure(RuntimeError):
    def __init__(self, report: dict):
        self.report = report
        super().__init__(f"run {report['run_id']} failed: {report['error']}")


def reconciliation_markdown(report: dict) -> str:
    lines = ["# Reconciliation report", "",
             f"Run: `{report['run_id']}`. Status: **{report['status']}**.",
             "", f"Watermark before: `{report['watermark_before']}`. "
             f"Watermark after: `{report['watermark_after']}`.", "",
             "| Day | Status | Stage | Raw rows | Curated rows | Reason |",
             "| :--- | :--- | :--- | ---: | ---: | :--- |"]
    for item in report["days"]:
        raw, curated = item.get("raw") or {}, item.get("curated") or {}
        lines.append(f"| {item['day']} | {item['status']} | {item['stage']} | "
                     f"{raw.get('rows', 'unknown')} | {curated.get('rows', 'unknown')} | "
                     f"{item.get('error', 'counts and all sums agree')} |")
        if raw and curated:
            for name in SUM_COLUMNS:
                lines.append(f"| {item['day']} / {name} | sum | {item['stage']} | "
                             f"{raw['sums'][name]} | {curated['sums'][name]} | compared exactly |")
    if report["error"]:
        lines += ["", f"Failure: `{report['error']}`"]
    lines += ["", "Failed prepublication checks compare raw against the candidate Parquet. "
              "Successful checks compare raw against the read-back S3 curated object."]
    return "\n".join(lines) + "\n"


def run(store: S3Store, output: Path, day: str | None = None,
        inject_failure_day: str | None = None) -> dict:
    run_id = uuid.uuid4().hex
    folder = Path(output) / run_id
    folder.mkdir(parents=True, exist_ok=False)
    logs = []
    report = dict(run_id=run_id, status="running", started_at=datetime.now(UTC).isoformat(),
                  watermark_before=None, watermark_after=None,
                  processed_days=[], days=[], error=None)

    def log(event: str, **fields):
        entry = dict(timestamp=datetime.now(UTC).isoformat(), run_id=run_id, event=event, **fields)
        logs.append(entry)
        with (folder / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
        print(json.dumps(entry, sort_keys=True))

    log("run_started", mode="reprocess" if day else "incremental")
    failure = None
    try:
        current = watermark(store)
        report["watermark_before"] = report["watermark_after"] = current
        discovered = raw_days(store)
        if day:
            parse_day(day)
            if current is None or day > current or day not in discovered:
                raise ValueError("reprocess requires an existing committed raw day")
            pending = [day]
        else:
            pending = [item for item in discovered if current is None or item > current]
        for selected in pending:
            item = dict(day=selected, status="running", stage="discovery", raw=None, curated=None)
            report["days"].append(item)
            log("partition_started", day=selected)
            if (not day and current and selected !=
                    (date.fromisoformat(current) + timedelta(days=1)).isoformat()):
                raise ValueError(
                    f"missing raw day after watermark {current}; next raw day is {selected}"
                )
            item["stage"] = "schema_validation"
            payload, version = store.read(store.raw_bucket, f"weather/date={selected}/source.csv")
            rows = validate_csv(payload, selected)
            item.update(raw=raw_metrics(rows), raw_version_id=version,
                        raw_sha256=hashlib.sha256(payload).hexdigest())
            log("raw_validated", day=selected, rows=len(rows))
            key = f"weather/date={selected}/part-00000.parquet"
            with tempfile.TemporaryDirectory() as temporary:
                candidate = Path(temporary) / "candidate.parquet"
                item["stage"] = "prepublication_reconciliation"
                item["curated"] = transform(payload, candidate, selected == inject_failure_day)
                differences = mismatches(item["raw"], item["curated"])
                if differences:
                    raise ValueError("reconciliation mismatch: " + "; ".join(differences))
                item["stage"] = "publication"
                store.put(store.curated_bucket, key, candidate.read_bytes(),
                          "application/vnd.apache.parquet")
                log("partition_published", day=selected, key=key)
                stored, curated_version = store.read(store.curated_bucket, key)
                candidate.write_bytes(stored)
                item["stage"] = "readback_reconciliation"
                item["curated"] = parquet_metrics(candidate)
                item["curated_version_id"] = curated_version
                differences = mismatches(item["raw"], item["curated"])
                if differences:
                    raise ValueError("readback reconciliation mismatch: " + "; ".join(differences))
            log("reconciled", day=selected, rows=item["curated"]["rows"])
            if not day:
                item["stage"] = "watermark_commit"
                store.put(store.curated_bucket, STATE_KEY,
                          json_bytes(dict(version=1, last_good_date=selected, run_id=run_id)))
                current = selected
                report["watermark_after"] = current
                log("watermark_committed", day=selected)
            item.update(status="passed", stage="readback_reconciliation")
            report["processed_days"].append(selected)
        report["status"] = "succeeded"
        log("run_completed", processed_days=report["processed_days"], watermark=current)
    except Exception as exc:
        failure = exc
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        if report["days"]:
            report["days"][-1].update(status="failed", error=report["error"])
        log("run_failed", error=report["error"], watermark=report["watermark_after"])
    report["finished_at"] = datetime.now(UTC).isoformat()
    json_report = json_bytes(report)
    markdown = reconciliation_markdown(report).encode()
    (folder / "reconciliation.json").write_bytes(json_report)
    (folder / "reconciliation.md").write_bytes(markdown)
    log_payload = ("\n".join(json.dumps(entry, sort_keys=True) for entry in logs) + "\n").encode()
    for name, payload, mime in (("reconciliation.json", json_report, "application/json"),
                                ("reconciliation.md", markdown, "text/markdown"),
                                ("events.jsonl", log_payload, "application/x-ndjson")):
        store.put(store.curated_bucket, f"_runs/{run_id}/{name}", payload, mime)
    store.put(store.curated_bucket, f"_history/{run_id}.json", json_report)
    if failure:
        raise PipelineFailure(report) from failure
    return report
