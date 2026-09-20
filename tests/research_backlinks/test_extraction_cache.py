from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import backlink_cache as cache_module
import backlink_lib as bl

if TYPE_CHECKING:
    from collections.abc import Callable


def test_build_graph_when_vault_is_unchanged_reuses_all_extractions(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path
) -> None:
    source = make_entry("agent-frameworks/alpha.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    target = make_entry("tools/beta.md")
    cache_path = tmp_path / "cache" / "backlinks.sqlite3"

    first = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    second = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert first.graph == {source.resolve(): [target.resolve()], target.resolve(): []}
    assert first.files_parsed == 2
    assert first.cache_hits == 0
    assert second.graph == first.graph
    assert second.files_parsed == 0
    assert second.cache_hits == 2


def test_build_graph_when_bytes_change_but_metadata_is_restored_reparses_changed_file(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path
) -> None:
    source = make_entry("agent-frameworks/alpha.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    make_entry("tools/beta.md")
    cache_path = tmp_path / "cache" / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    original_stat = source.stat()
    original = source.read_bytes()
    changed = original.replace(b"uses beta", b"uses zeta")
    assert len(changed) == len(original)
    source.write_bytes(changed)
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert scan.files_parsed == 1
    assert scan.cache_hits == 1


def test_build_graph_when_cached_target_is_deleted_rechecks_current_filesystem(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path
) -> None:
    source = make_entry("agent-frameworks/alpha.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    target = make_entry("tools/beta.md")
    cache_path = tmp_path / "cache" / "backlinks.sqlite3"
    first = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    assert first.graph[source.resolve()] == [target.resolve()]
    target.unlink()

    second = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert second.graph == {source.resolve(): []}
    assert second.files_parsed == 0
    assert second.cache_hits == 1


def test_build_graph_when_parse_fails_does_not_cache_incomplete_extraction(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path
) -> None:
    make_entry(
        "tools/broken.md",
        custom_markdown=(
            "# Broken\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|--------------|\n"
            "| beta.md | tools | missing link |\n"
        ),
    )
    cache_path = tmp_path / "cache" / "backlinks.sqlite3"

    first = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    second = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert [skip.reason for skip in first.skips] == ["parse"]
    assert [skip.reason for skip in second.skips] == ["parse"]
    assert first.files_parsed == second.files_parsed == 1
    assert first.cache_hits == second.cache_hits == 0


def test_build_graph_when_cache_is_corrupt_falls_back_to_uncached_scan(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    entry = make_entry("tools/alpha.md")
    cache_path = tmp_path / "backlinks.sqlite3"
    cache_path.write_bytes(b"not a sqlite database")

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path)

    assert scan.graph == {entry.resolve(): []}
    assert scan.files_parsed == 1
    assert scan.cache_hits == 0
    assert "extraction-cache-disabled" in capsys.readouterr().err


def test_build_graph_when_cached_rows_are_incomplete_reparses_vault(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = make_entry("agent-frameworks/alpha.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    target = make_entry("tools/beta.md")
    cache_path = tmp_path / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    connection = sqlite3.connect(cache_path)
    try:
        connection.execute("DELETE FROM extraction_rows")
        connection.commit()
    finally:
        connection.close()

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path)

    assert scan.graph == {source.resolve(): [target.resolve()], target.resolve(): []}
    assert scan.files_parsed == 2
    assert scan.cache_hits == 0
    assert "row count does not match" in capsys.readouterr().err


def test_build_graph_when_cached_row_fails_validation_reparses_vault(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    early = make_entry("agent-frameworks/alpha.md")
    target = make_entry("tools/beta.md")
    source = make_entry("zz/omega.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    cache_path = tmp_path / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    connection = sqlite3.connect(cache_path)
    try:
        connection.execute("UPDATE extraction_rows SET link_path = ?", (sqlite3.Binary(b"\xff"),))
        connection.commit()
    finally:
        connection.close()

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path)

    assert scan.graph == {early.resolve(): [], target.resolve(): [], source.resolve(): [target.resolve()]}
    assert scan.skips == []
    assert scan.files_parsed == 3
    assert scan.cache_hits == 0
    assert "cached extraction row failed validation" in capsys.readouterr().err


def test_build_graph_when_late_cache_failure_emits_retained_skip_once(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = make_entry(
        "00-broken.md",
        custom_markdown=(
            "# Broken\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|--------------|\n"
            "| beta.md | tools | missing link |\n"
        ),
    )
    early = make_entry("agent-frameworks/alpha.md")
    target = make_entry("tools/beta.md")
    source = make_entry("zz/omega.md", cross_refs=[("../tools/beta.md", "tools", "Beta", "uses beta")])
    cache_path = tmp_path / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    connection = sqlite3.connect(cache_path)
    try:
        connection.execute("UPDATE extraction_rows SET link_path = ?", (sqlite3.Binary(b"\xff"),))
        connection.commit()
    finally:
        connection.close()

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path)

    assert scan.graph == {
        broken.resolve(): [],
        early.resolve(): [],
        target.resolve(): [],
        source.resolve(): [target.resolve()],
    }
    assert [(skip.path, skip.reason) for skip in scan.skips] == [("00-broken.md", "parse")]
    assert scan.files_parsed == 4
    assert scan.cache_hits == 0
    stderr = capsys.readouterr().err
    assert stderr.count("warning: scan-skipped") == 1


def test_build_graph_when_entry_is_not_utf8_records_read_skip(tmp_vault: Path) -> None:
    entry = tmp_vault / "tools" / "invalid.md"
    entry.write_bytes(b"\xff\xfe")

    scan = bl.build_cross_reference_graph(tmp_vault, quiet=True)

    assert scan.graph == {entry.resolve(): []}
    assert [(skip.path, skip.reason) for skip in scan.skips] == [("tools/invalid.md", "read")]
    assert scan.files_parsed == 0


def test_build_graph_when_parser_fingerprint_changes_reparses_every_entry(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_entry("agent-frameworks/alpha.md")
    make_entry("tools/beta.md")
    cache_path = tmp_path / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    monkeypatch.setattr(bl, "_PARSER_FINGERPRINT", "marko=test;extractor=next")

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert scan.files_parsed == 2
    assert scan.cache_hits == 0


def test_build_graph_when_cache_schema_changes_rebuilds_disposable_cache(
    tmp_vault: Path, make_entry: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_entry("agent-frameworks/alpha.md")
    make_entry("tools/beta.md")
    cache_path = tmp_path / "backlinks.sqlite3"
    bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)
    monkeypatch.setattr(cache_module, "_SCHEMA_VERSION", cache_module._SCHEMA_VERSION + 1)

    scan = bl.build_cross_reference_graph(tmp_vault, cache_path=cache_path, quiet=True)

    assert scan.files_parsed == 2
    assert scan.cache_hits == 0
