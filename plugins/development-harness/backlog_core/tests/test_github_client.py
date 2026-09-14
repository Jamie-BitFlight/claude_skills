"""Tests for the shared PyGithub client factory.

The security-critical assertions live in TestSslContextKeepsVerification. The module
exists to clear exactly one X.509 verification flag, so that PyGithub reaches GitHub
through a TLS-intercepting proxy the way the Go-based ``gh`` CLI already does. Every
other verification guarantee has to survive that change, so each one is asserted
directly rather than inferred from a connection succeeding.
"""

from __future__ import annotations

import datetime as dt
import os
import ssl
from pathlib import Path

import certifi
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from github.Requester import HTTPSRequestsConnectionClass, Requester
from urllib3.util.ssl_ import create_urllib3_context

from backlog_core.github_client import (
    CA_BUNDLE_ENV_VARS,
    DEFAULT_TIMEOUT,
    TOKEN_ENV_VARS,
    MissingGitHubTokenError,
    _build_ssl_context,
    _InstallState,
    _make_connection_class,
    bundle_requires_relaxed_verification,
    install_proxy_tls_support,
    make_github_client,
    resolve_ca_bundle,
    resolve_token,
)

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
    _InstallState.installed = False
    yield
    Requester.resetConnectionClasses()
    _InstallState.installed = False


