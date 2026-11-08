"""A small Dagster job, importable and executable without a Dagster server."""

from pathlib import Path

from dagster import Field, RetryPolicy, job, op, resource

from data_platform_lab.pipeline import ingest, run
from data_platform_lab.storage import make_store


@resource(config_schema={"endpoint": Field(str, default_value="http://localhost:4566"),
                         "prefix": Field(str, default_value="aws-data-platform-lab"),
                         "role_arn": Field(str, default_value="")})
def storage_resource(context):
    config = context.resource_config
    return make_store(config["endpoint"], config["prefix"], config["role_arn"] or None)


@op(required_resource_keys={"storage"}, config_schema={"source": str})
def ingest_source(context) -> list[str]:
    return ingest(context.resources.storage, Path(context.op_config["source"]))


@op(required_resource_keys={"storage"}, config_schema={"output": str},
    retry_policy=RetryPolicy(max_retries=1, delay=0))
def curate_new_days(context, ingested_days: list[str]) -> dict:
    context.log.info(f"Source supplied {len(ingested_days)} daily partitions")
    return run(context.resources.storage, Path(context.op_config["output"]))


@job(resource_defs={"storage": storage_resource})
def daily_platform_job():
    curate_new_days(ingest_source())


def execute_job(store, source: Path, output: Path):
    return daily_platform_job.execute_in_process(
        resources={"storage": store},
        run_config={"ops": {"ingest_source": {"config": {"source": str(source)}},
                             "curate_new_days": {"config": {"output": str(output)}}}},
    )
