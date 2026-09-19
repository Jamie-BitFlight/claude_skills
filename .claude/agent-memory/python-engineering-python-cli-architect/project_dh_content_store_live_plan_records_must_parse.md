---
name: dh-content-store-live-plan-records-must-parse
description: "Every ContentKind.PLAN record in the live backend is parsed when ContentTaskProvider loads, so one non-plan PLAN record crashes every content-store sam plan command for everyone; live-test with ARTIFACT_CONTENT"
metadata:
  type: project
---

`ContentTaskProvider.__init__` (`sam_schema/core/backends/content.py`) lists every `ContentKind.PLAN` record in the configured backend and validates each with `parse_plan_content`. That makes `PLAN` the live plan index, and `ContentKind` has no staging kind. A record whose content is not a valid plan raises (`ValidationError`, or a `ruamel.yaml` error when the text is neither JSON nor YAML) and breaks every content-store `plan` command for every caller: `plan create`, `plan list --limit ...`, and address-based reads.

To live-verify content-store behaviour (writes, CAS) against the real repo, write `ContentKind.ARTIFACT_CONTENT` with a distinct `artifact_type`. If the test must use `PLAN`, write content that `parse_plan_content` accepts and delete the record straight after the read-back. Then re-list the branch tree (`gh api repos/<owner>/<repo>/git/trees/<branch>?recursive=true`) to confirm it is gone.
