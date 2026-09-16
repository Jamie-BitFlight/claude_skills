"""Tests for the shared PyGithub client factory.

The security-critical assertions live in TestSslContextKeepsVerification. The module
exists to clear exactly one X.509 verification flag, so that PyGithub reaches GitHub
through a TLS-intercepting proxy the way the Go-based ``gh`` CLI already does. Every
other verification guarantee has to survive that change, so each one is asserted
directly rather than inferred from a connection succeeding.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path

import certifi
import pytest
from github.Requester import HTTPSRequestsConnectionClass, Requester
from github_client import (
    CA_BUNDLE_ENV_VARS,
    DEFAULT_TIMEOUT,
    TOKEN_ENV_VARS,
    InstallState,
    MissingGitHubTokenError,
    build_ssl_context,
    install_proxy_tls_support,
    make_connection_class,
    make_github_client,
    resolve_ca_bundle,
    resolve_token,
)
from urllib3.util.ssl_ import create_urllib3_context

_ALL_ENV_VARS = (*CA_BUNDLE_ENV_VARS, *TOKEN_ENV_VARS, "GITHUB_API_URL")

#: Snapshot of the real environment, captured at import before any fixture strips it.
#: The integration class restores it, because a live request needs the genuine token
#: and the genuine CA bundle.
_AMBIENT_ENV = {name: os.environ.get(name) for name in _ALL_ENV_VARS}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove every variable this module reads, so ambient session config cannot leak in."""
    for name in _ALL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def restore_pygithub_classes():
    """Undo the process-wide connection-class substitution after each test.

    install_proxy_tls_support writes to the Requester class, which outlives any one test.
    Without this, one test that installs would change how every later test in the session
    builds its connections.
    """
    InstallState.installed = False
    yield
    Requester.resetConnectionClasses()
    InstallState.installed = False


@pytest.fixture
def ca_file(tmp_path):
    """A real, parseable CA bundle standing in for the one a proxy configures.

    certifi ships with requests, which PyGithub already depends on, so this needs no new
    dependency and gives load_verify_locations genuine certificates to parse.
    """
    bundle = tmp_path / "ca-bundle.crt"
    bundle.write_text(Path(certifi.where()).read_text(encoding="utf-8"), encoding="utf-8")
    return bundle


