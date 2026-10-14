# Graph Report - development-harness  (2026-10-14)

## Corpus Check
- Large corpus: 496 files · ~751,039 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 7557 nodes · 18803 edges · 355 communities (167 shown, 188 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1840 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 107
- Community 108
- Community 109
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 175
- Community 176
- Community 177
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 225
- Community 226
- Community 228
- Community 229
- Community 230
- Community 232
- Community 233
- Community 235
- Community 236
- Community 237
- Community 239
- Community 240
- Community 241
- Community 242
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248
- Community 249
- Community 250
- Community 251
- Community 252
- Community 253
- Community 254
- Community 255
- Community 257
- Community 258
- Community 262
- Community 264
- Community 267
- Community 268
- Community 272
- Community 273
- Community 274
- Community 275
- Community 276
- Community 277
- Community 278
- Community 279
- Community 280
- Community 281
- Community 282
- Community 283
- Community 284
- Community 285
- Community 286
- Community 287
- Community 288
- Community 289
- Community 290
- Community 291
- Community 292
- Community 293
- Community 294
- Community 296
- Community 298
- Community 299
- Community 300
- Community 301
- Community 302
- Community 303
- Community 304
- Community 305
- Community 306
- Community 307
- Community 308
- Community 309
- Community 310
- Community 311
- Community 312
- Community 313
- Community 314
- Community 315
- Community 316
- Community 317
- Community 318
- Community 319
- Community 320
- Community 321
- Community 322
- Community 323
- Community 324
- Community 325
- Community 326
- Community 327
- Community 328
- Community 329
- Community 330
- Community 331
- Community 332
- Community 333
- Community 334
- Community 335
- Community 336
- Community 338
- Community 339
- Community 340
- Community 341
- Community 342
- Community 343
- Community 344
- Community 345
- Community 353
- Community 354

## God Nodes (most connected - your core abstractions)
1. `Output` - 297 edges
2. `BacklogItem` - 238 edges
3. `GitHubBackend` - 123 edges
4. `SQLiteBackend` - 104 edges
5. `ContentRecord` - 101 edges
6. `InMemoryBackend` - 93 edges
7. `Task` - 91 edges
8. `get_config()` - 89 edges
9. `IssueNode` - 89 edges
10. `ContentRef` - 85 edges

## Surprising Connections (you probably didn't know these)
- `_status_from_labels()` --uses--> `LabelNode`  [INFERRED]
  sam_schema/core/backends/github_task.py → backlog_core/backend_types.py
- `GitHubTaskProvider` --uses--> `IssueNode`  [INFERRED]
  sam_schema/core/backends/github_task.py → backlog_core/backend_types.py
- `_node_to_task_data()` --uses--> `IssueNode`  [INFERRED]
  sam_schema/core/backends/github_task.py → backlog_core/backend_types.py
- `_rebuild_metadata_body()` --uses--> `IssueNode`  [INFERRED]
  sam_schema/core/backends/github_task.py → backlog_core/backend_types.py
- `_migrate_task()` --uses--> `IssueNode`  [INFERRED]
  scripts/migrate_tasks_to_github.py → backlog_core/backend_types.py

## Import Cycles
- 3-file cycle: `dh_core/ledger/__init__.py -> dh_core/ledger/commands.py -> dh_core/ledger/port.py -> dh_core/ledger/__init__.py`
- 3-file cycle: `dh_core/ledger/__init__.py -> dh_core/ledger/commands.py -> dh_core/ledger/queries.py -> dh_core/ledger/__init__.py`
- 3-file cycle: `dh_core/ledger/__init__.py -> dh_core/ledger/commands.py -> dh_core/ledger/transitions.py -> dh_core/ledger/__init__.py`
- 4-file cycle: `dh_core/ledger/__init__.py -> dh_core/ledger/commands.py -> dh_core/ledger/port.py -> dh_core/ledger/transitions.py -> dh_core/ledger/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/sqlite_backend.py -> backlog_core/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/beads_backend.py -> backlog_core/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/memory_backend.py -> backlog_core/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 4-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/_capability_gates.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/sqlite_backend.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/_capability_gates.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backend_types.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/beads_backend.py -> backlog_core/github_sync.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/beads_backend.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/backends/github_contents.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/backends/github_work_items.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/github_sync.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/models.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/memory_backend.py -> backlog_core/models.py -> backlog_core/__init__.py`

## Hyperedges (group relationships)
- **Acceptance Criteria Bookends** — agents_swarm_task_planner_swarm_task_planner, agents_t0_baseline_capture_t0_baseline_capture, agents_tn_verification_gate_tn_verification_gate [EXTRACTED 1.00]
- **Backlog Item Grooming Artifacts** — templates_backlog_item_acceptance_criteria, templates_backlog_item_fact_check, templates_backlog_item_rt_ica, templates_backlog_item_groomed [EXTRACTED 1.00]
- **Change-impact analysis loop** — docs_change_impact_analysis_research_change_impact_analysis, docs_change_impact_analysis_research_auditable_change_chain, docs_change_impact_analysis_research_nist_ai_rmf [EXTRACTED 1.00]
- **Context-Fit Complexity Model** — docs_complexity_fit_and_economics_of_agents_context_fit_complexity_model, docs_complexity_fit_and_economics_of_agents_three_term_equation, docs_complexity_fit_and_economics_of_agents_context_fit_spectrum, docs_complexity_fit_and_economics_of_agents_session_economics [EXTRACTED 1.00]
- **Unified section contract** — docs_unified_section_layer_brief_unified_section_layer, docs_unified_section_layer_brief_canonical_logical_contract, docs_unified_section_layer_brief_writer_adapter_boundary [EXTRACTED 1.00]
- **Harness Measurement Set** — docs_work_ledger_measurements_harness_claude_code_harness_facts_claude_code, docs_work_ledger_measurements_harness_codex_harness_facts_codex, docs_work_ledger_measurements_harness_cursor_harness_facts_cursor, docs_work_ledger_measurements_harness_hermes_harness_facts_hermes, docs_work_ledger_measurements_harness_kilo_code_harness_facts_kilo_code, docs_work_ledger_measurements_harness_kimi_harness_facts_kimi, docs_work_ledger_measurements_harness_opencode_harness_facts_opencode, docs_work_ledger_measurements_harness_pi_harness_facts_pi [EXTRACTED 1.00]
- **Quality Gate Completion Workflow** — skills_complete_implementation_complete_implementation, skills_complete_implementation_references_completion_verification_gate, skills_complete_implementation_references_qg_dispatch_step, skills_complete_implementation_references_read_code_review_verdict, skills_complete_implementation_references_recursive_follow_up_handling [EXTRACTED 1.00]
- **Skill Discovery Reference Suite** — skills_setup_skill_discovery_skill_setup_skill_discovery_wizard, skills_setup_skill_discovery_references_repo_inference_patterns_repository_inference_patterns, skills_setup_skill_discovery_references_skill_marketplace_search_skill_marketplace_search, skills_setup_skill_discovery_references_skill_discovery_schema_skill_discovery_schema, skills_setup_skill_discovery_references_wizard_questions_wizard_questions [EXTRACTED 1.00]
- **Work Backlog Item Phases** — skills_work_backlog_item_references_workflows_work_locate_workflow_locate_workflow, skills_work_backlog_item_references_workflows_work_validate_workflow_validate_workflow, skills_work_backlog_item_references_workflows_work_prepare_workflow_prepare_workflow, skills_work_backlog_item_references_workflows_work_plan_workflow_plan_workflow [EXTRACTED 1.00]
- **Work Backlog Item Route Workflows** — skills_work_backlog_item_references_workflows_quick_start_quick_backlog_workflow, skills_work_backlog_item_references_workflows_progress_start_backlog_progress_report, skills_work_backlog_item_references_workflows_resume_start_backlog_resume [EXTRACTED 1.00]
- **Multi-Perspective Review** — agents_review_synthesizer_review_synthesizer, agents_reviewer_accessibility_accessibility_reviewer, agents_reviewer_performance_performance_reviewer, agents_reviewer_quality_quality_reviewer, agents_reviewer_security_security_reviewer [INFERRED 0.85]
- **Multi-Perspective Review** — skills_review_accessibility_change_skill_review_accessibility_change, skills_review_performance_change_skill_review_performance_change, skills_review_quality_change_skill_review_quality_change, skills_review_security_change_skill_review_security_change [INFERRED 0.95]

## Communities (355 total, 188 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (48): BeadsTaskProvider, _build_plan_data(), _issue_to_task_data(), parse_plan_content(), DocumentBackend, GitHubTaskProvider, _render_metadata_section(), _render_plan_body() (+40 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (59): reset_config(), set_config(), AddedCommentNode, AssigneeNode, BacklogConfig, LabelNode, MilestoneNode, _beads_content_lock() (+51 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (74): replace_manifest_in_body(), _body_preamble(), heading_to_section_key(), _merge_groomed(), merge_item(), _parse_groomed_section(), parse_issue_body(), _parse_metadata_block() (+66 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (76): get_config(), require_github_extras(), require_milestone_support(), UnsupportedBackendCapabilityError, _add_comment_graphql(), analyze_impact_radius_conflicts(), _apply_plan_to_item(), apply_status_blocked() (+68 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (23): persist_work_item(), RepositoryScopedCachedListing, WorkItemBackend, _BdRunnerLike, _beads_priority_for_item_priority(), _beads_status_for_item_status(), _beads_type_for_item_type(), BeadsBackend (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (69): list_plans(), canonical_plan_id(), parse_address(), FormatDetectionError, absent(), accept(), _address(), append_task() (+61 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (4): MilestoneFullNode, _now(), _serialized_connection_operation(), SQLiteBackend

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (22): _GitHubContentCache, _GitHubContentMigration, _OnlineContent, _PlanPersistence, _content_revision(), _ContentPersistence, _DispatchIndexEntry, _GitHubDispatchPersistence (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (60): tracked_connect(), Column, add_column_ddl(), admits_integer(), affinity(), all_events(), append_event(), blank_row() (+52 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (59): fetch_task(), json_list(), now(), timestamp(), transaction(), accept(), append(), append_section() (+51 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (25): _get_migrate_artifact_provider(), ArtifactBackend, create_artifact_provider(), LocalFilesystemArtifactProvider, _GitHubPlanPersistence, ArtifactRegistryClient, _get_provider(), PlanContentUnavailableError (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (44): SyncProvider, ItemNotFoundError, ReconcileRequest, ReconcileScope, add_item(), close_item(), _decision_context(), _extract_changes() (+36 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (3): InMemoryBackend, _make_issue_node(), _now()

### Community 13 - "Community 13"
Cohesion: 0.03
Nodes (47): CommandResult, _DispatchBase, DispatchPlan, GateResult, GateRunMode, ItemPriority, ItemStatus, MilestoneHeader (+39 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (33): BranchBackend, create_integration_branch(), delete_integration_branch(), get_integration_branch_status(), list_integration_branches(), merge_integration_branch(), require_branch_support(), BacklogError (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.03
Nodes (21): FileCache, acknowledge(), replace(), replace(), queue(), reject(), LegacyMigrationError, CacheCheckpoint (+13 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (49): RegisterResult, artifact_register(), _run(), dispatch_create_plan(), _dispatch_reference(), dispatch_validate(), _get_artifact_provider(), _read_dispatch_plan() (+41 more)

### Community 17 - "Community 17"
Cohesion: 0.04
Nodes (40): artifact_content_reference(), load_manifest(), publish_artifact(), register_manifest_entry(), ArtifactRegistry, _extract_table_from_rendered(), parse_manifest_section(), _parse_table_row() (+32 more)

### Community 18 - "Community 18"
Cohesion: 0.04
Nodes (25): IssueCommentNode, IssueNode, ListPageRequest, ListPageResult, _body_digest(), _comment_metadata(), _CommentMetadata, find_work_item_comment() (+17 more)

### Community 20 - "Community 20"
Cohesion: 0.03
Nodes (23): BeadsDispatchAdapter, dispatch_stale_check(), DispatchStateManager, _row_to_item(), DispatchItemRecord, DispatchSpawnSummary, DispatchWaveRecord, DispatchWaveSummary (+15 more)

### Community 21 - "Community 21"
Cohesion: 0.04
Nodes (11): claim_task(), get_plan_status(), update_task_status(), LocalYamlTaskProvider, plan_id_from_path(), _resolve_writable_path(), DependencyGraph, dfs() (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (42): artifact_get(), artifact_list(), backlog_add(), backlog_assign_item_to_milestone(), backlog_close(), backlog_comment_issue(), backlog_create_milestone(), backlog_create_project() (+34 more)

### Community 23 - "Community 23"
Cohesion: 0.04
Nodes (20): BdInvocationError, BdJsonDecodeError, BdNotInstalledError, _beads_workspace_path(), DHConfig, _context_backend(), _plan_backend(), BeadsContextBackend (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (40): _build_parser(), _build_spawn_record(), _build_spawn_shell_cmd(), check_session_limit(), _claude_tmux_session_name(), cmd_kill(), cmd_list(), cmd_read() (+32 more)

### Community 25 - "Community 25"
Cohesion: 0.03
Nodes (20): append_task(), _canonicalize_patch_keys(), create_plan(), finalize_plan(), get_ready_tasks(), _plan_fields_for_update(), read_plan(), read_task() (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.04
Nodes (38): _apply_show_filter(), _deduplicate_timestamps(), _entry_from_span(), EntrySpan, _find_balanced_close(), find_entry_spans(), generate_diff(), _is_entry_id() (+30 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (22): CodeBlockExtractor, CodeBlockStubRenderer, _attach_to_section(), _build_link_ref(), LinkExtractor, LinkKind, LinkRef, LinkTokenOrigin (+14 more)

### Community 28 - "Community 28"
Cohesion: 0.03
Nodes (14): BeadsCommentRaw, BeadsDependencyRaw, BeadsIssueRaw, BeadsLabelRaw, BeadsPriority, BeadsStatus, parse_dependency_list(), parse_issue() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (24): _agent_name_from_path(), _build_manifest_name_index(), find_agent(), _find_bare(), _find_plugin_qualified(), _get_manifest_name_for_dir(), get_plugins_root(), _looks_like_semver() (+16 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (31): add(), assign_milestone(), close(), comment_issue(), comments(), create_milestone(), create_project(), _emit() (+23 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (17): BackendName, _is_dict_of_object(), LinearArtifactProvider, _auth_headers(), gitlab_create_issue_note(), gitlab_create_snippet(), gitlab_get_snippet(), gitlab_list_issue_notes() (+9 more)

### Community 32 - "Community 32"
Cohesion: 0.05
Nodes (6): GitHubGistArtifactProvider, GitLabArtifactProvider, _make_github_client(), _replace_old_manifest_with_sentinel(), _require_int_item_id(), _sanitize_gist_filename()

### Community 33 - "Community 33"
Cohesion: 0.05
Nodes (27): _Unstated, mount_command_types(), mount_table(), mountinfo_types(), branch_head(), terminate_windows_process_tree(), agent_last_actions(), capture_pane_by_id() (+19 more)

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (28): clear_plan(), clearable_tables(), content_plan(), content_task(), created_payload(), decode_row(), divergences(), excluded_columns() (+20 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (13): BacklogViewDisclosureHandler, _entry_block_text(), _entry_ordinal_for_code(), _entry_ordinal_for_sub_heading(), _extract_entry_title(), _extract_preview(), NormalizedEntry, NormalizedSection (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.06
Nodes (30): _apply_status_label(), create_issue_for_item(), _create_issue_graphql(), create_task_issue(), _desired_label_set(), ensure_dh_labels(), fetch_github_issue_body(), _fetch_issue_graphql() (+22 more)

### Community 37 - "Community 37"
Cohesion: 0.05
Nodes (18): read(), parse_item_id(), known_failure_types(), err(), _is_result_mapping(), output_json(), err(), output_json() (+10 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (20): Plan, create_plan(), update_plan_fields(), append_section(), _atomic_write(), create_plan_file(), _is_yaml_frontmatter(), _locate_task_entry() (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.06
Nodes (23): ContentProviderError, GitHubRateLimitedError, _retryable(), _attempt_sync(), _compute_backoff_delay(), _count(), _make_progress_callback(), _callback() (+15 more)

### Community 40 - "Community 40"
Cohesion: 0.05
Nodes (24): check_commands(), conflict_groups_for(), content_store(), held_source(), import_task(), imported_task_row(), milestone_source(), milestone_task() (+16 more)

### Community 42 - "Community 42"
Cohesion: 0.05
Nodes (17): AppendTaskInput, _CliInput, CreatePlanInput, PlanUpdateFields, PlanUpdateInput, TaskUpdateFields, TaskUpdateInput, CreatePlanConfig (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.04
Nodes (21): apply_status_blocked(), apply_status_groomed(), apply_status_verified(), batch_fetch_statuses(), fetch_item_status(), get_github(), probe_backend_status(), try_get_github() (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.05
Nodes (4): Edge, Graph, Observation, LayeredGraph

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (14): Descriptor, Freshness, Node, Authority, ErrorRoute, EvidenceRequirement, Operation, SideEffect (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.06
Nodes (11): _GitHubReconciliation, ProviderSnapshot, ReconcileResult, _account_for_patch_outcomes(), ActionResult, finalize_reconciliation(), LogicalCacheRecord, reconcile_backlog() (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.07
Nodes (19): _parse_spawn_data(), _call_sam_cli(), _call_sam_plan_settle(), extract_launch_from_prompt(), _extract_prompt_from_transcript(), _extract_text_from_user_record(), _first_nonempty_line(), _first_text_block() (+11 more)

### Community 48 - "Community 48"
Cohesion: 0.06
Nodes (7): _has_cycles(), dfs(), _is_ready(), _node_to_task_data(), _parse_metadata(), _rebuild_metadata_body(), _status_from_labels()

### Community 49 - "Community 49"
Cohesion: 0.08
Nodes (18): _get_migrate_yaml(), _migrate_classify_plan_file(), _migrate_coerce_issue(), _migrate_discover_candidates(), migrate_dry_run(), _migrate_extract_issue(), _migrate_find_issue_via_backlog(), migrate_live_run() (+10 more)

### Community 50 - "Community 50"
Cohesion: 0.06
Nodes (12): _classify(), _classify_by_token_sets(), _compute_diff(), _extract_bak_body(), _extract_content_tokens(), FileResult, main(), _normalise_whitespace() (+4 more)

### Community 51 - "Community 51"
Cohesion: 0.09
Nodes (19): attempt_open(), check_progress_values(), expired(), expired_row(), outstanding(), Progress, ready(), ready_parameters() (+11 more)

### Community 52 - "Community 52"
Cohesion: 0.06
Nodes (20): _apply_body_section_filter(), _assemble_view_compact(), _assemble_view_content(), _build_sections_compact(), _build_sections_index_from_body(), _build_sections_metadata(), _compact_entry_count(), _description_matches_section_filter() (+12 more)

### Community 53 - "Community 53"
Cohesion: 0.07
Nodes (20): _build_registration_rows(), _build_slug_index(), _collect_artifact_files(), _detect_artifact_type(), _execute_registrations(), _extract_artifact_slug(), _extract_issue_int_from_backlog_data(), _extract_plan_field_slug() (+12 more)

### Community 54 - "Community 54"
Cohesion: 0.09
Nodes (3): _CacheState, _CacheStateStore, CacheStateCorruptError

### Community 55 - "Community 55"
Cohesion: 0.08
Nodes (16): _ActionConfigBase, ClaimTaskConfig, ClearActiveTaskConfig, FinalizePlanConfig, GetActiveTaskConfig, ReadPlanConfig, ReadTaskConfig, ReadyPlanConfig (+8 more)

### Community 56 - "Community 56"
Cohesion: 0.08
Nodes (15): PlanStatus, ListPlansConfig, AppendTaskResult, CreatePlanError, CreatePlanResult, FinalizePlanResult, PaginatedResult, PaginationMeta (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.07
Nodes (13): DecompositionSourceKind, ContractBasis, Predicate, PredicateDefinition, Projection, Severity, InstructionKind, ReferentKind (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.08
Nodes (17): _build_task_dict(), _extract_body_task_blocks(), _extract_bold_fields(), _extract_prose_sections(), _extract_task_id_title_from_entry(), _is_single_followup_format(), _merge_prose_fields(), _parse_body_prose_fields() (+9 more)

### Community 59 - "Community 59"
Cohesion: 0.08
Nodes (6): SourceSpan, EdgeType, ExtensionOperation, WorkEdge, WorkGraph, WorkNode

### Community 60 - "Community 60"
Cohesion: 0.07
Nodes (15): _call_with_deadline(), _DeadlineExceeded, _fetch_milestones_graphql(), _github_exception_message(), _graphql_operation_name(), _graphql_request(), _graphql_total_timeout_seconds(), _GraphQLCapable (+7 more)

### Community 61 - "Community 61"
Cohesion: 0.09
Nodes (9): _char_bisect_chunks(), chunk_text(), _chunk_text_impl(), _disclosure_to_result(), DisclosureConfig, _pack_parts(), paginate_results(), ProgressiveDisclosure (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.08
Nodes (7): _chunks_to_pages(), _make_page(), Paginator, _char_bisect_chunks(), _pack_parts(), _split_impl(), TokenBudgeter

### Community 63 - "Community 63"
Cohesion: 0.11
Nodes (19): resolve_provider_plan_address(), LedgerReadyResult, get_backend(), _sam_plan_append_task(), _from_content(), _sam_plan_finalize(), _from_content(), sam_plan_impl() (+11 more)

### Community 65 - "Community 65"
Cohesion: 0.06
Nodes (16): AccumulatedUsage, ArtifactEntryOut, BacklogViewResponse, CommentEntry, DispatchItemStatusResponse, DispatchWaveStartResponse, FollowupItem, IssueEntry (+8 more)

### Community 66 - "Community 66"
Cohesion: 0.08
Nodes (16): pytest_unconfigure(), remove_network_guard(), Check, _clear_attempt_effects(), _cols(), Command, Config, Effect (+8 more)

### Community 67 - "Community 67"
Cohesion: 0.08
Nodes (15): create_backend(), BacklogConfig, discover_repo(), _discover_repo_with_root(), _discover_via_env(), _discover_via_git(), get_backlog_dir(), get_config() (+7 more)

### Community 68 - "Community 68"
Cohesion: 0.06
Nodes (31): type, additionalProperties, description, properties, type, type, description, type (+23 more)

### Community 69 - "Community 69"
Cohesion: 0.09
Nodes (21): { execFileSync }, fs, os, path, { execFileSync }, fs, os, path (+13 more)

### Community 70 - "Community 70"
Cohesion: 0.09
Nodes (8): _render_stub(), _build_selector(), _BuildState, _code_summary(), _make_slug(), MarkdownIndexer, _SectionBuilder, CodeBlock

### Community 72 - "Community 72"
Cohesion: 0.10
Nodes (4): DecompositionGate, normalize(), Finding, Instruction

### Community 74 - "Community 74"
Cohesion: 0.09
Nodes (19): BacklogListItem, create_project(), _create_project_v2_node(), _CreatedProjectV2, _CreateProjectV2MutationData, _CreateProjectV2Result, ListCommentsResult, ListItemsResult (+11 more)

### Community 75 - "Community 75"
Cohesion: 0.10
Nodes (11): resolve_task_id(), derive_slug(), migrate(), _parse_directory(), _parse_frontmatter(), parse_task_file(), _parse_task_from_block(), TaskRecord (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.09
Nodes (8): create_parser(), main(), process_group_is_alive(), run_command(), terminate_process_tree(), _find_project_root(), main(), _build_parser()

### Community 77 - "Community 77"
Cohesion: 0.09
Nodes (7): _Branch, _Commit, _ContentsFile, _ContentsRepository, _GitTree, _GitTreeEntry, _Requester

### Community 78 - "Community 78"
Cohesion: 0.09
Nodes (12): DuplicateItemError, _apply_regex_result_page(), _check_for_duplicates(), _classify_duplicate_check(), apply_search_filter(), apply_search_filter_with_context(), _contains_regex_form(), ContentDuplicateMatch (+4 more)

### Community 79 - "Community 79"
Cohesion: 0.14
Nodes (6): _AndPred, _OrPred, _Predicate, _SearchParser, _TermPred, _TruePred

### Community 80 - "Community 80"
Cohesion: 0.11
Nodes (11): clear_active_task(), get_active_task(), set_active_task(), SetActiveTaskConfig, UpdateActiveTaskConfig, ActiveTaskClearResult, ActiveTaskGetResult, ActiveTaskSetResult (+3 more)

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (13): backlog_dir(), compute_slug(), context_dir(), _dh_user_root(), ensure_dirs(), _get_dh_user_root(), git_project_root(), milestones_dir() (+5 more)

### Community 83 - "Community 83"
Cohesion: 0.12
Nodes (10): _load_yaml_block(), _parse_embedded_task_blocks(), _parse_frontmatter_content(), _parse_prose_fields(), _parse_tasks_list_block(), read_frontmatter_plan(), _split_outside_fences(), make_yaml() (+2 more)

### Community 84 - "Community 84"
Cohesion: 0.09
Nodes (4): ReferentResolver, RepoResolver, SourceReader, Referent

### Community 85 - "Community 85"
Cohesion: 0.11
Nodes (5): _build_comment_body(), _closing_tag(), GitHubContextBackend, _opening_tag(), _parse_comment_body()

### Community 86 - "Community 86"
Cohesion: 0.13
Nodes (8): _classify_frontmatter(), detect_format(), FormatType, read_plan(), _read_directory(), _read_single_file(), read_yaml_plan(), load_yaml()

### Community 88 - "Community 88"
Cohesion: 0.12
Nodes (5): live_sandbox(), main(), open_sandbox(), cleanup_run(), LiveTestScope

### Community 89 - "Community 89"
Cohesion: 0.09
Nodes (4): ProviderError, CallableMarkdownContentProvider, MarkdownContentProvider, MCPMarkdownContentProvider

### Community 91 - "Community 91"
Cohesion: 0.09
Nodes (10): _add_comment_graphql(), close_github_issue(), _comment_then_close(), _fetch_comment_by_id_graphql(), _fetch_issue_comments_graphql(), _mutation_payload(), _parse_comment_node(), _parse_full_database_id() (+2 more)

### Community 92 - "Community 92"
Cohesion: 0.11
Nodes (8): _check_codes_unique(), failure_type(), FailureCategory, FailureTypeRow, KnownFailureTypesPage, page(), RecoveryDisposition, SuggestedRoute

### Community 93 - "Community 93"
Cohesion: 0.12
Nodes (8): AmbiguousSectionRefError, CodeBlockNotFoundError, DocumentNotLoadedError, OrdinalNotFoundError, PaginationError, ParserError, ProgressiveMarkdownError, SectionNotFoundError

### Community 94 - "Community 94"
Cohesion: 0.11
Nodes (8): build_concept_query(), _candidate_item_ref(), _extract_concept_words(), _format_match_text(), _make_snippet_parts(), _NotPred, _worker_context_fact_is_valid(), _worker_contexts_are_valid()

### Community 95 - "Community 95"
Cohesion: 0.12
Nodes (11): _make_snippet(), _parse_body_sections(), tokenize_search(), _collect_field_matches(), _collect_match_context(), _collect_plain_matches(), _collect_regex_matches(), _enrich_with_match_context() (+3 more)

### Community 96 - "Community 96"
Cohesion: 0.12
Nodes (5): _extract_manifest_from_metadata(), _is_dict_of_object(), _parse_manifest_value(), run_server(), apply_project_dir_from_argv()

### Community 97 - "Community 97"
Cohesion: 0.10
Nodes (4): _der_sequence_length(), graphql_total_timeout_seconds(), _InstallState, _strip_trusted_certificate_trailer()

### Community 98 - "Community 98"
Cohesion: 0.12
Nodes (9): _build_conflict_groups(), _overlapping_systems(), _parse_impact_radius_paths(), _path_contains(), _repository_path(), _UnionFind, _without_repository_symbol(), extract_leading_code_list_items() (+1 more)

### Community 99 - "Community 99"
Cohesion: 0.12
Nodes (8): _build_spawn_cmd(), dispatch_spawn(), _dispatch_state_manager(), dispatch_wave_status(), _poll_until_done(), _project_stub(), _run_spawn_item(), _WaveCounters

### Community 100 - "Community 100"
Cohesion: 0.11
Nodes (5): RequestShapedListing, SnapshotCheckpointProvider, SnapshotCompletenessProvider, require_request_shaped_listing(), _listing_provenance()

### Community 101 - "Community 101"
Cohesion: 0.13
Nodes (4): Layer, LedgerEdge, LedgerGraph, LedgerNode

### Community 102 - "Community 102"
Cohesion: 0.16
Nodes (6): MissingSessionIdError, require_session_id(), active_task_clear(), active_task_get(), active_task_set(), active_task_update()

### Community 103 - "Community 103"
Cohesion: 0.15
Nodes (6): _guarded_connect(), _guarded_connect_ex(), _guarded_getaddrinfo(), install_network_guard(), _is_local(), pytest_configure()

### Community 104 - "Community 104"
Cohesion: 0.14
Nodes (5): close_sqlite_connections(), _hermetic_dh_config(), _hermetic_project_root(), _live_sandbox_contract(), track_sqlite_connections()

### Community 105 - "Community 105"
Cohesion: 0.19
Nodes (6): get_ready_tasks(), list_features(), _load_tasks_via_sam(), ready_tasks(), status(), validate()

### Community 107 - "Community 107"
Cohesion: 0.16
Nodes (6): _format_yaml_value(), has_yaml_frontmatter(), normalize_status(), parse_yaml_frontmatter(), resolve_task_id(), update_yaml_field()

### Community 108 - "Community 108"
Cohesion: 0.16
Nodes (5): AddressingError, _parse_prefix(), _reject_path_traversal(), resolve_plan_address(), _yaml_first_key()

### Community 109 - "Community 109"
Cohesion: 0.19
Nodes (7): SchemaGap, detect_gaps(), _detect_gaps(), _normalize_status(), normalize_task(), normalize_task_lenient(), _resolve_task_id()

### Community 111 - "Community 111"
Cohesion: 0.12
Nodes (16): Already Implemented Check, Feasibility Gate, Feature Request, Backlog Item Matching, Auto-Groom Check, Interactive Browser, Issue-First Path, Issue Sync (+8 more)

### Community 112 - "Community 112"
Cohesion: 0.19
Nodes (4): find_first_event(), _iter_json_lines(), parse_jsonl_events(), read_session_transcript_usage()

### Community 113 - "Community 113"
Cohesion: 0.15
Nodes (6): _auto_detect_beads(), _dh_user_root_path(), _get_config_search_paths(), _is_str_dict(), _load_yaml_config(), _resolve_from_config()

### Community 114 - "Community 114"
Cohesion: 0.13
Nodes (6): check_open_prs_for_issue(), CommentNode, CreatedIssueNode, _parse_search_pr_node(), SearchPRNode, SubIssueNode

### Community 115 - "Community 115"
Cohesion: 0.16
Nodes (9): ArtifactContent, _run(), _run(), artifact_read(), _run(), _artifact_type(), _load_manifest(), _manifest_reference() (+1 more)

### Community 116 - "Community 116"
Cohesion: 0.18
Nodes (6): _artifact_manifest_instructions(), _detect_layout(), migrate(), _project_root(), register_artifacts(), verify()

### Community 117 - "Community 117"
Cohesion: 0.17
Nodes (15): Complete Implementation, Completion Verification Gate, Concerns Processing, Final Handoff, Migration Fidelity Gate, Quality Gate Dispatch Step, Read Code Review Verdict, Recursive Follow-up Handling (+7 more)

### Community 118 - "Community 118"
Cohesion: 0.19
Nodes (6): _coerce_timestamp(), parse_dependencies(), parse_task_content(), _parse_yaml_dependencies(), _parse_yaml_skills(), _status_from_title()

### Community 119 - "Community 119"
Cohesion: 0.18
Nodes (7): fetch_tasks_from_backend(), fetch_tasks_from_beads(), fetch_tasks_from_github(), _load_tasks_from_cache(), Task, _task_sort_key(), TaskPriority

### Community 120 - "Community 120"
Cohesion: 0.16
Nodes (4): DisclosureRequest, DisclosureRequestParser, DisclosureMode, DisclosureParamError

### Community 121 - "Community 121"
Cohesion: 0.16
Nodes (3): _build_ssl_context(), __init__(), _ProxyAwareAdapter

### Community 122 - "Community 122"
Cohesion: 0.16
Nodes (8): _apply_issue_status_labels(), _apply_non_in_progress_status(), _apply_updates_to_item(), _apply_verified_status(), _create_issue_and_update_item(), _update_item_description(), update_item_metadata(), _work_item()

### Community 123 - "Community 123"
Cohesion: 0.15
Nodes (6): CommentListEntry, _list_status_resolution(), _listing_status_metadata(), _ListStatusMapResolution, _OpenScan, _resolve_list_status_map()

### Community 124 - "Community 124"
Cohesion: 0.09
Nodes (6): _apply_fields_projection(), _assert_config(), _build_sync_state_block(), _page_status_source(), _parse_args(), _probe_backend_status()

### Community 125 - "Community 125"
Cohesion: 0.19
Nodes (7): _first_git_ancestor(), _git_root_if_directory(), _infer_dh_project_root_env(), _infer_from_codex_pwd(), _infer_from_ide_env_vars(), _infer_from_workspace_folder_paths(), infer_project_root()

### Community 126 - "Community 126"
Cohesion: 0.17
Nodes (6): _extract_content_block(), extract_description_from_issue_body(), extract_groomed_section(), body_section(), _patch_frontmatter_field(), _patch_segment_in_multi_task()

### Community 127 - "Community 127"
Cohesion: 0.21
Nodes (5): bundle_requires_relaxed_verification(), _cert_fails_strict_checks(), _load_certificates(), _new_anchors(), _parse_pem_certificate_blocks()

### Community 128 - "Community 128"
Cohesion: 0.18
Nodes (5): _apply_regex_search_filter(), _apply_regex_search_filter_result(), _cleanup_regex_worker(), _regex_worker(), _worker_record_is()

### Community 129 - "Community 129"
Cohesion: 0.19
Nodes (6): _launch_background_sync(), _log_sync_task_exc(), _register_bg_task(), sync_now(), sync_status(), get_sync_state()

### Community 131 - "Community 131"
Cohesion: 0.19
Nodes (5): discover_plan_directory(), Feature, find_task_file_by_slug(), find_task_files(), _has_task_content()

### Community 133 - "Community 133"
Cohesion: 0.18
Nodes (3): _extract_heading_text(), collect(), _PositionedHeading

### Community 134 - "Community 134"
Cohesion: 0.20
Nodes (5): _compile_regex_term(), _original_span_for_casefolded_match(), _predicate_with_regex_context(), _regex_pattern_from_term(), _regex_term_context()

### Community 135 - "Community 135"
Cohesion: 0.17
Nodes (6): _compute_match_tokens(), _paginate_match_items(), _resolve_effective_limit(), _section_without_entry_content(), _token_count(), _view_payload_token_count()

### Community 137 - "Community 137"
Cohesion: 0.18
Nodes (6): _build_task_status_map(), _extract_feature_slug(), get_ready_sam_tasks(), get_sam_tasks(), _is_sam_task_ready(), _SamTaskLookupResult

### Community 138 - "Community 138"
Cohesion: 0.20
Nodes (4): _build_haystack(), _candidate_matched_field_and_snippet(), _item_field_text(), _item_matches_term()

### Community 139 - "Community 139"
Cohesion: 0.18
Nodes (4): _keys_to_kebab(), _make_yaml(), _snake_to_kebab(), write_dispatch_plan()

### Community 141 - "Community 141"
Cohesion: 0.18
Nodes (4): _create_task_from_dict(), _sam_task_to_dict(), TaskData, TaskDict

### Community 142 - "Community 142"
Cohesion: 0.18
Nodes (10): description, type, additionalProperties, description, type, properties, commands, required (+2 more)

### Community 144 - "Community 144"
Cohesion: 0.20
Nodes (4): bundle_adds_new_anchor(), install_proxy_tls_support(), _make_connection_class(), make_github_client()

### Community 145 - "Community 145"
Cohesion: 0.20
Nodes (3): _git_common_root(), GitResolutionTimeoutError, _resolve_repo_with_timeout()

### Community 146 - "Community 146"
Cohesion: 0.29
Nodes (3): default_parallelism(), isolated_options(), main()

### Community 147 - "Community 147"
Cohesion: 0.36
Nodes (10): Artifact Conventions, Default Development Flow, Human Touchpoint Model, Role Resolution Protocol, SDLC Stage Naming Taxonomy, Discovery, Evaluate SDLC Layers, Execution (+2 more)

### Community 148 - "Community 148"
Cohesion: 0.25
Nodes (3): has_github_credentials(), MissingGitHubTokenError, resolve_token()

### Community 153 - "Community 153"
Cohesion: 0.28
Nodes (3): get_active_task(), get_available_features(), main()

### Community 154 - "Community 154"
Cohesion: 0.25
Nodes (4): _normalize_status(), parse_status(), _parse_yaml_status(), TaskStatus

### Community 157 - "Community 157"
Cohesion: 0.25
Nodes (8): Command Canonicalization, Command-and-Content Identity, Recoverable Staleness, Caller-Visible Cache Metadata, Forced Refresh, Revalidation, Session Keying, Content Keying

### Community 158 - "Community 158"
Cohesion: 0.32
Nodes (3): _ledger_holds(), on_ledger(), route()

### Community 160 - "Community 160"
Cohesion: 0.29
Nodes (3): _configured_ca_bundles(), _is_openssl_hashed_ca_directory(), resolve_ca_bundle()

### Community 161 - "Community 161"
Cohesion: 0.33
Nodes (6): npx, uv, backlog, sam, sequential_thinking, @modelcontextprotocol/server-sequential-thinking

### Community 163 - "Community 163"
Cohesion: 0.33
Nodes (3): _apply_item_depth(), _parse_body_section_first_lines(), _parse_body_section_names()

### Community 164 - "Community 164"
Cohesion: 0.33
Nodes (3): _build_compact_manifest(), _build_over_budget_view(), _sections_index_from_result()

### Community 166 - "Community 166"
Cohesion: 0.33
Nodes (6): Audit Partitions, Purpose Audit Clause Evidence Manifest, Audit Evidence Schema, Historical Source Exclusion, Purpose Audit Reference Selection, Audit Source Precedence

### Community 167 - "Community 167"
Cohesion: 0.33
Nodes (6): Canonical Human Touchpoint Model, Canonical Artifact Conventions, SDLC-Agnostic Framework, ARL Meta-Layer, Layer 0, SDLC Layer Separation Architecture

### Community 168 - "Community 168"
Cohesion: 0.33
Nodes (3): get_task_config(), set_task_config(), TaskConfig

### Community 169 - "Community 169"
Cohesion: 0.33
Nodes (6): Dispatch Plan Schema, Groom Milestone, Group Items to Milestone, Stream-JSON Protocol, Team Health Check, Kage Bunshin

### Community 170 - "Community 170"
Cohesion: 0.33
Nodes (6): Runner Reuse Handoff, Chain-of-Verification Reduces Hallucination, Reverse Thinking Enhances Missing Information Detection in LLMs, RT-ICA, Start Task, Subagent Contract

### Community 171 - "Community 171"
Cohesion: 0.33
Nodes (6): Acceptance Criteria, Acceptance Criteria Verification, Backlog Item Template, Fact-Check, Groomed, RT-ICA

### Community 172 - "Community 172"
Cohesion: 0.40
Nodes (5): Review Synthesizer, Accessibility Reviewer, Performance Reviewer, Quality Reviewer, Security Reviewer

### Community 173 - "Community 173"
Cohesion: 0.40
Nodes (5): RT-ICA Assessor, Close Resolve Semantic Redesign, Development Harness Backend Providers, Backlog Item Groomed Schema, Backlog Item Lifecycle

### Community 182 - "Community 182"
Cohesion: 0.50
Nodes (5): Follow-Up Relationship, CLI MCP Operation Parity, Generic Work-Item Protocol, Key-Based Query Filter, Purpose Audit Remediation Plan

### Community 183 - "Community 183"
Cohesion: 0.40
Nodes (5): Amendments to the Findings Files, Blind Completeness Audit, Producers Without Consumers, Model Fidelity Audit, Finding Verification

### Community 190 - "Community 190"
Cohesion: 0.40
Nodes (5): Architecture Audit Module Dependency Graph, Node.js Code Review Patterns, Python Code Review Patterns, TypeScript Code Review Patterns, Web Frontend Code Review Patterns

### Community 191 - "Community 191"
Cohesion: 0.40
Nodes (5): Multi-Perspective Review Maintenance, Multi-Perspective Review Acceptance Test Guide, Multi-Perspective Review Dispatch Flow, Multi-Perspective Review Goals, Multi-Perspective Review

### Community 192 - "Community 192"
Cohesion: 0.40
Nodes (4): Skill Discovery Schema, Skill Marketplace Search, Wizard Questions, Setup Skill Discovery Wizard

### Community 193 - "Community 193"
Cohesion: 0.40
Nodes (5): dh:dh-cli-usage, Runner Contract, Self-Discovery, dh:subagent-contract, Worktree Worker Protocol

### Community 194 - "Community 194"
Cohesion: 0.50
Nodes (3): FastMCP Call, Plain SAM CLI, Hook Subprocess Invocation Rule

### Community 195 - "Community 195"
Cohesion: 0.50
Nodes (4): Gate Token Fallback Path Tests, Gate Token Fallback Scan, Gate Token Remote Execution Fix Plan, Read Gate Token

### Community 196 - "Community 196"
Cohesion: 0.50
Nodes (4): Alignment Analyst, Design Intent Alignment, Backlog Item Groomer, RT-ICA Assessment

### Community 197 - "Community 197"
Cohesion: 0.50
Nodes (4): Backlog MCP Package Architecture, Agent Markdown Consumption Contract, Artifact Type Registry, Development Harness Purpose

### Community 206 - "Community 206"
Cohesion: 0.50
Nodes (3): Composite Routing, Create-Only Reference Assignment, Route-Aware Provider Status

### Community 207 - "Community 207"
Cohesion: 0.50
Nodes (3): Persistence Read-Back Gate, Ready for Design, Work Brief

### Community 214 - "Community 214"
Cohesion: 0.50
Nodes (3): Test Designer, Test Failure Analysis Mindset, Test Reviewer

### Community 215 - "Community 215"
Cohesion: 1.00
Nodes (3): AI Agent Swarm Coordination Planner, T0 Baseline Capture, TN Verification Gate

### Community 222 - "Community 222"
Cohesion: 0.67
Nodes (3): Stale Marker, Write-Triggered Invalidation, Source Index

### Community 240 - "Community 240"
Cohesion: 0.67
Nodes (3): Agent Health Check, Plan Status Shapes, Implement Feature

### Community 241 - "Community 241"
Cohesion: 0.67
Nodes (3): Blocker Handling, Completion Report, Constant Commits Protocol

## Knowledge Gaps
- **223 isolated node(s):** `npx`, `@modelcontextprotocol/server-sequential-thinking`, `Development Harness Agent Governance`, `Development Harness Architecture`, `Cross-Harness Claims Register` (+218 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3753 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **188 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Output` connect `Community 14` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 137`, `Community 11`, `Community 12`, `Community 16`, `Community 17`, `Community 19`, `Community 22`, `Community 30`, `Community 35`, `Community 36`, `Community 43`, `Community 49`, `Community 52`, `Community 71`, `Community 201`, `Community 74`, `Community 91`, `Community 115`, `Community 122`, `Community 123`, `Community 124`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 126 inferred relationships involving `Output` (e.g. with `migrate_live_run()` and `_migrate_queue_manifest_only()`) actually correct?**
  _`Output` has 126 INFERRED edges - model-reasoned connections that need verification._
- **What connects `npx`, `@modelcontextprotocol/server-sequential-thinking`, `Development Harness Agent Governance` to the rest of the system?**
  _223 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0236496862796718 - nodes in this community are weakly interconnected._
- **Why does `GitHubBackend` connect `Community 19` to `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 10`, `Community 11`, `Community 14`, `Community 15`, `Community 18`, `Community 148`, `Community 32`, `Community 39`, `Community 43`, `Community 46`, `Community 67`, `Community 198`, `Community 199`, `Community 91`, `Community 114`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `BacklogItem` (e.g. with `persist_work_item()` and `GitHubExtras`) actually correct?**
  _`BacklogItem` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.021952964320844138 - nodes in this community are weakly interconnected._