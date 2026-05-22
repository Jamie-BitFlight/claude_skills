"""Focused tests for setup_gh.py release/checksum metadata caching."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    import pytest

# Load script module from path.
_SCRIPT = Path(__file__).parent.parent / "scripts" / "setup_gh.py"
_spec = importlib.util.spec_from_file_location("setup_gh", _SCRIPT)
assert _spec is not None, f"Cannot find spec for {_SCRIPT}"
assert _spec.loader is not None, f"Cannot find loader for {_SCRIPT}"
_setup_gh = importlib.util.module_from_spec(_spec)
sys.modules["setup_gh"] = _setup_gh
_spec.loader.exec_module(_setup_gh)


def _mock_http_client(response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get.return_value = response
    return client


def test_fetch_latest_release_uses_cache_without_network(tmp_path: Path) -> None:
    cache_path = tmp_path / "latest-release.json"
    _setup_gh._write_cache_json(
        cache_path,
        {
            "tag_name": "v9.9.9",
            "assets": [{"name": "gh_9.9.9_linux_amd64.tar.gz", "url": "https://example.invalid/a.tgz", "size": 7}],
        },
    )

    with (
        patch("setup_gh._latest_release_cache_path", return_value=cache_path),
        patch("setup_gh.httpx.Client", side_effect=AssertionError("network should not be used")),
    ):
        tag, assets = _setup_gh.fetch_latest_release(use_cache=True, cache_ttl_seconds=600)

    assert tag == "v9.9.9"
    assert len(assets) == 1
    assert assets[0].name == "gh_9.9.9_linux_amd64.tar.gz"


def test_fetch_latest_release_refreshes_stale_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "latest-release.json"
    _setup_gh._write_cache_json(cache_path, {"tag_name": "v0.0.1", "assets": []})
    os.utime(cache_path, (1, 1))

    api_response = MagicMock()
    api_response.status_code = _setup_gh.HTTP_OK
    api_response.json.return_value = {
        "tag_name": "v2.0.0",
        "assets": [
            {"name": "gh_2.0.0_linux_amd64.tar.gz", "browser_download_url": "https://example.invalid/b.tgz", "size": 42}
        ],
    }
    client = _mock_http_client(api_response)

    with (
        patch("setup_gh._latest_release_cache_path", return_value=cache_path),
        patch("setup_gh.httpx.Client", return_value=client),
    ):
        tag, assets = _setup_gh.fetch_latest_release(use_cache=True, cache_ttl_seconds=1)

    assert tag == "v2.0.0"
    assert assets[0].name == "gh_2.0.0_linux_amd64.tar.gz"
    client.get.assert_called_once()
    cached = _setup_gh._read_cache_json(cache_path, ttl_seconds=999999)
    assert cached is not None
    assert cached["tag_name"] == "v2.0.0"


def test_fetch_latest_release_no_cache_always_uses_network(tmp_path: Path) -> None:
    cache_path = tmp_path / "latest-release.json"
    _setup_gh._write_cache_json(cache_path, {"tag_name": "v0.0.1", "assets": []})
    stale_mtime = cache_path.stat().st_mtime

    api_response = MagicMock()
    api_response.status_code = _setup_gh.HTTP_OK
    api_response.json.return_value = {"tag_name": "v3.0.0", "assets": []}
    client = _mock_http_client(api_response)

    with (
        patch("setup_gh._latest_release_cache_path", return_value=cache_path),
        patch("setup_gh.httpx.Client", return_value=client),
    ):
        tag, _ = _setup_gh.fetch_latest_release(use_cache=False)

    assert tag == "v3.0.0"
    client.get.assert_called_once()
    assert cache_path.stat().st_mtime == stale_mtime


def test_fetch_checksums_uses_cache_without_network(tmp_path: Path) -> None:
    checksums_asset = _setup_gh.ReleaseAsset(name="gh_1.2.3_checksums.txt", url="https://example.invalid/sums", size=12)
    cache_path = tmp_path / "checksums.json"
    _setup_gh._write_cache_json(cache_path, {"checksums": {"gh_1.2.3_linux_amd64.tar.gz": "abc123"}})

    with (
        patch("setup_gh._checksums_cache_path", return_value=cache_path),
        patch("setup_gh.httpx.Client", side_effect=AssertionError("network should not be used")),
    ):
        checksums = _setup_gh.fetch_checksums(checksums_asset, use_cache=True, cache_ttl_seconds=600)

    assert checksums == {"gh_1.2.3_linux_amd64.tar.gz": "abc123"}


# ---------------------------------------------------------------------------
# Tests for _get_git_remote_url()
# ---------------------------------------------------------------------------


def test__get_git_remote_url_returns_url_on_success() -> None:
    """Arrange: subprocess.run returns returncode=0 with a URL. Assert: URL returned stripped."""
    import subprocess

    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="http://proxy@127.0.0.1:41425/git/Jamie-BitFlight/claude_skills\n", stderr=""
    )
    with patch("setup_gh.subprocess.run", return_value=completed):
        url = _setup_gh._get_git_remote_url()

    assert url == "http://proxy@127.0.0.1:41425/git/Jamie-BitFlight/claude_skills"


def test__get_git_remote_url_returns_none_on_nonzero_exit() -> None:
    """Arrange: subprocess.run returns returncode=128. Assert: None returned."""
    import subprocess

    completed = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="")
    with patch("setup_gh.subprocess.run", return_value=completed):
        url = _setup_gh._get_git_remote_url()

    assert url is None


def test__get_git_remote_url_returns_none_on_oserror() -> None:
    """Arrange: subprocess.run raises OSError. Assert: None returned."""
    with patch("setup_gh.subprocess.run", side_effect=OSError("not found")):
        url = _setup_gh._get_git_remote_url()

    assert url is None


# ---------------------------------------------------------------------------
# Tests for detect_owner_repo()
# ---------------------------------------------------------------------------


def test_detect_owner_repo_env_var_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: GITHUB_REPO env var set. Assert: returned directly without calling git."""
    monkeypatch.setenv("GITHUB_REPO", "my-org/my-repo")
    with patch("setup_gh._get_git_remote_url", side_effect=AssertionError("git should not be called")):
        result = _setup_gh.detect_owner_repo()

    assert result == "my-org/my-repo"