def _self_signed_ca(*, key_usage: bool, basic_constraints: bool = True, basic_critical: bool = True) -> str:
    """Build a self-signed anchor in PEM form, with the extensions under test toggled.

    Args:
        key_usage: Include a ``keyUsage`` extension.
        basic_constraints: Include a ``basicConstraints`` extension.
        basic_critical: Mark ``basicConstraints`` critical.

    Returns:
        The certificate as a PEM string.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-anchor")])
    now = dt.datetime.now(dt.UTC)
    builder = (
        x509
        .CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=1))
    )
    if basic_constraints:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=basic_critical)
    if key_usage:
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode("ascii")


def _installed_https_connection_class() -> type:
    """Read the HTTPS connection class Requester currently builds instances from.

    PyGithub sets this through name-mangled class attributes assigned only inside
    ``injectConnectionClasses``/``resetConnectionClasses`` bodies (``cls.__httpsConnectionClass
    = ...``), so no static type ever declares it and a type checker cannot resolve a direct
    ``Requester._Requester__httpsConnectionClass`` access. Indexing ``__dict__`` reads the same
    process-wide state PyGithub itself relies on without that unresolved-attribute error, and
    without the ``getattr``-with-a-constant form ruff's B009 asks to rewrite back into the
    direct access this exists to avoid.

    Returns:
        The class ``Requester.injectConnectionClasses``/``resetConnectionClasses`` last set.
    """
    return Requester.__dict__["_Requester__httpsConnectionClass"]


def _requester_connection_class(requester: Requester) -> type:
    """Read the HTTPS connection class one already-built Requester instance captured.

    Same name-mangling rationale as ``_installed_https_connection_class``, but for the
    per-instance copy ``Requester.__init__`` takes at construction time.

    Args:
        requester: A built Requester instance, as found on ``Github(...).requester``.

    Returns:
        The connection class that requester's constructor captured.
    """
    return requester.__dict__["_Requester__connectionClass"]


@pytest.fixture
def stock_store_file(tmp_path):
    """A copy of the public trust store, which is what Nix and conda point these vars at.

    certifi ships with requests, which PyGithub already depends on, so this needs no new
    dependency and gives load_verify_locations genuine certificates to parse.
    """
    bundle = tmp_path / "stock-store.crt"
    bundle.write_text(Path(certifi.where()).read_text(encoding="utf-8"), encoding="utf-8")
    return bundle


@pytest.fixture
def ca_file(tmp_path, stock_store_file):
    """A bundle shaped like the one a TLS-intercepting proxy installs.

    The public roots plus one locally added anchor that carries no ``keyUsage`` extension —
    the certificate shape that makes VERIFY_X509_STRICT reject the chain.
    """
    bundle = tmp_path / "ca-bundle.crt"
    bundle.write_text(stock_store_file.read_text(encoding="utf-8") + _self_signed_ca(key_usage=False), encoding="utf-8")
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


class TestBundleRequiresRelaxedVerification:
    """Only a locally added anchor that strict verification rejects earns the relaxation.

    The three rejected shapes below were each observed against a loopback TLS server:
    OpenSSL refuses them under VERIFY_X509_STRICT and accepts them once the flag is
    cleared, which is the whole condition this predicate stands for.
    """

    def test_the_stock_trust_store_needs_nothing(self, stock_store_file):
        """Nix and conda point these variables at a copy of the public roots.

        The public store already contains anchors that strict mode rejects, so a bundle
        is judged by what it adds, not by what it inherited.
        """
        assert bundle_requires_relaxed_verification(str(stock_store_file)) is False

    def test_an_added_anchor_without_key_usage_requires_it(self, ca_file):
        """The proxy CA shape this module exists for: verify code 92."""
        assert bundle_requires_relaxed_verification(str(ca_file)) is True

    def test_an_added_anchor_with_non_critical_basic_constraints_requires_it(self, tmp_path, stock_store_file):
        """Verify code 89: Basic Constraints of CA cert not marked critical."""
        bundle = tmp_path / "non-critical.crt"
        bundle.write_text(
            stock_store_file.read_text(encoding="utf-8") + _self_signed_ca(key_usage=True, basic_critical=False),
            encoding="utf-8",
        )

        assert bundle_requires_relaxed_verification(str(bundle)) is True

    def test_an_added_anchor_without_basic_constraints_requires_it(self, tmp_path, stock_store_file):
        """Verify code 79: invalid CA certificate."""
        bundle = tmp_path / "no-basic-constraints.crt"
        bundle.write_text(
            stock_store_file.read_text(encoding="utf-8") + _self_signed_ca(key_usage=True, basic_constraints=False),
            encoding="utf-8",
        )

        assert bundle_requires_relaxed_verification(str(bundle)) is True

    def test_a_compliant_added_anchor_needs_nothing(self, tmp_path, stock_store_file):
        """A private CA that satisfies RFC 5280 verifies under strict mode as it is."""
        bundle = tmp_path / "compliant-private-ca.crt"
        bundle.write_text(
            stock_store_file.read_text(encoding="utf-8") + _self_signed_ca(key_usage=True), encoding="utf-8"
        )

        assert bundle_requires_relaxed_verification(str(bundle)) is False

    def test_a_bundle_holding_no_certificates_needs_nothing(self, tmp_path):
        """An empty or non-PEM file announces no proxy, so it must not relax anything."""
        bundle = tmp_path / "empty.crt"
        bundle.write_text("not a certificate\n", encoding="utf-8")

        assert bundle_requires_relaxed_verification(str(bundle)) is False


class TestSslContextKeepsVerification:
    """The relaxation clears one flag. Every other guarantee must survive it."""

    def test_strict_x509_flag_is_cleared(self, ca_file):
        """This is the whole point: the proxy CA carries no keyUsage extension."""
        context = _build_ssl_context(str(ca_file))

        assert not context.verify_flags & ssl.VERIFY_X509_STRICT

    def test_certificate_verification_stays_required(self, ca_file):
        """Clearing the strict flag must not weaken chain verification to optional or off."""
        context = _build_ssl_context(str(ca_file))

        assert context.verify_mode == ssl.CERT_REQUIRED

    def test_hostname_verification_stays_on(self, ca_file):
        """A relaxed extension check must not become a licence to accept any host."""
        context = _build_ssl_context(str(ca_file))

        assert context.check_hostname is True

    def test_the_bundle_is_actually_loaded(self, ca_file):
        """A context trusting nothing would fail closed rather than verify."""
        context = _build_ssl_context(str(ca_file))

        assert context.get_ca_certs(), "expected the CA bundle to load as a trust anchor"

    def test_no_other_verify_flag_is_cleared(self, ca_file):
        """Nothing but VERIFY_X509_STRICT is dropped from the library default.

        Whether the default sets VERIFY_X509_STRICT varies by Python and urllib3
        version, so this asserts the subset relation rather than equality: on a build
        where the default already omits the flag, clearing it is a no-op and the
        difference is empty, which this still accepts.
        """
        default_flags = create_urllib3_context().verify_flags
        actual_flags = _build_ssl_context(str(ca_file)).verify_flags
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

        assert _InstallState.installed is False

    def test_install_reports_true_when_a_bundle_exists(self, monkeypatch, ca_file):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        assert install_proxy_tls_support() is True

    def test_install_records_the_installed_state(self, monkeypatch, ca_file):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        install_proxy_tls_support()

        assert _InstallState.installed is True

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

    def test_a_stock_trust_store_does_not_install(self, monkeypatch, stock_store_file):
        """A CA bundle variable is not a proxy: Nix and conda set these on ordinary networks.

        Installing there would drop VERIFY_X509_STRICT and PyGithub's connection reuse on a
        network that verifies perfectly well without either.
        """
        monkeypatch.setenv("SSL_CERT_FILE", str(stock_store_file))

        assert install_proxy_tls_support() is False
        assert _InstallState.installed is False
        assert _installed_https_connection_class() is HTTPSRequestsConnectionClass

    def test_install_substitutes_pygithubs_connection_class(self, monkeypatch, ca_file):
        """The reported state has to mean PyGithub actually builds connections differently."""
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))

        install_proxy_tls_support()

        assert _installed_https_connection_class() is not HTTPSRequestsConnectionClass

    def test_force_uninstalls_when_the_bundle_is_gone(self, monkeypatch, ca_file):
        """A forced call that finds no proxy must leave nothing of the previous install.

        Reporting False while the substituted class stays live — and the recorded state
        stays True — leaves the process relaxed with no way to observe it.
        """
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))
        install_proxy_tls_support()
        ca_file.unlink()

        assert install_proxy_tls_support(force=True) is False
        assert _InstallState.installed is False
        assert _installed_https_connection_class() is HTTPSRequestsConnectionClass

    def test_force_uninstalls_when_the_bundle_no_longer_announces_a_proxy(self, monkeypatch, ca_file, stock_store_file):
        """Same requirement when the bundle still exists but no longer needs the relaxation."""
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))
        install_proxy_tls_support()
        monkeypatch.setenv("SSL_CERT_FILE", str(stock_store_file))

        assert install_proxy_tls_support(force=True) is False
        assert _InstallState.installed is False
        assert _installed_https_connection_class() is HTTPSRequestsConnectionClass


class TestConnectionClassFactory:
    """The substituted class must remain a drop-in for the one PyGithub ships."""

    def test_returns_a_subclass_of_pygithubs_own_class(self, ca_file):
        """PyGithub builds connections from it, so it has to satisfy that contract."""
        connection_class = _make_connection_class(str(ca_file))

        assert issubclass(connection_class, HTTPSRequestsConnectionClass)

    def test_each_call_builds_a_distinct_class(self, ca_file):
        """force depends on a rebuild, so the factory must not cache one class."""
        assert _make_connection_class(str(ca_file)) is not _make_connection_class(str(ca_file))


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
        connection_class = _make_connection_class(str(ca_file))

        connection = connection_class("api.github.com")

        assert connection.verify == str(ca_file)

    def test_an_explicit_verify_kwarg_from_the_caller_still_wins(self, ca_file):
        """PyGithub itself is free to pass an explicit verify; this module must not
        silently override an explicit caller decision."""
        connection_class = _make_connection_class(str(ca_file))

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

    def test_only_a_client_built_after_the_install_uses_the_substituted_class(self, monkeypatch, ca_file):
        """A Requester copies its connection class at construction, so ordering matters.

        PyGithub's ``Requester.__init__`` reads the class off the Requester class and stores
        it on the instance, which is why this factory installs before it builds anything: a
        client built earlier keeps the stock strict class for its whole life, and no later
        install reaches it.
        """
        monkeypatch.setenv("GITHUB_TOKEN", "t" * 40)
        built_before_install = make_github_client()

        monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))
        built_after_install = make_github_client()

        assert _requester_connection_class(built_before_install.requester) is HTTPSRequestsConnectionClass
        assert _requester_connection_class(built_after_install.requester) is not HTTPSRequestsConnectionClass

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
