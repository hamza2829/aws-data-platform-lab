"""Publish only test results and LocalStack evidence measured by this workflow."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

artifacts, reports = Path("artifacts"), Path("reports")
reports.mkdir(exist_ok=True)
tests = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
for suite in ET.parse(artifacts / "junit.xml").getroot().iter("testsuite"):
    for key in tests:
        tests[key] += int(suite.attrib.get(key, 0))
assert tests["tests"] and not any(tests[key] for key in ("failures", "errors", "skipped"))
coverage = json.loads((artifacts / "coverage.json").read_text())["totals"]
integration = json.loads((artifacts / "integration.json").read_text())
infrastructure = json.loads((artifacts / "infra-verification.json").read_text())
assert integration["passed"] and infrastructure["passed"]
url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
report = dict(workflow_url=url, source_commit=os.environ["GITHUB_SHA"], tests=tests,
              coverage=coverage, integration=integration, infrastructure=infrastructure)
(reports / "final.json").write_text(json.dumps(report, indent=2) + "\n")
shutil.copyfile(artifacts / "environment.txt", reports / "environment.txt")
shutil.copyfile(artifacts / "terraform.lock.hcl", Path("infra/.terraform.lock.hcl"))
shutil.copyfile(artifacts / "history.json", reports / "history.json")
for label, field in (("failed-load", "failure_run_id"), ("resumed-load", "resume_run_id"),
                      ("schema-failure", "schema_failure_run_id")):
    source = artifacts / "pipeline" / integration[field]
    shutil.copytree(source, reports / label, dirs_exist_ok=True)
lines = [
    f"Measured by [GitHub Actions]({url}) on source commit `{os.environ['GITHUB_SHA']}`.", "",
    f"**{tests['tests']} tests passed**, none skipped. Statement and branch coverage: "
    f"**{coverage['percent_covered']:.2f}%**.", "",
    "Terraform format, validation, apply, a second no-change plan, boto3 resource checks, "
    "the pipeline recovery drill, Dagster execution, and emulator cleanup all passed.", "",
    f"The LocalStack integration produced **{integration['curated_partitions']} daily partitions** "
    f"and **{integration['curated_rows']} curated rows**. Final watermark: "
    f"`{integration['watermark']}`. Run history records **{integration['history_runs']} attempts**, "
    f"including **{integration['failed_attempts']} deliberately failed loads**.", "",
    "The injected row-loss failure left the watermark at `2012-01-02`; resume began at "
    "`2012-01-03`. An unchanged rerun processed no days. Reprocessing an existing day "
    "replaced its single object, created a new S3 version, and kept the partition count fixed. "
    "A renamed `wind` column was rejected with an explicit schema error.", "",
    "Evidence: [raw CI summary](reports/final.json), [run history](reports/history.json), "
    "[failed load reconciliation](reports/failed-load/reconciliation.md), "
    "[recovered reconciliation](reports/resumed-load/reconciliation.md), "
    "[schema failure](reports/schema-failure/reconciliation.md), and "
    "[failed structured logs](reports/failed-load/events.jsonl). The full artifact also contains "
    "Parquet objects, coverage HTML, Terraform outputs, and all run reports.", "",
    "This section and the evidence are committed after the required jobs pass. "
    "That generated report commit does not trigger another workflow. The source commit "
    "above identifies the code actually verified.",
]
readme = Path("README.md")
before, tail = readme.read_text().split("<!-- RESULTS:START -->")
_, after = tail.split("<!-- RESULTS:END -->")
readme.write_text(before + "<!-- RESULTS:START -->\n" + "\n".join(lines)
                  + "\n<!-- RESULTS:END -->" + after)
with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
    stream.write("\n".join(lines) + "\n")
