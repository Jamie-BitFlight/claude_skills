"""Shared PyGithub client construction for every GitHub caller in this repository.

One place that knows how to build a PyGithub client, so no caller repeats token
lookup, timeout defaults, or TLS configuration inline.

Why the TLS handling exists
---------------------------
Agent sessions route outbound HTTPS through a TLS-intercepting egress proxy whose
CA certificate carries no ``keyUsage`` extension. Python 3.13 turns on
``ssl.VERIFY_X509_STRICT`` by default, and that flag rejects such a CA with
``CA cert does not include key usage extension``. Every PyGithub call in the
process then fails before a single request byte leaves the socket.

The ``gh`` CLI reaches the same API through the same proxy without trouble because
it is written in Go, whose verifier does not impose that extension check. This
module brings PyGithub to the same posture and no further: the certificate chain
and the hostname are both still verified, and only the strict extension checks are
cleared. Verification is never disabled.

The relaxation applies only when a CA bundle environment variable names a real
file, which is how an interception proxy announces itself. On an ordinary network
the strict default stays in force.

Why this module imports ``requests``
------------------------------------
PyGithub drives its HTTP through ``requests``, not ``httpx``: its
``HTTPSRequestsConnectionClass`` builds a ``requests.Session`` and mounts a
``requests.adapters.HTTPAdapter``. Substituting the TLS context means subclassing
that adapter, so this module must speak the same library. It introduces no new HTTP
client of its own. ``backlog_core/sync_state.py`` carries the same exception for the
same reason.
"""

from __future__ import annotations

import os
import pathlib
import ssl
import threading
from typing import TYPE_CHECKING, Final

import requests.adapters
from github import Auth, Github
from github.Requester import HTTPRequestsConnectionClass, HTTPSRequestsConnectionClass, Requester
from urllib3.util.ssl_ import create_urllib3_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from urllib3.poolmanager import PoolManager
    from urllib3.util.retry import Retry

__all__ = [
    "CA_BUNDLE_ENV_VARS",
    "DEFAULT_TIMEOUT",
    "TOKEN_ENV_VARS",
    "MissingGitHubTokenError",
    "install_proxy_tls_support",
    "make_github_client",
    "resolve_ca_bundle",
    "resolve_token",
]

DEFAULT_TIMEOUT: Final = 30
"""Seconds before a GitHub request gives up, when a caller states no preference."""

CA_BUNDLE_ENV_VARS: Final[Sequence[str]] = ("GITHUB_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")
"""CA bundle variables in priority order. The first one naming a real file wins."""

TOKEN_ENV_VARS: Final[Sequence[str]] = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN")
"""Token variables in priority order. The first non-empty one wins."""


class MissingGitHubTokenError(RuntimeError):
    """Raised when no environment variable supplies a GitHub token."""


class _InstallState:
    """Process-wide record of whether the proxy-aware classes are installed.

    PyGithub keeps its connection classes on the Requester class itself, so this
    state is process-wide to match. A class attribute carries it rather than a
    module global, so no function needs a ``global`` statement to update it.
    """

    lock: Final = threading.Lock()
    installed: bool = False


def resolve_token(token: str | None = None) -> str:
    """Return the GitHub token to authenticate with.

    Args:
        token: An explicit token. When given and non-empty, it is returned unchanged.

    Returns:
        The explicit token, or the first non-empty value among TOKEN_ENV_VARS.

    Raises:
        MissingGitHubTokenError: No explicit token, and no environment variable supplies one.
    """
    if token:
        return token
    for env_var in TOKEN_ENV_VARS:
        value = os.environ.get(env_var)
        if value:
            return value
    names = ", ".join(TOKEN_ENV_VARS)
    msg = f"No GitHub token found. Set one of: {names}"
    raise MissingGitHubTokenError(msg)


