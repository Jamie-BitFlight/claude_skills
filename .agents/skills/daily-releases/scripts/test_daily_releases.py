"""Focused regression checks for the daily-release range default."""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import NotRequired, TypedDict, cast

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "daily_releases_lib"))
spec = importlib.util.spec_from_file_location("list_daily_ranges", SCRIPT_DIR / "list_daily_ranges.py")
assert spec
assert spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

finalizer_spec = importlib.util.spec_from_file_location(
    "finalize_day_analysis", SCRIPT_DIR / "finalize_day_analysis.py"
)
assert finalizer_spec
assert finalizer_spec.loader
finalizer = importlib.util.module_from_spec(finalizer_spec)
sys.modules[finalizer_spec.name] = finalizer
finalizer_spec.loader.exec_module(finalizer)

formatter_spec = importlib.util.spec_from_file_location("format_release_notes", SCRIPT_DIR / "format_release_notes.py")
assert formatter_spec
assert formatter_spec.loader
formatter = importlib.util.module_from_spec(formatter_spec)
sys.modules[formatter_spec.name] = formatter
formatter_spec.loader.exec_module(formatter)


class _Task(TypedDict):
    id: str
    input: str
    artifact: str
    model: NotRequired[str]
    status: str
    attempt: NotRequired[int]


def _tasks(result: dict[str, object]) -> list[_Task]:
    value = result["tasks"]
    assert isinstance(value, list)
    return cast("list[_Task]", value)


def _transitions(result: dict[str, object]) -> list[dict[str, object]]:
    value = result["transitions"]
    assert isinstance(value, list)
    return cast("list[dict[str, object]]", value)


class _Adapters:
    def __init__(self) -> None:
        self.publishes: list[str] = []
        self.fail_old_once = True
        self.remote_tags: dict[str, str] = {}

    def discover(self, **_options: object) -> list[dict[str, str]]:
        return [
            {"date": "2026-09-26", "tag": "v2026.09.26", "base_ref": "old-base", "head_ref": "old-head"},
            {"date": "2026-09-27", "tag": "v2026.09.27", "base_ref": "new-base", "head_ref": "new-head"},
        ]

    def collect(self, **_task: object) -> None:
        return None

    def bucket(self, *, date: str, **_task: object) -> list[str]:
        return ["001", "002"] if date == "2026-09-26" else ["001"]

    def render(self, **_task: object) -> None:
        return None

    def publish(self, *, date: str, **_task: object) -> None:
        if date == "2026-09-26" and self.fail_old_once:
            self.fail_old_once = False
            raise RuntimeError("tag created before release request failed")
        self.publishes.append(date)
        self.remote_tags[date] = cast("str", _task["tag"])

    def release_identity(self, *, date: str, head_ref: str, **_task: object) -> dict[str, str] | None:
        tag = self.remote_tags.get(date)
        return {"tag": tag, "head_ref": head_ref} if tag else None


def test_default_start_uses_latest_daily_release_and_explicit_start_wins() -> None:
    repo = SimpleNamespace(
        get_releases=lambda: [
            SimpleNamespace(tag_name="unrelated"),
            SimpleNamespace(tag_name="v2026.05.22"),
            SimpleNamespace(tag_name="v2026.08.01-r2"),
            SimpleNamespace(tag_name="v2026.13.40"),
        ]
    )

    assert module._resolve_start_date(None, repo) == date(2026, 8, 1)
    assert module._resolve_start_date(date(2025, 1, 2), repo) == date(2025, 1, 2)
    assert module._resolve_start_date(None, SimpleNamespace(get_releases=list)) is None


