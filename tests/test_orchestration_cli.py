import pytest
from dagster import build_init_resource_context

from data_platform_lab.cli import main
from data_platform_lab.orchestration import daily_platform_job, execute_job, storage_resource
from data_platform_lab.pipeline import run


def test_dagster_import_execute_and_retry(store, source, tmp_path, monkeypatch):
    assert daily_platform_job.name == "daily_platform_job"
    attempts = []

    def flaky(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("transient load problem")
        return run(*args, **kwargs)

    monkeypatch.setattr("data_platform_lab.orchestration.run", flaky)
    result = execute_job(store, source, tmp_path)
    assert result.success
    assert len(attempts) == 2
    assert len(result.output_for_node("curate_new_days")["processed_days"]) == 7


def test_resource_build(store, monkeypatch):
    monkeypatch.setattr("data_platform_lab.orchestration.make_store", lambda *args: store)
    context = build_init_resource_context(config={"endpoint": "http://localhost:4566",
                                                  "prefix": "lab", "role_arn": ""})
    assert storage_resource(context) is store


def test_cli_ingest_run_history_orchestration(store, source, tmp_path, monkeypatch):
    monkeypatch.setattr("data_platform_lab.cli.make_store", lambda *args: store)
    assert main(["ingest", str(source)]) == 0
    assert main(["run", "--output", str(tmp_path)]) == 0
    assert main(["history"]) == 0
    assert main(["orchestrate", str(source), "--output", str(tmp_path)]) == 0


def test_cli_failure_drill(store, source, tmp_path, monkeypatch):
    monkeypatch.setattr("data_platform_lab.cli.make_store", lambda *args: store)
    assert main(["failure-drill", str(source), "--output", str(tmp_path)]) == 0


def test_cli_readable_failure(store, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("data_platform_lab.cli.make_store", lambda *args: store)
    with pytest.raises(SystemExit) as caught:
        main(["run", "--output", str(tmp_path), "--day", "2012-01-01"])
    assert caught.value.code == 2
    assert "reprocess requires" in capsys.readouterr().err
