"""Discriminating offline contracts for evaluation records and sample isolation.

The subprocess fixture emits host-shaped events; it is not a live model test.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "skill-creator" / "scripts"


@pytest.fixture
def script_loader(monkeypatch):
    """Load actual script files without permanently claiming the scripts namespace."""
    package = types.ModuleType("scripts")
    package.__path__ = [str(SCRIPTS)]
    monkeypatch.setitem(sys.modules, "scripts", package)
    for key in tuple(sys.modules):
        if key.startswith("scripts."):
            monkeypatch.delitem(sys.modules, key)
    loaded = []

    def load(name):
        qualified = f"scripts.{name}"
        if qualified in sys.modules:
            return sys.modules[qualified]
        spec = importlib.util.spec_from_file_location(qualified, SCRIPTS / f"{name}.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, qualified, module)
        spec.loader.exec_module(module)
        loaded.append(qualified)
        return module

    yield load
    # Imports performed by the modules also belong to this temporary namespace.
    for key in tuple(sys.modules):
        if key.startswith("scripts."):
            sys.modules.pop(key, None)


def _emitter(monkeypatch, module, code):
    monkeypatch.setattr(module, "_build_claude_cmd", lambda query, model: [sys.executable, "-c", code])


def test_failed_launch_never_passes_negative_case(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_eval")
    monkeypatch.setattr(module, "_build_claude_cmd", lambda query, model: [str(tmp_path / "absent-executable")])
    result = module.run_eval(
        [{"query": "List nearby stars", "should_trigger": False}], "sql", "Query plans", 1, 1, tmp_path
    )
    case = result["results"][0]
    assert case["pass"] is None
    assert case["valid_runs"] == 0
    assert case["trigger_rate"] is None
    assert case["observations"][0]["status"] == "ERROR"
    assert result["summary"] == {"total": 1, "passed": 0, "failed": 0, "inconclusive": 1}


@pytest.mark.parametrize(
    "code",
    [
        "print('not-json')",
        "print('{}')",
        "import json; print(json.dumps({'type':'result','is_error':True,'subtype':'error_during_execution'}))",
        "import json,sys; print(json.dumps({'type':'result','is_error':False,'subtype':'success'})); sys.exit(7)",
    ],
)
def test_incomplete_or_failed_stream_is_not_negative(script_loader, monkeypatch, tmp_path, code):
    module = script_loader("run_eval")
    _emitter(monkeypatch, module, code)
    with pytest.raises(module.EvaluationError):
        module.run_single_query("scenario", "sql", "Query plans", 2, str(tmp_path))


def test_timeout_is_not_negative(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_eval")
    _emitter(monkeypatch, module, "import time; time.sleep(30)")
    with pytest.raises(module.EvaluationError, match="TIMEOUT"):
        module.run_single_query("scenario", "sql", "Query plans", 0.1, str(tmp_path))


def test_successful_terminal_without_match_is_negative(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_eval")
    _emitter(
        monkeypatch, module, "import json; print(json.dumps({'type':'result','is_error':False,'subtype':'success'}))"
    )
    assert module.run_single_query("scenario", "sql", "Query plans", 2, str(tmp_path)) is False


def test_later_match_and_concurrent_workspace_isolation(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_eval")
    code = """
