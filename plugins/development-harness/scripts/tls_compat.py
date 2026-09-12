"""TLS compatibility shim: runs before any ``urllib3``/``httpx``-importing module.

CPython 3.13 changed ``ssl.create_default_context()`` to set
``ssl.VERIFY_X509_STRICT`` by default; 3.11 and 3.12 do not. ``urllib3``
(used internally by both ``requests`` and PyGithub) deliberately mirrors
that default on 3.13+ even though it builds its own ``SSLContext`` via
``SSLContext(PROTOCOL_TLS_CLIENT)`` rather than calling
``create_default_context()`` (see urllib3's own ``util/ssl_.py``, which
sets ``VERIFY_X509_STRICT`` explicitly under a ``sys.version_info >= (3, 13)``
guard to match it). ``httpx`` calls ``ssl.create_default_context()``
directly, so it inherits the interpreter's own default. In sandboxes whose
TLS-terminating proxy issues a CA certificate lacking a ``keyUsage``
extension, that stricter check rejects the chain with "CA cert does not
include key usage extension" -- a failure that does not occur under
3.11/3.12, nor with curl or Node's TLS stack, none of which enforce this
extra RFC 5280 check by default.

``relax_verify_x509_strict()`` clears that one flag from every ``SSLContext``
built by ``ssl.create_default_context()`` (covers ``httpx`` and anything
else using the standard path) and by ``urllib3``'s own context builder
(covers ``requests``/PyGithub), restoring parity with 3.11/3.12. It leaves
``verify_mode`` (``CERT_REQUIRED`` stays on) and hostname checking
untouched -- certificate verification still happens, just without this one
additional check. It is a no-op on Python <3.13, where the flag was never
set by default. Every script that imports this module already depends on
PyGithub, which pulls in ``urllib3`` transitively, so importing it here
unconditionally adds no new dependency.

Must run before any ``backlog_core``/``github``/``requests``/``httpx``
import: ``urllib3.connection`` binds ``create_urllib3_context`` via
``from .util.ssl_ import create_urllib3_context`` at import time, so
patching the source after that binding has already been made would not
reach code using the already-bound reference. Both bindings are patched
here for that reason; ``ssl.create_default_context`` is looked up via
qualified attribute access at call time by both ``httpx`` and the stdlib,
so patching the ``ssl`` module attribute alone is sufficient there.
"""

from __future__ import annotations

import ssl
import sys

import urllib3.connection
import urllib3.util.ssl_


def relax_verify_x509_strict() -> None:
    """Clear ssl.VERIFY_X509_STRICT from every SSLContext urllib3/httpx builds."""
    if sys.version_info < (3, 13):
        return

    def _without_strict(context: ssl.SSLContext) -> ssl.SSLContext:
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        return context

    original_create_default_context = ssl.create_default_context

    def _create_default_context_no_strict(*args: object, **kwargs: object) -> ssl.SSLContext:
        return _without_strict(original_create_default_context(*args, **kwargs))  # type: ignore[arg-type]

    ssl.create_default_context = _create_default_context_no_strict

    original_create_urllib3_context = urllib3.util.ssl_.create_urllib3_context

    def _create_urllib3_context_no_strict(*args: object, **kwargs: object) -> ssl.SSLContext:
        return _without_strict(original_create_urllib3_context(*args, **kwargs))  # type: ignore[arg-type]

    urllib3.util.ssl_.create_urllib3_context = _create_urllib3_context_no_strict
    if hasattr(urllib3.connection, "create_urllib3_context"):
        urllib3.connection.create_urllib3_context = _create_urllib3_context_no_strict
