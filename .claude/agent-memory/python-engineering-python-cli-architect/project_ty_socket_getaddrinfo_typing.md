---
name: project_ty_socket_getaddrinfo_typing
description: ty's actual return type for socket.getaddrinfo is a precise Literal-keyed union, not the flatter typeshed-looking tuple[AddressFamily, SocketKind, ...] shape — verify with reveal_type, not by grepping vendored cache dirs
metadata:
  type: project
---

`socket.getaddrinfo`'s type as resolved by `ty` (0.0.65, verified 2026-07-31) is:

```python
list[
    tuple[Literal[AddressFamily.AF_INET], SocketKind, int, str, tuple[str, int]]
    | tuple[Literal[AddressFamily.AF_INET6], SocketKind, int, str, tuple[str, int, int, int] | tuple[int, bytes]]
]
```

This is the precise per-family-literal union from current upstream typeshed
(`stdlib/socket.pyi` `_GetAddrInfoResult` alias, confirmed against
`raw.githubusercontent.com/python/typeshed/main/stdlib/socket.pyi`), pairing each
`AddressFamily` literal with the exact tuple shape it returns. It is **not** the flatter,
easier-to-guess `list[tuple[AddressFamily, SocketKind, int, str, tuple[str, int] |
tuple[str, int, int, int] | tuple[int, bytes]]]` shape that both `socket.pyi` copies found
in `~/.cache/ty/vendored/typeshed/<hash>/stdlib/socket.pyi` on disk literally display, and
that a naive read of the private `_RetAddress`/`AddressFamily`/`SocketKind` names would
suggest.

**Why**: `ty` ships/resolves a newer typeshed at runtime than the two commit-hash snapshots
that happen to sit in the local `~/.cache/ty/vendored/typeshed/` directory — those on-disk
copies are stale decoys for this purpose. Grepping them for a function's declared type gives
a wrong answer for `getaddrinfo` specifically.

**How to apply**: When annotating a wrapper function whose body returns
`socket.getaddrinfo(...)` (or any stdlib function that might have per-overload/per-literal
precision), do not trust a grep of the vendored typeshed cache or of memory/training data for
the "declared" type. Confirm the actual type `ty` will check against by running a throwaway
`reveal_type(socket.getaddrinfo)` through `ty check` (or the analogous pattern for other
functions) — see [[project_auto_sync_manifests]] for the sibling pattern of verifying seam
contracts against real tool output rather than assumed shapes.

**Where this recurs**: `plugins/development-harness/conftest.py`'s `_guarded_getaddrinfo`
was fixed to this exact type. `plugins/frustration-analyzer/tests/conftest.py` has an
identical `_guarded_getaddrinfo` wrapper that is currently **unannotated** (no return type) —
the moment someone adds a return-type annotation there, they will hit this same trap unless
they use the Literal-keyed union above.
