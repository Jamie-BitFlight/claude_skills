---
name: project-ty-reveal-type-gotchas
description: ty typing gotchas settled by reveal_type — isinstance(x, list) on a T | list[T] union with a non-final 3rd-party T leaves Unknown in the list items; stdlib signatures like socket.getaddrinfo come from ty's own typeshed
metadata:
  type: project
---

Confirm a type with a throwaway `reveal_type(...)` run through `uv run ty check` before
annotating or narrowing against it.

**Narrow on the non-container member.** For `x: T | list[T]` where `T` is a non-`@final`
third-party class (e.g. PyGithub `ContentFile`), `isinstance(x, list)` leaves
`(ContentFile & list[Unknown]) | list[ContentFile]` in the list branch, and each item is `Unknown | ContentFile`. Flip it:

    items = [x] if isinstance(x, ContentFile) else x   # list[ContentFile]

Example: `research/knowledge-explorer.py` `fetch_github_metadata`.

**Stdlib signatures come from ty's own typeshed; `~/.cache/ty/vendored/typeshed/` holds only a few extracted stubs.**
`socket.getaddrinfo` resolves to a per-`AddressFamily`
Literal-keyed union; the annotated wrapper `_guarded_getaddrinfo` in
`plugins/development-harness/conftest.py` has the exact type to copy.
`plugins/frustration-analyzer/tests/conftest.py`'s `_guarded_getaddrinfo` has no return
annotation; reuse that type when you add one.
