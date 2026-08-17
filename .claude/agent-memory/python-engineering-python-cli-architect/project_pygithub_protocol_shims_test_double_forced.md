---
name: project-pygithub-protocol-shims-test-double-forced
description: Why github_contents.py's 5 custom Protocols wrapping PyGithub return types must stay, verified via ty cascade, even though PyGithub does ship real py.typed classes
metadata:
  type: project
---

`plugins/development-harness/backlog_core/backends/github_contents.py` defines 5 Protocols
(`_ContentsFile`, `_Commit`, `_Branch`, `_GitTreeEntry`, `_GitTree`) typing PyGithub API return
values. A prior investigation claimed this was because "PyGithub ships no usable type stubs" —
that premise is **false**: `PyGithub==2.9.0` is PEP 561-compliant
(`importlib.resources.files('github').joinpath('py.typed').exists()` → `True`) and ships real,
correctly-typed classes (`github.ContentFile.ContentFile`, `github.Commit.Commit`,
`github.Branch.Branch`, `github.GitTree.GitTree`, `github.GitTreeElement.GitTreeElement`),
verified via `inspect.signature`.

**But the Protocols are still load-bearing**, for a different reason: PyGithub's real classes
have private, requester-bound constructors only PyGithub itself can call. The test suite's fakes
(`tests/test_github_contents.py`: `_File`, `_FakeCommit`, `_FakeBranch`, `_TreeEntry`, `_Tree` —
plain Pydantic models) satisfy the Protocols' *structural* shape but can never become *nominal*
instances of the concrete PyGithub classes. `ty check` proves this empirically and cascades: swap
one Protocol for its real class → the next Protocol's test double fails
`invalid-argument-type` on `_GitHubContentsStore(lambda: repository)`. Tested the cascade in order
`get_branch`(`Branch`) → `get_contents`(`ContentFile`) → `get_git_tree`(`GitTree`); all five had to
be reverted before `ty check` on both files passed clean again.

`_ContentsFile` additionally needs `@runtime_checkable` because `put()` does
`isinstance(written, _ContentsFile)` at runtime — a real `isinstance(x, ContentFile)` check would
reject every test double at runtime too, not just fail static type-checking.

**Verification method for "is this Protocol still forced?" claims**: don't just run `ty check` on
the source file alone — it will pass since the file's own internal consistency holds. Run it
together with the test file that constructs the fake (`uv run ty check <source>.py
<tests>/test_<source>.py`), and revert Protocols one at a time to see which member fails next
(fail-fast reporting only shows the first mismatch per run).

See PR #2939 for the corrected reasoning committed as an inline comment (code itself unchanged —
all 5 Protocols retained, only the docstring/comment explaining *why* was fixed).
