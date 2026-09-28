#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["daily-releases-lib"]
#
# [tool.uv.sources]
# daily-releases-lib = { path = "daily_releases_lib", editable = true }
#
# [tool.ty.environment]
# extra-paths = ["./daily_releases_lib"]
# ///
"""JSON-only control plane for the daily-releases skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO, cast

from daily_releases_lib.github_utils import get_github_repo, make_github_client
from github import GithubException

SKILL_ROOT = Path(__file__).resolve().parent.parent


NOT_FOUND = 404


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


class LiveAdapters:
    """Invoke the skill's existing command-line workers."""

    def _run(self, *args: str) -> None:
        subprocess.run([sys.executable, *args], check=True, stdout=sys.stderr)

    def discover(self, **options: object) -> list[dict[str, str]]:
        """Discover release days.

        Returns:
            The discovered day records.
        """
        command = [str(SKILL_ROOT / "scripts/list_daily_ranges.py")]
        for name in ("start_date", "end_date", "branch", "repo"):
            if value := options.get(name):
                command.extend([f"--{name.replace('_', '-')}", str(value)])
        result = subprocess.run([sys.executable, *command], check=True, text=True, capture_output=True)
        return json.loads(result.stdout)

    def collect(self, *, base_ref: str, head_ref: str, day_dir: str, repo: str | None = None, **_: object) -> None:
        """Collect a day's source data."""
        command = [str(SKILL_ROOT / "scripts/collect_day_dataset.py"), base_ref, head_ref, day_dir]
        if repo:
            command.extend(["-R", repo])
        self._run(*command)

    def bucket(self, *, day_dir: str, token_limit: object = None, **_: object) -> list[str]:
        """Split collected data into worker buckets.

        Returns:
            The bucket identifiers.
        """
        command = [str(SKILL_ROOT / "scripts/bucket_day_data.py"), day_dir]
        if isinstance(token_limit, int):
            command.extend(["--token-limit", str(token_limit)])
        self._run(*command)
        return [path.name.removeprefix("bucket_") for path in sorted((Path(day_dir) / "buckets").glob("bucket_*"))]

    def render(self, *, analysis: str, output: str, **_: object) -> None:
        """Render final analysis as release notes."""
        self._run(str(SKILL_ROOT / "scripts/format_release_notes.py"), analysis, "--output", output)

    def publish(
        self,
        *,
        date: str,
        tag: str,
        head_ref: str,
        notes: str,
        repo: str | None = None,
        dry_run: object = False,
        **_: object,
    ) -> None:
        """Publish one completed release."""
        command = [
            str(SKILL_ROOT / "scripts/publish_daily_release.py"),
            "--date",
            date,
            "--tag",
            tag,
            "--head-ref",
            head_ref,
            "--notes-file",
            notes,
        ]
        if repo:
            command.extend(["-R", repo])
        if dry_run:
            command.append("--dry-run")
        self._run(*command)

    def release_identity(
        self, *, tag: str, head_ref: str, repo: str | None = None, **_: object
    ) -> dict[str, str] | None:
        """Return the remote release identity when it exists."""
        token = os.environ.get("GITHUB_TOKEN")
        slug = repo or os.environ.get("DEFAULT_REPO") or os.environ.get("GITHUB_REPOSITORY")
        if not token or not slug:
            return None
        gh_repo = get_github_repo(make_github_client(token), slug)
        try:
            release = gh_repo.get_release(tag)
            actual_head = gh_repo.get_git_ref(f"tags/{tag}").object.sha
        except GithubException as error:
            if error.status == NOT_FOUND:
                return None
            raise
        return {"tag": release.tag_name, "head_ref": actual_head}


