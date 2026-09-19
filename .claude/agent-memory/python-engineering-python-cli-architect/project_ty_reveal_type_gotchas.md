---
name: project-ty-reveal-type-gotchas
description: ty typing gotchas settled by reveal_type — isinstance(x, list) on a T | list[T] union with a non-final 3rd-party T widens to object; stdlib signatures like socket.getaddrinfo differ from the on-disk vendored typeshed cache
metadata:
  type: project
---

Confirm a type with a throwaway `reveal_type(...)` run through `uv run ty check` before
annotating or narrowing against it.

**Narrow on the non-container member.** For `x: T | list[T]` where `T` is a non-`@final`
third-party class (e.g. PyGithub `ContentFile`), `isinstance(x, list)` leaves
`T & Top[list[Unknown]]` in the list branch and downstream values widen to `object`. Flip it:

    items = [x] if isinstance(x, ContentFile) else x   # list[ContentFile]

Example: `research/knowledge-explorer.py` `fetch_github_metadata`.

**Stdlib signatures come from ty's resolved typeshed, not `~/.cache/ty/vendored/typeshed/`.**
The cached copies on disk can be older. `socket.getaddrinfo` resolves to a per-`AddressFamily`
Literal-keyed union; the annotated wrapper `_guarded_getaddrinfo` in
`plugins/development-harness/conftest.py` has the exact type to copy.
`plugins/frustration-analyzer/tests/conftest.py`'s `_guarded_getaddrinfo` has no return
annotation; reuse that type when you add one.
