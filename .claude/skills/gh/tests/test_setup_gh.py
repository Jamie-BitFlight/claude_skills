"""Focused tests for setup_gh.py release/checksum metadata caching."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