class Controller:
    """Persist and advance daily-release supervisor state."""

    def __init__(self, adapters: LiveAdapters, artifact_root: Path) -> None:
        """Create a controller with its worker adapters and artifact root."""
        self.adapters, self.root = adapters, artifact_root

    def _run_dir(self, run: str) -> Path:
        return self.root / "daily-releases" / run

    def _input(self, run: str) -> dict[str, object]:
        value = _read_json(self._run_dir(run) / "input.json")
        if value is None:
            raise ValueError(f"unknown run: {run}")
        return value

    def _task(self, run: str, day: dict[str, str], kind: str, bucket: str | None = None) -> dict[str, str]:
        suffix = f"/{bucket}" if bucket else ""
        artifact = f"daily-releases/{run}/{day['date']}/artifacts/{kind}{('-' + bucket) if bucket else ''}.json"
        content = (
            f"daily-releases/{run}/{day['date']}/buckets/bucket_{bucket}/content.txt"
            if bucket
            else f"daily-releases/{run}/{day['date']}/synthesis-input.json"
        )
        return {
            "id": f"{day['date']}/{kind}{suffix}",
            "input": content,
            "artifact": artifact,
            "model": "codex:luna:low" if kind == "bucket" else "codex:terra:low",
            "status": "pending",
        }

    def _record(self, run: str, task: dict[str, str], status: str, attempt: int) -> None:
        path = self._run_dir(run) / task["id"].split("/")[0] / "tasks" / (task["id"].replace("/", "-") + ".json")
        _write_json(
            path, {key: task[key] for key in ("id", "input", "artifact")} | {"status": status, "attempt": attempt}
        )

    def _record_path(self, run: str, task: dict[str, str]) -> Path:
        return self._run_dir(run) / task["id"].split("/")[0] / "tasks" / (task["id"].replace("/", "-") + ".json")

    def _valid(self, run: str, task: dict[str, str]) -> bool:
        value = _read_json(self.root / task["artifact"])
        return value is not None and value.get("id") == task["id"] and value.get("run") == run

    def _queue(self, run: str, task: dict[str, str]) -> tuple[dict[str, object], list[dict[str, object]]] | None:
        record = _read_json(self._record_path(run, task))
        attempt = int(cast("int | str", record.get("attempt", 1))) if record else 1
        if self._valid(run, task):
            self._record(run, task, "succeeded", attempt)
            return None
        transitions: list[dict[str, object]] = []
        if record:
            transitions.append({"id": task["id"], "from": record["status"], "to": "failed", "attempt": attempt})
            self._record(run, task, "failed", attempt)
            attempt += 1
            transitions.append({"id": task["id"], "from": "failed", "to": "pending", "attempt": attempt})
        self._record(run, task, "running", attempt)
        queued: dict[str, object] = {**task, "status": "pending"}
        if record:
            queued["attempt"] = attempt
        return queued, transitions

    def prepare(self, options: dict[str, object]) -> dict[str, object]:
        """Create persisted input state for a new run.

        Returns:
            The prepared run state.
        """
        days = self.adapters.discover(**options)
        run = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        run_dir = self._run_dir(run)
        _write_json(run_dir / "input.json", {"run": run, "days": days, "options": options})
        for day in days:
            _write_json(run_dir / day["date"] / "input.json", day)
        return {"run": run, "state": "prepared"}

    def advance(self, run: str) -> dict[str, object]:
        """Collect inputs and return the next worker batch.

        Returns:
            The next control-plane state.
        """
        manifest = self._input(run)
        days = cast("list[dict[str, str]]", manifest["days"])
        options = cast("dict[str, object]", manifest["options"])
        bucket_tasks: list[dict[str, object]] = []
        synthesis: list[dict[str, object]] = []
        transitions: list[dict[str, object]] = []
        for day in days:
            day_dir = self._run_dir(run) / day["date"]
            if not (day_dir / "buckets").exists():
                self.adapters.collect(**day, day_dir=str(day_dir), **options)
                buckets = self.adapters.bucket(**day, day_dir=str(day_dir), **options)
                _write_json(day_dir / "buckets.json", {"buckets": buckets})
            else:
                buckets = cast("list[str]", (_read_json(day_dir / "buckets.json") or {"buckets": []})["buckets"])
            tasks = [self._task(run, day, "bucket", bucket) for bucket in buckets]
            for task in tasks:
                queued = self._queue(run, task)
                if queued:
                    worker, changes = queued
                    bucket_tasks.append(worker)
                    transitions.extend(changes)
            if len(tasks) > 1 and all(self._valid(run, task) for task in tasks):
                task = self._task(run, day, "synthesis")
                _write_json(
                    day_dir / "synthesis-input.json",
                    {"run": run, "date": day["date"], "bucket_artifacts": [task["artifact"] for task in tasks]},
                )
                queued = self._queue(run, task)
                if queued:
                    worker, changes = queued
                    synthesis.append(worker)
                    transitions.extend(changes)
        tasks = bucket_tasks or synthesis
        if tasks:
            result: dict[str, object] = {
                "run": run,
                "state": "awaiting_worker",
                "tasks": tasks,
                "concurrency": max(1, (os.cpu_count() or 1) - 1),
            }
            if transitions:
                result["transitions"] = sorted(
                    transitions, key=lambda transition: (transition["to"] != "failed", transition["id"])
                )
            return result
        return {"run": run, "state": "ready_to_publish"}

    def _run_finalizer(self, day_dir: Path) -> None:
        subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts/finalize_day_analysis.py"), str(day_dir)],
            check=True,
            stdout=sys.stderr,
        )

    def _ensure_description(self, run: str, day: dict[str, str]) -> Path | None:
        day_dir = self._run_dir(run) / day["date"]
        buckets = cast("list[str]", (_read_json(day_dir / "buckets.json") or {"buckets": []})["buckets"])
        tasks = [self._task(run, day, "bucket", bucket) for bucket in buckets]
        if len(tasks) == 1 and self._valid(run, tasks[0]):
            source, target = self.root / tasks[0]["artifact"], day_dir / "summaries" / f"bucket_{buckets[0]}.json"
        elif len(tasks) > 1 and self._valid(run, self._task(run, day, "synthesis")):
            source, target = self.root / self._task(run, day, "synthesis")["artifact"], day_dir / "analysis.json"
        else:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        self._run_finalizer(day_dir)
        description = day_dir / "artifacts" / "description.md"
        if not description.exists():
            self.adapters.render(**day, analysis=str(day_dir / "analysis.json"), output=str(description))
        return description

    def _receipt_matches(self, saved: dict[str, object] | None, run: str, day: dict[str, str]) -> bool:
        if not saved or any(
            saved.get(key) != value
            for key, value in (("run", run), ("date", day["date"]), ("tag", day["tag"]), ("head_ref", day["head_ref"]))
        ):
            return False
        expected = {"tag": day["tag"], "head_ref": day["head_ref"]}
        if hasattr(self.adapters, "release_identity"):
            return self.adapters.release_identity(**day) == expected
        return bool(getattr(self.adapters, "release_exists", lambda **_: False)(**day))

    def _publish_day(self, run: str, day: dict[str, str], options: dict[str, object]) -> dict[str, str]:
        day_dir = self._run_dir(run) / day["date"]
        receipt = day_dir / "publish-receipt.json"
        if self._receipt_matches(_read_json(receipt), run, day):
            return {"date": day["date"], "status": "verified"}
        notes = self._ensure_description(run, day)
        if notes is None:
            result = {"date": day["date"], "status": "waiting_for_analysis"}
        else:
            try:
                self.adapters.publish(**day, notes=str(notes), **options)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                result = {"date": day["date"], "status": "failed", "error": str(error)}
            else:
                identity = {"tag": day["tag"], "head_ref": day["head_ref"]}
                _write_json(receipt, {"run": run, "date": day["date"], **identity, "status": "published"})
                result = {"date": day["date"], "status": "published"}
        _write_json(day_dir / "publish-status.json", {"run": run, **result})
        return result

    def publish(self, run: str) -> dict[str, object]:
        """Publish each run day whose analysis is ready.

        Returns:
            The post-publication state.
        """
        manifest = self._input(run)
        days = cast("list[dict[str, str]]", manifest["days"])
        options = cast("dict[str, object]", manifest["options"])
        with ThreadPoolExecutor(max_workers=max(1, (os.cpu_count() or 1) - 1)) as pool:
            results = list(pool.map(lambda day: self._publish_day(run, day, options), days))
        statuses = {result["status"] for result in results}
        state = (
            "failed"
            if "failed" in statuses
            else "waiting_for_analysis"
            if "waiting_for_analysis" in statuses
            else "published"
            if "published" in statuses
            else "complete"
        )
        return {"run": run, "state": state, "tasks": results}


def main(
    argv: list[str] | None = None,
    *,
    adapters: LiveAdapters | None = None,
    artifact_root: Path | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Run the JSON-only daily-release control-plane CLI."""
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command", required=True)
    prepare = command.add_parser("prepare")
    for flag in ("start-date", "end-date", "branch", "repo"):
        prepare.add_argument(f"--{flag}")
    prepare.add_argument("--dry-run", action="store_true")
    prepare.add_argument("--token-limit", type=int)
    for name in ("advance", "publish"):
        command.add_parser(name).add_argument("--run", required=True)
    args = vars(parser.parse_args(argv))
    controller = Controller(adapters or LiveAdapters(), artifact_root or Path.cwd())
    if args["command"] == "prepare":
        options = {
            key: value
            for key, value in args.items()
            if key != "command" and value is not None and (key != "dry_run" or value)
        }
        result = controller.prepare(options)
    elif args["command"] == "advance":
        result = controller.advance(args["run"])
    else:
        result = controller.publish(args["run"])
    print(json.dumps(result, separators=(",", ":")), file=stdout or sys.stdout)


if __name__ == "__main__":
    main()
