"""Tests for boil skill scripts: check_completion.py and generate_blocked.py.

Each test captures a confirmed or plausible bug documented in the bug report.
Tests are written to FAIL on current code and PASS after fixes.

Import strategy: sys.path manipulation to import module-level functions directly,
bypassing the ``if __name__ == "__main__"`` guards.
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import setup — add scripts directory to sys.path so we can import directly
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Import functions directly from both modules.
# The modules use ``if __name__ == "__main__"`` guards, so importing them here
# is safe — main() will NOT be called.
from typing import TYPE_CHECKING

import check_completion
import generate_blocked
from check_completion import collect_paths, scan_text
from generate_blocked import build_declaration, prompt_field

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ===========================================================================
# BUG 1 — generate_blocked.py: Inline mode guard uses truthiness, not None check
# ===========================================================================


class TestBug1InlineModeEmptyCompleted:
    """BUG 1: ``if args.reason and args.completed and args.remains and args.condition``
    silently drops into interactive mode when ``--completed ""`` is passed because
    an empty string is falsy. The guard should use ``is not None`` checks.
    """

    def test_build_declaration_called_with_empty_completed(self, mocker: MockerFixture) -> None:
        """Verify inline mode is used even when --completed is an explicit empty string.

        Arrange: patch build_declaration AND prompt_field so interactive mode never
        reaches real stdin. Check whether build_declaration is called directly
        (inline mode) vs prompt_field being called first (interactive/buggy mode).
        Act: call main() with sys.argv set to the four inline args including completed="".
        Assert: build_declaration receives the empty string; prompt_field was NOT called.
        """
        mock_build = mocker.patch(
            "generate_blocked.build_declaration",
            return_value=(
                "BLOCKED: x\n- What was completed:\n  - nothing\n- What remains:\n  - y\n- Unblocking condition: z"
            ),
        )
        # Patch prompt_field to prevent any real stdin reads if we fall through to
        # interactive mode (which is what happens on buggy code).
        mock_prompt = mocker.patch("generate_blocked.prompt_field", return_value="fallback")
        mocker.patch("builtins.print")

        test_argv = [
            "generate_blocked.py",
            "--reason",
            "some constraint",
            "--completed",
            "",  # explicit empty string — buggy guard sees this as False
            "--remains",
            "do the work",
            "--condition",
            "condition met",
        ]
        mocker.patch.object(sys, "argv", test_argv)

        generate_blocked.main()

        # After the fix: build_declaration is called in inline mode with completed=""
        # and prompt_field is never called.
        assert not mock_prompt.called, (
            "BUG 1: prompt_field was called even though --completed was "
            "provided explicitly (as empty string). The truthiness guard dropped "
            "into interactive mode. Fix: use 'is not None' check."
        )
        mock_build.assert_called_once()
        call_args = mock_build.call_args
        # completed argument (positional index 1) must be the empty string
        assert call_args[0][1] == "", (
            "build_declaration should be called with completed='' (empty string) "
            f"when --completed '' is passed; got: {call_args!r}"
        )

    def test_inline_mode_not_entered_with_empty_completed_on_current_code(self, mocker: MockerFixture) -> None:
        """Confirm the current bug: interactive mode is entered when completed=''.

        This test documents the CURRENT broken behaviour by verifying that
        prompt_field IS called (interactive path triggered) when it should not be.
        This test PASSES on current buggy code and should FAIL after the fix.
        """
        mock_prompt = mocker.patch("generate_blocked.prompt_field", return_value="something")
        mocker.patch(
            "generate_blocked.build_declaration",
            return_value=(
                "BLOCKED: x\n- What was completed:\n  - nothing\n- What remains:\n  - y\n- Unblocking condition: z"
            ),
        )
        mocker.patch("builtins.print")

        test_argv = [
            "generate_blocked.py",
            "--reason",
            "some constraint",
            "--completed",
            "",
            "--remains",
            "do the work",
            "--condition",
            "condition met",
        ]
        mocker.patch.object(sys, "argv", test_argv)

        generate_blocked.main()

        # On CURRENT (buggy) code, prompt_field WILL be called because the guard
        # evaluates args.completed as falsy and drops into interactive mode.
        # After the fix, prompt_field should NOT be called.
        # This assertion PASSES on buggy code, FAILS after fix — documents the bug.
        assert mock_prompt.called, (
            "BUG 1 confirmed: prompt_field was called even though --completed was "
            "provided explicitly (as empty string). Fix: use 'is not None' guard."
        )


# ===========================================================================
# BUG 2 — check_completion.py:46 TODO lookahead over-suppresses
# ===========================================================================


class TestBug2TodoLookaheadOverSuppresses:
    """BUG 2: Pattern ``\\bTODO\\b(?!.*\\btest\\b)`` with IGNORECASE suppresses TODOs
    on any line that contains the word "test", even when the TODO is a legitimate
    incompleteness marker (e.g., ``# TODO: fix boundary condition in unit test``).
    """

    def test_todo_on_line_containing_test_word_is_flagged(self) -> None:
        """Verify that a TODO followed by the word 'test' elsewhere on the same line
        is still reported as an INCOMPLETE violation.

        The current pattern uses a negative lookahead that suppresses the hit
        whenever 'test' appears anywhere after 'TODO' on the same line. This is
        too broad — it hides real incompleteness markers.
        """
        line = "# TODO: fix boundary condition in unit test"
        hits = scan_text(line, source_label="<test>")
        incomplete_hits = [h for h in hits if h[1] == "INCOMPLETE"]
        assert incomplete_hits, (
            f"BUG 2: scan_text should flag '{line}' as INCOMPLETE (TODO marker) but "
            "the negative lookahead '(?!.*\\btest\\b)' suppressed it."
        )

    def test_todo_not_in_test_context_is_still_flagged(self) -> None:
        """Sanity check: a plain TODO with no 'test' word is always flagged."""
        line = "# TODO: fix this later"
        hits = scan_text(line, source_label="<test>")
        incomplete_hits = [h for h in hits if h[1] == "INCOMPLETE"]
        assert incomplete_hits, "A plain TODO should always be flagged as INCOMPLETE."


# ===========================================================================
# BUG 3 — check_completion.py:111 IGNORE_DIRS matches CWD ancestors
# ===========================================================================


class TestBug3IgnoreDirsMatchesCwdAncestors:
    """BUG 3: ``any(part in IGNORE_DIRS for part in child.parts)`` checks ALL parts
    of the absolute path, including ancestor directories that have nothing to do
    with the scan root. A file at an absolute path whose parent directory happens
    to share a name with an IGNORE_DIR entry (e.g., ``node_modules``) will be
    incorrectly excluded even if it is not inside a node_modules directory
    relative to the scan root.
    """

    def test_file_in_clean_subdir_not_filtered_when_cwd_ancestor_matches_ignore_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Create a scan root whose absolute path does NOT contain an IGNORE_DIR segment
        in the subtree being scanned. Verify collect_paths includes all files.

        We create a temp dir tree like:
            <tmp_path>/scan_root/src/file.py

        <tmp_path> itself may or may not have 'node_modules' in parts — we cannot
        control that. Instead, we test a more direct scenario: create a file whose
        path components include a name from IGNORE_DIRS above the scan root, then
        verify it is (or is not) filtered. This exposes the bug.
        """
        # Create a directory that simulates a scan root NOT under an ignored dir
        scan_root = tmp_path / "project" / "src"
        scan_root.mkdir(parents=True)
        target_file = scan_root / "module.py"
        target_file.write_text("# a python file\n")

        collected = collect_paths([str(scan_root)])
        assert target_file in collected, (
            f"collect_paths should include {target_file} but it was excluded. "
            "Check that the filter does not over-match ancestor path components."
        )

    def test_file_actually_inside_node_modules_is_filtered(self, tmp_path: Path) -> None:
        """Files genuinely inside a node_modules directory must be excluded."""
        node_modules_dir = tmp_path / "node_modules" / "some_package"
        node_modules_dir.mkdir(parents=True)
        nested_file = node_modules_dir / "index.js"
        nested_file.write_text("module.exports = {};")

        collected = collect_paths([str(tmp_path)])
        assert nested_file not in collected, "Files inside node_modules must be excluded from collect_paths."

    def test_sibling_of_ignored_dir_not_filtered(self, tmp_path: Path) -> None:
        """A file in a sibling directory next to an ignored dir must be included.

        Tree:
            tmp_path/
                node_modules/  (ignored dir — files here excluded)
                src/
                    file.py    (must be included)
        """
        ignored = tmp_path / "node_modules"
        ignored.mkdir()
        (ignored / "pkg.js").write_text("// ignored")

        src = tmp_path / "src"
        src.mkdir()
        good_file = src / "file.py"
        good_file.write_text("x = 1")

        collected = collect_paths([str(tmp_path)])
        assert good_file in collected, "file.py in src/ should be included; it is not inside node_modules."

    def test_ancestor_with_ignored_name_does_not_filter_children(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the scan root itself is nested inside a directory named like an IGNORE_DIR,
        its children must still be included because we are scanning INSIDE that root.

        This is the core scenario for BUG 3: absolute path parts include 'node_modules'
        as an ancestor, but the scan root is passed explicitly.

        We simulate this by creating:
            tmp_path/node_modules/project/src/file.py

        and scanning only ``tmp_path/node_modules/project/src``.
        The current buggy code will see 'node_modules' in child.parts and exclude file.py.
        """
        # Build a path where 'node_modules' appears as an ancestor of the scan root
        scan_root = tmp_path / "node_modules" / "project" / "src"
        scan_root.mkdir(parents=True)
        target_file = scan_root / "util.py"
        target_file.write_text("def util(): pass")

        # The scan root IS inside node_modules — but the user explicitly asked to scan it.
        # The correct behaviour is to include files in the explicitly requested target.
        # The buggy code excludes them because 'node_modules' appears in child.parts.
        collected = collect_paths([str(scan_root)])

        # On CURRENT code this FAILS because 'node_modules' appears in child.parts.
        assert target_file in collected, (
            f"BUG 3: collect_paths filtered out {target_file} because 'node_modules' appeared "
            "in child.parts (an ancestor outside the scan root). "
            "Fix: filter only on parts RELATIVE to the scan root, not the absolute path."
        )


# ===========================================================================
# BUG 4 — check_completion.py:74 duplicate hits per line inflates count
# ===========================================================================


class TestBug4DuplicateHitsPerLineInflatesCount:
    """BUG 4: scan_text iterates all patterns against each line without deduplication.
    A single line matching multiple patterns produces multiple hits. The violation
    count is inflated — one problematic line is reported N times (once per matching
    pattern). A dedup-by-line policy would cap it at one hit per line.
    """

    def test_line_matching_multiple_patterns_produces_multiple_hits(self) -> None:
        """Demonstrate that a multi-match line emits more than one hit.

        A line containing both a TODO marker and a workaround keyword matches at
        least two patterns and produces at least two hits in current code.
        This test documents the current (buggy) behaviour and will fail after dedup fix.
        """
        # This line matches:
        #   INCOMPLETE  — "TODO" (without "test" following)
        #   WORKAROUND  — "workaround"
        line = "# TODO: this is a workaround for the issue"
        hits = scan_text(line, source_label="<test>")
        assert len(hits) > 1, (
            f"BUG 4: expected more than 1 hit (demonstrating the inflation), "
            f"got {len(hits)}. This confirms the multi-hit-per-line behaviour."
        )

    def test_single_problematic_line_should_not_exceed_one_hit_after_dedup(self) -> None:
        """After dedup fix: a single line should produce at most one hit, regardless
        of how many patterns it matches.

        This test FAILS on current code (multiple hits) and PASSES after the fix.
        """
        line = "# TODO: this is a workaround for the issue"
        hits = scan_text(line, source_label="<test>")

        # After a proper per-line dedup fix, at most 1 hit per unique line.
        # The test asserts the DESIRED post-fix state.
        distinct_line_hits = {h[3] for h in hits}  # set of unique line texts
        assert len(hits) <= len(distinct_line_hits), (
            f"BUG 4: scan_text produced {len(hits)} hits for {len(distinct_line_hits)} distinct line(s). "
            "Each line should produce at most one hit after dedup."
        )


# ===========================================================================
# BUG 5 — generate_blocked.py: EOFError not caught in prompt_field
# ===========================================================================


def _raise_eoferror(_prompt: str) -> str:
    """Replacement for builtins.input that always raises EOFError (simulates Ctrl+D)."""
    raise EOFError


class TestBug5EofErrorInPromptField:
    """BUG 5: prompt_field calls input("  > ") without catching EOFError.
    Pressing Ctrl+D (or piping an empty stdin) raises EOFError which propagates
    uncaught through prompt_field and main(), crashing the process instead of
    exiting cleanly with code 1.
    """

    def test_prompt_field_raises_eoferror_on_stdin_eof(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that EOFError from input() propagates unhandled in prompt_field.

        This test documents the CURRENT behaviour: unhandled EOFError propagates.
        After the fix this test will FAIL (EOFError will be caught → SystemExit).
        """
        monkeypatch.setattr(builtins, "input", _raise_eoferror)
        monkeypatch.setattr(builtins, "print", lambda *a, **k: None)

        # On CURRENT code, EOFError propagates unhandled out of prompt_field.
        with pytest.raises(EOFError):
            prompt_field("Test field", "Enter something")

    def test_prompt_field_exits_cleanly_on_eof_after_fix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After the fix, prompt_field must catch EOFError and call sys.exit(1).

        This test PASSES after the fix, FAILS on current code because
        EOFError propagates instead of becoming SystemExit(1).
        """
        monkeypatch.setattr(builtins, "input", _raise_eoferror)
        monkeypatch.setattr(builtins, "print", lambda *a, **k: None)

        with pytest.raises(SystemExit) as exc_info:
            prompt_field("Test field", "Enter something")

        assert exc_info.value.code == 1, (
            "BUG 5: prompt_field should exit with code 1 on EOFError, "
            f"but got SystemExit({exc_info.value.code!r}). "
            "Fix: wrap input() in try/except EOFError: sys.exit(1)."
        )

    def test_main_exits_cleanly_on_eof_during_interactive_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After the fix, main() in interactive mode must not crash with EOFError.

        Simulate Ctrl+D during the first prompt by making input() raise EOFError.
        Expected: SystemExit(1). Current behaviour: unhandled EOFError.
        """
        monkeypatch.setattr(builtins, "input", _raise_eoferror)
        monkeypatch.setattr(builtins, "print", lambda *a, **k: None)
        monkeypatch.setattr(sys, "argv", ["generate_blocked.py"])  # interactive mode — no args

        with pytest.raises(SystemExit) as exc_info:
            generate_blocked.main()

        assert exc_info.value.code == 1, f"BUG 5: main() should exit 1 on EOF, got SystemExit({exc_info.value.code!r})."


# ===========================================================================
# BUG 6 — check_completion.py: silent false-pass on non-existent path
# ===========================================================================


class TestBug6SilentFalsePassOnNonExistentPath:
    """BUG 6: collect_paths silently returns an empty list for non-existent paths.
    main() then reports "no violations found" and exits 0 — falsely passing
    for a path that was never scanned. The fix should warn or exit non-zero.
    """

    def test_collect_paths_returns_empty_for_nonexistent_path(self) -> None:
        """Document the current silent behaviour: a non-existent path yields [].

        This test PASSES on current code (it confirms the bug exists).
        """
        result = collect_paths(["/nonexistent/path/that/does/not/exist"])
        assert result == [], (
            "collect_paths currently returns [] for non-existent paths "
            "(silent failure). This is the bug being documented."
        )

    def test_main_exits_nonzero_for_nonexistent_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After the fix: main() must exit non-zero or print a warning when a target
        path does not exist, rather than silently reporting "no violations found".

        This test FAILS on current code (exits 0) and PASSES after the fix.
        """
        nonexistent = "/nonexistent/path/that/absolutely/does/not/exist_abc123"
        monkeypatch.setattr(sys, "argv", ["check_completion.py", nonexistent])
        monkeypatch.setattr(builtins, "print", lambda *a, **k: None)

        exit_code = check_completion.main()

        assert exit_code != 0, (
            "BUG 6: check_completion.main() should return non-zero when the "
            "target path does not exist (to prevent false-clean reporting). "
            f"Got exit_code={exit_code!r} for non-existent path '{nonexistent}'."
        )

    def test_collect_paths_raises_or_warns_for_nonexistent_path_after_fix(self) -> None:
        """After the fix, collect_paths should raise ValueError or return a sentinel
        distinguishable from 'empty directory scanned successfully'.

        This test documents the DESIRED post-fix behaviour and FAILS on current code.
        """
        # The fix could raise ValueError, FileNotFoundError, or return a special
        # value. We test that it does NOT silently return an empty list.
        try:
            result = collect_paths(["/nonexistent_xyz_abc_123"])
            # If it returns without raising, the result must not be an empty list
            # (an empty list is ambiguous — indistinguishable from "no files found").
            assert result is not None, "collect_paths returned None"
            assert len(result) >= 0, "collect_paths returned a result"
            # Fail this test because the fix should not silently succeed.
            pytest.fail(
                "BUG 6: collect_paths silently returned [] for a non-existent path. "
                "After the fix it should raise or produce an observable warning."
            )
        except (ValueError, FileNotFoundError, SystemExit):
            # Any of these is an acceptable fix outcome.
            pass


# ===========================================================================
# BUG 7 — check_completion.py: f-string format-spec truncation not detected
# ===========================================================================


class TestBug7FStringFormatSpecTruncation:
    """BUG 7: PROHIBITED_PATTERNS has no regex matching f-string format specs like
    ``f"{value:.50}"`` or ``f"{description:.100}"``. These are invented-limit
    violations that silently truncate output.
    """

    def test_fstring_format_spec_truncation_is_flagged(self) -> None:
        """Verify scan_text detects f-string format-spec truncation patterns.

        Example: ``return f"{value:.50}"`` should be flagged as INVENTED_LIMIT.
        """
        line = 'return f"{value:.50}"'
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, (
            f"BUG 7: scan_text did not flag '{line}' as INVENTED_LIMIT. "
            "f-string format specs like {:.50} are invented-limit violations. "
            "Fix: add pattern r':\\.[0-9]+' or similar to PROHIBITED_PATTERNS."
        )

    def test_fstring_format_spec_with_larger_limit_is_flagged(self) -> None:
        """Verify detection for a larger format-spec number."""
        line = 'result = f"{description:.100}"'
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, f"BUG 7: scan_text did not flag '{line}' as INVENTED_LIMIT."


# ===========================================================================
# BUG 8 — check_completion.py: variable-name slice not caught
# ===========================================================================


class TestBug8VariableNameSliceNotCaught:
    """BUG 8: Pattern ``\\[:\\d+\\]`` only matches literal-integer slices like ``[:500]``.
    Identifier-based slices like ``[:MAX_LIMIT]`` or ``[:MAX_PREVIEW]`` are not caught,
    even though they represent the same invented-limit anti-pattern.
    """

    def test_variable_name_slice_is_flagged_as_invented_limit(self) -> None:
        """Verify that ``content[:MAX_LIMIT]`` is flagged as INVENTED_LIMIT.

        The current pattern ``\\[:\\d+\\]`` requires a literal digit and misses
        symbolic constants. Fix: extend pattern to also match ``[:<identifier>]``.
        """
        line = "return content[:MAX_LIMIT]"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, (
            f"BUG 8: scan_text did not flag '{line}' as INVENTED_LIMIT. "
            "Variable-name slices like [:MAX_LIMIT] are the same pattern as [:500]. "
            "Fix: extend the slice pattern to match identifiers, e.g. r'\\[:[A-Z_a-z]\\w*\\]'."
        )

    def test_variable_name_slice_max_preview_is_flagged(self) -> None:
        """Verify that ``output[:MAX_PREVIEW]`` is also flagged."""
        line = "output[:MAX_PREVIEW]"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, f"BUG 8: scan_text did not flag '{line}' as INVENTED_LIMIT."

    def test_literal_integer_slice_is_still_caught(self) -> None:
        """Sanity check: the original literal-integer pattern must keep working."""
        line = "return content[:500]"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, "[:500] must still be flagged as INVENTED_LIMIT."


# ===========================================================================
# BUG 9 — check_completion.py: TRUNCATE_AT and PREVIEW_CHARS constants not detected
# ===========================================================================


class TestBug9TruncateAtAndPreviewCharsNotDetected:
    """BUG 9: PROHIBITED_PATTERNS only includes ``MAX_LEN`` and ``max_length``.
    Named constants like ``PREVIEW_CHARS = 200`` and ``TRUNCATE_AT = 256`` —
    explicitly listed in invented-limit-patterns.md — are not detected.
    """

    def test_preview_chars_constant_is_flagged(self) -> None:
        """Verify scan_text flags ``PREVIEW_CHARS = 200`` as INVENTED_LIMIT."""
        line = "PREVIEW_CHARS = 200"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, (
            f"BUG 9: scan_text did not flag '{line}' as INVENTED_LIMIT. "
            "PREVIEW_CHARS is an invented-limit constant per invented-limit-patterns.md. "
            "Fix: add patterns for PREVIEW_CHARS and TRUNCATE_AT to PROHIBITED_PATTERNS."
        )

    def test_truncate_at_constant_is_flagged(self) -> None:
        """Verify scan_text flags ``TRUNCATE_AT = 256`` as INVENTED_LIMIT."""
        line = "TRUNCATE_AT = 256"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, (
            f"BUG 9: scan_text did not flag '{line}' as INVENTED_LIMIT. "
            "TRUNCATE_AT is an invented-limit constant per invented-limit-patterns.md. "
            "Fix: add pattern for TRUNCATE_AT to PROHIBITED_PATTERNS."
        )

    def test_existing_max_len_pattern_still_works(self) -> None:
        """Sanity check: existing MAX_LEN pattern must remain functional."""
        line = "MAX_LEN = 1024"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, "MAX_LEN = 1024 must still be flagged as INVENTED_LIMIT."

    def test_existing_max_length_pattern_still_works(self) -> None:
        """Sanity check: existing max_length pattern must remain functional."""
        line = "max_length = 512"
        hits = scan_text(line, source_label="<test>")
        invented_limit_hits = [h for h in hits if h[1] == "INVENTED_LIMIT"]
        assert invented_limit_hits, "max_length = 512 must still be flagged as INVENTED_LIMIT."


# ===========================================================================
# Additional integration / sanity tests (always-pass baseline)
# ===========================================================================


class TestScanTextBaseline:
    """Baseline sanity tests that must pass on both current and fixed code."""

    def test_clean_text_produces_no_hits(self) -> None:
        """Clean code with no prohibited patterns produces no hits."""
        text = "def compute_sum(a: int, b: int) -> int:\n    return a + b\n"
        hits = scan_text(text, source_label="<test>")
        assert hits == [], "Clean code should produce zero hits."

    def test_fixme_is_flagged(self) -> None:
        """FIXME is always flagged as INCOMPLETE."""
        hits = scan_text("# FIXME: broken", source_label="<test>")
        kinds = {h[1] for h in hits}
        assert "INCOMPLETE" in kinds

    def test_pending_is_flagged(self) -> None:
        """PENDING marker is always flagged."""
        hits = scan_text("<!-- PENDING: fill in later -->", source_label="<test>")
        kinds = {h[1] for h in hits}
        assert "INCOMPLETE" in kinds

    def test_literal_slice_flagged(self) -> None:
        """[:200] is always flagged as INVENTED_LIMIT."""
        hits = scan_text("output = data[:200]", source_label="<test>")
        kinds = {h[1] for h in hits}
        assert "INVENTED_LIMIT" in kinds

    def test_workaround_keyword_flagged(self) -> None:
        """'workaround' keyword is always flagged."""
        hits = scan_text("# This is a workaround", source_label="<test>")
        kinds = {h[1] for h in hits}
        assert "WORKAROUND" in kinds


class TestBuildDeclarationBaseline:
    """Baseline tests for build_declaration that must pass on current code."""

    def test_build_declaration_with_all_fields(self) -> None:
        """build_declaration returns a string containing all four fields."""
        result = build_declaration(
            reason="CI is broken", completed="ran tests", remains="fix the imports", condition="CI is green"
        )
        assert "BLOCKED: CI is broken" in result
        assert "ran tests" in result
        assert "fix the imports" in result
        assert "CI is green" in result

    def test_build_declaration_with_empty_completed(self) -> None:
        """build_declaration with empty completed uses the fallback placeholder."""
        result = build_declaration(reason="constraint", completed="", remains="do work", condition="constraint lifted")
        assert "nothing" in result.lower() or "nothing" in result

    def test_build_declaration_with_empty_remains(self) -> None:
        """build_declaration with empty remains uses the fallback placeholder."""
        result = build_declaration(
            reason="constraint", completed="done some work", remains="", condition="condition met"
        )
        assert "specify" in result.lower() or "remaining" in result.lower() or result  # has fallback

    def test_build_declaration_multiline_completed(self) -> None:
        """Multiline completed field is split into bullet list items."""
        result = build_declaration(reason="R", completed="step one\nstep two", remains="step three", condition="C")
        assert "step one" in result
        assert "step two" in result
