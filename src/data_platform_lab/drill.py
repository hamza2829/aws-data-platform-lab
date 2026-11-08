"""A reproducible bad-load drill, recovery, and schema-change rejection."""

import json
from pathlib import Path

from data_platform_lab.pipeline import PipelineFailure, ingest, run, watermark
from data_platform_lab.storage import S3Store


def failure_drill(store: S3Store, source: Path, output: Path) -> dict:
    if watermark(store) is not None:
        raise ValueError("failure drill requires an empty curated watermark")
    days = ingest(store, source)
    if len(days) < 3:
        raise ValueError("failure drill requires at least three consecutive input days")
    broken_day = days[2]
    try:
        run(store, output, inject_failure_day=broken_day)
    except PipelineFailure as exc:
        failed = exc.report
    else:
        raise AssertionError("injected load failure did not fail")
    assert failed["watermark_after"] == days[1]
    assert failed["days"][-1]["raw"]["rows"] > failed["days"][-1]["curated"]["rows"]
    assert not store.keys(store.curated_bucket, f"weather/date={broken_day}/")
    resumed = run(store, output)
    assert resumed["processed_days"] == days[2:]
    assert watermark(store) == days[-1]
    noop = run(store, output)
    assert noop["processed_days"] == []
    reprocessed = run(store, output, day=days[0])
    assert watermark(store) == days[-1]
    raw_key = f"weather/date={broken_day}/source.csv"
    original, _ = store.read(store.raw_bucket, raw_key)
    store.put(store.raw_bucket, raw_key, original.replace(b"wind", b"gust"), "text/csv")
    try:
        run(store, output, day=broken_day)
    except PipelineFailure as exc:
        schema_failure = exc.report
    else:
        raise AssertionError("changed schema did not fail")
    finally:
        store.put(store.raw_bucket, raw_key, original, "text/csv")
    assert "schema columns changed" in schema_failure["error"]
    assert watermark(store) == days[-1]
    schema_repaired = run(store, output, day=broken_day)
    keys = store.keys(store.curated_bucket, "weather/")
    assert len(keys) == len(days)
    assert len(store.history()) == 6
    report = dict(
        passed=True, source_days=days, curated_partitions=len(keys), watermark=watermark(store),
        failure=failed, resumed=resumed, noop=noop, reprocessed=reprocessed,
        schema_failure=schema_failure, schema_repaired=schema_repaired,
    )
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / "drill.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
