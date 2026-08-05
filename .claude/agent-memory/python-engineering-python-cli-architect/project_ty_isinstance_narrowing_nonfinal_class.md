---
name: project-ty-isinstance-narrowing-nonfinal-class
description: ty's isinstance narrowing on a union member checked against a non-final external class produces Top[...] intersection artifacts that widen to object — fix by narrowing on the other union member instead
metadata:
  type: project
---

ty's isinstance narrowing goes wrong when the checked class (`list`, or any builtin/stdlib
container type) is one branch of a union and the other branch is a non-`@final` third-party
class (e.g. PyGithub's `ContentFile`). ty cannot prove the third-party class isn't itself a list
subclass at runtime, so it produces a synthetic intersection type
(`ContentFile & Top[list[Unknown]]`) instead of eliminating that branch. Everything downstream
(`list(x)`, iteration, attribute access) then widens to `object`.

Confirmed via `reveal_type()` probes against `repo.get_contents("")` typed as
`list[ContentFile] | ContentFile` in `research/knowledge-explorer.py`:

```python
items = list(root_contents) if isinstance(root_contents, list) else [root_contents]
# root_contents in the `list` branch reveals as:
#   list[ContentFile] | (ContentFile & Top[list[Unknown]])
# → list(root_contents) widens to list[object]
```

**Fix**: narrow on the *other* union member's concrete class instead of the container type. ty
proves two unrelated nominal classes (`ContentFile` vs `list`) are disjoint far more reliably
than it can rule out an unknown subclass satisfying a builtin container check:

```python
items = [root_contents] if isinstance(root_contents, ContentFile) else root_contents
# reveal_type(items) → list[ContentFile], zero diagnostics
```

Same fix applied at two call sites in `research/knowledge-explorer.py` (`fetch_github_metadata`,
lines ~390 and ~403) — both resolved cleanly with no `# ty: ignore` needed.

**General pattern**: when `isinstance(x, list)` (or any builtin container check) against a
`T | list[T]`-shaped union produces `unresolved-attribute`/`object`-widening diagnostics, try
`isinstance(x, T)` instead and flip the branches. Verify with `reveal_type()` before committing —
see [[project_ty_socket_getaddrinfo_typing]] for the sibling case (stdlib typeshed shape, not
narrowing) and the same reveal_type-first verification discipline.
