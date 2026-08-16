---
name: dh-content-store-live-verification-pollutes-real-plan-list
description: Live-writing a ContentKind.PLAN record with non-plan content through _GitHubContentsStore against the real repo breaks the live `sam plan list` for everyone until deleted
metadata:
  type: project
---

Writing a live-verification `.dh/content/v1/` record through
`_GitHubContentsStore` (`plugins/development-harness/backlog_core/backends/github_contents.py`)
against the real `Jamie-BitFlight/claude_skills` repo with `kind=ContentKind.PLAN` and
arbitrary string content (e.g. `"live-verification-test"`) is not inert. `sam plan list`
(`sam_schema/sam_plan.py::_backend()` -> `ContentTaskProvider.__init__` ->
`parse_plan_content`) eagerly lists and parses *every* `ContentKind.PLAN` record in the
configured backend on every invocation. A record whose `content` is not valid Plan YAML
raises a Pydantic `ValidationError` and crashes `plan list` for every real caller (verified:
this broke `plugins/development-harness/tests/test_frontend_parity.py::TestParityInfrastructure::test_cli_plan_list_returns_json`,
which spawns a real CLI subprocess against the real repo, until the stray record was deleted).

**Why:** `ContentKind.PLAN` is not a namespace-isolated sandbox — it is the live plan index
the whole repo's SAM tooling reads. There's no test/staging kind.

**How to apply:** When live-verifying content-store behavior (writes, branch redirects, CAS)
against the real repo, either (a) use `ContentKind.ARTIFACT_CONTENT` with a distinct
`artifact_type` instead of `PLAN`/`DISPATCH_PLAN` (kinds that real tooling eagerly parses and
validates), or (b) if `PLAN` must be used for the test, write content that round-trips through
`parse_plan_content` (a minimal valid Plan YAML shape), or (c) delete the record immediately
after the read-back assertion, before any other real invocation of `sam plan list`/`dispatch`
tooling can observe it. Always verify cleanup by re-listing the target path/branch's tree
afterward (`gh api repos/.../git/trees/<branch>?recursive=true`) rather than assuming the
delete call succeeded.

See also [[project_auto_sync_manifests]] for other auto_sync_manifests-adjacent live-repo
gotchas; unrelated system but same "live repo is not a sandbox" lesson.