def test_finalize_single_bucket_adds_release_contract(tmp_path: Path) -> None:
    day = tmp_path / "2026-09-10"
    (day / "summaries").mkdir(parents=True)
    (day / "dataset").mkdir()
    (day / "summaries/bucket_001.json").write_text(
        json.dumps({"bucket_summary": "Updated Codex defaults.", "change_categories": {}, "breaking_changes": []}),
        encoding="utf-8",
    )
    (day / "dataset/files.json").write_text(json.dumps([{"lines_added": 3, "lines_deleted": 1}]), encoding="utf-8")
    (day / "dataset/commits.json").write_text(json.dumps([{"sha": "abc"}]), encoding="utf-8")

    analysis_file = finalizer.finalize_day(day)
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))

    assert analysis["title"] == "Daily Release 2026-09-10"
    assert analysis["summary"] == "Updated Codex defaults."
    assert "bucket_summary" not in analysis
    assert analysis["statistics"] == {"commit_count": 1, "files_changed": 1, "lines_added": 3, "lines_deleted": 1}


def test_release_formatter_renders_daily_analysis() -> None:
    description = formatter.format_release_notes({
        "title": "Daily Release 2026-09-10",
        "summary": "Updated Codex defaults.",
        "statistics": {"commit_count": 1, "files_changed": 1, "lines_added": 3, "lines_deleted": 1},
        "change_categories": {"enhancements": [{"title": "Tune Codex", "description": "Pinned agent limits."}]},
        "components_affected": ["codex"],
        "breaking_changes": ["Default model changed."],
    })

    assert description.startswith("# Daily Release 2026-09-10")
    assert "- **Commits**: 1" in description
    assert "- **Tune Codex**: Pinned agent limits." in description
    assert "- Default model changed." in description


