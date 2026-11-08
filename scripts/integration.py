"""Exercise the applied LocalStack platform, recovery, and Dagster in CI."""

import json
from pathlib import Path

from data_platform_lab.drill import failure_drill
from data_platform_lab.orchestration import execute_job
from data_platform_lab.pipeline import parquet_metrics
from data_platform_lab.storage import make_store

outputs = json.loads(Path("artifacts/terraform-outputs.json").read_text())
store = make_store(role_arn=outputs["pipeline_role_arn"]["value"])
source, output = Path("data/seattle-weather.csv"), Path("artifacts/pipeline")
drill = failure_drill(store, source, output)
orchestration = execute_job(store, source, Path("artifacts/orchestration"))
assert orchestration.success
assert orchestration.output_for_node("curate_new_days")["processed_days"] == []
metrics = []
for key in store.keys(store.curated_bucket, "weather/"):
    payload, version = store.read(store.curated_bucket, key)
    local = Path("artifacts/curated") / key
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(payload)
    metrics.append(dict(key=key, version_id=version, **parquet_metrics(local)))
versions = store.client.list_object_versions(Bucket=store.curated_bucket, Prefix="weather/")
assert len(versions["Versions"]) > len(metrics)
history = store.history()
assert len(history) == 7
assert sum(item["status"] == "failed" for item in history) == 2
summary = dict(passed=True, source_days=len(drill["source_days"]),
               curated_partitions=len(metrics), curated_rows=sum(item["rows"] for item in metrics),
               watermark=drill["watermark"], history_runs=len(history), failed_attempts=2,
               orchestration_success=orchestration.success, metrics=metrics,
               failure_run_id=drill["failure"]["run_id"], resume_run_id=drill["resumed"]["run_id"],
               schema_failure_run_id=drill["schema_failure"]["run_id"])
Path("artifacts/integration.json").write_text(json.dumps(summary, indent=2) + "\n")
Path("artifacts/history.json").write_text(json.dumps(history, indent=2) + "\n")
print(json.dumps(summary, indent=2))
