---
name: 'Fix broken import in test_backlog_gh_first.py (ModuleNotFoundError: state_handler)'
description: "test_backlog_gh_first.py has a broken import — `ModuleNotFoundError: No module named 'state_handler'` — which prevents the entire test file from running. The module was likely renamed or moved. Fix the import to match the current module location while preserving test design intent."
metadata:
  topic: fix-broken-import-in-testbacklogghfirstpy-modulenotfounderro
  source: 'PR #561 code review — pre-existing issue'
  added: '2026-03-10'
  priority: P1
  type: Bug
  status: open
  issue: '#563'
  last_synced: '2026-03-10T08:16:47Z'
---