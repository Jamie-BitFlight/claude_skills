"""TLS compatibility shim: runs before any ``urllib3``-importing module.

CPython 3.13 changed ``ssl.create_default_context()`` to set
``ssl.VERIFY_X509_STRICT`` by default; 3.11 and 3.12 do not. ``urllib3``
(used internally by both ``requests`` and PyGithub) inherits that default
when it builds its own ``SSLContext`` via ``create_urllib3_context()``. In
sandboxes whose TLS-terminating proxy issues a CA certificate lacking a
``keyUsage`` extension, that stricter check rejects the chain with
"CA cert does not include key usage extension" -- a failure that does not
occur under 3.11/3.12, nor with curl or Node's TLS stack, none of which
enforce this extra RFC 5280 check by default.

``relax_verify_x509_strict()`` clears that one flag from every ``SSLContext``
``urllib3`` builds, restoring parity with 3.11/3.12. It leaves
``verify_mode`` (``CERT_REQUIRED`` stays on) and hostname checking
untouched -- certificate verification still happens, just without this one
additional check. It is a no-op on Python <3.13, where the flag was never
set by default. Both scripts that import this module already depend on
PyGithub, which pulls in ``urllib3`` transitively, so importing it here
unconditionally adds no new dependency.

Must run before any ``backlog_core``/``github``/``requests`` import:
``urllib3.connection`` binds ``create_urllib3_context`` via
``from .util.ssl_ import create_urllib3_context`` at import time, so
patching the source after that binding has already been made would not
reach code using the already-bound reference. Both bindings are patched
here for that reason.
"""

from __future__ import annotations

import ssl
import sys

import urllib3.connection
import urllib3.util.ssl_


def relax_verify_x509_strict() -> None:
    """Clear ssl.VERIFY_X509_STRICT from every SSLContext urllib3 builds."""
    if sys.version_info < (3, 13):
        return

    original_create_urllib3_context = urllib3.util.ssl_.create_urllib3_context

    def _create_urllib3_context_no_strict(*args: object, **kwargs: object) -> ssl.SSLContext:
        context = original_create_urllib3_context(*args, **kwargs)  # type: ignore[arg-type]
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        return context

    urllib3.util.ssl_.create_urllib3_context = _create_urllib3_context_no_strict
    if hasattr(urllib3.connection, "create_urllib3_context"):
        urllib3.connection.create_urllib3_context = _create_urllib3_context_no_strict
