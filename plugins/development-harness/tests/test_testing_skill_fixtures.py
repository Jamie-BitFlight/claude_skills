"""Check executable evaluation fixtures, not the reviewing agent's effectiveness."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "skills" / "test-reviewer" / "evals" / "fixtures" / "review_project"
)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("original", "replacement", "expected_failures"),
    [
        (None, None, set()),
        ("return net_cents + net_cents * tax_percent // 100", "return net_cents", set()),
        (
            '    if not allowed:\n        raise PermissionError("Publication denied")\n    events.append("write")',
            '    events.append("write")\n    if not allowed:\n        raise PermissionError("Publication denied")',
            {"test_denied_publication"},
        ),
        (
            'return int(json.loads(wire)["quantity"])',
            'return int(json.loads(wire).get("units", -1))',
            {"test_quantity_consumption"},
        ),
        (
            "return net_cents + net_cents * tax_percent // 100",
            "tax_cents = (net_cents * tax_percent) // 100\n    return tax_cents + net_cents",
            set(),
        ),
    ],
    ids=["baseline", "tax-omitted", "denied-write", "consumer-field", "equivalent-refactor"],
)
def test_fixture_failure_mechanisms(
    tmp_path: Path, original: str | None, replacement: str | None, expected_failures: set[str]
) -> None:
    """Reach the intended assertion in each isolated control without changing the original."""
    preserved = {path.name: path.read_bytes() for path in FIXTURE_ROOT.iterdir() if path.is_file()}
    project = tmp_path / "review_project"
    shutil.copytree(FIXTURE_ROOT, project)
    if original is not None:
        assert replacement is not None
        source = project / "app.py"
        text = source.read_text(encoding="utf-8")
        assert text.count(original) == 1
        source.write_text(text.replace(original, replacement), encoding="utf-8")

    report = tmp_path / "results.xml"
    env = dict(os.environ)
    # The fixture explicitly uses only built-in pytest facilities. Keep the outer
    # repository's configured plugins/gates unchanged and isolate nested discovery.
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-c", "pytest.ini", "test_app.py", f"--junitxml={report}"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    output = result.stdout + result.stderr
    assert report.is_file(), output
    cases = ET.parse(report).findall(".//testcase")
    assert {case.attrib["name"] for case in cases} == {
        "test_total",
        "test_approved_publication",
        "test_denied_publication",
        "test_quantity_encoding",
        "test_quantity_consumption",
    }, output
    assert not [case for case in cases if case.find("error") is not None], output
    assert not [case for case in cases if case.find("skipped") is not None], output
    failures = {case.attrib["name"] for case in cases if case.find("failure") is not None}
    assert failures == expected_failures, output
    for case in cases:
        failure = case.find("failure")
        if failure is not None:
            assert "assert " in failure.attrib.get("message", ""), output
    assert result.returncode == (1 if expected_failures else 0), output
    assert {path.name: path.read_bytes() for path in FIXTURE_ROOT.iterdir() if path.is_file()} == preserved