def resolve_ca_bundle() -> str | None:
    """Return the CA bundle path an interception proxy has configured, if any.

    Returns:
        The first path among CA_BUNDLE_ENV_VARS that names an existing file. None when
        no variable is set, or when every path named is absent from disk.
    """
    for env_var in CA_BUNDLE_ENV_VARS:
        candidate = os.environ.get(env_var)
        if candidate and pathlib.Path(candidate).is_file():
            return candidate
    return None


def _build_ssl_context(ca_bundle: str) -> ssl.SSLContext:
    """Build a context that trusts ca_bundle and skips only the strict extension checks.

    Chain verification and hostname verification both stay on. Clearing
    ``VERIFY_X509_STRICT`` matches what Go-based clients such as ``gh`` already do, and
    is what lets a proxy CA carrying no ``keyUsage`` extension verify.

    Args:
        ca_bundle: Path to the CA bundle the proxy presents its chain against.

    Returns:
        A configured SSLContext.
    """
    context = create_urllib3_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    context.load_verify_locations(cafile=ca_bundle)
    return context


class _ProxyAwareAdapter(requests.adapters.HTTPAdapter):
    """An HTTPAdapter that applies its SSL context on the proxied path as well.

    ``requests`` builds a separate ProxyManager through ``proxy_manager_for`` and does
    not carry the context given to ``init_poolmanager`` into it. Overriding only
    ``init_poolmanager`` therefore leaves every proxied request on the default strict
    context, which is the exact failure this module exists to remove.
    """

    def __init__(
        self,
        ca_bundle: str,
        *,
        pool_connections: int = requests.adapters.DEFAULT_POOLSIZE,
        pool_maxsize: int = requests.adapters.DEFAULT_POOLSIZE,
        max_retries: int | Retry = requests.adapters.DEFAULT_RETRIES,
    ) -> None:
        """Store the bundle before delegating, because the base __init__ builds the pools.

        Args:
            ca_bundle: Path passed to every SSL context this adapter creates.
            pool_connections: Number of connection pools to cache.
            pool_maxsize: Maximum connections to keep in each pool.
            max_retries: Retry policy handed to urllib3.
        """
        self._ca_bundle = ca_bundle
        super().__init__(pool_connections=pool_connections, pool_maxsize=pool_maxsize, max_retries=max_retries)

    def init_poolmanager(
        self, connections: int, maxsize: int, block: bool = requests.adapters.DEFAULT_POOLBLOCK, **pool_kwargs: object
    ) -> None:
        """Attach the context to the direct connection pool.

        Args:
            connections: Number of connection pools to cache.
            maxsize: Maximum connections to keep in each pool.
            block: Whether the pool blocks when it has no free connection.
            **pool_kwargs: Extra pool options, which this override extends with the context.
        """
        pool_kwargs["ssl_context"] = _build_ssl_context(self._ca_bundle)
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: object) -> PoolManager:
        """Attach the context to the proxied connection pool.

        Args:
            proxy: Proxy URL that requests is about to tunnel through.
            **proxy_kwargs: Extra pool options, which this override extends with the context.

        Returns:
            The ProxyManager the base implementation builds.
        """
        proxy_kwargs["ssl_context"] = _build_ssl_context(self._ca_bundle)
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def _make_connection_class(ca_bundle: str) -> type[HTTPSRequestsConnectionClass]:
    """Build the HTTPS connection class PyGithub should use.

    Args:
        ca_bundle: Path passed to every SSL context the class creates.

    Returns:
        A subclass that remounts PyGithub's own session on a proxy-aware adapter.
    """

    class ProxyAwareHTTPSConnection(HTTPSRequestsConnectionClass):
        """PyGithub's HTTPS connection, remounted on a proxy-aware adapter."""

        def __init__(
            self,
            host: str,
            port: int | None = None,
            strict: bool = False,
            timeout: int | None = None,
            retry: int | Retry | None = None,
            pool_size: int | None = None,
            **kwargs: object,
        ) -> None:
            """Replace the adapter that the base class mounted.

            Also pins ``self.verify`` to ``ca_bundle`` when the caller left it unset.
            ``HTTPSRequestsConnectionClass.__init__`` sets ``self.verify =
            kwargs.get("verify", True)``, and ``getresponse`` passes that value
            straight through as ``session.get(url, ..., verify=self.verify, ...)`` on
            every call. Left at PyGithub's own default of ``True``,
            ``requests.Session.merge_environment_settings`` independently re-derives
            its own CA bundle from ``REQUESTS_CA_BUNDLE``/``CURL_CA_BUNDLE`` whenever
            ``verify is True or verify is None`` -- entirely bypassing the bundle
            ``resolve_ca_bundle`` selected and the SSL context ``_ProxyAwareAdapter``
            already built for it below. Pinning ``self.verify`` to the same
            ``ca_bundle`` this module resolved means ``merge_environment_settings``
            sees a concrete path instead of ``True`` and skips its own re-derivation
            entirely -- the only bundle that can reach the handshake is the one
            ``install_proxy_tls_support`` already selected. An explicit ``verify``
            kwarg from the caller still wins.

            Args:
                host: API hostname.
                port: API port, defaulting to 443.
                strict: Retained for signature compatibility with the base class.
                timeout: Seconds before a request gives up.
                retry: Retry policy handed to urllib3.
                pool_size: Connection pool size.
                **kwargs: Extra options the base class reads, such as ``verify``.
            """
            super().__init__(host, port, strict, timeout, retry, pool_size, **kwargs)
            if kwargs.get("verify", True) is True:
                self.verify = ca_bundle
            self.adapter = _ProxyAwareAdapter(
                ca_bundle, max_retries=self.retry, pool_connections=self.pool_size, pool_maxsize=self.pool_size
            )
            self.session.mount("https://", self.adapter)

    return ProxyAwareHTTPSConnection


