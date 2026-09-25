"""Execute the Generic Package component against a hermetic HTTP fixture.

The fixture supplies upload/download outcomes; it is not a GitLab server or a
Runner. These checks exercise the shipped shell's publication success predicate.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).parents[1]
COMPONENT = PLUGIN_ROOT / "skills/gitlab-skill/assets/release-components/templates/generic-package.yml"
PACKAGE_PATH = "/api/v4/projects/42/packages/generic/widgets/v1.2.3/release.bin"
BUILD_BYTES = b"built artifact\x00\xff\x01\n"
pytestmark = pytest.mark.skipif(
    os.name != "posix" or not shutil.which("sh") or not shutil.which("curl"),
    reason="The release component executes in a POSIX curl container",
)


def component_script() -> str:
    """Read the shipped job commands rather than copying a publication implementation."""
    documents = list(yaml.safe_load_all(COMPONENT.read_text(encoding="utf-8")))
    job = documents[1]["$[[ inputs.job-name ]]"]
    commands = job["script"]
    assert isinstance(commands, list)
    assert all(isinstance(command, str) for command in commands)
    return "set -eu\n" + "\n".join(commands)


def run_component(work: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Bound the complete shell/curl process group, retaining untruncated evidence."""
    args = ["sh", "-c", component_script()]
    with subprocess.Popen(
        args,
        cwd=work,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            pytest.fail(f"Component timed out\nstdout:\n{stdout}\nstderr:\n{stderr}")
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


@pytest.mark.parametrize(
    ("upload_status", "download_status", "download_bytes", "expected_success"),
    [
        (201, 200, BUILD_BYTES, True),
        (503, 200, BUILD_BYTES, False),
        (201, 200, b"a different build", False),
        (201, 404, b"missing", False),
        (201, 403, b"forbidden", False),
        (201, 500, b"storage unavailable", False),
    ],
    ids=["matching-readback", "upload-failed", "wrong-bytes", "missing", "read-denied", "read-failed"],
)
def test_publication_requires_matching_readback(
    tmp_path: Path,
    upload_status: int,
    download_status: int,
    download_bytes: bytes,
    expected_success: bool,
) -> None:
    """An upload acknowledgment alone cannot satisfy destination verification."""
    uploads: list[bytes] = []
    requests: list[tuple[str, str, str | None]] = []

    class PackageHandler(BaseHTTPRequestHandler):
        """Serve exactly one package coordinate without external state."""

        def do_PUT(self) -> None:
            requests.append(("PUT", self.path, self.headers.get("JOB-TOKEN")))
            uploads.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(upload_status if self.path == PACKAGE_PATH else 404)
            self.end_headers()
            self.wfile.write(b"upload response")

        def do_GET(self) -> None:
            requests.append(("GET", self.path, self.headers.get("JOB-TOKEN")))
            self.send_response(download_status if self.path == PACKAGE_PATH else 404)
            self.end_headers()
            self.wfile.write(download_bytes)

        def log_message(self, message: str, *args: object) -> None:
            pass

    artifact = tmp_path / "build output.bin"
    artifact.write_bytes(BUILD_BYTES)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    environment = {key: value for key, value in os.environ.items() if "proxy" not in key.lower()}
    environment.update(
        CI_PIPELINE_SOURCE="push",
        CI_COMMIT_TAG="v1.2.3",
        CI_COMMIT_BRANCH="",
        CI_COMMIT_REF_PROTECTED="true",
        CI_PROJECT_ID="42",
        CI_JOB_TOKEN="fixture-token",
        RELEASE_ASSET_PATH=str(artifact),
        RELEASE_ASSET_NAME="release.bin",
        GENERIC_PACKAGE_NAME="widgets",
        TMPDIR=str(downloads),
        HOME=str(tmp_path),
        CURL_HOME=str(tmp_path),
        NO_PROXY="*",
        no_proxy="*",
    )
    with ThreadingHTTPServer(("127.0.0.1", 0), PackageHandler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        environment["CI_API_V4_URL"] = f"http://127.0.0.1:{server.server_port}/api/v4"
        try:
            result = run_component(tmp_path, environment)
        finally:
            server.shutdown()
            thread.join(timeout=5)
        assert not thread.is_alive()

    assert (result.returncode == 0) is expected_success, result.stdout + result.stderr
    assert uploads == [BUILD_BYTES]
    assert all(path == PACKAGE_PATH and token == "fixture-token" for _, path, token in requests)
    if upload_status != 201:
        assert [method for method, _, _ in requests] == ["PUT"]
    assert artifact.read_bytes() == BUILD_BYTES
    assert list(downloads.iterdir()) == []