class TestResolveToken:
    """Token precedence, and the failure when nothing supplies one."""

    def test_explicit_token_wins(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "from-env")

        assert resolve_token("explicit") == "explicit"

    def test_first_env_var_in_order_wins(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "second")
        monkeypatch.setenv("GITHUB_TOKEN", "first")

        assert resolve_token() == "first"

    def test_falls_through_to_later_env_var(self, monkeypatch):
        monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "third")

        assert resolve_token() == "third"

    def test_empty_env_var_does_not_count(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setenv("GH_TOKEN", "real")

        assert resolve_token() == "real"

    def test_no_token_anywhere_raises(self):
        with pytest.raises(MissingGitHubTokenError) as excinfo:
            resolve_token()

        for name in TOKEN_ENV_VARS:
            assert name in str(excinfo.value)


class TestResolveCaBundle:
    """A CA bundle counts only when the path it names exists on disk."""

    def test_returns_none_when_no_variable_is_set(self):
        assert resolve_ca_bundle() is None

    def test_returns_the_path_when_the_file_exists(self, monkeypatch, ca_file):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        assert resolve_ca_bundle() == str(ca_file)

    def test_ignores_a_variable_naming_a_missing_file(self, monkeypatch, tmp_path):
        """A stale path is not a configured proxy, so it is skipped rather than trusted."""
        monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "does-not-exist.crt"))

        assert resolve_ca_bundle() is None

    def test_first_variable_in_order_wins(self, monkeypatch, tmp_path, ca_file):
        preferred = tmp_path / "preferred.crt"
        preferred.write_text(Path(certifi.where()).read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setenv("GITHUB_CA_BUNDLE", str(preferred))
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        assert resolve_ca_bundle() == str(preferred)


class TestSslContextKeepsVerification:
    """The relaxation clears one flag. Every other guarantee must survive it."""

    def test_strict_x509_flag_is_cleared(self, ca_file):
        """This is the whole point: the proxy CA carries no keyUsage extension."""
        context = build_ssl_context(str(ca_file))

        assert not context.verify_flags & ssl.VERIFY_X509_STRICT

    def test_certificate_verification_stays_required(self, ca_file):
        """Clearing the strict flag must not weaken chain verification to optional or off."""
        context = build_ssl_context(str(ca_file))

        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_hostname_verification_stays_on(self, ca_file):
        """A relaxed extension check must not become a licence to accept any host."""
        context = build_ssl_context(str(ca_file))

        assert context.check_hostname is True

    def test_the_bundle_is_actually_loaded(self, ca_file):
        """A context trusting nothing would fail closed rather than verify."""
        context = build_ssl_context(str(ca_file))

        assert context.get_ca_certs(), "expected the CA bundle to load as a trust anchor"

    def test_no_other_verify_flag_is_cleared(self, ca_file):
        """Nothing but VERIFY_X509_STRICT is dropped from the library default.

        Whether the default sets VERIFY_X509_STRICT varies by Python and urllib3
        version, so this asserts the subset relation rather than equality: on a build
        where the default already omits the flag, clearing it is a no-op and the
        difference is empty, which this still accepts.
        """
        default_flags = create_urllib3_context().verify_flags
        actual_flags = build_ssl_context(str(ca_file)).verify_flags
        cleared = default_flags & ~actual_flags

        assert not cleared & ~ssl.VERIFY_X509_STRICT, f"cleared a flag beyond VERIFY_X509_STRICT: {cleared!r}"


class TestInstallProxyTlsSupport:
    """Installation is conditional, idempotent, and process-wide."""

    def test_no_ca_bundle_means_no_install(self):
        """On an ordinary network PyGithub keeps its own strict default."""
        assert install_proxy_tls_support() is False

    def test_no_ca_bundle_records_no_install(self):
        """A no-op call must not mark the process as installed."""
        install_proxy_tls_support()

        assert InstallState.installed is False

    def test_install_reports_true_when_a_bundle_exists(self, monkeypatch, ca_file):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        assert install_proxy_tls_support() is True

    def test_install_records_the_installed_state(self, monkeypatch, ca_file):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        install_proxy_tls_support()

        assert InstallState.installed is True

    def test_second_call_is_idempotent(self, monkeypatch, ca_file):
        """Repeat calls neither reinstall nor report failure."""
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        assert install_proxy_tls_support() is True
        assert install_proxy_tls_support() is True

    def test_force_reports_true_when_already_installed(self, monkeypatch, ca_file):
        """force re-runs the substitution, so a changed bundle path takes effect."""
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        install_proxy_tls_support()

        assert install_proxy_tls_support(force=True) is True


class TestConnectionClassFactory:
    """The substituted class must remain a drop-in for the one PyGithub ships."""

    def test_returns_a_subclass_of_pygithubs_own_class(self, ca_file):
        """PyGithub builds connections from it, so it has to satisfy that contract."""
        connection_class = make_connection_class(str(ca_file))

        assert issubclass(connection_class, HTTPSRequestsConnectionClass)

    def test_each_call_builds_a_distinct_class(self, ca_file):
        """force depends on a rebuild, so the factory must not cache one class."""
        assert make_connection_class(str(ca_file)) is not make_connection_class(str(ca_file))


class TestConnectionClassPinsVerifyToTheResolvedBundle:
    """PyGithub's HTTPSRequestsConnectionClass defaults ``verify`` to ``True`` and
    passes it straight through to every ``session.get(..., verify=self.verify)``
    call. Left at ``True``, ``requests.Session.merge_environment_settings``
    independently re-derives its own CA bundle from REQUESTS_CA_BUNDLE/
    CURL_CA_BUNDLE, bypassing whatever bundle this module resolved and mounted
    an SSL context for (backlog #3601) -- so the connection class must pin
    ``self.verify`` to that same bundle whenever the caller leaves it unset.
    """

    def test_verify_is_pinned_to_the_ca_bundle_when_the_caller_leaves_it_unset(self, ca_file):
        connection_class = make_connection_class(str(ca_file))

        connection = connection_class("api.github.com")

        assert connection.verify == str(ca_file)

    def test_an_explicit_verify_kwarg_from_the_caller_still_wins(self, ca_file):
        """PyGithub itself is free to pass an explicit verify; this module must not
        silently override an explicit caller decision."""
        connection_class = make_connection_class(str(ca_file))

        connection = connection_class("api.github.com", verify=False)

        assert connection.verify is False


class TestMakeGithubClient:
    """Client construction resolves the token and the API root."""

    def test_uses_the_environment_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "x" * 40)

        assert make_github_client() is not None

    def test_no_token_raises_before_any_request(self):
        """Construction fails fast rather than deferring to an opaque 401."""
        with pytest.raises(MissingGitHubTokenError):
            make_github_client()

    def test_explicit_base_url_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_API_URL", "https://from-env.example/api/v3")

        client = make_github_client("t" * 40, base_url="https://explicit.example/api/v3")

        assert "explicit.example" in client.requester.base_url

    def test_env_base_url_is_used_when_no_argument(self, monkeypatch):
        """GitHub Enterprise installs are configured through the environment."""
        monkeypatch.setenv("GITHUB_API_URL", "https://ghe.example/api/v3")

        client = make_github_client("t" * 40)

        assert "ghe.example" in client.requester.base_url

    def test_defaults_to_the_public_api(self):
        client = make_github_client("t" * 40)

        assert "api.github.com" in client.requester.base_url

    def test_default_timeout_is_applied(self):
        """The documented default reaches the client rather than PyGithub's own 15s."""
        client = make_github_client("t" * 40)

        assert client.requester.kwargs["timeout"] == DEFAULT_TIMEOUT


@pytest.mark.integration
class TestAgainstLiveGitHub:
    """Proves the module reaches GitHub from whatever network is actually present.

    Deselected by default. Run with ``-m integration``. The unit tests above assert the
    TLS context's shape; only a real request proves that shape completes a handshake.
    """

    @pytest.fixture(autouse=True)
    def restore_ambient_env(self, monkeypatch):
        """Put back the real environment that the module-level fixture strips.

        A live request needs the genuine token and the genuine CA bundle, so this class
        opts out of the isolation every other test in the module depends on.
        """
        for name, value in _AMBIENT_ENV.items():
            if value is not None:
                monkeypatch.setenv(name, value)

    def test_a_real_repository_read_succeeds(self):
        """The end-to-end path: install, build a client, and fetch a public repository."""
        client = make_github_client()
        repo = client.get_repo("Jamie-BitFlight/claude_skills")

        assert repo.full_name == "Jamie-BitFlight/claude_skills"
