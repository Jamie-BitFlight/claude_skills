"""Compatibility import surface for the dependency-neutral GitHub client factory."""

from __future__ import annotations

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

__all__ = [
    "CA_BUNDLE_ENV_VARS",
    "DEFAULT_TIMEOUT",
    "TOKEN_ENV_VARS",
    "InstallState",
    "MissingGitHubTokenError",
    "build_ssl_context",
    "install_proxy_tls_support",
    "make_connection_class",
    "make_github_client",
    "resolve_ca_bundle",
    "resolve_token",
]