def test_detect_owner_repo_env_var_invalid_format_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: GITHUB_REPO is not a valid slug. Assert: falls through to git remote."""
    monkeypatch.setenv("GITHUB_REPO", "not-a-slug")
    with patch("setup_gh._get_git_remote_url", return_value="http://proxy@127.0.0.1/git/fallback-org/fallback-repo"):
        result = _setup_gh.detect_owner_repo()

    assert result == "fallback-org/fallback-repo"


def test_detect_owner_repo_proxy_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote returns a proxy URL. Assert: owner/repo extracted correctly."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch(
        "setup_gh._get_git_remote_url",
        return_value="http://local_proxy@127.0.0.1:41425/git/Jamie-BitFlight/claude_skills",
    ):
        result = _setup_gh.detect_owner_repo()

    assert result == "Jamie-BitFlight/claude_skills"


def test_detect_owner_repo_ssh_scp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote returns an SSH SCP URL. Assert: owner/repo extracted correctly."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch("setup_gh._get_git_remote_url", return_value="git@github.com:my-org/my-repo.git"):
        result = _setup_gh.detect_owner_repo()

    assert result == "my-org/my-repo"


def test_detect_owner_repo_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote returns an HTTPS URL. Assert: owner/repo extracted correctly."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch("setup_gh._get_git_remote_url", return_value="https://github.com/my-org/my-repo.git"):
        result = _setup_gh.detect_owner_repo()

    assert result == "my-org/my-repo"


def test_detect_owner_repo_ssh_proto_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote returns an SSH protocol URL. Assert: owner/repo extracted correctly."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch("setup_gh._get_git_remote_url", return_value="ssh://git@github.com/my-org/my-repo.git"):
        result = _setup_gh.detect_owner_repo()

    assert result == "my-org/my-repo"


def test_detect_owner_repo_no_remote_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote returns None. Assert: detect_owner_repo returns None."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch("setup_gh._get_git_remote_url", return_value=None):
        result = _setup_gh.detect_owner_repo()

    assert result is None


def test_detect_owner_repo_unrecognised_url_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrange: git remote URL matches no pattern. Assert: detect_owner_repo returns None."""
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    with patch("setup_gh._get_git_remote_url", return_value="ftp://weird.host/path"):
        result = _setup_gh.detect_owner_repo()

    assert result is None