def install_proxy_tls_support(*, force: bool = False) -> bool:
    """Teach every PyGithub client in this process to trust an interception proxy.

    PyGithub resolves its connection classes on the Requester class, so one call covers
    every ``Github`` instance the process builds, whether built before or after this
    call. The call is idempotent and safe from more than one thread.

    ``Requester.injectConnectionClasses`` also turns off PyGithub's connection reuse,
    because its intended caller is PyGithub's own HTTP-replay test harness. Restoring
    reuse would mean writing to a name-mangled private attribute, and measurement put
    the gain at roughly 3% of per-call wall time (637 ms against 660 ms over 12 calls
    through the proxy), which PyGithub's own 250 ms inter-request delay dominates. The
    reuse therefore stays off, on purpose, and this module stays on public API only.

    Args:
        force: Install again even when a previous call already installed.

    Returns:
        True when the proxy-aware classes are now installed. False when no CA bundle
        variable names a real file, which means no interception proxy is configured and
        PyGithub's own strict default stays in force.
    """
    with _InstallState.lock:
        if _InstallState.installed and not force:
            return True
        ca_bundle = resolve_ca_bundle()
        if ca_bundle is None:
            return False
        Requester.injectConnectionClasses(HTTPRequestsConnectionClass, _make_connection_class(ca_bundle))
        _InstallState.installed = True
        return True


def make_github_client(
    token: str | None = None, *, timeout: int = DEFAULT_TIMEOUT, base_url: str | None = None
) -> Github:
    """Build a PyGithub client that works on a normal network and behind a TLS proxy.

    Prefer this over calling ``Github(...)`` directly, so that TLS handling and token
    lookup stay in one place.

    Args:
        token: An explicit token. When omitted, TOKEN_ENV_VARS supplies one.
        timeout: Seconds before a request gives up.
        base_url: API root. When omitted, GITHUB_API_URL supplies it, and the public API
            is the final fallback.

    Returns:
        A configured Github client.

    Raises:
        MissingGitHubTokenError: No explicit token, and no environment variable supplies one.
    """
    install_proxy_tls_support()
    resolved_base_url = base_url or os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    return Github(auth=Auth.Token(resolve_token(token)), base_url=resolved_base_url, timeout=timeout)
