import json

import pytest

from data_platform_lab.drill import failure_drill
from data_platform_lab.pipeline import (
    STATE_KEY,
    PipelineFailure,
    ingest,
    json_bytes,
    mismatches,
    parquet_metrics,
    raw_days,
    run,
    transform,
    watermark,
)


def test_incremental_run_noop_and_partition_replacement(store, source, tmp_path):
    days = ingest(store, source)
    report = run(store, tmp_path)
    assert report["processed_days"] == days
    assert watermark(store) == "2012-01-07"
    assert all(item["status"] == "passed" for item in report["days"])
    assert run(store, tmp_path)["processed_days"] == []
    key = "weather/date=2012-01-02/part-00000.parquet"
    first, first_version = store.read(store.curated_bucket, key)
    reprocess = run(store, tmp_path, day="2012-01-02")
    second, second_version = store.read(store.curated_bucket, key)
    assert first == second
    assert first_version != second_version
    assert reprocess["processed_days"] == ["2012-01-02"]
    assert watermark(store) == "2012-01-07"
    assert len(store.keys(store.curated_bucket, "weather/")) == 7
    local = tmp_path / report["run_id"]
    assert json.loads((local / "reconciliation.json").read_text()) == report
    assert "counts and all sums agree" in (local / "reconciliation.md").read_text()
    events = [json.loads(line) for line in (local / "events.jsonl").read_text().splitlines()]
    assert all(event["run_id"] == report["run_id"] for event in events)
    assert events[-1]["event"] == "run_completed"
    assert len(store.history()) == 3


def test_failure_drill_and_resume_from_last_good_watermark(store, source, tmp_path):
    result = failure_drill(store, source, tmp_path)
    assert result["passed"]
    assert result["failure"]["watermark_after"] == "2012-01-02"
    assert result["failure"]["days"][-1]["curated"]["rows"] == 0
    assert "row count" in result["failure"]["error"]
    assert result["resumed"]["processed_days"][0] == "2012-01-03"
    assert result["curated_partitions"] == 7
    assert "schema columns changed" in result["schema_failure"]["error"]
    with pytest.raises(ValueError, match="empty"):
        failure_drill(store, source, tmp_path)


def test_missing_calendar_day_stops_watermark(store, source, tmp_path):
    ingest(store, source)
    store.client.delete_object(Bucket=store.raw_bucket, Key="weather/date=2012-01-02/source.csv")
    with pytest.raises(PipelineFailure, match="missing raw day") as caught:
        run(store, tmp_path)
    assert caught.value.report["watermark_after"] == "2012-01-01"
    ingest(store, source)
    assert run(store, tmp_path)["processed_days"][0] == "2012-01-02"


def test_commit_interruption_retries_same_partition_without_duplicates(
    store, source, tmp_path, monkeypatch
):
    ingest(store, source)
    original = store.put

    def fail_state(bucket, key, payload, content_type="application/json"):
        if key == STATE_KEY:
            raise OSError("simulated interruption before state commit")
        return original(bucket, key, payload, content_type)

    monkeypatch.setattr(store, "put", fail_state)
    with pytest.raises(PipelineFailure, match="interruption"):
        run(store, tmp_path)
    assert watermark(store) is None
    assert len(store.keys(store.curated_bucket, "weather/")) == 1
    monkeypatch.setattr(store, "put", original)
    assert len(run(store, tmp_path)["processed_days"]) == 7
    assert len(store.keys(store.curated_bucket, "weather/")) == 7


def test_readback_reconciliation_detects_corruption(store, source, tmp_path, monkeypatch):
    ingest(store, source)
    original = store.read
    raw, _ = original(store.raw_bucket, "weather/date=2012-01-01/source.csv")
    candidate = tmp_path / "bad.parquet"
    transform(raw, candidate, break_load=True)

    def corrupt_read(bucket, key):
        if key.endswith(".parquet"):
            return candidate.read_bytes(), "bad-version"
        return original(bucket, key)

    monkeypatch.setattr(store, "read", corrupt_read)
    with pytest.raises(PipelineFailure, match="readback reconciliation") as caught:
        run(store, tmp_path / "runs")
    assert caught.value.report["days"][-1]["stage"] == "readback_reconciliation"
    assert watermark(store) is None
    monkeypatch.setattr(store, "read", original)
    assert run(store, tmp_path / "runs")["status"] == "succeeded"


def test_state_and_key_validation(store, tmp_path):
    assert watermark(store) is None
    assert raw_days(store) == []
    assert run(store, tmp_path)["status"] == "succeeded"
    store.put(store.curated_bucket, STATE_KEY, json_bytes(dict(version=999)))
    with pytest.raises(ValueError, match="watermark"):
        watermark(store)
    store.put(store.raw_bucket, "weather/unexpected.csv", b"bad")
    with pytest.raises(ValueError, match="unexpected raw"):
        raw_days(store)


@pytest.mark.parametrize("day", ["2012-01-01", "2012-01-99", "2099-01-01"])
def test_reprocess_rejects_uncommitted_days(store, tmp_path, day):
    with pytest.raises(PipelineFailure):
        run(store, tmp_path, day=day)


def test_transform_schema_types_metrics_and_difference(source, tmp_path):
    import duckdb

    output = tmp_path / "data.parquet"
    metrics = transform(source.read_bytes(), output)
    assert metrics == parquet_metrics(output)
    assert metrics["rows"] == 7
    assert metrics["sums"]["precipitation"] == "35.8"
    with duckdb.connect() as db:
        assert db.read_parquet(str(output)).columns[-1] == "temperature_range"
        row = db.execute("SELECT temperature_range FROM read_parquet(?) ORDER BY date LIMIT 1",
                         [str(output)]).fetchone()
        assert str(row[0]) == "7.8"
    changed = dict(rows=6, sums=dict(metrics["sums"], wind="999"))
    assert len(mismatches(metrics, changed)) == 2
    assert mismatches(metrics, metrics) == []


def test_drill_rejects_too_few_days(store, source, tmp_path):
    short = tmp_path / "short.csv"
    short.write_bytes(b"\n".join(source.read_bytes().splitlines()[:3]) + b"\n")
    with pytest.raises(ValueError, match="three"):
        failure_drill(store, short, tmp_path / "runs")