import json,time
from pathlib import Path
commands = list(Path('.claude/commands').glob('*.md'))
assert len(commands) == 1, commands
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Glob','input':{'pattern':'*'}}]}}), flush=True)
time.sleep(0.05)
assert list(Path('.claude/commands').glob('*.md')) == commands
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Skill','input':{'skill':commands[0].stem}}]}}), flush=True)
"""
    _emitter(monkeypatch, module, code)
    result = module.run_eval(
        [{"query": f"scenario {i}", "should_trigger": True} for i in range(4)], "sql", "Query plans", 4, 3, tmp_path
    )
    assert result["summary"]["passed"] == 4
    assert result["summary"]["inconclusive"] == 0
    assert not (tmp_path / ".claude").exists()


def test_partial_matching_argument_is_not_a_complete_invocation(script_loader):
    module = script_loader("run_eval")
    state = module._TriggerStream("chosen")
    state.feed({
        "type": "stream_event",
        "event": {
            "type": "content_block_start",
            "index": 1,
            "content_block": {"type": "tool_use", "name": "Skill", "input": {}},
        },
    })
    state.feed({
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"skill":"chosen'},
        },
    })
    assert state.triggered is False
    state.feed({
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '"}'},
        },
    })
    state.feed({"type": "stream_event", "event": {"type": "content_block_stop", "index": 1}})
    assert state.triggered is True


@pytest.mark.parametrize(
    ("cases", "message"),
    [
        ([], "nonempty list"),
        ([{"query": "q", "should_trigger": "false"}], "boolean should_trigger"),
        ([{"query": "q", "should_trigger": True}, {"query": "q", "should_trigger": False}], "duplicate query identity"),
    ],
)
def test_invalid_or_duplicate_cases_fail_before_dispatch(script_loader, monkeypatch, tmp_path, cases, message):
    module = script_loader("run_eval")
    monkeypatch.setattr(module, "run_single_query", lambda *args: pytest.fail("invalid cases were dispatched"))
    with pytest.raises(ValueError, match=message):
        module.run_eval(cases, "name", "description", 1, 1, tmp_path)


def _grading(**extra):
    return {"summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0}, **extra}


def _record(module, path, grading):
    return module._build_run_result(1, 1, grading, path / "grading.json", path)


def test_characters_are_not_token_measurements(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    result = _record(module, tmp_path, _grading(execution_metrics={"output_chars": 4096}))
    assert result["tokens"] is None
    assert result["output_chars"] == 4096
    assert result["time_seconds"] is None
    assert module.calculate_stats([None])["mean"] is None


def test_each_metric_resolves_independently_and_zero_survives(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    (tmp_path / "timing.json").write_text(json.dumps({"total_tokens": 0}))
    result = _record(module, tmp_path, _grading(timing={"total_duration_seconds": 4.5}))
    assert result["tokens"] == 0
    assert result["time_seconds"] == pytest.approx(4.5)
    assert result["measurement_sources"]["tokens"] == ["timing.json"]
    (tmp_path / "timing.json").write_text(json.dumps({"total_duration_seconds": 0, "total_tokens": 0}))
    result = _record(module, tmp_path, _grading())
    assert result["time_seconds"] == 0
    assert result["tokens"] == 0
    stats = module.calculate_stats([0, None])
    assert stats["mean"] == 0
    assert stats["observed"] == stats["missing"] == 1


def test_legacy_per_run_metrics_carrier_is_read(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    (tmp_path / "metrics.json").write_text(json.dumps({"total_tokens": 12, "total_duration_seconds": 3}))
    result = _record(module, tmp_path, _grading())
    assert (result["tokens"], result["time_seconds"]) == (12, 3)


@pytest.mark.parametrize("value", [True, -1, "123", float("nan")])
def test_invalid_token_measurements_stay_unavailable(script_loader, tmp_path, value):
    module = script_loader("aggregate_benchmark")
    result = _record(module, tmp_path, _grading(timing={"total_tokens": value}))
    assert result["tokens"] is None
    assert result["measurement_gaps"]


def test_conflicting_measurements_do_not_choose_a_convenient_value(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    (tmp_path / "timing.json").write_text(json.dumps({"total_tokens": 20}))
    result = _record(module, tmp_path, _grading(timing={"total_tokens": 10}))
    assert result["tokens"] is None
    assert "conflicting" in " ".join(result["measurement_gaps"])


def test_observed_repetitions_and_missing_grading_are_reported(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    first = tmp_path / "eval-1" / "with_skill" / "run-1"
    first.mkdir(parents=True)
    (first / "grading.json").write_text(json.dumps(_grading()))
    report = module.generate_benchmark(tmp_path)
    assert report["metadata"]["runs_per_configuration"] == 1
    assert report["metadata"]["grading_status"] == "COMPLETE"
    assert report["run_summary"]["delta"]["tokens"] is None
    second = first.parent / "run-2"
    second.mkdir()
    report = module.generate_benchmark(tmp_path)
    assert report["metadata"]["runs_per_configuration"] == 2
    assert report["metadata"]["grading_status"] == "INCOMPLETE"
    assert len(report["runs"]) == 2
    assert report["runs"][1]["result"]["pass_rate"] is None
    text = module.generate_markdown(report)
    assert "INCOMPLETE" in text
    assert "N/A" in text
    assert "3 runs each" not in text
    json.dumps(report, allow_nan=False)


def test_empty_benchmark_is_not_a_zero_cost_success(script_loader, tmp_path):
    module = script_loader("aggregate_benchmark")
    report = module.generate_benchmark(tmp_path)
    assert report["metadata"]["grading_status"] == "INCOMPLETE"
    assert report["metadata"]["runs_per_configuration"] is None
    assert all(value is None for value in report["run_summary"]["delta"].values())


def test_duplicate_queries_rejected_before_selection_split(script_loader):
    module = script_loader("run_loop")
    with pytest.raises(ValueError, match="duplicate"):
        module.split_eval_set([{"query": "q", "should_trigger": True}] * 2, 0.4)


def test_selection_keeps_training_and_holdout_nonempty(script_loader):
    module = script_loader("run_loop")
    cases = [{"query": f"q{i}", "should_trigger": i < 3} for i in range(6)]
    train, selection = module.split_eval_set(cases, 0.4)
    assert train
    assert selection
    assert {r["query"] for r in train}.isdisjoint(r["query"] for r in selection)
    with pytest.raises(ValueError, match="not enough"):
        module.split_eval_set(cases[:1], 0.4)


def test_inconclusive_iteration_neither_selects_nor_invokes_improver(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_loop")
    (tmp_path / "SKILL.md").write_text("---\nname: example\ndescription: original\n---\nBody\n")

    def fail_eval(*args, **kwargs):
        return {
            "results": [
                {
                    "query": "q",
                    "should_trigger": False,
                    "pass": None,
                    "runs": 1,
                    "valid_runs": 0,
                    "triggers": 0,
                    "errors": 1,
                }
            ],
            "environment": {},
        }

    monkeypatch.setattr(module, "run_eval", fail_eval)
    monkeypatch.setattr(
        module, "_propose_description", lambda **kwargs: pytest.fail("incomplete evidence fed to improver")
    )
    output = module.run_loop(
        [{"query": "q", "should_trigger": False}], tmp_path, None, 1, 1, 3, 1, 0.5, 0, "test-model", False
    )
    assert output["exit_reason"] == "inconclusive_evaluation"
    assert output["best_description"] is None
    assert output["history"][0]["train_inconclusive"] == 1
    assert output["final_generalization_test"] == "NOT_RUN"
    rendered = module.generate_html(output)
    assert "INCONCLUSIVE" in rendered
    assert "No eligible candidate" in rendered


def test_complete_candidate_selection_uses_selection_set_not_final_test(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_loop")
    cases = [{"query": f"q{i}", "should_trigger": False} for i in range(4)]
    (tmp_path / "SKILL.md").write_text("---\nname: example\ndescription: original\n---\nBody\n")

    def complete_eval(eval_set, *args):
        return {"results": [{**case, "pass": True, "runs": 1, "valid_runs": 1, "triggers": 0} for case in eval_set]}

    monkeypatch.setattr(module, "run_eval", complete_eval)
    output = module.run_loop(cases, tmp_path, None, 1, 1, 1, 1, 0.5, 0.4, "test-model", False)
    assert output["best_description"] == "original"
    assert output["best_iteration"] == 1
    assert output["holdout_role"] == "candidate-selection"
    assert output["final_generalization_test"] == "NOT_RUN"


def test_report_does_not_count_errors_as_correct_negatives(script_loader):
    module = script_loader("generate_report")
    case = {"pass": None, "should_trigger": False, "runs": 2, "valid_runs": 0, "triggers": 0, "errors": 2}
    assert module.aggregate_runs([case]) == (0, 0)
    assert "INCONCLUSIVE" in module._result_cell(case)
    assert "2 errors" in module._result_cell(case)
    assert "No eligible candidate" in module.generate_html({"history": []})


def test_benchmark_viewer_renders_unknown_values_without_zero_coercion(script_loader, tmp_path):
    import shutil
    import subprocess

    module = script_loader("aggregate_benchmark")
    directory = tmp_path / "eval-1" / "with_skill" / "run-1"
    directory.mkdir(parents=True)
    report = module.generate_benchmark(tmp_path)
    viewer = SCRIPTS.parent / "eval-viewer" / "viewer.html"
    text = viewer.read_text(encoding="utf-8")
    renderer = text.split("// ---- Benchmark rendering ----", 1)[1].split("// ---- Start ----", 1)[0]
    node = shutil.which("node")
    assert node is not None, "Node.js is required to execute the bundled benchmark renderer contract"
    # Renderer unit boundary: DOM sink is a test double, not a browser smoke test.
    script = (
        "const EMBEDDED_DATA = "
        + json.dumps({"benchmark": report})
        + ";\n"
        + "const sink = {style:{},innerHTML:''}; const document = {getElementById:()=>sink};\n"
        + "const escapeHtml = value => String(value).replaceAll('<','&lt;');\n"
        + renderer
        + "\nrenderBenchmark(); console.log(sink.innerHTML);\n"
    )
    execution = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=10, check=True)
    assert "INCOMPLETE" in execution.stdout
    assert "N/A" in execution.stdout
    assert "0% (0/0)" not in execution.stdout
    assert "1 observed run(s)" in execution.stdout


def test_success_result_cannot_hide_unfinished_tool_arguments(script_loader):
    module = script_loader("run_eval")
    state = module._TriggerStream("chosen")
    state.feed({
        "type": "stream_event",
        "event": {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "tool_use", "name": "Skill", "input": {}},
        },
    })
    with pytest.raises(module.EvaluationError, match="unfinished"):
        state.feed({"type": "result", "is_error": False, "subtype": "success"})


def test_partial_sample_population_cannot_pass(script_loader, monkeypatch, tmp_path):
    module = script_loader("run_eval")
    returns = iter([False, module.EvaluationError("provider unavailable")])

    def sample(*args):
        result = next(returns)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(module, "run_single_query", sample)
    output = module.run_eval([{"query": "q", "should_trigger": False}], "name", "description", 1, 1, tmp_path, 2)
    assert output["results"][0]["valid_runs"] == 1
    assert output["results"][0]["trigger_rate"] == 0
    assert output["results"][0]["pass"] is None


def test_direct_improvement_rejects_missing_evidence_before_provider_call(script_loader, monkeypatch):
    sdk = types.ModuleType("anthropic")
    sdk_types = types.ModuleType("anthropic.types")
    vars(sdk_types).update(TextBlock=type("TextBlock", (), {}), ThinkingBlock=type("ThinkingBlock", (), {}))
    monkeypatch.setitem(sys.modules, "anthropic", sdk)
    monkeypatch.setitem(sys.modules, "anthropic.types", sdk_types)
    module = script_loader("improve_description")
    incomplete = {"results": [{"pass": None, "errors": 1}], "summary": {"passed": 0, "total": 1}}
    with pytest.raises(ValueError, match="complete behavioral"):
        module._build_prompt("name", "body", "description", incomplete, [], None)