def test_copied_controller_runs_directly(tmp_path: Path) -> None:
    copied_skill = tmp_path / "daily-releases"
    shutil.copytree(SCRIPT_DIR.parent, copied_skill)

    result = subprocess.run(
        ["uv", "run", str(copied_skill / "scripts/daily_releases.py"), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


def test_controller_batches_workers_retries_invalid_artifacts_and_publishes_ready_days(tmp_path: Path) -> None:
    """The public controller protocol is the only supervisor/worker boundary."""
    controller_path = SCRIPT_DIR / "daily_releases.py"
    assert controller_path.exists(), "daily release controller is not implemented"
    controller_spec = importlib.util.spec_from_file_location("daily_releases", controller_path)
    assert controller_spec
    assert controller_spec.loader
    controller = importlib.util.module_from_spec(controller_spec)
    sys.modules[controller_spec.name] = controller
    controller_spec.loader.exec_module(controller)

    adapters = _Adapters()

    def invoke(*args: str) -> dict[str, object]:
        stdout = io.StringIO()
        controller.main([*args], adapters=adapters, artifact_root=tmp_path, stdout=stdout)
        lines = stdout.getvalue().splitlines()
        assert len(lines) == 1
        return json.loads(lines[0])

    prepared = invoke("prepare", "--dry-run", "--token-limit", "17")
    run = prepared["run"]
    assert prepared == {"run": run, "state": "prepared"}
    manifest = json.loads((tmp_path / "daily-releases" / str(run) / "input.json").read_text(encoding="utf-8"))
    assert manifest["options"] == {"dry_run": True, "token_limit": 17}

    analysis_batch = invoke("advance", "--run", str(run))
    assert analysis_batch["state"] == "awaiting_worker"
    tasks = _tasks(analysis_batch)
    assert [(task["id"], task["model"], task["status"]) for task in tasks] == [
        ("2026-09-26/bucket/001", "codex:luna:low", "pending"),
        ("2026-09-26/bucket/002", "codex:luna:low", "pending"),
        ("2026-09-27/bucket/001", "codex:luna:low", "pending"),
    ]
    records = {
        value["id"]: value
        for path in (tmp_path / "daily-releases" / str(run)).rglob("*.json")
        if isinstance((value := json.loads(path.read_text(encoding="utf-8"))), dict)
        and {"id", "input", "artifact", "status"} <= value.keys()
    }
    assert {task["id"] for task in tasks} <= records.keys()
    assert {records[task["id"]]["status"] for task in tasks} == {"running"}

    for task in tasks:
        artifact = tmp_path / task["artifact"]
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({"id": task["id"], "run": "another-run"}), encoding="utf-8")

    retry_batch = invoke("advance", "--run", str(run))
    retry_tasks = _tasks(retry_batch)
    assert [task["id"] for task in retry_tasks] == [task["id"] for task in tasks]
    assert _transitions(retry_batch) == [
        {"id": task["id"], "from": "running", "to": "failed", "attempt": 1} for task in tasks
    ] + [{"id": task["id"], "from": "failed", "to": "pending", "attempt": 2} for task in tasks]
    assert all(task["attempt"] == 2 and task["status"] == "pending" for task in retry_tasks)

    for contents in (None, "not json"):
        artifact = tmp_path / tasks[0]["artifact"]
        if contents is None:
            artifact.unlink()
        else:
            artifact.write_text(contents, encoding="utf-8")
        retry_batch = invoke("advance", "--run", str(run))
        retried_task = next(task for task in _tasks(retry_batch) if task["id"] == tasks[0]["id"])
        assert {
            "id": tasks[0]["id"],
            "from": "running",
            "to": "failed",
            "attempt": retried_task["attempt"] - 1,
        } in _transitions(retry_batch)
        assert {
            "id": tasks[0]["id"],
            "from": "failed",
            "to": "pending",
            "attempt": retried_task["attempt"],
        } in _transitions(retry_batch)
        artifact.write_text(json.dumps({"id": tasks[0]["id"], "run": run}), encoding="utf-8")

    for task in tasks:
        artifact = tmp_path / task["artifact"]
        artifact.write_text(json.dumps({"id": task["id"], "run": run}), encoding="utf-8")

    synthesis_batch = invoke("advance", "--run", str(run))
    assert synthesis_batch["state"] == "awaiting_worker"
    synthesis_tasks = _tasks(synthesis_batch)
    assert len(synthesis_tasks) == 1
    synthesis = synthesis_tasks[0]
    assert synthesis["id"] == "2026-09-26/synthesis"
    assert synthesis["model"] == "codex:terra:low"
    assert synthesis["status"] == "pending"
    assert set(synthesis) == {"id", "input", "artifact", "model", "status"}
    synthesis_input = json.loads((tmp_path / synthesis["input"]).read_text(encoding="utf-8"))
    assert synthesis_input["bucket_artifacts"] == [
        task["artifact"] for task in tasks if task["id"].startswith("2026-09-26/")
    ]
    artifact = tmp_path / synthesis["artifact"]
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({"id": synthesis["id"], "run": run}), encoding="utf-8")

    first_publish = invoke("publish", "--run", str(run))
    assert first_publish["state"] == "failed"
    assert adapters.publishes == ["2026-09-27"]
    receipts = [
        tmp_path / "daily-releases" / str(run) / day / "publish-receipt.json" for day in ("2026-09-26", "2026-09-27")
    ]
    assert not receipts[0].exists()
    assert json.loads(receipts[1].read_text(encoding="utf-8")) == {
        "run": run,
        "date": "2026-09-27",
        "tag": "v2026.09.27",
        "head_ref": "new-head",
        "status": "published",
    }

    restarted_publish = invoke("publish", "--run", str(run))
    assert restarted_publish["state"] == "published"
    assert adapters.publishes == ["2026-09-27", "2026-09-26"]

    assert json.loads(receipts[0].read_text(encoding="utf-8"))["tag"] == "v2026.09.26"
    resumed_publish = invoke("publish", "--run", str(run))
    assert resumed_publish["state"] == "complete"
    assert adapters.publishes == ["2026-09-27", "2026-09-26"]

    adapters.remote_tags["2026-09-26"] = "wrong-tag"
    republished = invoke("publish", "--run", str(run))
    assert republished["state"] == "published"
    assert adapters.publishes == ["2026-09-27", "2026-09-26", "2026-09-26"]
