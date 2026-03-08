# Test Coverage Gaps

## Gap: implementation_manager.py — --github flag and fetch_tasks_from_github

**Files**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
**Behavior to cover**:
- `fetch_tasks_from_github`: returns None when `_BACKLOG_CORE` absent; reads cache when GitHub offline; returns None when offline+cache absent; returns None when cache malformed; writes cache on successful GitHub fetch; converts SamTask to Task correctly
- `_load_tasks_from_cache`: returns None when file absent; returns None on JSON decode error; skips malformed entries with warning; returns list of Tasks on success
- `ready_tasks` with `--github`: falls back to local when GitHub returns None; emits error JSON + exit 1 when both GitHub and local absent; identical output when no flag
- `status` with `--github`: falls back to local when GitHub returns None; task_file shows "github:N" when source is GitHub
**Reason not written**: architecture spec (7.3) designates these tests for `tests/test_implementation_manager/test_github_flag.py` — scope boundary; no test fixtures for backlog_core mocking exist in this agent's context

## Gap: implementation_manager.py — claim-task command and helpers

**Files**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`, `plugins/python3-development/skills/implementation-manager/scripts/task_format.py`
**Behavior to cover**:
- `claim_task` command: success path (not-started → in-progress), already-in-progress rejection, task-not-found rejection, write-error path
- `_try_claim_part`: single-frontmatter file (part starts with `---`), multi-frontmatter file (part without leading `---`), non-matching task ID
- `_apply_claim_to_content`: single-frontmatter file, multi-frontmatter file, task-not-found returns None, preserves existing `started` field
- `_find_task_section_in_file`: single-frontmatter file, multi-frontmatter file, task-not-found returns None
- `_resolve_task_status`: parse-error path, task-not-found for multi-frontmatter
- `normalize_status` in `task_format.py`: already-normalized inputs (in-progress, not-started) pass through without mapping to not-started
**Reason not written**: Scope constraint — task T1.1 covers implementation only; test authoring is a separate task in the SAM plan.

## Gap: plugin_validator.py — PR005 command-is-skill-directory check

**Files**: `plugins/plugin-creator/scripts/plugin_validator.py`
**Behavior to cover**: `PluginRegistrationValidator.validate()` should emit a PR005 error when
a path listed in the `commands` array of `plugin.json` is a directory that contains a `SKILL.md`
file. Tests should verify:
- A command entry pointing to a plain `.md` file produces no PR005 error.
- A command entry pointing to a directory without `SKILL.md` produces no PR005 error.
- A command entry pointing to a directory containing `SKILL.md` produces exactly one PR005 error
  with `severity="error"`, `code=ErrorCode.PR005`, and a suggestion referencing the `skills` array.
**Reason not written**: No existing test suite for `plugin_validator.py` was found in `tests/`.
Adding tests is out of scope for this surgical fix task; creating a test suite for the entire
validator from scratch exceeds the stated constraint of a surgical change only.

## Gap: bucket_day_data.py — core bucketing logic

**Files**: `.claude/skills/daily-releases/scripts/bucket_day_data.py`
**Behavior to cover**:
- `semantic_prefix()` with root-level file, 1-level path, 2-level path, and 3+-level path
- `build_file_groups()` groups files by prefix, accumulates token counts, maps commit SHAs
- `assign_buckets()` greedy fill: groups that fit stay in current bucket; overflow starts a new bucket; single group exceeding limit gets its own bucket
- `load_file_entries()` filters `is_source=false` and `is_excluded=true` entries out
- `load_commit_records()` returns correct `CommitRecord` instances
- `build_content_text()` renders `=== File: ===` and `=== Commits ===` sections correctly
- `count_tokens()` returns non-negative integer for arbitrary input strings
**Reason not written**: No existing test suite for the daily-releases scripts directory. Creating a full test suite from scratch is out of scope for the initial implementation task.

## Gap: implementation_manager.py — skills field support

**Files**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
**Behavior to cover**:
- `parse_task_from_frontmatter()` with `skills: [skill1, skill2]` list in YAML frontmatter — returns `Task.skills == ["skill1", "skill2"]`
- `parse_task_from_frontmatter()` without `skills` field — returns `Task.skills == []` (backward compat)
- `_parse_yaml_skills()` with list input, string input, and `None` input
- `SkillsParser.parse()` with `**Skills**: skill1, skill2` legacy markdown format — sets `task_data["skills"]`
- `_create_empty_task_data()` returns `TaskData` with `skills == []`
- `_create_task_from_dict()` passes `skills` from `TaskData` to `Task`
- `ready-tasks` CLI command JSON output includes `"skills": [...]` for each ready task
**Reason not written**: No test suite exists for `implementation_manager.py`. Task 2.3 scope was limited to data model changes only; creating a full test suite from scratch exceeds the stated constraint.

## Gap: state_manager.py integration with validators

**Files**: `plugins/scientific-method/mcp/experiment-registry/state_manager.py`
**Behavior to cover**:
- `complete_step` returns `{"success": False, "validation_errors": [...]}` and does not mutate `state.artefacts` when any validator returns errors (pre-merge validation pattern)
- `_compute_frozen_hashes` stores SHA-256 hash in `state.artefact_integrity[key]` as `ArtefactIntegrity` after merge
- `_complete_iterate_step` derives `criteria_passed` from `rubric_scores.values()` (not from `artefacts["criteria_passed"]`) and stores `rubric_scores_iter{N}` as JSON in `state.artefacts`
- iterate-specific validators (`validate_iteration_output`, `validate_rubric_scores`) are only called when `step_id == "iterate"` — not for other steps
- `complete_step` returns `{"success": False, "blocked_on_human_input": True, ...}` when `human_input_required` and artefacts are missing
- Experiment reaches `status="complete"` when `all(rubric_scores.values())` is True on the iterate step
- Experiment reaches `status="inconclusive"` when `iteration_count >= max_iterations`

**Reason not written**: T4 scope is integration wiring only. Test creation is assigned to T6 per the task plan.

## Gap: server.py complete_step rubric_scores passthrough

**Files**: `plugins/scientific-method/mcp/experiment-registry/server.py`
**Behavior to cover**:
- `complete_step` MCP tool accepts `rubric_scores: dict[str, bool] | None` and passes it through to `manager.complete_step`
- MCP tool returns `{"success": False, "validation_errors": [...]}` when validation fails
- MCP tool raises `ToolError` when `step_id` does not match current step
**Reason not written**: T4 scope is integration wiring only. Test creation is assigned to T6 per the task plan.

## Gap: task_status_hook.py — GitHub sync functions (T4)

**Files**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
**Behavior to cover**:
- `get_parent_issue_number()`: returns int when `parent_issue_number` key present in context file; returns None when key absent; returns None when context file missing; returns None on JSON parse error
- `sync_completion_to_github()`: no GitHub call when `github_issue` field absent from task YAML (warning to stderr); calls `update_task_status(repo, N, "complete")` with correct args on success; catches `GithubException` and exits cleanly (exit 0); catches `GitHubUnavailableError` and exits cleanly (exit 0); wraps entire body in `try/except Exception`
- `handle_subagent_stop()` integration: `sync_completion_to_github` called after context file deletion; local YAML update is not rolled back on GitHub failure; exit 0 always
- `handle_activity_update()`: never imports `backlog_core` or calls `update_task_status` from `backlog_core`
**Reason not written**: Subordinate-agent boundary — test authoring for Phase 4 is assigned to a separate task (`tests/test_task_status_hook/test_github_sync.py`) per the architecture spec section 7.4. `backlog_core.github` mocking requires fixtures not available in this scope.

## Gap: registry_loader.py_apply_extension merge of new fields

**Files**: `plugins/scientific-method/mcp/experiment-registry/registry_loader.py`
**Behavior to cover**:
- `_apply_extension` appends `ext.additional_validation_rules` to `step.validation_rules`
- `_apply_extension` merges `ext.additional_frozen_artefacts` into `step.frozen_artefacts` with order-preserving deduplication (via `dict.fromkeys`)
- Duplicate keys in `additional_frozen_artefacts` that already exist in `step.frozen_artefacts` are deduplicated (base key wins position)
**Reason not written**: T4 scope is integration wiring only. Test creation is assigned to T6 per the task plan.

## Gap: frustration-analyzer MCP server

**Files**: `plugins/frustration-analyzer/mcp/server.py`
**Behavior to cover**:
- `_heuristic_rate()`: verify creativity/severity/humor/accuracy base scores per category, modifier logic (+1 for technical terms, +1 for metaphors, +1 for caps/punctuation), cap at 5, composite calculation
- `_sanitize_text_impl()`: EMAIL, IP, PATH, URL, TOKEN pattern matching and replacement; TOKEN minimum length filter; redaction ordering (most specific first)
- `_extract_scenario()`: preceding message extraction, compact_boundary detection, had_prior_correction via kaizen soft signals, tool_sequence extraction
- `_index_insult()`: duplicate detection (session_id + message_uuid), insert into all 3 tables, heuristic rating storage
- `_scan_transcripts_impl()`: glob resolution, JSONL parsing, insult pattern matching across 8 categories, first-match-wins behavior, result counts
- `scan_transcripts` / `list_insults` / `get_scenario` / `top_insults` / `generate_social_post` / `sanitize_text`: async tool wrappers with parameter validation, error cases (invalid sort_by, invalid mode, missing insult_id)
- All 8 `_INSULT_PATTERNS` regex patterns: positive and negative matches per category
- `_build_hashtags()`: category-specific hashtag, #ClaudeCode conditional on model name
- `_fetch_insult_for_post()`: ToolError on missing insult
**Reason not written**: New plugin created in this session; sub-agent scope limited to implementation. Test suite creation is a separate task.
