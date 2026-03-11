---
name: 'backlog CLI: deduplicate ~25 functions/constants already in backlog_core'
description: 'The CLI script `backlog.py` retains full duplicates of ~15 functions and ~10 constants that now have canonical implementations in `backlog_core/` (models.py, parsing.py, github.py). The CLI imports `backlog_core.operations` but then re-implements everything locally with untyped dicts.\n\nDuplicated items include: `_title_to_slug`, `_infer_type`, `_parse_backlog_from_directory`, `_parse_item_file`, `find_item`, `_normalize_issue_title`, `_find_fuzzy_duplicates`, `build_issue_body`, `create_issue_for_item`, `_today`, `_now_iso`, `_update_item_metadata`, plus constants BACKLOG_DIR, DEFAULT_REPO, SECTION_RE, SKIP_STATUS, TYPE_TO_LABEL, ROLE_MAP, BENEFIT_MAP.\n\nThe CLI should be a thin wrapper delegating to backlog_core, converting between typed models and CLI display at the boundary.\n\nDiscovered during code review session 2026-03-11.'
metadata:
  topic: backlog-cli-deduplicate-25-functionsconstants-already-in-bac
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: P1
  type: Refactor
  status: open
  issue: '#611'
  last_synced: '2026-03-11T22:09:11Z'
---