# ---------------------------------------------------------------------------
# Tests for write_gh_config()
# ---------------------------------------------------------------------------


def test_write_gh_config_creates_file_when_absent(tmp_path: Path) -> None:
    """Arrange: config_path does not exist. Assert: file created with gh.repo key."""
    config_path = tmp_path / "config.yaml"

    result = _setup_gh.write_gh_config(config_path, "my-org/my-repo")

    assert result is True
    assert config_path.exists()
    content = config_path.read_text()
    assert "gh:" in content
    assert "repo: my-org/my-repo" in content


def test_write_gh_config_preserves_existing_keys(tmp_path: Path) -> None:
    """Arrange: config.yaml has backend and task keys. Assert: all keys preserved after upsert."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("backend:\n  name: github\ntask:\n  backend: local\n")

    result = _setup_gh.write_gh_config(config_path, "my-org/my-repo")

    assert result is True
    content = config_path.read_text()
    assert "backend:" in content
    assert "name: github" in content
    assert "task:" in content
    assert "backend: local" in content
    assert "gh:" in content
    assert "repo: my-org/my-repo" in content


def test_write_gh_config_idempotent(tmp_path: Path) -> None:
    """Arrange: write called twice with same value. Assert: no duplicate keys in file."""
    config_path = tmp_path / "config.yaml"

    _setup_gh.write_gh_config(config_path, "my-org/my-repo")
    _setup_gh.write_gh_config(config_path, "my-org/my-repo")
    content = config_path.read_text()

    assert content.count("gh:") == 1
    assert content.count("repo:") == 1
    assert "repo: my-org/my-repo" in content


def test_write_gh_config_creates_parent_dirs(tmp_path: Path) -> None:
    """Arrange: config_path nested under non-existent dirs. Assert: dirs created and file written."""
    config_path = tmp_path / "nested" / "dirs" / "config.yaml"

    result = _setup_gh.write_gh_config(config_path, "my-org/my-repo")

    assert result is True
    assert config_path.exists()


# ---------------------------------------------------------------------------
# Tests for render_gh_examples()
# ---------------------------------------------------------------------------


def test_render_gh_examples_substitutes_owner_repo_token(tmp_path: Path) -> None:
    """Arrange: template has <owner/repo> token. Assert: token replaced and file written."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (tmp_path / "gh-examples.md.template").write_text("Run: gh pr list -R <owner/repo>\n")

    with patch("setup_gh._SCRIPT_DIR", scripts_dir):
        result = _setup_gh.render_gh_examples("my-org/my-repo")

    assert result is True
    output = (tmp_path / "gh-examples.md").read_text()
    assert "gh pr list -R my-org/my-repo" in output
    assert "<owner/repo>" not in output


def test_render_gh_examples_substitutes_owner_token(tmp_path: Path) -> None:
    """Arrange: template has <owner/repo>, <owner>, and <repo> tokens. Assert: all substituted."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (tmp_path / "gh-examples.md.template").write_text(
        "gh pr list -R <owner/repo>\ngh project --owner <owner>\ngh api repos/<owner>/<repo>\n"
    )

    with patch("setup_gh._SCRIPT_DIR", scripts_dir):
        result = _setup_gh.render_gh_examples("my-org/my-repo")

    assert result is True
    output = (tmp_path / "gh-examples.md").read_text()
    assert "my-org/my-repo" in output
    assert "my-org" in output
    assert "my-repo" in output
    assert "<owner/repo>" not in output
    assert "<owner>" not in output
    assert "<repo>" not in output


def test_render_gh_examples_returns_false_when_template_missing(tmp_path: Path) -> None:
    """Arrange: template file does not exist. Assert: returns False."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    with patch("setup_gh._SCRIPT_DIR", scripts_dir):
        result = _setup_gh.render_gh_examples("my-org/my-repo")

    assert result is False
