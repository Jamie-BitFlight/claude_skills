---
name: 'backlog: add status field to BacklogItem model'
description: "BacklogItem model lacks a `status` field. The `view_result_from_local_item()` function must re-read the file from disk just to extract status from frontmatter metadata, even though all other fields (description, source, added, raw_body) are already on the model. Adding `status: str = ''` to BacklogItem and populating it during `parse_item_file()` would eliminate the redundant file read entirely.\\n\\nDiscovered during code review session 2026-03-11."
metadata:
  topic: backlog-add-status-field-to-backlogitem-model
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: P2
  type: Refactor
  status: open
  issue: '#612'
  last_synced: '2026-03-11T22:09:15Z'
---