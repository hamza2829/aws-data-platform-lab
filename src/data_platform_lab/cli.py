"""Command-line access to ingestion, incremental loading, orchestration, and drills."""

import argparse
import json
from pathlib import Path

from data_platform_lab.drill import failure_drill
from data_platform_lab.orchestration import execute_job
from data_platform_lab.pipeline import PipelineFailure, ingest, run
from data_platform_lab.storage import make_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LocalStack data platform lab")
    parser.add_argument("--endpoint", default="http://localhost:4566")
    parser.add_argument("--prefix", default="aws-data-platform-lab")
    parser.add_argument("--role-arn")
    commands = parser.add_subparsers(dest="command", required=True)
    ingestion = commands.add_parser("ingest")
    ingestion.add_argument("source", type=Path)
    processing = commands.add_parser("run")
    processing.add_argument("--output", type=Path, required=True)
    processing.add_argument("--day")
    processing.add_argument("--inject-failure-day")
    orchestration = commands.add_parser("orchestrate")
    orchestration.add_argument("source", type=Path)
    orchestration.add_argument("--output", type=Path, required=True)
    drill = commands.add_parser("failure-drill")
    drill.add_argument("source", type=Path)
    drill.add_argument("--output", type=Path, required=True)
    commands.add_parser("history")
    args = parser.parse_args(argv)
    try:
        store = make_store(args.endpoint, args.prefix, args.role_arn)
        if args.command == "ingest":
            result = dict(ingested_days=ingest(store, args.source))
        elif args.command == "run":
            result = run(store, args.output, args.day, args.inject_failure_day)
        elif args.command == "orchestrate":
            result = dict(dagster_success=execute_job(store, args.source, args.output).success)
        elif args.command == "failure-drill":
            result = failure_drill(store, args.source, args.output)
        else:
            result = store.history()
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, PipelineFailure) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
