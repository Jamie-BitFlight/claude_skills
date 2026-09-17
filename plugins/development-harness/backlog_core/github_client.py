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

Loading a custom CA bundle and relaxing VERIFY_X509_STRICT are two independent
decisions, both gated on the bundle adding at least one anchor beyond the public
trust store this process already ships (bundle_adds_new_anchor decides that by
certificate identity, not by the variable's mere presence). A bundle that adds a
*compliant* anchor still has to be loaded: ``requests`` only ever consumes
REQUESTS_CA_BUNDLE and CURL_CA_BUNDLE on its own (see the next section), so
GITHUB_CA_BUNDLE and a lone SSL_CERT_FILE reach GitHub only through the connection
class this module installs — skipping installation for a compliant bundle would
leave those two variables unenforced against a non-standard GITHUB_API_URL, and
verification would fail even though the override is configured correctly. Whether
that same bundle also needs VERIFY_X509_STRICT cleared is judged separately, by
bundle_requires_relaxed_verification, which inspects the added anchors' certificate
shape (a missing or non-critical extension). Nix and conda export these same
variables on an ordinary network, pointed at an unmodified copy of the public
roots; treating that presence alone as proxy evidence would install a redundant
connection class and drop PyGithub's connection reuse for every session on such a
machine, whether or not a proxy is actually there. On an ordinary network, once
judged this way — no new anchor at all — nothing installs and the strict default
stays in force.

Why CA_BUNDLE_ENV_VARS checks REQUESTS_CA_BUNDLE before SSL_CERT_FILE
-----------------------------------------------------------------------
The bundle this module judges has to be the same bundle ``requests`` itself will
actually verify against, or the judgment and the connection disagree: judging the
wrong file lets ``install_proxy_tls_support`` decide no proxy is present while
PyGithub's underlying ``requests.Session`` still connects through one under the
strict default. ``requests.Session.merge_environment_settings`` resolves an unset
``verify`` to ``os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE")
or verify`` (confirmed by reading ``requests/sessions.py`` in this repository's own
``.venv``, ``requests==2.33.1``), so ``REQUESTS_CA_BUNDLE`` outranks ``CURL_CA_BUNDLE``
there — and neither that function nor ``HTTPAdapter.cert_verify`` in
``requests/adapters.py`` ever reads ``SSL_CERT_FILE``: a bare ``verify=True`` falls
through to ``requests.utils.DEFAULT_CA_BUNDLE_PATH`` (certifi's bundle), not to
OpenSSL's own ``SSL_CERT_FILE``-aware default-verify-paths lookup. A Nix or conda
shell that exports stock roots through ``SSL_CERT_FILE`` while a proxy supplies its
deficient CA through ``REQUESTS_CA_BUNDLE`` therefore needs ``REQUESTS_CA_BUNDLE``
judged first, or the stock file wins the old first-match order, the deficient CA
never gets evaluated, and PyGithub keeps ``VERIFY_X509_STRICT`` while ``requests``
verifies the live connection against the deficient bundle anyway. ``SSL_CERT_FILE``
stays in the tuple, last, only because some environments set it alone with neither
``REQUESTS_CA_BUNDLE`` nor ``CURL_CA_BUNDLE`` present. ``GITHUB_CA_BUNDLE`` stays
first as this module's own explicit override, independent of what ``requests`` would
resolve unprompted.

Why a CA bundle variable may also name a directory
-----------------------------------------------------
``requests.adapters.HTTPAdapter.cert_verify`` (same file cited above) branches on
``os.path.isdir(cert_loc)``: a directory is handed to urllib3 as ``conn.ca_cert_dir``,
which OpenSSL consults lazily, through ``SSLContext.load_verify_locations(capath=...)``,
at verification time rather than eagerly loading every entry the way a single-file
``cafile`` bundle is loaded (confirmed empirically: ``SSLContext.get_ca_certs()``
returns an empty list immediately after a ``capath`` load, even though the
certificate it points at verifies a real handshake). That directory shape is the
OpenSSL ``c_rehash``/``openssl rehash`` layout: one certificate per file, named
``<8-hex-digit-subject-hash>.<n>``. A caller whose interception proxy or private
GitHub Enterprise install ships its trust anchors that way, rather than as one
concatenated PEM file, needs the same detection and loading this module already
gives a single bundle file — resolve_ca_bundle accepts either shape, and
_build_ssl_context loads a directory through ``capath`` instead of ``cafile``.

Why a missing SubjectKeyIdentifier also forces relaxation
-------------------------------------------------------------
OpenSSL 3.0 added a fourth ``X509_V_FLAG_X509_STRICT`` check beyond the three this
module already mirrored: a CA certificate with no ``SubjectKeyIdentifier`` extension
now fails with verify code 86, ``X509_V_ERR_MISSING_SUBJECT_KEY_IDENTIFIER``
(``check_extensions()`` in ``crypto/x509/x509_vfy.c``, gated the same way as the
``keyUsage``/``basicConstraints`` checks on ``ctx->param->flags &
X509_V_FLAG_X509_STRICT``; confirmed against the current ``openssl/openssl`` header
and source, and against `openssl/openssl#13283
<https://github.com/openssl/openssl/issues/13283>`_, which documents that OpenSSL
1.1.1 accepted a CA cert missing this extension even under ``-x509_strict`` and 3.0
stopped accepting it). A custom CA that predates this stricter check — carrying a
critical ``basicConstraints`` and a ``keyUsage`` extension, the two properties the
pre-existing checks already require, but no ``SubjectKeyIdentifier`` — passed both of
this module's prior checks and kept ``VERIFY_X509_STRICT`` enabled, failing every
connection through that CA on Python 3.13/OpenSSL 3 with the same verify code.
``_cert_fails_strict_checks`` now tests for this extension the same way it tests for
the other two.

Why a TRUSTED CERTIFICATE PEM block still counts as an anchor
-------------------------------------------------------------
OpenSSL's ``x509 -trustout``/``-addtrust`` writes a non-standard, OpenSSL-specific PEM
variant: the block is labeled ``BEGIN/END TRUSTED CERTIFICATE`` instead of
``BEGIN/END CERTIFICATE``, and — critically — the base64 body itself decodes to more
than a certificate. ``d2i_X509_AUX``/``i2d_X509_AUX`` (see ``x_x509a.c`` and the
``d2i_X509`` manual page's description of the ``_AUX`` variants) encode the ordinary
X.509 certificate DER immediately followed, in the same blob, by a second top-level
DER ``SEQUENCE`` carrying trust/reject key-usage OIDs and an optional alias. Verified
empirically in this session: converting a certificate with ``openssl x509 -in
test.crt -addtrust serverAuth -out test-trusted.pem`` grows the decoded body by
exactly the bytes of that trailing ``SEQUENCE`` (14 bytes, for one trust OID), with
the leading bytes identical to the untrusted certificate's own DER. ``SSLContext.
load_verify_locations()`` loads this file without complaint — OpenSSL's own
``PEM_read_bio_X509_AUX`` understands the format — but ``cryptography``'s
``load_pem_x509_certificate(s)`` only recognizes the plain ``CERTIFICATE`` label and,
even once that label is substituted, its ASN.1 parser rejects the trailing
``SEQUENCE`` as extra data (also verified empirically in this session; substituting
just the label is a workaround reported to succeed in `pyca/cryptography#4794
<https://github.com/pyca/cryptography/issues/4794>`_ for a certificate carrying no
such trailer, but it does not hold once one is present). ``load_pem_x509_certificates``
(plural) additionally raises for the *entire* input the instant one block fails to
parse, so a single ``TRUSTED CERTIFICATE`` block anywhere in an otherwise compliant
bundle previously made every other certificate in that bundle disappear too, not only
the one in the incompatible block. ``_parse_pem_certificate_blocks`` locates each PEM
block by hand instead of delegating to that function, decodes a ``TRUSTED
CERTIFICATE`` block's body, and discards everything past the leading DER ``SEQUENCE``
(``_strip_trusted_certificate_trailer``) before handing the remainder to
``load_der_x509_certificate`` — so a bundle in this format is parsed, not silently
treated as holding zero certificates.

Why this module imports ``requests``
------------------------------------
PyGithub drives its HTTP through ``requests``, not ``httpx``: its
``HTTPSRequestsConnectionClass`` builds a ``requests.Session`` and mounts a
``requests.adapters.HTTPAdapter``. Substituting the TLS context means subclassing
that adapter, so this module must speak the same library. It introduces no new HTTP
client of its own. ``backlog_core/sync_state.py`` carries the same exception for the
same reason.

Why this module imports ``cryptography`` and ``certifi``
----------------------------------------------------------
Deciding whether a bundle actually needs the relaxation means parsing the
certificates it adds and inspecting their extensions, which only a certificate
library provides — ``ssl``/urllib3 load and use anchors but expose no extension
introspection. ``cryptography`` is not an incidental choice: PyGithub already
requires ``pyjwt[crypto]`` for its own auth, which pulls it in unconditionally, so
this adds no new dependency either. ``certifi`` is the baseline a bundle is compared
against, and ``requests`` — already a hard dependency for the reason above — pulls
that in the same way.
"""

from __future__ import annotations

import base64
import binascii
import os
import pathlib
import re
import ssl
import sys
import threading
from typing import TYPE_CHECKING, Final

import certifi
import requests.adapters
from cryptography import x509
from cryptography.hazmat.primitives import hashes
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
    "bundle_adds_new_anchor",
    "bundle_requires_relaxed_verification",
    "install_proxy_tls_support",
    "make_github_client",
    "resolve_ca_bundle",
    "resolve_token",
]

DEFAULT_TIMEOUT: Final = 30
"""Seconds before a GitHub request gives up, when a caller states no preference."""

CA_BUNDLE_ENV_VARS: Final[Sequence[str]] = ("GITHUB_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE")
"""CA bundle variables in priority order. The first one naming a real file or an
OpenSSL-hashed CA directory wins.

See the module docstring's "Why CA_BUNDLE_ENV_VARS checks REQUESTS_CA_BUNDLE before
SSL_CERT_FILE" section: this order matches the bundle ``requests`` itself resolves,
not an arbitrary preference.
"""

TOKEN_ENV_VARS: Final[Sequence[str]] = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN")
"""Token variables in priority order. The first non-empty one wins."""

_OPENSSL_HASH_FILENAME: Final = re.compile(r"^[0-9a-f]{8}\.\d+$")
"""Filename shape ``c_rehash``/``openssl rehash`` produces inside a CA directory.

See the module docstring's "Why a CA bundle variable may also name a directory"
section.
"""

_PEM_CERTIFICATE_BLOCK: Final = re.compile(
    rb"-----BEGIN (?P<label>(?:TRUSTED )?CERTIFICATE)-----(?P<body>.*?)-----END (?P=label)-----", re.DOTALL
)
"""Matches one PEM certificate block, capturing the optional ``TRUSTED`` prefix.

See the module docstring's "Why a TRUSTED CERTIFICATE PEM block still counts as an
anchor" section: ``cryptography.x509.load_pem_x509_certificates`` accepts only the
plain ``CERTIFICATE`` label, and even a relabeled ``TRUSTED CERTIFICATE`` block still
fails that function's stricter DER parsing — so each block is located and decoded by
hand instead of delegating to it.
"""

_DER_SEQUENCE_TAG: Final = 0x30
"""ASN.1 universal tag for SEQUENCE, the DER construct every X.509 certificate (and
OpenSSL's appended X509_CERT_AUX trailer) begins with.
"""

_DER_SHORT_FORM_LENGTH_LIMIT: Final = 0x80
"""Below this value, a DER length octet encodes its content length directly (X.690
section 8.1.3.4's "short form"); at or above it, the low seven bits count how many
following octets hold the length instead ("long form").
"""

_DER_MINIMUM_TLV_HEADER_LENGTH: Final = 2
"""Smallest possible DER tag-length header: one tag octet, one length octet."""


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


def _is_openssl_hashed_ca_directory(path: pathlib.Path) -> bool:
    """Whether path is a directory in the OpenSSL ``c_rehash`` layout requests accepts.

    Args:
        path: Candidate directory.

    Returns:
        True when path is a directory holding at least one hash-named entry (eight
        lowercase hex digits, a dot, and a numeric suffix — the shape ``c_rehash``/
        ``openssl rehash`` produces, and the shape ``requests.adapters.HTTPAdapter.
        cert_verify`` hands to urllib3 as ``conn.ca_cert_dir``). False for a plain
        file, a directory with no such entry, or a path this process cannot list.
    """
    if not path.is_dir():
        return False
    try:
        return any(_OPENSSL_HASH_FILENAME.match(entry.name) for entry in path.iterdir())
    except OSError:
        return False


def resolve_ca_bundle() -> str | None:
    """Return the CA bundle path an interception proxy has configured, if any.

    Returns:
        The first path among CA_BUNDLE_ENV_VARS that names an existing file, or an
        OpenSSL-hashed CA directory (see the module docstring's "Why a CA bundle
        variable may also name a directory" section). None when no variable is set,
        or when every path named is neither.
    """
    for env_var in CA_BUNDLE_ENV_VARS:
        candidate = os.environ.get(env_var)
        if not candidate:
            continue
        path = pathlib.Path(candidate)
        if path.is_file() or _is_openssl_hashed_ca_directory(path):
            return candidate
    return None


def _cert_fails_strict_checks(cert: x509.Certificate) -> bool:
    """Report whether cert has the shape ``VERIFY_X509_STRICT`` rejects as a CA anchor.

    Mirrors the four OpenSSL strict-mode checks this module exists to work around: a
    missing ``keyUsage`` extension (verify code 92), a missing ``basicConstraints``
    extension (verify code 79), one present but not marked critical (verify code 89),
    and a missing ``SubjectKeyIdentifier`` extension (verify code 86 — see the module
    docstring's "Why a missing SubjectKeyIdentifier also forces relaxation" section).

    Args:
        cert: A parsed certificate to test.

    Returns:
        True when strict verification would reject cert as a trust anchor.
    """
    try:
        cert.extensions.get_extension_for_class(x509.KeyUsage)
    except x509.ExtensionNotFound:
        return True
    try:
        basic_constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints)
    except x509.ExtensionNotFound:
        return True
    if not basic_constraints.critical:
        return True
    try:
        cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
    except x509.ExtensionNotFound:
        return True
    return False


def _der_sequence_length(data: bytes) -> int | None:
    """Length in bytes of the leading DER SEQUENCE TLV that data begins with.

    Reads a definite-length BER/DER header (the only form DER permits) by hand: X.509
    never uses indefinite-length encoding, so a two-branch definite-length reader is
    sufficient. Used to find where a ``TRUSTED CERTIFICATE`` block's own X.509
    certificate ends and OpenSSL's appended trust-info ``SEQUENCE`` begins — see the
    module docstring's "Why a TRUSTED CERTIFICATE PEM block still counts as an anchor"
    section.

    Args:
        data: DER-encoded bytes expected to begin with a SEQUENCE tag (0x30).

    Returns:
        The total byte length of the tag, length, and content octets of the leading
        SEQUENCE in data (its self-contained TLV size), or None when data does not
        begin with a SEQUENCE tag, its length encoding is truncated, or the declared
        content length runs past the end of data.
    """
    if len(data) < _DER_MINIMUM_TLV_HEADER_LENGTH or data[0] != _DER_SEQUENCE_TAG:
        return None
    first_length_byte = data[1]
    if first_length_byte < _DER_SHORT_FORM_LENGTH_LIMIT:
        content_length = first_length_byte
        header_length = _DER_MINIMUM_TLV_HEADER_LENGTH
    else:
        length_octet_count = first_length_byte & 0x7F
        header_length = _DER_MINIMUM_TLV_HEADER_LENGTH + length_octet_count
        if length_octet_count == 0 or len(data) < header_length:
            return None
        content_length = int.from_bytes(data[2:header_length], "big")
    total_length = header_length + content_length
    return total_length if total_length <= len(data) else None


def _strip_trusted_certificate_trailer(der: bytes) -> bytes | None:
    """Return just the X.509 certificate TLV from a decoded TRUSTED CERTIFICATE body.

    OpenSSL's ``d2i_X509_AUX``/``i2d_X509_AUX`` format (see the module docstring's
    "Why a TRUSTED CERTIFICATE PEM block still counts as an anchor" section) is the
    ordinary X.509 certificate DER immediately followed, in the same blob, by a second
    top-level ``SEQUENCE`` carrying trust/reject OIDs and an optional alias.
    ``cryptography``'s parser rejects that trailing ``SEQUENCE`` as extra data, so it
    is located and discarded here, leaving only the bytes an ordinary DER certificate
    parser accepts.

    Args:
        der: Base64-decoded body of a ``BEGIN TRUSTED CERTIFICATE`` PEM block.

    Returns:
        Just the leading certificate TLV, or None when der does not begin with a
        well-formed DER SEQUENCE (see ``_der_sequence_length``).
    """
    length = _der_sequence_length(der)
    return der[:length] if length is not None else None


def _parse_pem_certificate_blocks(data: bytes) -> list[x509.Certificate]:
    """Parse every certificate PEM block in data, including TRUSTED CERTIFICATE blocks.

    ``x509.load_pem_x509_certificates`` raises ``ValueError`` for the *entire* input
    the instant one block fails to parse — its own documented behavior — so a single
    ``BEGIN TRUSTED CERTIFICATE`` block anywhere in an otherwise compliant bundle would
    make every other certificate in that bundle disappear too. This function parses
    each block independently instead, so one incompatible or malformed block costs
    only itself. See the module docstring's "Why a TRUSTED CERTIFICATE PEM block still
    counts as an anchor" section.

    Args:
        data: Raw bytes of a PEM file, or one hash-named entry in an OpenSSL CA
            directory.

    Returns:
        Every certificate this function could parse from an individual ``CERTIFICATE``
        or ``TRUSTED CERTIFICATE`` block. A block whose body cannot be base64-decoded,
        whose ``TRUSTED CERTIFICATE`` trailer cannot be located, or whose resulting DER
        is not a valid certificate contributes nothing and does not stop the rest from
        being parsed.
    """
    certificates: list[x509.Certificate] = []
    for match in _PEM_CERTIFICATE_BLOCK.finditer(data):
        try:
            der = base64.b64decode(match["body"], validate=False)
        except binascii.Error:
            continue
        if match["label"] == b"TRUSTED CERTIFICATE":
            stripped = _strip_trusted_certificate_trailer(der)
            if stripped is None:
                continue
            der = stripped
        try:
            certificates.append(x509.load_der_x509_certificate(der))
        except ValueError:
            continue
    return certificates


def _load_certificates(ca_bundle: str) -> list[x509.Certificate]:
    """Parse every certificate ca_bundle supplies, whether a file or a hashed directory.

    Args:
        ca_bundle: Path to a PEM-encoded CA bundle file, or an OpenSSL-hashed CA
            directory (see the module docstring's "Why a CA bundle variable may also
            name a directory" section).

    Returns:
        Every certificate ca_bundle holds. Empty when ca_bundle cannot be read, holds
        no certificates, or (for a directory) has no readable hash-named entry.
    """
    path = pathlib.Path(ca_bundle)
    if path.is_dir():
        certificates: list[x509.Certificate] = []
        for entry in sorted(path.iterdir()):
            if not _OPENSSL_HASH_FILENAME.match(entry.name):
                continue
            try:
                certificates.extend(_parse_pem_certificate_blocks(entry.read_bytes()))
            except OSError:
                continue
        return certificates
    try:
        return _parse_pem_certificate_blocks(path.read_bytes())
    except OSError:
        return []


def _new_anchors(ca_bundle: str) -> list[x509.Certificate]:
    """Certificates ca_bundle supplies that the baseline trust store does not already carry.

    Args:
        ca_bundle: Path to a PEM-encoded CA bundle file, or an OpenSSL-hashed CA directory.

    Returns:
        Every certificate in ca_bundle whose SHA-256 fingerprint is absent from
        certifi's bundle — the store ``requests``, a hard dependency, already ships.
    """
    candidate_certs = _load_certificates(ca_bundle)
    if not candidate_certs:
        return []
    try:
        baseline_certs = _parse_pem_certificate_blocks(pathlib.Path(certifi.where()).read_bytes())
    except OSError:
        baseline_certs = []
    baseline_fingerprints = {cert.fingerprint(hashes.SHA256()) for cert in baseline_certs}
    return [cert for cert in candidate_certs if cert.fingerprint(hashes.SHA256()) not in baseline_fingerprints]


def bundle_adds_new_anchor(ca_bundle: str) -> bool:
    """Decide whether ca_bundle supplies any certificate the baseline trust store lacks.

    This is the gate for loading ca_bundle at all, independent of whether what it adds
    also needs VERIFY_X509_STRICT cleared — bundle_requires_relaxed_verification
    decides that separately. ``requests`` never consumes GITHUB_CA_BUNDLE or a lone
    SSL_CERT_FILE on its own (see the module docstring), so a *compliant* custom CA
    named by either still has to be loaded through the connection class this module
    installs, or a non-standard GITHUB_API_URL fails verification despite the override
    being configured correctly.

    Args:
        ca_bundle: Path to a PEM-encoded CA bundle file, or an OpenSSL-hashed CA directory.

    Returns:
        True when ca_bundle holds at least one certificate absent from the baseline
        store. False when ca_bundle cannot be read, holds no certificates, or every
        certificate it holds already appears in the baseline store — the shape Nix and
        conda hand these variables on an ordinary network.
    """
    return bool(_new_anchors(ca_bundle))


def bundle_requires_relaxed_verification(ca_bundle: str) -> bool:
    """Decide whether ca_bundle adds an anchor that VERIFY_X509_STRICT would reject.

    A bundle is judged by what it adds beyond the public trust store this process
    already ships (certifi, which requests — already a hard dependency — pulls in):
    that store itself carries a small number of certificates that fail these checks in
    isolation, so scanning every certificate in a full bundle would flag an unmodified
    copy of the public roots, which Nix and conda hand these variables on an ordinary
    network. Only a certificate genuinely new to the bundle can be the interception
    proxy's own CA, so only those are tested. This is independent of whether ca_bundle
    should be loaded at all — bundle_adds_new_anchor decides that, and a compliant
    added anchor still needs loading even though it does not need this relaxation.

    Args:
        ca_bundle: Path to a PEM-encoded CA bundle file, or an OpenSSL-hashed CA directory.

    Returns:
        True when at least one certificate in ca_bundle, absent from the baseline
        store, fails the checks in ``_cert_fails_strict_checks``. False when ca_bundle
        cannot be read or parsed, holds no certificates, or every added certificate
        passes those checks.
    """
    return any(_cert_fails_strict_checks(cert) for cert in _new_anchors(ca_bundle))


def _build_ssl_context(ca_bundle: str, *, relax_strict: bool) -> ssl.SSLContext:
    """Build a context that trusts ca_bundle, clearing strict checks only when asked.

    Loading ca_bundle and clearing ``VERIFY_X509_STRICT`` are independent decisions
    (see the module docstring): a compliant custom CA still has to be loaded so a
    non-standard GITHUB_API_URL verifies at all, even when its certificate shape needs
    no relaxation. Chain verification and hostname verification both stay on
    regardless of relax_strict. Clearing the flag, when asked, matches what Go-based
    clients such as ``gh`` already do, and is what lets a proxy CA carrying no
    ``keyUsage`` extension verify.

    Args:
        ca_bundle: Path to the CA bundle file, or OpenSSL-hashed CA directory, the
            proxy (or a private GitHub Enterprise install) presents its chain against.
        relax_strict: Whether to clear ``ssl.VERIFY_X509_STRICT``. True only when
            bundle_requires_relaxed_verification judged ca_bundle to add an anchor
            that flag would reject.

    Returns:
        A configured SSLContext.
    """
    context = create_urllib3_context()
    if relax_strict:
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    elif sys.version_info >= (3, 13):
        # Match urllib3's unpatched default even when a pre-import compatibility
        # shim replaced create_urllib3_context with a relaxing wrapper.
        context.verify_flags |= ssl.VERIFY_X509_STRICT
    if pathlib.Path(ca_bundle).is_dir():
        context.load_verify_locations(capath=ca_bundle)
    else:
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
        relax_strict: bool,
        pool_connections: int = requests.adapters.DEFAULT_POOLSIZE,
        pool_maxsize: int = requests.adapters.DEFAULT_POOLSIZE,
        max_retries: int | Retry = requests.adapters.DEFAULT_RETRIES,
    ) -> None:
        """Store the bundle before delegating, because the base __init__ builds the pools.

        Args:
            ca_bundle: Path passed to every SSL context this adapter creates.
            relax_strict: Whether every SSL context this adapter creates should clear
                ``ssl.VERIFY_X509_STRICT``.
            pool_connections: Number of connection pools to cache.
            pool_maxsize: Maximum connections to keep in each pool.
            max_retries: Retry policy handed to urllib3.
        """
        self._ca_bundle = ca_bundle
        self._relax_strict = relax_strict
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
        pool_kwargs["ssl_context"] = _build_ssl_context(self._ca_bundle, relax_strict=self._relax_strict)
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: object) -> PoolManager:
        """Attach the context to the proxied connection pool.

        Args:
            proxy: Proxy URL that requests is about to tunnel through.
            **proxy_kwargs: Extra pool options, which this override extends with the context.

        Returns:
            The ProxyManager the base implementation builds.
        """
        proxy_kwargs["ssl_context"] = _build_ssl_context(self._ca_bundle, relax_strict=self._relax_strict)
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def _make_connection_class(ca_bundle: str, *, relax_strict: bool) -> type[HTTPSRequestsConnectionClass]:
    """Build the HTTPS connection class PyGithub should use.

    Args:
        ca_bundle: Path passed to every SSL context the class creates.
        relax_strict: Whether every SSL context the class creates should clear
            ``ssl.VERIFY_X509_STRICT``.

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
                ca_bundle,
                relax_strict=relax_strict,
                max_retries=self.retry,
                pool_connections=self.pool_size,
                pool_maxsize=self.pool_size,
            )
            self.session.mount("https://", self.adapter)

    return ProxyAwareHTTPSConnection


def install_proxy_tls_support(*, force: bool = False) -> bool:
    """Teach every PyGithub client in this process to trust a custom CA bundle.

    PyGithub resolves its connection classes on the Requester class, so a call made
    before any ``Github`` instance is built covers every instance built afterward.
    This is **not** retroactive, though: ``Requester.__init__`` copies the connection
    class onto the instance at construction time, so a client already built when this
    call runs keeps the class it captured for its whole life, and no later call
    reaches it. Call this (or use ``make_github_client``, which always does) before
    building a client, never after. The call itself is idempotent and safe from more
    than one thread.

    Loading ca_bundle and clearing VERIFY_X509_STRICT are independent decisions (see
    the module docstring): ``bundle_adds_new_anchor`` gates installation itself, and
    ``bundle_requires_relaxed_verification`` — checked only once installation is
    already warranted — gates the strict-mode relaxation within it.

    ``Requester.injectConnectionClasses`` also turns off PyGithub's connection reuse,
    because its intended caller is PyGithub's own HTTP-replay test harness. Restoring
    reuse would mean writing to a name-mangled private attribute, and measurement put
    the gain at roughly 3% of per-call wall time (637 ms against 660 ms over 12 calls
    through the proxy), which PyGithub's own 250 ms inter-request delay dominates. The
    reuse therefore stays off, on purpose, and this module stays on public API only.

    Args:
        force: Re-evaluate and install (or uninstall) again even when a previous call
            already decided. Without it, a previous installed=True short-circuits, so a
            bundle that starts, stops, or changes needing installation or relaxation
            after the first call is picked up only when this is set.

    Returns:
        True when ca_bundle now supplies at least one certificate absent from the
        baseline trust store — that certificate is loaded through the substituted
        connection class regardless of whether it also needs VERIFY_X509_STRICT
        cleared. False when no CA bundle variable names a real file or OpenSSL-hashed
        directory, or the one named adds nothing beyond the baseline store — in both
        cases no custom trust is judged necessary, PyGithub's own defaults and
        connection reuse stay in force, and (under force) a previous install is undone.
    """
    with _InstallState.lock:
        if _InstallState.installed and not force:
            return True
        ca_bundle = resolve_ca_bundle()
        if ca_bundle is None or not bundle_adds_new_anchor(ca_bundle):
            if _InstallState.installed:
                Requester.injectConnectionClasses(HTTPRequestsConnectionClass, HTTPSRequestsConnectionClass)
                _InstallState.installed = False
            return False
        relax_strict = bundle_requires_relaxed_verification(ca_bundle)
        Requester.injectConnectionClasses(
            HTTPRequestsConnectionClass, _make_connection_class(ca_bundle, relax_strict=relax_strict)
        )
        _InstallState.installed = True
        return True


def make_github_client(
    token: str | None = None, *, timeout: int = DEFAULT_TIMEOUT, base_url: str | None = None
) -> Github:
    """Build a PyGithub client that works on a normal network and behind a TLS proxy.

    Prefer this over calling ``Github(...)`` directly, so that TLS handling and token
    lookup stay in one place. Calls ``install_proxy_tls_support`` before constructing
    the client on every call, not only the first: that function's own installation is
    not retroactive (see its docstring), so a client built here always needs its own
    fresh install to precede its own construction.

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
