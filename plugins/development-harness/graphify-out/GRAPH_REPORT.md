# Graph Report - development-harness  (2026-09-18)

## Corpus Check
- 802 files · ~1,370,647 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 21923 nodes · 49161 edges · 804 communities (608 shown, 196 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 2355 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dd208ce5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ItemContentNormalizer
- ContentTaskProvider
- backlog_core/models.py
- ContentRef
- write_plan
- ADR-1770-1: Single-Writer Contract for TaskBackend
- test_backlog_core_server.py
- sam_schema/core/models.py
- GitHubBackend
- _Repository
- cli_active_task.py
- BacklogItem
- parsing.py
- MockerFixture
- test_beads_models.py
- backlog_list
- ArtifactManifest
- OrdinalPathMapper
- tests_sam/test_server.py
- InMemoryTaskProvider
- _heading_path
- InMemoryBackend
- Task
- load_item
- GistTaskLayer
- Valid Dispatch Plan
- test_ledger_conformance.py
- BeadsBackend
- test_query.py
- _BuildState
- backlog_core/server.py
- BacklogViewDisclosureHandler
- MockerFixture
- transitions.py
- dh_paths.py
- artifact_provider.py
- GroomedData
- parse_entries
- run_quality_gates
- call_mcp_tool
- _extract_response_dict
- MockerFixture
- test_startup_sync.py
- test_ledger_port.py
- test_section_registry.py
- BacklogConfig
- _patch_github_body
- BeadsTaskProvider
- LocalFilesystemArtifactProvider
- ArtifactType
- store.py
- TaskBackend
- test_consolidated_tools.py
- ProgressiveMarkdownNavigator
- FormatType
- ViewItemResult
- BeadsArtifactProvider
- test_validator.py
- port.py
- client
- DHConfig
- ledger/__init__.py
- Section
- spawn.py
- Path
- BdRunner
- DisclosureRequestParser
- GitHubGistArtifactProvider
- IssueCommentNode
- discover_repo
- test_scripted_runner.py
- open_ledger
- _PositionedHeading
- test_action_models.py
- test_agent_portability_and_verdict_drift.py
- scripted_runner.py
- read_manifest_plan
- DispatchItemRecord
- get_repo_root
- view_item
- migrate_tasks_to_github.py
- BeadsContextBackend
- test_mcp_call_shape_drift.py
- _apply_body_section_filter
- helpers.py
- workflow_multigraph/__init__.py
- CacheCheckpoint
- backlog.py
- find_item
- _paginate
- _write_item
- test_backend_config_search.py
- test_ledger_fold.py
- Page
- test_frontmatter_reader.py
- dh_migrate.py
- test_decomposition_gate.py
- add_item
- get_sync_state
- merge_layer.py
- SyncState
- Path
- _resolve_labels_graphql
- DispatchPlan
- _call_view
- test_artifact_registry_ownership.py
- test_known_failure_types.py
- ._bd_id_for_task
- _item
- Path
- parse_issue_body
- test_readers/test_yaml_reader.py
- test_github_tools_milestones.py
- .from_markdown
- sync_issues_graphql
- monitor.py
- test_file_cache.py
- Graph
- Path
- Entry
- analyze_impact_radius_conflicts
- parametrize
- migrate_backlog_to_yaml.py
- MockerFixture
- model.py
- detect_format
- test_spawn.py
- render_issue_body
- LoopDriver
- Path
- _github_exception
- properties
- dispatch_schema/__init__.py
- Agent Markdown Consumption — Behaviour Specification
- ActiveTaskContext
- _extract_log_messages
- Path
- test_github_client.py
- test_cli_migrate_fallback.py
- install_proxy_tls_support
- test_status_filter_fabrication.py
- assemble_graph.py
- create_task_backend
- _build_task_dict
- MockerFixture
- enumerate_scope.py
- test_dh_migrate.py
- test_backward_compat_local_plans.py
- parse_item_file
- Path
- parse_show_issue
- Any
- github_client.py
- MockerFixture
- test_addressing.py
- test_github_tools_projects.py
- test_task_status_hook.py
- task_status_hook.py
- manifest_reader.py
- _build_ssl_context
- _write_item_file
- test_github_tools_prs.py
- read_dispatch_plan
- run_cli_subprocess
- _make_snippet_parts
- implementation_manager.py
- test_ledger_cascade_ancestors.py
- ._write_through
- MonkeyPatch
- test_status_source_wire.py
- NavigationResult
- test_progressive_markdown.py
- Development Harness Backend Providers
- _task
- TestBacklogItemMetadataTypeValidator
- _require_int_item_id
- Quick Mode (Step Q)
- github_context_backend.py
- ._verify_queue_keys
- migrate_plan_artifacts.py
- _call
- Path
- MockerFixture
- CommandResult
- ProgressiveDisclosure
- Cursor agent (IDE Agent mode + `agent` / `cursor-agent` CLI) — harness facts
- loads_frontmatter
- WorkGraph
- progressive_markdown/exceptions.py
- CallableMarkdownContentProvider
- resolve_plan_address
- test_dispatch_validation.py
- _save_registry
- DH Workflow Map — Coverage Manifest
- test_linear_artifact_provider.py
- TestBeadsBackendConformance
- TestMilestoneHeaderConstruction
- test_github_flag.py
- _ContentsRepository
- test_backlog_core_parsing.py
- _store_dispatch_plan
- _make_mixed_items
- WorkItemBackend
- _CheckpointedBackend
- Check
- TestTaskRequiredFields
- BdInvocationError
- make_github_client
- sam_plan.py
- _build_over_budget_view
- _make_local_item
- Observation
- beads_artifact_provider.py
- test_reconciliation.py
- BeadsDispatchAdapter
- search.py
- _Predicate
- ledger_spec.py
- emit_result
- _InMemoryArtifactStore
- Evaluate SDLC Layers Skill
- MonkeyPatch
- GitHubArtifactProvider
- _StubEncoder
- Path
- Context-Fit Complexity: Adoption Conditions
- test_backlog_groom_sections.py
- test_rtica_verdict_vocabulary_drift.py
- beads_models.py
- view_result_from_local_item
- _patch_backend
- Blind completeness audit — the workflow multigraph
- TestTaskFieldValidators
- test_agent_profile/conftest.py
- _trace
- _seed_wave
- test_paginate_body.py
- TestBuildIssueBodyFromFileDict
- test_scenarios.py
- TestMainIntegration
- _load_frontmatter_from_path
- bundle_requires_relaxed_verification
- parse_jsonl_events
- handle_subagent_stop
- test_github_tools_labels.py
- build_issue_body_from_file
- Final Verification Skill (SAM Stage 7)
- _item
- TestSelectorAndSlugGeneration
- exit_with_json_error
- TestTaskBookendFields
- TestStatusMap
- TestBackendStatusDefaults
- _item
- test_ledger_spec.py
- new_ledger
- _call
- _populated_cache_state
- issue_to_local_fields
- Technical Researcher
- merge_integration_branch
- _validate_slug
- groom_item
- find_content_duplicates
- _item
- _warnings
- TestCodeBlocks
- _build_all_nodes
- Model fidelity — the workflow multigraph against `ledger_spec.py` and `sam_schema/core/models.py`
- .__init__
- RT-ICA: Reverse Thinking - Information Completeness Assessment
- test_cli.py
- Path
- test_ledger_check_order.py
- TestCommitPrefixRegex
- TestLegacyPathMap
- test_network_guard.py
- test_retired_terms.py
- TestSemanticMatchingInfrastructure
- _CacheStateStore
- build_issue_body
- _validate_metadata
- test_open_pr_search_failure.py
- Findings — finding verification: the falsified predicates, and the severity rule
- cli.py
- ._load_plan
- Path
- TestRealPluginsIntegration
- Path
- _is_not_found_error
- TestParentChildRelationships
- Backlog Item Groomer
- Execution Skill (SAM Stage 5)
- Multi-Perspective Review
- TestBodySpanBoundaries
- dh_config.py
- LayeredGraph
- ADR-9: Close/Resolve Semantic Redesign
- Groomed
- Sample Item Groomed Fixture (fact_check, rt_ica, issue_classification, groomed sections)
- command-routes.schema.json
- Worktree Worker Full Protocol (M1,M2,M4,M8,M9)
- TestTaskAliasHandling
- TestTaskStatusEnum
- MonkeyPatch
- _make_item
- TestEndToEndQueryToResult
- resolve_ca_bundle
- linear_client.py
- Refusal
- RepoResolver
- Findings: producers without consumers between grooming and the bookends
- Task
- Human Touchpoint Model
- dispatch_task
- github_branches.py
- BranchConflictError
- ContentDuplicateMatch
- T-P6-PROTOCOL: Reshape BacklogBackend protocol (generic vs GitHub-specific)
- _section_display_title
- _provider_with_mock_runner
- assemble
- terminate_process_tree
- main
- Verdict Schema — Multi-Perspective Review
- write_test_item
- plan_with
- TestAcceptanceCriterionModel
- TestBackendAvailabilityEnum
- test_placeholder_vocabulary_drift.py
- test_high_level_storage_boundaries.py
- TestRepoDiscoveryError
- test_github_branches.py
- Groom Milestone
- struck_view_result
- dh:interop — Superpowers Plan Interop Adapter
- _canonicalize_patch_keys
- Work Phase 4: Plan
- work-milestone Skill Command
- Harness facts: Hermes Agent (Nous Research)
- Path
- Harness facts: Kilo Code (Kilo CLI / Kilo Code VS Code extension, Kilo-Org/kilocode)
- TestParentIssueNumberValidator
- scripts/task_format.py
- _make_item_with_section
- TestGitCommonRootHangProtection
- _backlog_ops
- TestResolveVerifiedGate
- test_server_sam.py
- _build_artifact_content_comment
- Path
- SAM Pipeline Stages (S1-S7)
- Workflow: Work Backlog Item
- _parse_comment_node
- delete_integration_branch
- TestRetryableErrorBoundedBackoff
- DH work ledger — plan
- Artifact Conventions
- TestArtifactEntryModelValidation
- TestParseManifestSection
- TestLazyRunnerConstruction
- register
- TestBookendVerificationModel
- TestCriterionStatusEnum
- TestModels
- setup-github Command
- .mcp.json
- Fact Check Skill
- _write_item_file
- Step 4.5: Post-Planning Output
- TestBacklogItemReferenceHealing
- TestResolveItem
- TestComputeSlug
- TestReconcileOpenItem
- infer_type
- _parse_frontmatter
- Backlog Core Domain
- SAM 7-Stage Pipeline
- NormalizedEntry
- .read_plan
- Per-Stage Detail
- SAM (Stateless Agent Methodology)
- test_server_pep723_header_omits_typer
- test_the_first_failing_check_is_the_one_the_spec_puts_first
- MonkeyPatch
- test_server_descriptions.py
- test_status_token_vocabulary_drift.py
- create_integration_branch
- _validate_milestone_number
- _make_connection_class
- .__init__
- _assemble_view_compact
- development-harness/conftest.py
- build_concept_query
- _token_count
- .test_a_closed_fetched_issue_without_a_status_label_is_not_fabricated_as_needs_grooming
- TestSyncStatePercent
- _filter_sections_isolated
- _build_graph_dict
- OpenAI Codex CLI harness facts
- OpenCode harness facts
- ._handle_create
- File Classification for Review Skill
- should_skip_hook
- Arranged
- _run_probe
- TestConflictGroupConstruction
- create_backend
- TN Verification Gate
- Layer 0: SDLC-Agnostic
- Linting Discovery Protocol
- TestDispatchPlanConstruction
- TestMCPIncludeClosedPropagation
- test_prepare_clean_worktree.py
- TestReconcileItem
- SOP
- TestFactoryIntegration
- .get_wave_items
- _resolve_section_indices
- bd Invalid JSON Stdout Fixture
- build_body_extra_only
- .test_github_enriched_view_item_returns_real_entry_id_not_zero
- _make_local_item
- close_sqlite_connections
- ReferentResolver
- self_check
- Harness facts: pi (pi coding agent)
- Work: Locate (Phase 1)
- Task T1 (Pure YAML)
- Task Worker
- /dh:complete-implementation
- The work loop
- _normalize_status
- NetworkBlocked
- TestParseAddressPNNN
- Audit Partition D: artifacts-durability-cross-surface-integration
- Audit Partition B: backlog-logical-objects-providers
- Plan and Artifact Lifecycle Policy
- _extract_import_roots
- _RejectedMutation
- _parse_full_database_id
- _run_spawn_item
- Work Backlog Item
- T0 Baseline Sample
- swarm-task-planner
- Output
- backlog pull
- development-harness/progressive_markdown/__init__.py
- Context-Fit Complexity Model
- Evidence Discipline
- dispatch_spawn
- ARCHITECTURE.md
- Backlog Item Lifecycle — Canonical Reference
- addressing.py
- _load_sentinel_issue
- TestPlanNumberResolutionPropertyBased
- Control Set
- TestSlugResolutionPNNN
- TestPriorityEnum
- TestPlanAcceptanceCriteriaStructured
- Clause P1: generic logical work-management purpose
- Clause P3: closed-loop intake through evidence-backed closure
- DH System Model
- TestBookendResultModel
- test_cross_backend.py
- TestWaveItemDefaults
- TestWaveConstruction
- TestCreateWave
- TestErrorPaths
- TestRecursionGuardScenarios
- field_validator
- merge_sections
- title_to_slug
- SyncClaim
- test_comment_database_id.py
- TestParsingCarriesTheIdentifier
- TestTheModelItselfRejectsANonIntDatabaseId
- test_list_status_filter_refusal.py
- TestSectionDisplayTitleConsistency
- Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code)
- Amendments to the findings files
- Default Development Flow
- Agent Resolution Protocol
- test_cli_ledger_holds.py
- The work graph
- _extract_content_from_comment
- _BdRunnerLike
- parse_sam_task_metadata
- _WireSchema
- _live_issue_wearing_an_emoji_label
- TestProbeBackendStatusHonorsEveryTokenVariable
- TestErrorTypeRelationships
- TestFixtureHasThePathology
- TestSyncStateToDict
- TestNarrowBodyToNamedSectionsUnit
- TestRootSectionOrdering
- .test_code_ordinal_matches_pattern
- Harness facts: Claude Code
- _open_pr_refusal
- Artifact Types
- Stage Descriptions
- get_available_features
- TestArtifactManifestModelValidation
- TestComplexityEnum
- TestIssueClassification
- TestTaskEnumCoercion
- TestBackendStatusAllFieldsPopulated
- TestParseCommentNode
- TestBackendStatus
- TestListItems
- TestViewEnrich
- TestQualityGatesConstruction
- TestEnsureSchema
- TestSemanticQueryCorpus
- test_tool_output_schemas.py
- Development Harness Architecture
- _try_register_dispatch_plan_artifact
- Claims register — development-harness
- _poll_until_done
- report
- plan_dir
- MonkeyPatch
- TestBacklogErrorIsBase
- TestCloseItem
- .test_git_common_root_closes_repo_object
- ._validate_artifact_path
- _GraphQLCapable
- _github_reachable
- .test_a_live_labeled_needs_grooming_entry_renders_bare
- .test_a_numeric_issue_falls_back_to_the_backend_owned_status
- TestFalsification
- Process Accumulated Concerns
- Development Harness Router
- ContentProvider
- SyncProvider
- DispatchStateManager
- OrdinalPathMapper
- .test_over_budget_drift_section_returns_directory
- Issue #3152 Fixture
- AGENTS.md
- Context Integration Skill
- Plan: DH Workflow Extractor System
- PRD: DH Workflow Extractor System
- ARL Touchpoints
- Artifact Conventions
- Orchestrator Discipline
- SAM Pipeline
- Harness Role Mapping
- Workflow Pattern Taxonomy
- _resolve_repo_with_timeout
- Layer 1 Overview
- SDLC Layer Separation Architecture
- Dispatch — Orchestrator as Manager
- DH Plugin Known Entities
- DH Workflow Extraction Scope
- plugin:dh:backlog
- plugin:dh:sam
- Alignment Analyst
- Classifier
- Codebase Analyzer
- Context Refinement Agent
- Contract Verification Agent
- Context Gathering Agent
- Doc Drift Auditor
- Ecosystem Researcher
- Feature Researcher
- ARL Human Touchpoints
- Artifact Manifest System
- artifact_register
- Dispatch Orchestration System
- sam_plan
- sam_task
- Plan Validator Agent
- Service Docs Maintainer Agent
- Workflow Extractor Reducer
- .__init__
- Backend Resolution
- Read the Code Review Verdict
- Workflow Extraction Rules
- Dispatcher
- Manager
- Orchestrator
- Stateless Agent Methodology (SAM)
- Worker
- Clause B1: MCP-primary, incomplete CLI surface (current boundary)
- Clause B3: provider/native identifier exposure (current boundary)
- Clause P4: CLI/MCP logical CRUD and queries
- Clause P5: CLI/MCP interchangeable transports
- T-DOC-B4: Document backlog persistence boundary
- DH Component Architecture Package Map
- DH Workflow Explorer
- DH Workflow Graph Node Types
- Plugin Deployment Model
- Which Shape `plan status` Answered In
- Backlog Lifecycle Process Audit (2026-03-02)
- TestParseTableRowEdgeCases
- Workflow-Continuity Risk Lens
- Unified Section Layer Design Brief
- test_backend_factory_import_order
- TestAnalysisMethod
- Workflow Graph Refresh
- Setup Skill Discovery Wizard
- TestTaskFailedStatus
- TestSchemaGapModel
- .test_read_result_with_gaps
- TestToolRegistration
- TestDryRun
- SAM Plan: Gate Token Remote Execution Fix
- Add New Feature (SAM Workflow)
- Analyze Test Failures
- API State
- TestFetchBody
- fixtures_dir
- TestWaveItemKebabCaseAliases
- TestWaveItemConstraints
- CLEAR + CoVe Task Design
- Code Review Architecture Skill
- Claude Skills Code Review
- CLI Code Review
- LLM Integration Code Review
- Node.js Code Review
- Python Code Review
- TypeScript Code Review
- Web Frontend Code Review
- Codebase Auditor Skill
- Codemod Runner Skill
- Migration Fidelity Sign-Off Gate
- Recursive Follow-up Handling
- Complete Milestone Skill
- Comprehensive Test Review Skill
- Context Integration Skill
- Create Artifact Skill
- Development Harness OpenAI Agent
- Repository Inference Patterns
- skill_discovery.yaml — Schema Reference
- Skill Marketplace Search Reference
- Wizard Questions Reference
- Start Task (SAM Task Execution Helper)
- Subagent Contract
- SAM Stage 4 — Task Decomposition
- Test Failure Analysis Mindset
- Fix Validation Protocol
- TestGetWave
- Groom - backlog item - Scope boundary
- Auto Mode Rules
- TestGetWaveItems
- Error Handling Reference
- .test_merge_different_branches_proceeds_to_api
- Feasibility Gate Reference
- Feature Request Template
- ProgressCallback
- _apply_key_filter
- Auto-Groom Check
- Global Manifest Fixture
- Global Manifest with Bold Fields
- Circular Dependencies YAML
- Invalid Status YAML
- Missing Required Fields YAML
- Non-standard Frontmatter Tasks
- Pure Markdown Checklist
- Pure YAML Task Plan
- Multi-task YAML Frontmatter
- Single-task YAML Frontmatter
- YAML Frontmatter Tasks List
- Invalid Plan Bad Ref
- Stale Plan
- session-end-kage-bunshin-child-notify.cjs
- session-end-kage-bunshin-cleanup.cjs
- stop-kage-bunshin-child-notify.cjs
- stop-kage-bunshin-idle-check.cjs
- task-completed-kage-bunshin-reminder.cjs
- .validate_parent_issue_number
- .update_plan_fields
- apply_project_dir_from_argv
- _find_project_root
- Issue Sync (Steps 2.2–2.4)
- _RemoteArtifactProviderFakeSpec
- test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case
- test_default_test_paths_match_pyproject_testpaths
- .test_pull_updates_local
- test_call_sam_cli_delegates_timeout_cleanup_to_terminate_process_tree
- test_an_attempt_clause_in_free_text_is_not_a_launch
- The workflow
- The decomposition-exit gate
- The orchestration loop
- The model
- test_import_boundaries.py
- _ViewBackend
- TestOperationsDoesNotImportFromGithubSync
- TestRenderGroomedSectionConsistency
- .test_progress_callback_updates_state_visible_from_event_loop
- TestPLRLintGate
- test_init_docstring.py
- Hook Subprocess Invocation
- pytest_runtest_protocol
- Config
- Backlog Item Groomed Schema
- Agent Health Check Procedure
- Groom finalize hardening provenance
- _patch_gh_client_batch_fetch
- import_existing_and_leased
- reads_as_plan
- test_guard_covers_testpath
- .test_list_for_milestone_selection
- .test_groomer_list_then_view
- TestCreateBacklogItem
- ._resolved_root_worktree
- SectionMeta
- TestTryGetGithubLogsMissingTokenAsAWarning
- _mock_get_encoding
- .check_reference_integrity
- .__init__
- dh Glossary
- Skill maintenance
- main
- main
- test_canonical_plan_id_leaves_a_non_uid_id_unchanged
- test_artifact_mcp_surface_matches_the_operations_signature
- .__init__
- ._runner
- backlog_core/backends/__init__.py
- backlog_core/tests/__init__.py
- integration/__init__.py
- dh_core/__init__.py
- dispatch_schema/core/__init__.py
- dispatch_schema/readers/__init__.py
- dispatch_schema/writers/__init__.py
- testing-mcp-servers.md
- inject-style-guide.cjs
- session-start-session-id.cjs
- core/backends/__init__.py
- sam_schema/core/__init__.py
- sam_schema/readers/__init__.py
- sam_schema/writers/__init__.py
- prepare_clean_worktree.sh
- completion-verification-gate.md
- qg-dispatch-step.md
- file-classification/SKILL-GOALS.md
- test_build_parser_spawn_effort_flag_listed_in_help
- test_build_spawn_shell_cmd_injects_effort_level_when_set
- test_build_parser_session_id_defaults_to_none
- test_main_resolves_session_id_to_default_for_non_list_subcommands
- test_main_resolves_session_id_from_env_var
- test_main_explicit_session_id_overrides_env_var
- test_main_list_subcommand_leaves_session_id_none_when_not_supplied
- test_session_id_scoping_isolates_registries
- test_cmd_list_all_registries_no_sessions_at_all
- test_cmd_status_shows_session_fields
- dispatch-flow.md
- github-integration-validation.md
- README.md
- tests_sam/__init__.py
- scripted_runner_lib/__init__.py
- plan_dir
- test_list_returns_json_with_items_count_total
- test_list_items_contain_expected_fields
- test_list_search_filters_by_feature_name
- test_list_offset_and_limit_paginate_results
- test_read_task_assignment_includes_plan_fields
- test_read_uses_slug_address
- test_read_invalid_address_exits_with_code_1
- test_read_plan_only_address_returns_plan_json
- test_read_plan_only_address_reads_the_ledger_once_it_holds_the_plan
- test_read_plan_only_address_with_an_attempt_is_refused_on_the_ledger
- test_read_nonexistent_plan_exits_with_code_1
- test_read_missing_plan_dir_exits_with_code_1
- test_status_returns_json_summary
- test_status_nonexistent_plan_exits_with_code_1
- test_status_missing_plan_dir_exits_with_code_1
- test_ready_nonexistent_plan_exits_with_code_1
- test_state_invalid_status_value_is_rejected_by_typer
- test_state_missing_task_component_exits_with_code_1
- test_state_nonexistent_task_exits_with_code_1
- test_validate_canonical_plan_reports_valid
- test_append_task_stdin_carries_fields_absent_from_typed_options
- test_agent_profile/__init__.py
- Workflow Change Process
- dh-meta-docs Skill

## God Nodes (most connected - your core abstractions)
1. `BacklogItem` - 608 edges
2. `Output` - 511 edges
3. `InMemoryBackend` - 260 edges
4. `ContentRef` - 247 edges
5. `BacklogError` - 245 edges
6. `GitHubBackend` - 212 edges
7. `ViewItemResult` - 206 edges
8. `ContentRecord` - 193 edges
9. `_Repository` - 191 edges
10. `ContentWrite` - 190 edges

## Surprising Connections (you probably didn't know these)
- `Sample Item Groomed Fixture (fact_check, rt_ica, issue_classification, groomed sections)` --semantically_similar_to--> `Step 3.1: Auto-Groom`  [INFERRED] [semantically similar]
  plugins/development-harness/tests/fixtures/sample_item_groomed.yaml → plugins/development-harness/skills/work-backlog-item/references/workflows/work/prepare.md
- `create_backend()` --references--> `WorkItemBackend`  [EXTRACTED]
  plugins/development-harness/backlog_core/backend_protocol.py → plugins/development-harness/backlog_core/ARCHITECTURE.md
- `test_create_plan_schema_describes_provider_neutral_identity()` --uses--> `CreatePlanConfig`  [INFERRED]
  plugins/development-harness/sam_schema/tests/test_action_models.py → plugins/development-harness/sam_schema/core/action_models.py
- `RT-ICA: Reverse Thinking - Information Completeness Assessment` --references--> `agent-orchestration:agent-orchestration Skill`  [INFERRED]
  plugins/development-harness/skills/rt-ica/SKILL.md → plugins/development-harness/skills/dispatch/SKILL.md
- `Dispatch — Orchestrator as Manager` --semantically_similar_to--> `Dispatch Contract`  [INFERRED] [semantically similar]
  plugins/development-harness/skills/dispatch/SKILL.md → plugins/development-harness/skills/dispatch-contract/SKILL.md

## Import Cycles
- 5-file cycle: `plugins/development-harness/backlog_core/__init__.py -> plugins/development-harness/backlog_core/_branch_delegates.py -> plugins/development-harness/backlog_core/backend_protocol.py -> plugins/development-harness/backlog_core/backends/beads_backend.py -> plugins/development-harness/backlog_core/github_sync.py -> plugins/development-harness/backlog_core/__init__.py`
- 5-file cycle: `plugins/development-harness/backlog_core/__init__.py -> plugins/development-harness/backlog_core/_branch_delegates.py -> plugins/development-harness/backlog_core/backend_protocol.py -> plugins/development-harness/backlog_core/backends/github_backend.py -> plugins/development-harness/backlog_core/github_sync.py -> plugins/development-harness/backlog_core/__init__.py`

## Hyperedges (group relationships)
- **Backlog Item Grooming Workflow** — plugins_development_harness_skills_work_backlog_item_references_workflows_groom_swarm, plugins_development_harness_skills_work_backlog_item_references_workflows_groom_finalize, plugins_development_harness_agents_technical_researcher [EXTRACTED 0.90]
- **Markdown Progressive Disclosure System** — progressive_markdown_engine, plugins_development_harness_docs_mcp_progressive_disclosure_contract_ordinals, plugins_development_harness_docs_component_architecture_package_map [EXTRACTED 0.90]
- **SAM Planning Pipeline** — skills_work_backlog_item_skill, skills_task_decomposition_skill, skills_start_task_skill [EXTRACTED 0.95]
- **Artifact Management Flow** — plugins_development_harness_agents_md_artifact_register, plugins_development_harness_agents_md_artifact_manifest, plugins_development_harness_agents_md_dh [EXTRACTED 1.00]
- **Backend Capability Protocols** — backlog_core_backend_protocol_workitembackend, backlog_core_backend_protocol_syncprovider, backlog_core_backend_protocol_contentprovider [EXTRACTED 1.00]
- **Backlog Item Creation Workflow** — skills_work_backlog_item_references_workflows_create_start, skills_work_backlog_item_references_workflows_create_scope [EXTRACTED 1.00]
- **Backlog Grooming Workflow** — skills_work_backlog_item_references_workflows_groom_intake, skills_work_backlog_item_references_workflows_groom_analyze, skills_work_backlog_item_references_workflows_groom_finally [EXTRACTED 1.00]
- **Backlog Grooming Swarm** — plugins_development_harness_agents_impact_analyst, plugins_development_harness_agents_rtica_assessor [EXTRACTED 1.00]
- **Bookend Verification Pattern** — plugins_development_harness_agents_swarm_task_planner, plugins_development_harness_agents_t0_baseline_capture, plugins_development_harness_agents_tn_verification_gate [EXTRACTED 1.00]
- **Code Review Skill Stack** — skills_code_review_python_skill, skills_code_review_typescript_skill, skills_code_review_nodejs_skill, skills_code_review_web_skill, skills_code_review_llm_skill, skills_code_review_cli_skill, skills_code_review_claude_skills_skill, skills_code_review_architecture_skill [EXTRACTED 1.00]
- **Complete Implementation Workflow** — skills_complete_implementation_references_concerns_processing, skills_complete_implementation_references_migration_fidelity_gate, skills_complete_implementation_references_final_handoff [EXTRACTED 1.00]
- **Grooming Swarm Agents** — plugins_development_harness_agents_alignment_analyst, plugins_development_harness_agents_classifier, plugins_development_harness_agents_fact_checker, plugins_development_harness_agents_backlog_item_groomer [EXTRACTED 1.00]
- **Layer 0 Design to Skill Reference Merger** — docs_sdlc_layers_layer_0_arl_touchpoints, docs_sdlc_layers_layer_0_artifact_conventions, docs_sdlc_layers_layer_0_sam_pipeline [EXTRACTED 1.00]
- **Multi-Perspective Review Team** — plugins_development_harness_agents_reviewer_accessibility, plugins_development_harness_agents_reviewer_performance, plugins_development_harness_agents_reviewer_quality, plugins_development_harness_agents_reviewer_security [EXTRACTED 1.00]
- **SAM Execution Flow** — plugins_development_harness_agents_md_feature_researcher, plugins_development_harness_agents_md_swarm_task_planner, plugins_development_harness_agents_md_task_worker, plugins_development_harness_agents_md_code_reviewer [EXTRACTED 1.00]
- **SAM Pipeline Stages** — plugins_development_harness_readme_add_new_feature, plugins_development_harness_readme_implement_feature, plugins_development_harness_readme_complete_implementation [EXTRACTED 1.00]
- **SAM Verification Flow** — tests_sam_fixtures_plan_with_bookends, tests_sam_fixtures_t0_baseline_sample, tests_sam_fixtures_tn_verification_sample [EXTRACTED 1.00]
- **Logging Service Task Chain** — tests_sam_fixtures_pure_yaml_directory_task_t1, tests_sam_fixtures_pure_yaml_directory_task_t2, tests_sam_fixtures_pure_yaml_directory_task_t3 [EXTRACTED 1.00]
- **Technical Research Flow** — plugins_development_harness_agents_technical_researcher, dh_api_state, dh_ecosystem_research, dh_impact_measurement, dh_codebase_auditor, dh_research_note [EXTRACTED 1.00]
- **SAM Task Plan Formats** — tests_sam_fixtures_pure_yaml_single, tests_sam_fixtures_pure_yaml_directory_plan, tests_sam_fixtures_yaml_frontmatter_multi [INFERRED 0.80]
- **Quality Assurance & Validation Framework** — skills_validation_protocol_skill, skills_verify_done_skill, skills_test_failure_mindset_skill, skills_subagent_contract_skill [INFERRED 0.85]
- **Research and Analysis Agents** — plugins_development_harness_agents_codebase_analyzer, plugins_development_harness_agents_ecosystem_researcher, plugins_development_harness_agents_feature_researcher, plugins_development_harness_agents_doc_drift_auditor [INFERRED 0.85]
- **Implementation Verification Layer** — plugins_development_harness_agents_feature_verifier, plugins_development_harness_agents_integration_checker [INFERRED 0.90]
- **SAM Pipeline Agents** — plugins_development_harness_agents_code_reviewer, plugins_development_harness_agents_context_refinement, plugins_development_harness_agents_contract_verification, plugins_development_harness_agents_dh_context_gathering [INFERRED 0.90]

## Communities (804 total, 196 thin omitted)

### Community 0 - "ItemContentNormalizer"
Cohesion: 0.03
Nodes (90): _build_entries(), _is_entry_section_metadata(), ItemContentNormalizer, NormalizedEntry, _parse_section_titles(), TypeGuard, Normalize ViewItemResult into an ordered list[NormalizedSection]. Single…, Return ``True`` when *section* is ``SectionEntryMetadata``. Discriminates the… (+82 more)

### Community 1 - "ContentTaskProvider"
Cohesion: 0.03
Nodes (65): _MutationResult, ContentTaskProvider, PlanUpdateValue, Task, Create and persist a plan. Returns: The created plan., Atomically reassign plan ownership., Update and persist plan fields., Claim and persist a task. Returns: Whether the task was claimed. (+57 more)

### Community 2 - "backlog_core/models.py"
Cohesion: 0.01
Nodes (269): AddedCommentNode, AssigneeNode, LabelNode, MilestoneFullNode, MilestoneNode, datetime, TypedDict, Backend-agnostic contracts for backlog implementations. (+261 more)

### Community 3 - "ContentRef"
Cohesion: 0.01
Nodes (275): load_manifest(), publish_artifact(), Revision-safe persistence for artifact manifests., Publish immutable content before atomically advancing its manifest entry.…, Load a manifest and the revision required for its next write. Returns: The…, Register one entry with bounded compare-and-swap retries. Returns: The…, register_manifest_entry(), ContentProvider (+267 more)

### Community 4 - "write_plan"
Cohesion: 0.02
Nodes (131): LiteralScalarString, PlanUpdateValue, Update top-level fields on a plan. Args: plan_id: Backend-assigned plan…, PlanUpdateValue, Update plan or task fields via a unified write operation. Supports three non-…, update_plan_fields(), append_section(), _atomic_write() (+123 more)

### Community 6 - "test_backlog_core_server.py"
Cohesion: 0.01
Nodes (324): _call(), _make_output_dict(), _make_view_result(), parametrize, Tests for the FastMCP 3.x server layer in backlog_core/server.py. All 10 MCP…, backlog_view with include_content=False response has 'sections_metadata' list.…, backlog_view with summary=True (default) returns 5-field routing manifest.…, backlog_view summary=True _hint embeds the exact selector the caller passed.… (+316 more)

### Community 7 - "sam_schema/core/models.py"
Cohesion: 0.01
Nodes (278): claim_task(), clear_active_task(), get_active_task(), list_plans(), ValueError, Retrieve the active task context for a session. This is the unified operation…, Store a task address as the active task for a session. This is the unified…, Update fields and/or append a section on the active task. This is the unified… (+270 more)

### Community 8 - "GitHubBackend"
Cohesion: 0.02
Nodes (203): GitHubBackend, datetime, MergeResult, Return a PyGithub Repository (raises GitHubUnavailableError on failure).…, Check backend availability and return a status report. Returns: BackendStatus…, Report whether a GitHub token is configured for this backend. This provider-…, Report whether a durable, honest provider snapshot has ever completed. Returns:…, Report whether the most recent local snapshot load skipped any unreadable file.… (+195 more)

### Community 9 - "_Repository"
Cohesion: 0.01
Nodes (149): GitHubExtras, IssueNode, Any, GitHub-specific surface only ``GitHubBackend`` implements. Backends that are…, Single issue from GraphQL query. Maps to repository.issue or issues.nodes[].…, Return None — beads does not use PyGithub Repository., Raise NotImplementedError — beads does not use PyGithub Repository. The…, Raise NotImplementedError — beads IDs are strings. Use… (+141 more)

### Community 10 - "cli_active_task.py"
Cohesion: 0.07
Nodes (47): CommentListEntry, BaseModel, One comment entry as returned by list_comments(). ``id`` is the GraphQL node…, MissingSessionIdError, Raised when an active-task operation is attempted without a real session id., Reject a missing, empty, or sentinel session id for an active-task operation.…, require_session_id(), active_task_clear() (+39 more)

### Community 11 - "BacklogItem"
Cohesion: 0.01
Nodes (119): List work items from the provider-private cache. Returns: Persisted work items., Get a cached work item by stable reference. Returns: The matching work item., Persist a work-item intent for provider reconciliation., Fetch the current status string for a single item. Returns: Status string (e.g.…, Transition an item to in-progress state on the backend., Transition an item to verified state on the backend., Transition an item to groomed state on the backend., Transition an item to blocked state on the backend. (+111 more)

### Community 12 - "parsing.py"
Cohesion: 0.01
Nodes (216): _deduplicate_timestamps(), _entry_from_span(), EntrySpan, _find_balanced_close(), find_entry_spans(), _is_entry_id(), _match_struck(), _new_entry_block() (+208 more)

### Community 13 - "MockerFixture"
Cohesion: 0.06
Nodes (32): allow_startup_sync, Reset the singleton to a fresh SyncState. Intended for tests only. Must be…, reset_sync_state(), fresh_sync_state(), fixture, MockerFixture, Background sync starts exactly once when the lifespan initialises. The lifespan…, Two consecutive lifespan entries must produce exactly one sync start. (+24 more)

### Community 14 - "test_beads_models.py"
Cohesion: 0.05
Nodes (78): Create a beads milestone issue via ``bd create --type milestone``. Args: title:…, BeadsIssueType, BeadsPriority, BeadsStatus, parse_issue(), IntEnum, StrEnum, Numeric priority levels (lower is more urgent). (+70 more)

### Community 15 - "backlog_list"
Cohesion: 0.05
Nodes (105): alias, artifact_get(), artifact_list(), artifact_read(), artifact_register(), _artifact_type(), backlog_add(), backlog_assign_item_to_milestone() (+97 more)

### Community 16 - "ArtifactManifest"
Cohesion: 0.02
Nodes (157): ArtifactRegistry, parse_manifest_section(), ItemId, Extract and parse the artifact manifest section from an issue body. Returns an…, Render an ``ArtifactManifest`` as a delimited markdown section. Produces the…, Replace the manifest section in an issue body, or append it if absent.…, Stateless business-logic layer for artifact manifest operations. All methods…, Upsert an artifact entry into the manifest. Upsert logic: - If an existing… (+149 more)

### Community 17 - "OrdinalPathMapper"
Cohesion: 0.02
Nodes (152): NormalizedSection, One section in document-order, with its ordered entries., code_only_entry_doc(), deeper_nesting_doc(), empty_section_doc(), groomed_body_doc(), _load_fixture(), _make_sections() (+144 more)

### Community 18 - "tests_sam/test_server.py"
Cohesion: 0.02
Nodes (209): Return the prospective plan after applying a task-level patch. The task…, _validated_task_patch_plan(), ClaimTaskConfig, CreatePlanConfig, model_validator, Task, Read a task and return a TaskAssignment (plan context + task fields).…, Claim a task (transition from not-started to in-progress). (+201 more)

### Community 19 - "InMemoryTaskProvider"
Cohesion: 0.02
Nodes (149): _build_plan_data(), BeadsTaskProvider and BeadsContextBackend — beads (bd CLI) backend for SAM.…, Extract doc content delimited by HTML-comment markers from issue notes. Args:…, Retrieve a document from bd issue notes by its handle. Parses the ``<!--…, Build a PlanData dict from a beads epic and task list. Args: plan_id: SAM plan…, Create a beads epic for the plan and child issues for each task. Plan ID is…, DocumentBackend, GitHubTaskProvider (+141 more)

### Community 20 - "_heading_path"
Cohesion: 0.50
Nodes (4): _heading_path(), Build a nested heading ordinal the way OrdinalPathMapper does. Mirrors the…, composite, DrawFn

### Community 21 - "InMemoryBackend"
Cohesion: 0.01
Nodes (142): InMemoryBackend, _now(), Any, MergeResult, In-memory backend for use in tests. All state lives in plain Python dicts and…, Report whether any mutation is queued and unacknowledged. Always ``False`` —…, Initialise empty in-memory storage for all backend state., List native in-memory work items. (+134 more)

### Community 22 - "Task"
Cohesion: 0.02
Nodes (157): append_task(), create_plan(), finalize_plan(), _plan_fields_for_update(), Task, Validate raw JSON patch fields through the Pydantic Task model. Reads the…, Update fields and/or append a section to a task. This is the unified operation…, Create a new plan with the given slug, goal, and task definitions. This is the… (+149 more)

### Community 23 - "load_item"
Cohesion: 0.02
Nodes (161): LegacyMigrationError, ValueError, Legacy item cannot be migrated without data loss., Parse a legacy item and verify its YAML representation without persisting it.…, Persist one verified legacy item as a YAML snapshot beside its source. Args:…, r"""Render a YAML BacklogItem's structured sections into a markdown body…, render_sections_as_body(), merge_entries() (+153 more)

### Community 24 - "GistTaskLayer"
Cohesion: 0.02
Nodes (161): ArtifactRegistryClient, _get_provider(), PlanContentUnavailableError, Thin wrapper decoupling GistTaskLayer from the backlog_core artifact surface.…, Return the provider, creating it lazily on first call. Returns: The configured…, Upload plan YAML to GitHub Gist via the artifact registry. Registers a manifest…, Retrieve plan YAML from the configured GitHub provider. Gist-first retrieval…, Upload the plan-index YAML to the sentinel issue's Gist. Args: sentinel_issue:… (+153 more)

### Community 26 - "test_ledger_conformance.py"
Cohesion: 0.03
Nodes (177): What one command does from one status: checks in order, then effects and events., Transition, Check every instruction against the tier it declares. Args: instructions: The…, Build and return a MarkdownDocument from a ParserResult. Args: result: Output…, accept_complete(), accept_refusal(), accept_returned(), add_reports() (+169 more)

### Community 27 - "BeadsBackend"
Cohesion: 0.02
Nodes (133): _beads_priority_for_item_priority(), _beads_status_for_item_status(), _beads_type_for_item_type(), _beads_workspace_path(), BeadsBackend, _collapse_beads_status(), _normalize_due_at(), Path (+125 more)

### Community 28 - "test_query.py"
Cohesion: 0.03
Nodes (139): Read a single task with its full plan context and return a TaskAssignment. This…, read_task(), Composite response returned by ``sam read P{N}/T{M}``. Combines plan-level…, TaskAssignment, claim_task(), create_plan(), get_plan_status(), get_ready_tasks() (+131 more)

### Community 29 - "_BuildState"
Cohesion: 0.13
Nodes (15): _build_selector(), _BuildState, _code_summary(), _make_slug(), Generate a deterministic one-line summary for a code block. Args: language:…, Walk token stream; dispatch heading and fence tokens to phase methods. Args:…, Extract and process a heading_open token. Updates state in-place. Args: token:…, Extract and process a fence token. Updates state.code_blocks in-place. Args:… (+7 more)

### Community 30 - "backlog_core/server.py"
Cohesion: 0.02
Nodes (155): Response shape returned by the ``artifact_register`` MCP tool. Indicates…, RegisterResult, _apply_fields_projection(), _apply_item_depth(), _assert_config(), _build_section_miss_error(), _build_sync_state_block(), _dedup_by_issue_number() (+147 more)

### Community 31 - "BacklogViewDisclosureHandler"
Cohesion: 0.03
Nodes (102): BacklogViewDisclosureHandler, DisclosureRequest, StatusSource, Disclosure handler for the MCP progressive disclosure contract. This module is…, Orchestrate progressive disclosure modes from un-gated item content.…, Initialise handler with optional injected collaborators. Args: normalizer:…, Fetch item content and dispatch to the appropriate disclosure handler. Calls…, Build a structural map response. ``MapResponse.total_est_tokens`` sums LEVEL-1… (+94 more)

### Community 32 - "MockerFixture"
Cohesion: 0.03
Nodes (109): make_add_comment_response(), make_add_sub_issue_response(), make_create_issue_response(), make_created_issue_node(), make_issue_by_number_response(), make_issue_comment_node(), make_issue_comments_response(), make_issue_node() (+101 more)

### Community 33 - "transitions.py"
Cohesion: 0.04
Nodes (135): Cursor, fetch_task(), json_list(), now(), plan_tasks(), Return the current instant as naive UTC at second precision. Returns: The…, Read a cursor into dictionaries keyed by column name. Args: cursor: A cursor…, Decode a JSON array column into a list of strings. Args: raw: The stored column… (+127 more)

### Community 34 - "dh_paths.py"
Cohesion: 0.04
Nodes (95): Read ``backlog.startup_sync.enabled`` from one config file. Isolates the…, Read ``backlog.startup_sync.enabled`` from .dh/config.yaml files. Returns the…, _read_enabled_from_config_file(), _read_startup_sync_enabled_from_yaml(), backlog_dir(), context_dir(), _dh_user_root(), ensure_dirs() (+87 more)

### Community 35 - "artifact_provider.py"
Cohesion: 0.02
Nodes (140): ArtifactBackend, create_artifact_provider(), GitLabArtifactProvider, _is_dict_of_object(), LinearArtifactProvider, ItemId, Path, Protocol (+132 more)

### Community 36 - "GroomedData"
Cohesion: 0.02
Nodes (86): _merge_groomed(), merge_item(), _parse_groomed_section(), _parse_metadata_block(), GitHub sync adapter: YAML BacklogItem <-> GitHub issue body markdown…, Extract key/value pairs from the ``<!-- backlog-metadata: -->`` comment. Args:…, Parse a ``Groomed (date)`` heading name + body into a GroomedData model. Args:…, Merge two GroomedData objects keeping longer subsection content. Args: local:… (+78 more)

### Community 37 - "parse_entries"
Cohesion: 0.02
Nodes (112): _apply_show_filter(), generate_diff(), parse_entries(), Apply the ``show`` filter to parsed entries. Returns: Filtered list of Entry…, Parse entry blocks from a section body. Args: section_body: Raw section text to…, Orchestrate section content modifications using entry blocks. Returns: Modified…, Generate a git-diff style comparison of entry blocks between local and remote.…, rewrite_section() (+104 more)

### Community 38 - "run_quality_gates"
Cohesion: 0.03
Nodes (87): CommandResult, GateResult, GateRunMode, computed_field, True iff exit_code == 0., Aggregate result of a quality gate run., Execution strategy for a quality gate run., Result of executing one gate command. (+79 more)

### Community 39 - "call_mcp_tool"
Cohesion: 0.04
Nodes (125): call_mcp_tool(), Call a tool through the in-memory FastMCP transport and parse the result. Args:…, _assert_compact_result(), _invoke_cli(), _mint_plan_id_with_a_letter_in_its_hex_suffix(), Any, _CASE_SPELLINGS, integration (+117 more)

### Community 40 - "_extract_response_dict"
Cohesion: 0.05
Nodes (72): _extract_response_dict(), _find_rt_ica_ordinal(), _find_subheading_entry_ordinal(), _load_fixture(), normalized_2515(), normalized_recursive_nav(), fixture, MockerFixture (+64 more)

### Community 41 - "MockerFixture"
Cohesion: 0.03
Nodes (81): list_items(), List backlog items. Default reads provider-backed record only. Use refresh=True…, Any, MockerFixture, parametrize, list_items(search=...) filters via backlog_core.search; None skips filtering…, list_items returns empty list when backlog directory has no items., Verify list_items returns items=[] when backlog directory is empty. Tests:… (+73 more)

### Community 42 - "test_startup_sync.py"
Cohesion: 0.03
Nodes (98): ContentProviderError, Exception, Raised when all repository discovery methods fail. Attributes: methods_tried:…, Base error for logical content capability failures., RepoDiscoveryError, _attempt_sync(), _count(), _make_progress_callback() (+90 more)

### Community 43 - "test_ledger_port.py"
Cohesion: 0.03
Nodes (115): Return a placeholder string proportional to the token count., clear_plan(), content_store(), created_payload(), existing_plan(), export_plan(), from_milestone(), import_plan() (+107 more)

### Community 44 - "test_section_registry.py"
Cohesion: 0.02
Nodes (106): heading_to_section_key(), Return the BacklogItem.sections key for a markdown heading text, or None if…, _normalize_section_key(), Return the canonical storage key for a section name. Resolves the name through…, heading_to_unknown_key(), Convert an arbitrary section heading/name to its canonical storage key. Inverse…, StrEnum, Canonical section-name registry — the single source of truth for backlog… (+98 more)

### Community 45 - "BacklogConfig"
Cohesion: 0.02
Nodes (154): Backend Protocol — implementation-agnostic abstraction for backlog storage.…, Register the active BacklogConfig. Args: config: BacklogConfig instance…, Clear the cached BacklogConfig singleton. Intended for test teardown — call…, reset_config(), set_config(), BacklogConfig, Container for the active backend instance. This dataclass replaces direct…, BacklogConfig (+146 more)

### Community 46 - "_patch_github_body"
Cohesion: 0.03
Nodes (79): Offline-safe ``tiktoken`` for backlog_core view tests (PR #2496 Codex finding).…, Regression tests for Failure 1 concurrent-write race scenario. Failure 1…, MockerFixture, mark_groomed=True emits warning and sets mark_groomed_skipped when re-lookup…, groom_item with mark_groomed=True and no content args must NOT call…, groom_item with mark_groomed=True AND groomed_content calls update_item with…, test_groom_item_mark_groomed_no_content_does_not_call_update_item(), test_groom_item_mark_groomed_skipped_when_item_not_found_after_reparse() (+71 more)

### Community 47 - "BeadsTaskProvider"
Cohesion: 0.04
Nodes (69): BeadsTaskProvider, Return a summary dict of task status counts for a plan. Args: plan_id: SAM plan…, TaskBackend implementation routing SAM plan/task operations to the bd CLI.…, Attempt to claim a task using ``bd claim``. ``bd claim`` is the atomic…, Update one or more scalar fields on a task via ``bd update``. Supported keys:…, _FakeBdRunner, _ListParentBdRunner, _ListShowBdRunner (+61 more)

### Community 48 - "LocalFilesystemArtifactProvider"
Cohesion: 0.03
Nodes (71): LocalFilesystemArtifactProvider, ItemId, Path, Local filesystem implementation of the ArtifactBackend protocol. Stores…, Persist *manifest* for *item_id* atomically. Acquires an exclusive advisory…, Read artifact file content from the root worktree. Args: path: Repo-relative…, Store artifact content as a file in the repository worktree. Writes content…, Read artifact content. This provider has no remote backend. Delegates to… (+63 more)

### Community 49 - "ArtifactType"
Cohesion: 0.05
Nodes (64): _get_migrate_yaml(), _migrate_classify_plan_file(), _migrate_coerce_issue(), _migrate_discover_candidates(), migrate_dry_run(), _migrate_extract_issue(), _migrate_find_issue_via_backlog(), migrate_live_run() (+56 more)

### Community 50 - "store.py"
Cohesion: 0.04
Nodes (110): Column, One column of a materialised table., add_column_ddl(), admits_integer(), affinity(), append_event(), blank_row(), carried() (+102 more)

### Community 51 - "TaskBackend"
Cohesion: 0.03
Nodes (66): get_plan_status(), get_ready_tasks(), PlanStatus, Return plan-level progress summary including autonomy mode. This is the unified…, Return tasks ready for dispatch along with plan-level metadata. This is the…, Unified backend protocol for the development harness. This module defines the…, Any, PlanUpdateValue (+58 more)

### Community 52 - "test_consolidated_tools.py"
Cohesion: 0.04
Nodes (90): InMemoryContextBackend, InMemoryContextBackend — in-memory ContextBackend implementation. Dict-based…, In-memory ContextBackend for testing. Stores ActiveTaskContext objects in a…, Initialise an empty in-memory context store., Remove the stored context for a session. Args: session_id: Session identifier.…, ContextBackend, Protocol, ContextBackend Protocol — implementation-agnostic abstraction for session… (+82 more)

### Community 53 - "ProgressiveMarkdownNavigator"
Cohesion: 0.03
Nodes (58): ProgressiveMarkdownNavigator, Load and parse markdown from the provider. Args: source: Source identifier…, Token-budget-aware navigator over a parsed markdown document. Provides document…, Tests for the NavigationResult Pydantic model., NavigationResult.model_dump_json() produces valid JSON that roundtrips., current_content() returns the content of the current page., current_content() returns empty string when no pages., model_dump() includes kind, title, pages, current_page, total_pages, has_more. (+50 more)

### Community 54 - "FormatType"
Cohesion: 0.04
Nodes (98): A missing or invalid field detected during legacy format reading. Schema gaps…, SchemaGap, FormatType, StrEnum, Supported task/plan file formats., detect_gaps(), normalize_plan(), normalize_task() (+90 more)

### Community 55 - "ViewItemResult"
Cohesion: 0.04
Nodes (56): Result of viewing a single backlog item, optionally enriched with GitHub data., ViewItemResult, Negative offset clamps to 0 (all entries) and must NOT report truncation. RED…, Intended contract: offset past the last entry → empty body, no flag. Mirrors…, A normal in-range page still reports remaining entries (no behavior change)., test_in_range_middle_page_reports_remaining(), test_negative_offset_returns_all_without_false_truncation(), test_offset_past_end_returns_empty_without_truncation_flag() (+48 more)

### Community 56 - "BeadsArtifactProvider"
Cohesion: 0.04
Nodes (55): BeadsArtifactProvider, Beads CLI implementation of the ``ArtifactBackend`` Protocol. Stores artifact…, _make_entry(), Unit tests for BeadsArtifactProvider. Coverage target: ≥85% line and ≥80%…, Flat dh.artifacts key is parsed into an ArtifactManifest., Nested {'dh': {'artifacts': ...}} key is parsed into an ArtifactManifest., get_manifest_bd calls run_json(["show", issue_id])., BdNotInstalledError from run_json propagates unchanged. (+47 more)

### Community 57 - "test_validator.py"
Cohesion: 0.06
Nodes (88): ConflictGroup, _DispatchBase, ItemPriority, ItemStatus, MilestoneHeader, BaseModel, StrEnum, QualityGates (+80 more)

### Community 58 - "port.py"
Cohesion: 0.04
Nodes (84): clearable_tables(), conflict_groups_for(), content_plan(), content_task(), ContentProjectionStore, decode_row(), divergences(), excluded_columns() (+76 more)

### Community 59 - "client"
Cohesion: 0.02
Nodes (89): client(), parametrize, sam_active_task stores separate contexts for different session_ids. Tests:…, Every sam_active_task action rejects a missing session_id. Regression guard for…, In-memory MCP client connected to the configured SAM server., An explicitly empty session_id is rejected the same way as an omitted one., Passing the reserved '_default' sentinel directly is rejected too, not just…, Server registers the 3 consolidated tools via the MCP protocol. Tests: Tool… (+81 more)

### Community 60 - "DHConfig"
Cohesion: 0.12
Nodes (51): _ALL_SUBSYSTEMS, DHConfig, Unified backend-name resolver using .dh/config.yaml. Resolution order per…, _TASK_AND_CONTEXT, _clear_all_backend_env_vars(), MonkeyPatch, Path, TDD tests for DHConfig — unified backend-name resolver using .dh/config.yaml.… (+43 more)

### Community 61 - "ledger/__init__.py"
Cohesion: 0.04
Nodes (83): Autonomy, check_commands(), The map from a ``ledger_spec.COMMANDS`` name to the callable that implements…, Reject a surface that does not match ``ledger_spec.COMMANDS`` one to one.…, attempt_open(), check_progress_values(), expired(), expired_row() (+75 more)

### Community 62 - "Section"
Cohesion: 0.05
Nodes (58): A named section within a backlog item containing an ordered list of entries., Section, _filter_sections(), r"""Render a ``## Sections`` index block listing all sections with counts. Each…, Return a filtered subset of *item.sections* matching *section*. Delegates form…, _render_section_index(), Section has an entries list., TestSection (+50 more)

### Community 63 - "spawn.py"
Cohesion: 0.05
Nodes (85): _build_parser(), _build_spawn_record(), _build_spawn_shell_cmd(), check_session_limit(), _claude_tmux_session_name(), cmd_kill(), cmd_list(), cmd_read() (+77 more)

### Community 64 - "Path"
Cohesion: 0.03
Nodes (54): compute_slug(), Compute project slug from absolute path. Algorithm: replace every ``/`` in…, isolated_project(), project_with_dirs(), fixture, MonkeyPatch, parametrize, Path (+46 more)

### Community 65 - "BdRunner"
Cohesion: 0.06
Nodes (73): _bd_env(), BdRunner, JsonValue, Lazy subprocess wrapper for the ``bd`` CLI. Parameters ----------…, Run ``bd`` with *argv*, inject ``--json`` if absent, parse output. Parameters…, Run ``bd`` with *argv* and return raw stdout. Parameters ---------- argv:…, Return ``True`` if ``bd`` is on ``PATH`` and responds to ``version``. The…, Return the filtered base environment merged with instance-level overrides.… (+65 more)

### Community 66 - "DisclosureRequestParser"
Cohesion: 0.04
Nodes (78): DisclosureRequestParser, Parse disclosure parameters and return a validated ``DisclosureRequest``. Args:…, Validate and parse four optional MCP parameters into a ``DisclosureRequest``.…, DisclosureParamError, Exception, Invalid disclosure parameter combination. Attributes: message: Human-readable…, Initialize with a human-readable message and the offending parameters., Tests for DisclosureRequestParser.parse() — TDD, authored before T16… (+70 more)

### Community 67 - "GitHubGistArtifactProvider"
Cohesion: 0.04
Nodes (57): GitHubGistArtifactProvider, _make_github_client(), Github, Read artifact file content from the root worktree filesystem. Validates that…, Raise ``ValueError`` when *path* fails the path traversal check. Args: path:…, Create a PyGithub :class:`~github.Github` client through the shared factory.…, Convert a repo-relative artifact path to a valid Gist filename. Gist filenames…, Replace an inline manifest block with a Gist sentinel comment. When the legacy… (+49 more)

### Community 68 - "IssueCommentNode"
Cohesion: 0.03
Nodes (87): IssueCommentNode, BaseModel, Comment node returned from issue comments listing query. ``id`` is GitHub's…, Fetch all comments on an issue. Returns: List of IssueCommentNode instances., Fetch a single comment by its GraphQL node ID. Returns: IssueCommentNode…, _body_digest(), _CommentMetadata, parse_work_item_comment() (+79 more)

### Community 69 - "discover_repo"
Cohesion: 0.04
Nodes (53): discover_repo(), _discover_via_env(), Validate that *slug* matches ``owner/repo`` format. Args: slug: Candidate…, Return the ``GITHUB_REPO`` environment variable value if set and valid.…, Discover the current repository's ``owner/repo`` slug. Resolution priority…, _validate_repo_slug(), clear_discover_repo_cache(), _make_mock_repo() (+45 more)

### Community 70 - "test_scripted_runner.py"
Cohesion: 0.05
Nodes (77): LoopRecord, Everything one run of the loop did and saw., assert_satisfied(), Observation, parametrize, The scripted runner: the whole work loop driven by the ``sam plan`` CLI and…, Fail with the observation's own wording when it is unsatisfied. Args:…, The entry script carries the canonical shebang, a PEP 723 block, and the… (+69 more)

### Community 71 - "open_ledger"
Cohesion: 0.05
Nodes (76): check_local_filesystem(), connect(), database_path(), ensure_schema(), existing_columns(), fetch_plan(), filesystem_type(), holds() (+68 more)

### Community 72 - "_PositionedHeading"
Cohesion: 0.20
Nodes (9): _extract_heading_text(), _PositionedHeading, Match, Record the source position, then parse the heading normally. Returns: The match…, Attach the recorded source position to the parsed heading., Reconstruct heading text from all inline descendants of a marko Heading node.…, A ``Heading`` that records where its own source line begins. marko 2.2.2…, Heading (+1 more)

### Community 73 - "test_action_models.py"
Cohesion: 0.03
Nodes (63): AppendTaskInput, _CliInput, CreatePlanInput, PlanUpdateFields, PlanUpdateInput, BaseModel, field_validator, model_validator (+55 more)

### Community 74 - "test_agent_portability_and_verdict_drift.py"
Cohesion: 0.04
Nodes (73): agent_files(), chain_steps_named(), cli_definition_tag_offenders(), _extract_tag_block(), governed_files(), guide_relocation_scan_files(), matching_lines(), plugin_root_variable_offenders() (+65 more)

### Community 75 - "scripted_runner.py"
Cohesion: 0.06
Nodes (59): build_parser(), The loop itself: the order ``work-loop.md`` and ``runner-contract.md`` put the…, Bind the driver to one CLI, one fixture set and one workspace. Args: cli: How…, CommandTimeoutError, FixtureMissingError, RuntimeError, Failing loudly: every reason a run stops, named rather than left to a traceback., A program the run needs is not resolvable on PATH. (+51 more)

### Community 76 - "read_manifest_plan"
Cohesion: 0.05
Nodes (71): Read a global-manifest format plan file. The global manifest format has: - A…, read_manifest_plan(), Path, Tests for sam_schema.readers.manifest_reader — global manifest format reader., Verify per-task YAML blocks in body provide structured fields like agent.…, Verify frontmatter entry status takes precedence over body YAML block status.…, Verify body content survives the read -> write round-trip for the hybrid…, Verify the real tasks-1-backlog-state-reconciliation.md has non-empty body… (+63 more)

### Community 77 - "DispatchItemRecord"
Cohesion: 0.04
Nodes (68): artifact_content_reference(), Return the immutable content identity referenced by an artifact entry. The…, dispatch_stale_check(), SQLite-backed state manager for dispatch orchestration. This module is…, Insert a wave row and all item rows. Args: milestone: GitHub milestone number.…, Route stale-PID detection through beads or SQLite based on BACKLOG_BACKEND.…, ArtifactContent, DispatchItemRecord (+60 more)

### Community 78 - "get_repo_root"
Cohesion: 0.05
Nodes (46): _get_migrate_artifact_provider(), Create the artifact provider used by a migration run. Returns: An artifact…, _discover_repo_with_root(), _discover_via_git(), get_backlog_dir(), get_config(), get_default_repo(), get_repo_root() (+38 more)

### Community 79 - "view_item"
Cohesion: 0.04
Nodes (45): View a backlog item or GitHub issue by URL, #N, bare number, or title. For…, view_item(), main(), Path, Regenerate full-content test fixtures for backlog issues. Calls…, Fetch full content for *issue_num* and write the fixture JSON file. Calls…, Regenerate all fixtures, printing a summary line per issue., regenerate() (+37 more)

### Community 80 - "migrate_tasks_to_github.py"
Cohesion: 0.05
Nodes (65): has_yaml_frontmatter(), Any, Task format detection and field resolution utilities. Provides helpers for…, r"""Return True if content begins with a valid YAML frontmatter block. A valid…, Resolve the task ID from a parsed YAML frontmatter dict. Supports both…, resolve_task_id(), _connect_github(), derive_slug() (+57 more)

### Community 81 - "BeadsContextBackend"
Cohesion: 0.04
Nodes (44): BdJsonDecodeError, BdNotInstalledError, Lazy subprocess wrapper for the bd (beads) CLI. All subprocess I/O is…, ``bd`` stdout could not be parsed as JSON. Attributes: raw_output: Raw stdout…, ``bd`` binary is not on ``PATH``. Callers catching this exception should…, BeadsContextBackend, ContextBackend persisting active-task context via bd remember. Context is…, Store the runner. No filesystem or subprocess activity at init. (+36 more)

### Community 82 - "test_mcp_call_shape_drift.py"
Cohesion: 0.06
Nodes (61): _artifact_call_spans(), _artifact_register_cli_defects(), _artifact_register_cli_starts(), _call_span(), _cli_command_span(), _cli_scan_character(), Defect, find_artifact_enum_defects() (+53 more)

### Community 83 - "_apply_body_section_filter"
Cohesion: 0.04
Nodes (41): _apply_body_section_filter(), narrow_body_to_named_sections(), Concatenate the *body* slices for the given *span* *indices* in order. The…, Narrow *body* and *result.body* to the requested section(s). Resolves *section*…, Return the slices of *body* whose ``## ``/``### `` headers match *names*. Used…, _slice_body_by_header_indices(), Edge-case coverage for _apply_body_section_filter filter-form dispatch (#2495).…, Comma-separated index forms with surrounding whitespace. (+33 more)

### Community 84 - "helpers.py"
Cohesion: 0.04
Nodes (47): FastMCP, Shared test helper functions for development-harness test suites. Centralises…, _advertised_enum(), Any, parametrize, The artifact tools must advertise their value domain and reject anything…, An invalid artifact type must produce an error response, not a success envelope., An unknown artifact type on a read must surface as a failed call. A read that… (+39 more)

### Community 85 - "workflow_multigraph/__init__.py"
Cohesion: 0.06
Nodes (53): DecompositionInput, DecompositionItem, DecompositionSourceKind, BaseModel, StrEnum, The decomposition input: what layer 3 consumes to produce a layer-2 work graph.…, The kinds of grooming and architecture output layer 3 decomposes, as the…, One piece of grooming or architecture output offered to layer 3's decomposition. (+45 more)

### Community 86 - "CacheCheckpoint"
Cohesion: 0.25
Nodes (5): Durably replace one provider checkpoint., CacheCheckpoint, Last provider revision and fingerprint acknowledged for content., Barrier, test_file_cache_serializes_concurrent_instances_and_reopens_valid_state()

### Community 87 - "backlog.py"
Cohesion: 0.09
Nodes (63): add(), assign_milestone(), close(), comment_issue(), comments(), create_milestone(), create_project(), _emit() (+55 more)

### Community 88 - "find_item"
Cohesion: 0.06
Nodes (32): _find_by_issue_number(), _find_by_reference(), _find_by_string_id(), find_item(), parse_issue_selector(), Extract issue number from selector (URL, #N, or bare number). Supports: -…, Return the item whose ``issue`` field resolves to ``issue_num``, or None., Return the item with an exact ``issue`` match (e.g. a beads nanoid), or None. (+24 more)

### Community 89 - "_paginate"
Cohesion: 0.05
Nodes (47): _assert_calibration(), _find_item2_exact_body(), _find_normal_body(), _find_oversized_body(), _make_item(), _paginate(), Any, given (+39 more)

### Community 90 - "_write_item"
Cohesion: 0.06
Nodes (41): _isolate_backlog_dir(), fixture, MonkeyPatch, Path, Redirect BACKLOG_DIR to tmp_path for test isolation. Tests: File-system…, Verify close_item returns closed=True for a valid item with a valid reason.…, update_item with title= and description= params updates local file fields., update_item with title= updates the name field in the local file. Tests:… (+33 more)

### Community 91 - "test_backend_config_search.py"
Cohesion: 0.09
Nodes (48): _auto_detect_beads(), Return ``"beads"`` when the explicit opt-in marker ``.beads/dh-backend``…, _BOTH_SIDES, _BOTH_SIDES_ONLY_MODULE, _BackendSearchModule, _patch_dh_paths(), MonkeyPatch, Path (+40 more)

### Community 92 - "test_ledger_fold.py"
Cohesion: 0.07
Nodes (58): Checkpoint, all_events(), Read the whole log, oldest first, with each payload decoded. Args: conn: An…, accepted_then_forced(), assert_rebuilt(), build_all(), drafted_plan(), forced() (+50 more)

### Community 93 - "Page"
Cohesion: 0.05
Nodes (41): Page, field_validator, Validate end_line >= start_line. Args: v: Value to validate. info: Pydantic…, Validate level is between 1 and 6. Args: v: Value to validate. Returns: The…, A single page of paginated content. Args: content: Text content for this page.…, Validate page_number >= 1. Args: v: Value to validate. Returns: The validated…, Validate total_pages >= 1. Args: v: Value to validate. Returns: The validated…, Validate budget > 0. Args: v: Value to validate. Returns: The validated value.… (+33 more)

### Community 94 - "test_frontmatter_reader.py"
Cohesion: 0.06
Nodes (59): Read a plan from any supported format. Detects the format via…, read_plan(), r"""Read a YAML-frontmatter-in-markdown plan file. Supports three file…, read_frontmatter_plan(), Path, Tests for sam_schema.readers.frontmatter_reader — YAML frontmatter in markdown., Verify that the prose body following a task YAML block populates description.…, Verify that ### Objective sections are extracted into the objective field.… (+51 more)

### Community 95 - "dh_migrate.py"
Cohesion: 0.06
Nodes (58): err(), output_json(), NoReturn, Shared CLI output helpers for development-harness migration scripts.…, Print an error message to stderr and exit. Args: msg: Error message for the…, Print *data* as compact JSON to stdout. No indentation — see…, _build_registration_rows(), _build_slug_index() (+50 more)

### Community 96 - "test_decomposition_gate.py"
Cohesion: 0.06
Nodes (47): The artifact-type registry this plugin declares: which agent may register which…, DecompositionGate, normalize(), The decomposition-exit gate: checks a task's instructions against the referents…, Reads source text at a…, Return the text at ``ref``, or ``None`` when the path it names does not exist.…, The decomposition-exit gate over a task's instructions. Constructed against a…, Return whether any finding over ``instructions`` is severity ``BROKEN``. Args:… (+39 more)

### Community 97 - "add_item"
Cohesion: 0.05
Nodes (33): add_item(), Add an item through the configured backend and optionally create its native…, add_item writes a per-item file with correct frontmatter fields., Verify add_item creates exactly one .yaml file in BACKLOG_DIR. Tests: add_item…, Verify add_item return dict contains title, priority, and file_path keys.…, Verify the written file frontmatter includes the item title. Tests: add_item…, Verify add_item persists the type-prefixed title create_issue_for_item sends to…, Verify add_item reports the stored title, not the raw title argument (#3546).… (+25 more)

### Community 98 - "get_sync_state"
Cohesion: 0.04
Nodes (42): _backlog_lifespan(), _log_sync_task_exc(), Task, Done-callback: log any unexpected exception that escapes the sync task. An…, Retain a strong reference to *task* and wire its done-callbacks. Args: task:…, Return True when the startup sync should run (default: True). Reads…, FastMCP lifespan: launch the background sync task before serving tools. The…, Return the current background sync state. Returns:… (+34 more)

### Community 99 - "merge_layer.py"
Cohesion: 0.07
Nodes (46): _bootstrap_layer_meta(), ExtractionFragment, LayerJSON, merge_fragment(), MergeResult, parse_extraction_fragment(), parse_layer_json(), Path (+38 more)

### Community 100 - "SyncState"
Cohesion: 0.05
Nodes (34): Process-singleton dataclass holding all background sync bookkeeping.…, Completion percentage 0-100, or None when total is unknown or zero. Returns:…, Return True when a sync is currently in progress. Returns: True only when…, Complete a successful transient claim without changing when it started., Return a JSON-serialisable representation of the sync state. The ``lock`` field…, SyncState, Exceptions outside the narrow (BackendUnavailableError, GithubException,…, RuntimeError escaping _attempt_sync must set status=ERROR, not leave RUNNING.… (+26 more)

### Community 101 - "Path"
Cohesion: 0.07
Nodes (36): _make_agent_entry(), _make_metadata(), MockerFixture, Path, profile_load populates name and plugin from the discovered agent entry. Tests:…, profile_load includes the agent instruction body in the response. Tests: body…, profile_load returns an empty skills list when the agent declares no skills.…, profile_load returns skills as raw URI strings, not resolved dicts. Tests:… (+28 more)

### Community 102 - "_resolve_labels_graphql"
Cohesion: 0.07
Nodes (39): Resolve label names via a single GraphQL query. Returns label name strings that…, _resolve_labels_graphql(), _graphql_response(), _make_mock_repo(), Any, MockerFixture, Tests for _resolve_labels_graphql() in backlog_core/gh_client.py. Covers: all-…, _resolve_labels_graphql omits null aliases and returns only existing labels. (+31 more)

### Community 103 - "DispatchPlan"
Cohesion: 0.10
Nodes (40): DispatchPlan, Root model for plan/milestone-{N}-dispatch.yaml., _keys_to_kebab(), _make_yaml(), Any, BaseException, Path, YAML (+32 more)

### Community 104 - "_call_view"
Cohesion: 0.07
Nodes (36): _patch_issue_2521(), MockerFixture, RED tests: section-filter miss returns an explicit error dict. These tests MUST…, Patch operations layer so view_item enriches with the #2521 fixture body. Args:…, section= miss with include_content=True returns an error dict. Exercises…, section= miss response contains an 'error' key. Arrange: GitHub enrichment…, section= miss response contains a non-empty 'valid_sections' list. Arrange:…, section= miss error response does not include a 'body' field. No content is… (+28 more)

### Community 105 - "test_artifact_registry_ownership.py"
Cohesion: 0.06
Nodes (52): ArtifactTypeRow, BaseModel, model_validator, One artifact type, the writers permitted to register it, and whether a gate…, Reject a gate-read row that names other than exactly one registering agent.…, _cli_flags(), _cli_registration(), declared_agents() (+44 more)

### Community 106 - "test_known_failure_types.py"
Cohesion: 0.05
Nodes (51): _check_codes_unique(), failure_type(), FailureCategory, FailureTypeRow, KnownFailureTypesPage, page(), BaseModel, computed_field (+43 more)

### Community 107 - "._bd_id_for_task"
Cohesion: 0.05
Nodes (33): _beads_to_task_status(), _issue_to_task_data(), Any, BaseModel, Task, TaskData, Append a single validated Task to an existing plan. Creates a new child issue…, Finalize a drafting plan. Beads issues are live after creation, so this is a… (+25 more)

### Community 108 - "_item"
Cohesion: 0.08
Nodes (30): _Backend, _item(), _patch_backend(), MockerFixture, parametrize, Tests for how a refused GraphQL query reaches the listing path.…, A network error/500/rate limit resolving the repo itself is not a refusal…, Closed and unlabeled issues remain distinguishable from absent issues. (+22 more)

### Community 109 - "Path"
Cohesion: 0.05
Nodes (32): plan_dir(), fixture, parametrize, Path, Tests for sam CLI ``create`` command. Tests: Plan creation via CLI with typed…, Two consecutive creates produce distinct UUID plan_ids. Tests: UUID uniqueness…, Test task creation through the named, typed create options., Typed task options persist all supported task fields. (+24 more)

### Community 110 - "parse_issue_body"
Cohesion: 0.04
Nodes (37): parse_issue_body(), Parse a GitHub issue body markdown string into a BacklogItem. Extracts the…, github_sync.py imports do not create circular dependencies., github_sync module is importable without errors., All three public functions are importable from backlog_core.github_sync., models.py does not import from github_sync (no cycle)., parse_issue_body: body without backlog-metadata comment returns defaults., parse_issue_body on body with no metadata comment returns BacklogItem. The… (+29 more)

### Community 111 - "test_readers/test_yaml_reader.py"
Cohesion: 0.06
Nodes (49): Format detection and plan read routing for SAM task/plan files. The…, _parse_manifest_frontmatter(), Path, Attempt to parse ``text`` as a YAML mapping. Returns the coerced plain dict on…, Split a manifest file into plan metadata, raw task list, and body. Args: path:…, _try_parse_yaml_dict(), Path, Pure YAML reader for canonical SAM task/plan files. Reads ``.yaml`` files in… (+41 more)

### Community 112 - "test_github_tools_milestones.py"
Cohesion: 0.06
Nodes (51): make_milestone_full_node(), Return a MilestoneFullNode-shaped dict with sensible defaults. Args:…, _call(), _inject_milestones(), MonkeyPatch, Tests for backlog milestone MCP tools and operations. Covers four tools and…, list_milestones forwards the state parameter to get_milestones. Tests:…, list_milestones returns count=0 and empty list when repo has no milestones.… (+43 more)

### Community 113 - ".from_markdown"
Cohesion: 0.05
Nodes (34): resolve_section raises AmbiguousSectionRefError when two sections share a slug.…, resolve_section returns the SectionNode when the slug is unambiguous. This is a…, test_resolve_section_raises_on_slug_collision(), test_resolve_section_unique_slug_returns_section_node(), Construct a navigator and immediately load the given markdown. Args: markdown:…, fenced_nav(), nav(), fixture (+26 more)

### Community 114 - "sync_issues_graphql"
Cohesion: 0.08
Nodes (36): datetime, Fetch issues with optional filtering and a per-issue callback. Pagination is…, sync_issues_graphql(), slow, _make_issue_node(), _make_mock_repo(), Any, MockerFixture (+28 more)

### Community 115 - "monitor.py"
Cohesion: 0.06
Nodes (49): agent_last_actions(), capture_pane_by_id(), extract_actions(), jsonl_dir_for_project(), latest_team(), Path, Health subcommand — team member JSONL action inspection and tmux pane capture., Find the agent's JSONL session and return last N actions. For the team-lead:… (+41 more)

### Community 116 - "test_file_cache.py"
Cohesion: 0.08
Nodes (49): _make_directory_matching_glob(), _make_symlink_escaping_cache_root(), _permission_bits_are_unenforced(), MonkeyPatch, parametrize, Path, ProcessBarrier, skipif (+41 more)

### Community 117 - "Graph"
Cohesion: 0.10
Nodes (45): ContractBasis, Finding, Predicate, PredicateDefinition, Projection, BaseModel, computed_field, Observation (+37 more)

### Community 118 - "Path"
Cohesion: 0.11
Nodes (20): AgentMetadata, Structured frontmatter extracted from an agent definition file. Corresponds to…, parse_agent_file(), parse_skill_frontmatter(), Frontmatter parsing and skill content reading for agent definition files.…, Read only the frontmatter of a SKILL.md to extract sub-skill URIs. Looks for a…, Read a skill's SKILL.md and all Markdown reference files. Reads ``SKILL.md``…, Read an agent ``.md`` file and return its structured metadata and body. The… (+12 more)

### Community 119 - "Entry"
Cohesion: 0.05
Nodes (33): Reconstruct the raw HTML entry block from a parsed Entry. Used when the…, _render_entry_raw(), Render all entries in a Section as concatenated div blocks. Args: section:…, _render_section_entries(), Entry, A single timestamped content block within a backlog item section., Require struck_at to be non-empty when struck is True. Returns: The validated…, Render *entries* grouped under their owning ``## ``/``### `` headers.… (+25 more)

### Community 120 - "analyze_impact_radius_conflicts"
Cohesion: 0.08
Nodes (45): analyze_impact_radius_conflicts(), _build_conflict_groups(), _collect_items_with_paths(), ImpactRadiusItem, _parse_impact_radius_paths(), Path-compressed union-find with union-by-rank (disjoint set union) for integer…, Return canonical root of x with path compression., Merge the sets containing x and y using union-by-rank. (+37 more)

### Community 121 - "parametrize"
Cohesion: 0.04
Nodes (30): parametrize, Heading positions come from marko, not from re-scanning the source lines. The…, A commented-out heading is invisible to marko and must be invisible here. Why:…, Fence tracking must respect CommonMark delimiter length. Why: A boolean toggle…, A ``<div><sub>`` that never closes must not consume to end of document. Why:…, The unterminated fix must not weaken entry-block opacity. Why: A heading-shaped…, The same document parsed with LF and with CRLF yields identical spans. Tests:…, A section's name is the spelling the source uses, not marko's flattening of it.… (+22 more)

### Community 122 - "migrate_backlog_to_yaml.py"
Cohesion: 0.08
Nodes (45): _dry_run_section_info(), _has_frontmatter(), main(), migrate_file_dry_run(), migrate_file_live(), MigrationReport, command, help (+37 more)

### Community 123 - "MockerFixture"
Cohesion: 0.09
Nodes (23): _BatchCapableBackend, _GitHubLikeBackend, _item(), _patch_view_backend(), MockerFixture, A string-ID backend's own status field is authoritative -- not a degradation., A skipped batch fetch (no GITHUB_TOKEN) must not be reported as 'live' (#3546,…, A skipped-for-credentials fetch is exactly as unevaluable as an attempted-and-… (+15 more)

### Community 124 - "model.py"
Cohesion: 0.08
Nodes (41): Descriptor, Freshness, BaseModel, Source anchors and the descriptor: the facets an input or output must carry.…, The freshness and version facet of a value., One declared input or output, carrying every facet the contract requires of…, Return whether this output's type satisfies ``consumer``'s declared input type.…, Edge (+33 more)

### Community 125 - "detect_format"
Cohesion: 0.06
Nodes (46): _classify_frontmatter(), detect_format(), Path, Detect the task/plan file format for a given path. Detection flowchart: 1. If…, Initialize FormatDetectionError with path and inspected content., Classify a YAML frontmatter block into a FormatType. Returns ``None`` when the…, Path, Tests for sam_schema.readers.detect — format detection logic. Tests: Format… (+38 more)

### Community 127 - "render_issue_body"
Cohesion: 0.14
Nodes (37): Render a BacklogItem as a GitHub issue body markdown string. Embeds priority,…, render_issue_body(), _merged_title(), Return the checkpoint hash for the provider-synchronized item projection., Return the provider's title when local never edited it, else keep local's.…, synchronized_fingerprint(), _applied(), _item() (+29 more)

### Community 128 - "LoopDriver"
Cohesion: 0.11
Nodes (27): CommandResult, LoopDriver, Return the ``--plan-address`` flag naming the plan this run built., Return the ``--address`` flag naming one task of the plan this run built. Args:…, Create the plan, append its three tasks, finalize it and validate it. ``--base-…, Add one task to the drafting plan and set the fields the fixture gives it.…, Read the dispatchable set and write down what it holds and what it withholds.…, Open an attempt on one task and return the attempt number ``dispatch`` printed.… (+19 more)

### Community 129 - "Path"
Cohesion: 0.06
Nodes (27): plan_dir(), fixture, Path, Tests for sam CLI ``claim`` command. Tests: Task claiming (transition to in-…, Successful claim includes the task_id in JSON output. Tests: Task ID echo. How:…, Successful claim includes a ``started`` ISO timestamp. Tests: Timestamp…, Claiming T1 does not change T2 or T3 status. Tests: Task isolation during…, Test ``plan claim`` on a task already in ``in-progress`` state. Tests: Double-… (+19 more)

### Community 130 - "_github_exception"
Cohesion: 0.08
Nodes (25): _github_exception_message(), is_graphql_unavailable(), GithubException, Return the human-readable message a GithubException carries. Args: exc: The…, Report whether this failure means GraphQL is refused environment-wide. A 403…, _FakeRepo, _FakeRequester, _github_exception() (+17 more)

### Community 131 - "properties"
Cohesion: 0.06
Nodes (35): auto, interactive, mode, route, type, additionalProperties, description, properties (+27 more)

### Community 132 - "dispatch_schema/__init__.py"
Cohesion: 0.05
Nodes (40): Shared constants for dispatch_schema. Kept in a leaf module (no imports from…, _build_issue_wave_map(), _check_conflict_group_refs(), _check_conflict_group_wave_placement(), _check_depends_on_existence(), _check_duplicate_issues(), _check_wave_ordering(), detect_stale_plan() (+32 more)

### Community 133 - "Agent Markdown Consumption — Behaviour Specification"
Cohesion: 0.06
Nodes (40): dh:task-worker agent, CONTEXT.md (Orchestrator/Manager/Worker vocabulary), ADR-3072-1: Budget Applies Only at Navigation, Item #2953 pathological-size case study, Collection/Generation/Navigation pipeline layering, ADR-3075-1: Content Identity and Cache Scope, Content identity = command + generated output hash, Session-scoped cache (superseded) (+32 more)

### Community 134 - "ActiveTaskContext"
Cohesion: 0.05
Nodes (26): Return all active task contexts stored in bd remember. Scans all remember…, _atomic_write(), LocalContextBackend, Path, LocalContextBackend — filesystem-based ContextBackend implementation. Reads and…, Return all active task contexts from the filesystem. Silently skips missing or…, Resolve the absolute path to the plan YAML file. Args: plan: Plan address…, Write JSON atomically using temp file + os.replace(). Args: path: Target file… (+18 more)

### Community 135 - "_extract_log_messages"
Cohesion: 0.05
Nodes (44): _extract_log_messages(), backlog_sync emits ctx.info with start message before the operation., backlog_sync emits ctx.info with '(dry-run)' suffix when dry_run=True., backlog_sync emits ctx.info with completion summary including counts., backlog_sync surfaces each out.warnings entry via ctx.warning., backlog_groom emits ctx.info with 'Grooming item: {selector}' before operation., backlog_groom emits ctx.info with 'Groomed: {title}' after operation., backlog_groom surfaces out.warnings via ctx.warning. (+36 more)

### Community 136 - "Path"
Cohesion: 0.07
Nodes (29): _make_items(), MockerFixture, Path, Tests for DispatchStateManager.get_all_waves., get_all_waves returns all waves for a milestone in wave_num order. Tests:…, get_all_waves returns an empty list when no waves exist for the milestone.…, Return a list of minimal DispatchItemRecord instances for test setup. Args:…, get_all_waves only returns waves for the requested milestone. Tests:… (+21 more)

### Community 137 - "test_github_client.py"
Cohesion: 0.07
Nodes (37): has_github_credentials(), Report whether a GitHub token is configured in this process's environment.…, MissingGitHubTokenError, RuntimeError, Raised when no environment variable supplies a GitHub token., Return the GitHub token to authenticate with. Args: token: An explicit token.…, resolve_token(), ca_directory() (+29 more)

### Community 138 - "test_cli_migrate_fallback.py"
Cohesion: 0.08
Nodes (42): _load_yaml(), _make_nonstandard_plan_dir(), _make_pure_markdown_plan_dir(), CaptureFixture, parametrize, Path, Tests for the best-effort fallback migration path in ``_migrate_one``. Covers…, _migrate_one_fallback stores the complete original content in context.body.… (+34 more)

### Community 139 - "install_proxy_tls_support"
Cohesion: 0.08
Nodes (22): install_proxy_tls_support(), Teach every PyGithub client in this process to trust a custom CA bundle.…, _installed_https_connection_class(), Read the HTTPS connection class Requester currently builds instances from.…, Installation is conditional, idempotent, and process-wide., On an ordinary network PyGithub keeps its own strict default., A no-op call must not mark the process as installed., Repeat calls neither reinstall nor report failure. (+14 more)

### Community 140 - "test_status_filter_fabrication.py"
Cohesion: 0.08
Nodes (24): _Backend, _item(), _patch_backend(), MockerFixture, Regression tests for the status-filter fabrication bug (#3546).…, A refusal must not turn one real match into three fabricated matches., Not just the GraphQL-refusal marker -- any BackendUnavailableError subclass…, status='in-progress' may still miss real matches under a degraded map (nothing… (+16 more)

### Community 141 - "assemble_graph.py"
Cohesion: 0.13
Nodes (41): _build_all_edges(), build_artifact_nodes(), build_branch_edges_from_l1(), build_calls_edges(), build_decision_nodes(), build_dispatches_edges(), build_reads_edges(), build_stores_in_edges() (+33 more)

### Community 142 - "create_task_backend"
Cohesion: 0.06
Nodes (28): create_task_backend(), Instantiate and return a TaskBackend by name. When *name* is ``None``,…, MonkeyPatch, Path, CONTEXTBACKEND=bad must raise SamError., create_context_backend('beads') must return a BeadsContextBackend., create_context_backend('github') must raise NotImplementedError., TASKBACKEND=beads must return a BeadsTaskProvider instance. (+20 more)

### Community 143 - "_build_task_dict"
Cohesion: 0.06
Nodes (32): _build_task_dict(), _extract_bold_fields(), _extract_task_id_title_from_entry(), _merge_prose_fields(), _parse_dependency_value(), _parse_skills_value(), Any, Extract ``**FieldName**: value`` patterns from task prose text. Parses lines… (+24 more)

### Community 144 - "MockerFixture"
Cohesion: 0.08
Nodes (23): _LiveGitHubBackend, _patch_view_backend(), MockerFixture, A non-refusal failure must not read as "issue #519 does not exist"., A network error/500/rate limit resolving the repo itself is not a refusal…, ``try_get_github`` returning None is the no-token config state, not a failure., A reachable repository confirming the issue does not exist must not become…, An inaccessible/nonexistent repository is not a missing-issue answer.… (+15 more)

### Community 145 - "enumerate_scope.py"
Cohesion: 0.11
Nodes (35): ReferenceType, _derive_entry_point_name(), enumerate_scope(), _extract_agent_refs(), _extract_mermaid_refs(), _extract_prose_file_refs(), extract_references(), _extract_skill_refs() (+27 more)

### Community 146 - "test_dh_migrate.py"
Cohesion: 0.09
Nodes (40): _artifact_manifest_instructions(), _detect_layout(), _old_dirs(), Return mapping of old-relative-path → absolute path for each legacy directory., Return presence flags for old and new layout indicators. Returns: Dict with…, Build artifact manifest update instructions for the calling agent. Artifact…, fake_project(), new_layout() (+32 more)

### Community 147 - "test_backward_compat_local_plans.py"
Cohesion: 0.08
Nodes (31): _create_local_only_plan(), _EmptyArtifactRegistryClient, _EmptyArtifactStore, _make_empty_client(), _make_layer_with_empty_gist(), Path, Task, Backward-compatibility tests for pre-fix local plans (AC4). Verifies that plans… (+23 more)

### Community 148 - "parse_item_file"
Cohesion: 0.11
Nodes (15): _fm_str(), parse_item_file(), Resolve a string field from metadata dict with frontmatter fallback. Returns:…, Parse a single per-item backlog file (frontmatter + body). Handles both flat…, Path, Tests for parse_item_file(text, path) -> BacklogItem., Body content below frontmatter is no longer stored on the item. LEGACY:…, When no frontmatter is found, an empty BacklogItem is returned. LEGACY:… (+7 more)

### Community 149 - "Path"
Cohesion: 0.08
Nodes (21): _add_plugin_root_to_path(), fake_project_root(), isolated_state(), fixture, MonkeyPatch, Path, Tests for backlog_core path resolution via dh_paths. Verifies that: -…, Test ensure_dirs creates the expected directory tree. (+13 more)

### Community 150 - "parse_show_issue"
Cohesion: 0.06
Nodes (27): _extract_content_block(), ItemId, Extract content between sentinel markers from a notes string. Parameters…, Retrieve the artifact manifest. Accepts a beads string ID at runtime (type…, Persist *manifest*. Accepts a beads string ID at runtime (type widening).…, Store artifact content in bd notes as a sentinel-delimited block. Accepts a…, Search bd notes for a stored artifact content block. Accepts a beads string ID…, Retrieve the artifact manifest for a beads issue. Fetches issue JSON via ``bd… (+19 more)

### Community 151 - "Any"
Cohesion: 0.11
Nodes (25): list_integration_branches(), List all branches matching the ``milestone/`` prefix. Args: repo: Repository in…, _make_mock_branch(), Any, datetime, MockerFixture, create_integration_branch creates a branch from a base SHA., Test successful branch creation returns correct BranchInfo. Tests:… (+17 more)

### Community 152 - "github_client.py"
Cohesion: 0.08
Nodes (29): bundle_adds_new_anchor(), _cert_fails_strict_checks(), _configured_ca_bundles(), _der_sequence_length(), _InstallState, _is_openssl_hashed_ca_directory(), _load_certificates(), _new_anchors() (+21 more)

### Community 153 - "MockerFixture"
Cohesion: 0.08
Nodes (27): _body_section_names(), MockerFixture, ``result.sections`` must mirror the narrowed ``result.body`` for ALL forms.…, section='2' (numeric, in range) narrows body AND populates sections. RED: body…, section='/Impact.*/' (regex) narrows body AND populates sections in sync. RED:…, section='Issue' (substring) matches two headers; sections holds both in sync.…, section='RT-ICA' (exact name) keeps body and sections in sync (regression…, A genuine miss must empty sections AND set section_filter_miss=True.… (+19 more)

### Community 154 - "test_addressing.py"
Cohesion: 0.09
Nodes (38): parse_address(), Raise AddressingError-compatible ValueError if address contains traversal…, Parse a task address string into its plan and task components. Args: address:…, _reject_path_traversal(), Tests for sam_schema.core.addressing module. Covers P{NNN}-{slug} primary…, test_parse_address_empty_string_raises_value_error(), test_parse_address_empty_task_component_raises_value_error(), test_parse_address_extension_error_message_suggests_correct_form() (+30 more)

### Community 155 - "test_github_tools_projects.py"
Cohesion: 0.07
Nodes (38): _call(), _fake_project_node(), MonkeyPatch, Tests for backlog Projects V2 MCP tools and operations. Covers two tools and…, list_projects forwards the limit to the GraphQL query variables. Tests:…, list_projects returns count=0 and empty list when owner has no projects. Tests:…, list_projects handles null nodes in the GraphQL response without crashing.…, list_projects resolves owner from repo.owner.login when owner param is None.… (+30 more)

### Community 156 - "test_task_status_hook.py"
Cohesion: 0.07
Nodes (38): _argv_after(), _frontmatter(), _hook_sources(), Any, Tests for task_status_hook.py — the SubagentStop settle. Covers: -…, Return the tail of *cmd* starting at the first occurrence of *token*. Isolates…, task_status_hook.py's own source never mentions 'fastmcp'. All task-state…, Every _call_sam_cli-family function's own timeout default must be < 60s. The… (+30 more)

### Community 157 - "task_status_hook.py"
Cohesion: 0.08
Nodes (35): _call_sam_cli(), _call_sam_plan_settle(), extract_launch_from_prompt(), _first_nonempty_line(), _get_uv_executable(), Launch, _launch_of(), BaseModel (+27 more)

### Community 158 - "manifest_reader.py"
Cohesion: 0.09
Nodes (34): _load_yaml_block(), _parse_embedded_task_blocks(), _parse_frontmatter_content(), _parse_prose_fields(), _parse_tasks_list_block(), Any, Path, YAML-frontmatter-in-markdown reader for SAM task/plan files. Reads ``.md``… (+26 more)

### Community 159 - "_build_ssl_context"
Cohesion: 0.07
Nodes (23): _build_ssl_context(), _ProxyAwareAdapter, Build a context that trusts ca_bundle, clearing strict checks only when asked.…, An HTTPAdapter that applies its SSL context on the proxied path as well.…, Store the bundle before delegating, because the base __init__ builds the pools.…, Attach the context to the direct connection pool. Args: connections: Number of…, Attach the context to the proxied connection pool. Args: proxy: Proxy URL that…, The relaxation clears one flag. Every other guarantee must survive it. (+15 more)

### Community 160 - "_write_item_file"
Cohesion: 0.17
Nodes (13): _backlog_dir(), MockerFixture, parametrize, Path, BacklogItem.reference self-heals at construction time (see models.py). A never-…, An item with a healed but never-persisted reference surfaces a KeyError. This…, _stored_text(), TestGroomItemWithSections (+5 more)

### Community 161 - "test_github_tools_prs.py"
Cohesion: 0.09
Nodes (35): _call(), _make_pr(), datetime, MonkeyPatch, Tests for backlog_list_merged_prs MCP tool and list_merged_prs operation. Tests…, list_merged_prs stops collecting once limit is reached., list_merged_prs returns empty list when all PRs are closed but not merged., list_merged_prs includes only PRs whose title contains the search string. (+27 more)

### Community 162 - "read_dispatch_plan"
Cohesion: 0.12
Nodes (17): _coerce_to_plain(), _load_yaml(), Any, Path, YAML reader for dispatch plan files. Reads ``plan/milestone-{N}-dispatch.yaml``…, Parse YAML text using ruamel.yaml round-trip mode. Args: content: Raw YAML text…, Recursively coerce ruamel.yaml CommentedMap/CommentedSeq to plain Python types.…, Read and validate a dispatch plan YAML file. Args: path: Path to a… (+9 more)

### Community 163 - "run_cli_subprocess"
Cohesion: 0.08
Nodes (26): CompletedProcess, Run a CLI subprocess (e.g. ``uv run <script>``) with whole-process-group…, run_cli_subprocess(), dh_state_home(), _get_project_slug(), Any, fixture, integration (+18 more)

### Community 164 - "_make_snippet_parts"
Cohesion: 0.07
Nodes (34): _format_match_text(), _make_snippet(), _make_snippet_parts(), _parse_body_sections(), Parse a markdown body string into (section_slug, text) tuples. Splits on ``##…, Extract a snippet around a match position with sliding-window budget. The total…, Compute snippet parts for a match, enabling both plain and formatted output.…, Format a single match entry as a human-readable snippet line. The section label… (+26 more)

### Community 165 - "implementation_manager.py"
Cohesion: 0.02
Nodes (142): exists, FeatureSlug, ProjectPath, resolve_path, plan_id_from_path(), Return the plan identifier — the full filename stem, never a prefix. Args:…, _claim_fail(), claim_task() (+134 more)

### Community 166 - "test_ledger_cascade_ancestors.py"
Cohesion: 0.15
Nodes (33): holding_cascades(), Return the ``cascade-reversed`` outcome reason for one reclaimed task. Args:…, Return the failed tasks whose cascade currently holds one dependent skipped. A…, reversal_code(), fail(), Connection, parametrize, A dependent two failures block, in both directions of the cascade.… (+25 more)

### Community 167 - "._write_through"
Cohesion: 0.08
Nodes (19): Any, Path, PlanUpdateValue, Task, Replace a stored task with mandatory Gist write-through. Read-modify-write…, Append a markdown section to a task with mandatory Gist write-through. Read-…, Append a task to an existing plan with mandatory Gist write-through. Read-…, Finalize a plan with mandatory Gist write-through. Read-modify-write flow: 1.… (+11 more)

### Community 168 - "MonkeyPatch"
Cohesion: 0.07
Nodes (22): MonkeyPatch, probe_backend_status returns NEEDS_AUTHENTICATION when GITHUB_TOKEN is absent.…, No token variable set -> availability=NEEDS_AUTHENTICATION. Tests:…, No token variable set -> error field names GITHUB_TOKEN among the options.…, probe_backend_status returns REACHABLE with counts when GitHub is accessible.…, Token set, GitHub reachable -> availability=REACHABLE. Tests:…, Token set, GitHub reachable -> open_count matches repo.open_issues_count.…, Token set, GitHub reachable -> total_count matches… (+14 more)

### Community 169 - "test_status_source_wire.py"
Cohesion: 0.08
Nodes (21): _apply_sync_state_to_response(), _build_count_only_response(), Merge sync_state block and warnings into a tool response dict in-place. No-ops…, Build the minimal count response while preserving degradation signals. Returns:…, Regression coverage for FastMCP response serialization., FastMCP must not serialize a dumped dict as a Pydantic model., test_dumped_response_matches_tool_return_annotation_without_warnings(), BacklogListResponse (+13 more)

### Community 170 - "NavigationResult"
Cohesion: 0.09
Nodes (21): NavigationResult.model_dump() must produce a complete serialisable dict.…, test_navigation_result_model_dump_available_for_dict_migration(), _disclosure_to_result(), Return page *page_num* (1-based) of full items as a NavigationResult. Page size…, Return the single item whose id field matches *selector*. Args: selector: Value…, Build a ``NavigationResult`` from disclosure parameters. Args: kind:…, NavigationResult, computed_field (+13 more)

### Community 171 - "test_progressive_markdown.py"
Cohesion: 0.09
Nodes (22): _char_bisect_chunks(), chunk_text(), _chunk_text_impl(), _pack_parts(), Encoding, Progressive disclosure engine for MCP endpoints that return structured data.…, Core implementation for lossless token-budget text chunking. Splits *text* into…, Greedily pack *parts* into chunks each fitting within *budget* tokens. Adjacent… (+14 more)

### Community 172 - "Development Harness Backend Providers"
Cohesion: 0.20
Nodes (12): LocalFilesystemArtifactProvider, BacklogBackend Protocol, Purpose Audit Clause/Evidence Manifest, Purpose Audit Reference Manifest, Purpose Audit Remediation Plan, Development Harness Backend Providers, FileCache contract (remote-provider private cache), One configured backend resolution order (env, config, .beads marker, github default) (+4 more)

### Community 173 - "_task"
Cohesion: 0.08
Nodes (19): TaskStatus, Task whose dependency is BLOCKED is NOT returned as ready., FAILED is not a satisfying status — downstream tasks must not be dispatched., Task with multiple deps — each in a different satisfying status — is ready., Task is blocked if even one dependency is not in a satisfying status., Tasks that are already IN_PROGRESS are not in the ready list., Completed tasks are not returned as ready — they are already done., Empty input returns empty list without error. (+11 more)

### Community 174 - "TestBacklogItemMetadataTypeValidator"
Cohesion: 0.06
Nodes (17): parametrize, BacklogItemMetadata.priority validator., P3 is a valid priority not in the canonical set — accepted verbatim., Unknown priority values are preserved verbatim, not rejected., case-insensitive idea* prefix is normalised to 'Ideas'., BacklogItemMetadata.item_type (alias 'type') validator., Documentation' is a known alias for 'Docs'., Unknown type values like 'Enhancement' are preserved verbatim. (+9 more)

### Community 175 - "_require_int_item_id"
Cohesion: 0.09
Nodes (14): Raise ``TypeError`` when *item_id* is a string. GitHub and GitLab providers…, _require_int_item_id(), Regression tests for item_id type contract in artifact_provider. Background:…, _require_int_item_id rejects all strings; ints pass through unchanged., A numeric string like '2459' must raise TypeError, not coerce. The MCP boundary…, A beads nanoid string like 'bd-a3f8' must still raise TypeError. The…, A plain int like 2459 must be returned as-is without modification. This is the…, The cls_name parameter appears in the TypeError message for GitLab too.… (+6 more)

### Community 176 - "Quick Mode (Step Q)"
Cohesion: 0.09
Nodes (27): artifact list, artifact read, artifact register, backlog add, backlog close, backlog groom, backlog list, backlog merged-prs (+19 more)

### Community 177 - "github_context_backend.py"
Cohesion: 0.11
Nodes (19): IssueComment, _build_comment_body(), _closing_tag(), GitHubContextBackend, _opening_tag(), _parse_comment_body(), GitHubContextBackend — GitHub issue comment-based ContextBackend…, Initialise the backend with GitHub credentials. Args: github_token: GitHub… (+11 more)

### Community 178 - "._verify_queue_keys"
Cohesion: 0.10
Nodes (15): BaseModel, Path, _T, Return the current state, salvaging what it can from a damaged file. Read-only…, Parse, demote a legacy checkpoint if present, then validate or salvage. Always…, Migrate the legacy file if needed, then load -- one lock acquisition, not two.…, Move a pre-rename ``cache.yaml`` onto ``cache.json``. Must only be called while…, Merge a recreated legacy file's queue and dead-letter entries into cache.json,… (+7 more)

### Community 179 - "migrate_plan_artifacts.py"
Cohesion: 0.11
Nodes (31): Candidate, _classify(), _classify_codebase(), discover_candidates(), _extract_issue_from_file(), _find_issue_via_slug(), _load_backlog_items(), _log_candidate_summary() (+23 more)

### Community 180 - "_call"
Cohesion: 0.10
Nodes (17): _call(), usefixtures, Live validation lifecycle: L1 creates an item, L2-L10 operate on it, L11…, L1: backlog_add creates a real GitHub issue., L2: backlog_list returns the item created in L1., L3: backlog_view by issue number returns full item data., L4: backlog_update attaches a plan path to the item., L5: backlog_update sets status to in-progress via GitHub label. (+9 more)

### Community 181 - "Path"
Cohesion: 0.08
Nodes (22): plan_dir(), fixture, Path, Tests for P{NNN} addressing scheme -- plan number resolution and backward…, Test edge cases in P{NNN} numeric plan resolution. Tests: Variable padding,…, P1 resolves to P001-*.yaml (3-digit padding). Tests: Minimal input matching…, P1 resolves to P1-*.yaml (no padding). Tests: Unpadded file matching. How:…, Plan number 9999 resolves correctly. Tests: Large plan number boundary. How:… (+14 more)

### Community 182 - "MockerFixture"
Cohesion: 0.07
Nodes (21): MockerFixture, ``backlog view`` forwards the ``--refresh`` flag to ``operations.view_item``., ``--refresh`` forwards ``refresh=True`` into ``operations.view_item``., Omitting ``--refresh`` forwards ``refresh=False`` into ``operations.view_item``., ``backlog list`` forwards the ``--refresh`` flag to ``operations.list_items``., ``--refresh`` forwards ``refresh=True`` into ``operations.list_items``., The ``backlog sync`` fallback invokes a command that actually exists., The fallback emits structured error JSON directly, no subprocess. After… (+13 more)

### Community 183 - "CommandResult"
Cohesion: 0.08
Nodes (18): CommandResult, parse_payload(), Any, Return the columns the command wrote., Return the task row the command rendered, when it rendered one., Return the task rows a listing command rendered., Return how many rows a listing command counted., Return the report sections the command rendered. (+10 more)

### Community 184 - "ProgressiveDisclosure"
Cohesion: 0.09
Nodes (24): disclosure(), fixture, Pin NavigationResult return contract for ProgressiveDisclosure.select() and…, page() must return NavigationResult (architect §4.1.1). PRE-FIX STATE: FAILS.…, paginate_results() must retain its legacy dict return shape — unchanged by C1.…, ProgressiveDisclosure instance over three sample task items., select() must return NavigationResult when the item is found (architect…, select() must return NavigationResult for an unmatched selector — never None.… (+16 more)

### Community 185 - "Cursor agent (IDE Agent mode + `agent` / `cursor-agent` CLI) — harness facts"
Cohesion: 0.07
Nodes (26): 1. Can the agent run a shell command, read a file, write a file? (tool names), 2. Hooks: events, payload fields, `hooks.json` location, plugin-shipped hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP: can project config or a plugin register an MCP server? — **Both, yes.**, 6. Environment variables set for a shell command the harness runs, After-tool and stop events — full field lists, Can a plugin ship hooks? — **Yes.** (+18 more)

### Community 186 - "loads_frontmatter"
Cohesion: 0.11
Nodes (20): dump_frontmatter(), loads_frontmatter(), _make_yaml(), _MdPost, YAML, Lightweight container for legacy .md frontmatter + body. Replaces…, Initialize post with parsed metadata dict and body content., Return a configured ruamel.yaml round-trip instance. Returns: YAML instance… (+12 more)

### Community 187 - "WorkGraph"
Cohesion: 0.09
Nodes (17): Observation, Find planned work-graph nodes whose ``decomposition_source`` names no item…, Find decomposition items that no work-graph node traces back to. Args: work:…, model_validator, Observation, Refuse a non-planned node that does not name who extended the graph and why.…, A recovered layer-2 graph: tasks, their ordering and exclusion, and the…, Reject a graph whose own references do not resolve. Returns: The validated… (+9 more)

### Community 188 - "progressive_markdown/exceptions.py"
Cohesion: 0.10
Nodes (24): AmbiguousSectionRefError, CodeBlockNotFoundError, DocumentNotLoadedError, PaginationError, ParserError, ProgressiveMarkdownError, ProviderError, Exception (+16 more)

### Community 189 - "CallableMarkdownContentProvider"
Cohesion: 0.08
Nodes (19): Construct a navigator and load markdown via the provider. Args: provider:…, CallableMarkdownContentProvider, MarkdownContentProvider, Protocol, Protocol for objects that supply markdown content given a source string., Return the markdown content for the given source. Args: source: Source…, Wrap any callable that returns a string as a MarkdownContentProvider. Args: fn:…, Initialise with a callable that returns markdown text. Args: fn: Callable with… (+11 more)

### Community 190 - "resolve_plan_address"
Cohesion: 0.14
Nodes (29): AddressingError, Exception, Resolve a plan address string to a file system path. Resolution order: 1.…, Raised when an address cannot be resolved to a file system path. Args: address:…, resolve_plan_address(), Path, test_resolve_plan_address_collision_error_message_suggests_disambiguation(), test_resolve_plan_address_collision_raises_addressing_error_with_paths() (+21 more)

### Community 191 - "test_dispatch_validation.py"
Cohesion: 0.09
Nodes (24): _ConflictGroupInput, _parse_conflict_group(), _parse_plan_item(), _parse_wave_start_item(), _PlanWaveItemInput, BaseModel, Parse and strictly validate an issue/title wave-start item. Returns: A…, Parse and strictly validate one conflict group. Returns: A validated conflict-… (+16 more)

### Community 192 - "_save_registry"
Cohesion: 0.08
Nodes (29): _make_stop_ns(), Ctrl-C causes session to exit within timeout — success without force., Ctrl-C causes session to exit within timeout — tmux kill-session NOT called for…, Session does not exit within timeout — force kill and forced=true in output., Session tmux is already gone — registry cleaned, already_dead=true reported., Verify Ctrl-C is sent to the tmux session from the registry, not the launcher., kb-launcher-{name} is killed after the session exits gracefully., Write each registry entry via _write_entry (mirrors the old single-file API).… (+21 more)

### Community 193 - "DH Workflow Map — Coverage Manifest"
Cohesion: 0.07
Nodes (27): Collected layers, Collection methodology, DH Workflow Map — Coverage Manifest, Follow-up protocol, Key findings from collected layers (optimization-relevant), Remaining gaps, Source provenance, Tier 1 — Only the assembler output needs refreshing (layer data unchanged) (+19 more)

### Community 194 - "test_linear_artifact_provider.py"
Cohesion: 0.09
Nodes (23): mock_linear_create(), mock_linear_get(), provider(), fixture, MockerFixture, Path, Tests for LinearArtifactProvider — attachment upsert, metadata size, error…, Constructor raises ValueError when api_key is whitespace-only. Tests:… (+15 more)

### Community 195 - "TestBeadsBackendConformance"
Cohesion: 0.08
Nodes (16): fixture, Conformance tests for BeadsBackend — beads-specific protocol surface. Uses…, Return a spec'd MagicMock for BdRunner., Return a BeadsBackend backed by a mocked BdRunner., Load the bd show fixture from the beads fixtures directory., Load the bd list fixture from the beads fixtures directory., BeadsBackend satisfies the runtime-checkable WorkItemBackend Protocol. Why:…, probe_backend_status returns REACHABLE when BdRunner.is_available() is True.… (+8 more)

### Community 196 - "TestMilestoneHeaderConstruction"
Cohesion: 0.07
Nodes (18): parametrize, WaveItem raises ValidationError for an unrecognised status string. Tests:…, MilestoneHeader construction with snake_case and kebab-case aliases., MilestoneHeader accepts snake_case field names at construction time. Tests:…, MilestoneHeader.model_validate accepts kebab-case 'integration-branch' key.…, MilestoneHeader rejects number values below the ge=1 constraint. Tests: ge=1…, MilestoneHeader rejects an empty title string. Tests: min_length=1 constraint…, MilestoneHeader raises ValidationError when required fields are absent. Tests:… (+10 more)

### Community 197 - "test_github_flag.py"
Cohesion: 0.13
Nodes (28): _make_cache_file(), _make_mock_task(), _make_task_file(), MockerFixture, Path, Task, Unit tests for the --github flag added to implementation_manager.py. Tests: CLI…, Write a minimal SAM tasks cache file. Args: tmp_path: Base directory; cache is… (+20 more)

### Community 198 - "_ContentsRepository"
Cohesion: 0.09
Nodes (8): _Branch, _Commit, _ContentsFile, _ContentsRepository, _GitTree, _GitTreeEntry, Protocol, _Requester

### Community 199 - "test_backlog_core_parsing.py"
Cohesion: 0.09
Nodes (17): extract_description_from_issue_body(), parse_backlog_from_directory(), Parse backlog items directly from ~/.dh/projects/{slug}/backlog/ per-item…, Extract the Description section from a GitHub issue body. Falls back to first…, parametrize, Tests for backlog_core/parsing.py — pure parsing functions with no GitHub or…, Tests for normalize_issue_title(title) -> str., parse_backlog_from_directory skips corrupt files and logs a warning. The… (+9 more)

### Community 200 - "_store_dispatch_plan"
Cohesion: 0.10
Nodes (24): dispatch_plan_file(), existing_plan_file(), _make_dispatch_plan_yaml(), _make_mgr(), mgr(), patch_dispatch_plan_path(), patch_state_manager(), fixture (+16 more)

### Community 201 - "_make_mixed_items"
Cohesion: 0.09
Nodes (18): _make_item(), _make_mixed_items(), Verify list_items function respects include_closed parameter end-to-end., list_items without include_closed filters out terminal status items., list_items with include_closed=True returns terminal status items too., The count field in result matches the number of items after filtering., Status fields are always returned for items with a GitHub issue., Items with skip=True are excluded even when include_closed=True. (+10 more)

### Community 202 - "WorkItemBackend"
Cohesion: 0.08
Nodes (6): Generic work-item surface every backend must implement. Methods take and return…, Report whether the most recent listing includes locally-queued mutations. Every…, WorkItemBackend, section_heading property is accessible on all backends and contains required…, section_heading returns a dict[str, str] with the minimum required section…, TestBackendProtocolSectionHeadingProperty

### Community 203 - "_CheckpointedBackend"
Cohesion: 0.11
Nodes (13): _CheckpointedBackend, _item(), OSError, parametrize, Backend stub that also implements ``SnapshotCheckpointProvider``. Unlike…, A never-synced cache triggers one automatic refresh instead of only naming the…, ``refresh=True`` must not cause two refresh attempts in one call., A refusal/offline failure (no token, still refused) is swallowed: it must not… (+5 more)

### Community 204 - "Check"
Cohesion: 0.10
Nodes (17): Check, Observation, ObservationLog, BaseModel, StrEnum, Return every observation recorded under one check. Args: check: The behaviour…, Return every observation the loop left unsatisfied., Writes down what each check expected and what the loop saw, in the order it saw… (+9 more)

### Community 205 - "TestTaskRequiredFields"
Cohesion: 0.08
Nodes (16): parametrize, Verify the TASK_ID_PATTERN regex matches expected patterns. Tests: Task ID…, Verify valid task IDs match the pattern., Verify invalid task IDs do not match the pattern., Verify Task model required field validation. Tests: id, title, status are…, Verify Task with only required fields constructs successfully., Verify missing 'id' raises ValidationError., Verify missing 'title' raises ValidationError. (+8 more)

### Community 206 - "BdInvocationError"
Cohesion: 0.10
Nodes (14): BdInvocationError, Initialise with the unparseable raw output. Args: message: Human-readable…, Store configuration only. Does not touch the filesystem., ``bd`` returned a non-zero exit code, timed out, or failed to start.…, Initialise with structured invocation details. Args: message: Human-readable…, Simulate bd commands that produce text output., Handle bd remember <value> --key <key>., Handle bd recall <key>. (+6 more)

### Community 207 - "make_github_client"
Cohesion: 0.10
Nodes (16): make_github_client(), Build a PyGithub client that works on a normal network and behind a TLS proxy.…, integration, Finding 3's chosen resolution: make_github_client always installs first. Since…, The documented default reaches the client rather than PyGithub's own 15s., Proves the module reaches GitHub from whatever network is actually present.…, Put back the real environment that the module-level fixture strips. A live…, The end-to-end path: install, build a client, and fetch a public repository. (+8 more)

### Community 208 - "sam_plan.py"
Cohesion: 0.03
Nodes (173): max, canonical_plan_id(), Give the one spelling every store records a UID-derived plan id under. Every…, FormatDetectionError, Exception, Raised when no known format can be identified for a path. Args: path: File or…, absent(), accept() (+165 more)

### Community 209 - "_build_over_budget_view"
Cohesion: 0.08
Nodes (23): _build_compact_manifest(), _build_over_budget_view(), Build the compact routing manifest returned by ``backlog_view(summary=True)``.…, r"""Build a ``## Sections`` index string from a populated ViewItemResult.…, Build a compact section-directory response for an over-budget backlog_view…, _sections_index_from_result(), Tests that all three server response shapes carry section_filter_miss. These…, _build_compact_manifest dict includes section_filter_miss=True. Arrange:… (+15 more)

### Community 210 - "_make_local_item"
Cohesion: 0.10
Nodes (19): _is_section_entry_metadata(), _make_local_item(), MockerFixture, TypeGuard, Bug A regression suite. Before the fix, _assemble_view_content ignores the…, Requesting section='Concerns' returns only the Concerns section content.…, result.body after section filter must not contain the next section's header.…, Bug B regression suite. _build_sections_metadata uses r"^### (.+?)$" to detect… (+11 more)

### Community 211 - "Observation"
Cohesion: 0.09
Nodes (14): Observation, One thing a graph query found, phrased as expected against observed., Return the node with this id, raising ``KeyError`` when none carries it. Args:…, Yield each edge that joins a declared output to a declared input, with both…, Find required inputs that no incoming edge fills. Returns: One observation per…, Find edges whose producer type does not satisfy the consumer's declared input…, Find edges where the supplied trust classification is below the required one.…, Find edges whose producer holds an authority other than the one the consumer… (+6 more)

### Community 212 - "beads_artifact_provider.py"
Cohesion: 0.11
Nodes (17): _extract_manifest_from_metadata(), _is_dict_of_object(), _parse_manifest_value(), TypeGuard, Beads CLI artifact provider — full implementation (T09). Stores artifact…, Decode a raw manifest value into an ``ArtifactManifest``. Parameters ----------…, Return True when v is a dict with string keys., Extract an ``ArtifactManifest`` from a bd metadata dict. Tries the nested… (+9 more)

### Community 213 - "test_reconciliation.py"
Cohesion: 0.12
Nodes (11): _RECONCILIATION_NOT_IMPLEMENTED, Tests for reconciliation functions added by T2. Tests: _has_active_work,…, Verify _reconcile_closed_item handles closed GitHub issues correctly., Returns wip_protected when GitHub is closed but active local work exists., Returns closed and updates to terminal status when no active work exists., When GitHub has a terminal status label (e.g. 'done'), uses that instead of…, Verify ReconcileResult dataclass has all required fields and is constructible., ReconcileResult stores issue_number, action, old_status, new_status, and… (+3 more)

### Community 214 - "BeadsDispatchAdapter"
Cohesion: 0.10
Nodes (14): BeadsDispatchAdapter, Path, Return the filesystem path to the SQLite database., Initialise the state manager and ensure the database schema exists. Args:…, Thin adapter that records wave membership in beads molecule epics. SQLite…, Initialise adapter and load the wave→molecule ID sidecar. Args: db_path: Path…, Return the sidecar dict key for a (milestone, wave_num) pair., Read the sidecar JSON file into a mapping. Returns: Mapping of… (+6 more)

### Community 215 - "search.py"
Cohesion: 0.10
Nodes (21): apply_search_filter(), _build_haystack(), _candidate_item_ref(), _candidate_matched_field_and_snippet(), _extract_concept_words(), _item_field_text(), _item_matches_term(), _OrPred (+13 more)

### Community 216 - "_Predicate"
Cohesion: 0.16
Nodes (14): _AndPred, _NotPred, _Predicate, Base class for search predicates. Subclasses implement ``__call__(item,…, Evaluate the predicate against a single backlog item. Args: item: Backlog item…, Match a single leaf term against an item., Conjunction: both sub-predicates must match., Negation: the sub-predicate must not match. (+6 more)

### Community 217 - "ledger_spec.py"
Cohesion: 0.11
Nodes (24): Check, _clear_attempt_effects(), _cols(), Command, Effect, EventKind, Flag, Provenance (+16 more)

### Community 218 - "emit_result"
Cohesion: 0.16
Nodes (25): emit_result(), _is_result_mapping(), TypeGuard, Emit an operation result as JSON to stdout, then exit nonzero on error.…, Narrow operation results to the mapping shape used for diagnostics. Returns:…, conflicts(), item_status(), command (+17 more)

### Community 219 - "_InMemoryArtifactStore"
Cohesion: 0.08
Nodes (15): _FakeArtifactRegistryClient, _InMemoryArtifactStore, fixture, ArtifactRegistryClient subclass that delegates I/O to an in-memory store.…, Fresh in-memory artifact store per test., AC5: create(tasks=[])->append_task x2->finalize registers a FINALIZED artifact.…, AC6: a second finalize_plan call on an already-ready plan is a no-op. Verifies…, Deterministic in-memory artifact store for offline tests. Stores keyed by… (+7 more)

### Community 220 - "Evaluate SDLC Layers Skill"
Cohesion: 0.40
Nodes (5): Evaluate SDLC Layers Skill, Cross-Reference Validation Check, Doc Completeness Check, Integration Points Check, verify-done Skill

### Community 221 - "MonkeyPatch"
Cohesion: 0.13
Nodes (15): parse_disabled_hooks(), Read CLAUDE_SKILLS_DISABLED_HOOKS and return the set of disabled hook IDs.…, MonkeyPatch, Single hook ID returns a one-element set. Tests: parse_disabled_hooks() with…, Multiple comma-separated IDs return the full set. Tests: parse_disabled_hooks()…, Whitespace around each ID is stripped. Tests: parse_disabled_hooks() whitespace…, Trailing comma produces no empty-string entry in the result set. Tests:…, Consecutive commas produce no empty-string entries. Tests:… (+7 more)

### Community 222 - "GitHubArtifactProvider"
Cohesion: 0.10
Nodes (16): GitHubArtifactProvider, Unit tests for GitHubArtifactProvider.get_manifest. Tests: Manifest retrieval…, get_manifest returns empty manifest when the issue body is empty. Tests: No…, get_manifest handles None issue body gracefully. Tests: GitHub issues with null…, Unit tests for GitHubArtifactProvider.set_manifest. Tests: Manifest persistence…, set_manifest calls gist.edit() but skips updateIssue when sentinel is already…, Unit tests for GitHubArtifactProvider.read_artifact_content. Tests: Successful…, read_artifact_content returns file content for a valid plan/ path. Tests:… (+8 more)

### Community 223 - "_StubEncoder"
Cohesion: 0.14
Nodes (12): AbstractSet, _ensure_cl100k_cached(), Deterministic ~4-chars-per-token stand-in for cl100k_base (offline only).…, Return a token list whose length tracks the input length monotonically., Pre-warm tiktoken's encoding cache so importing ``server`` never downloads.…, _StubEncoder, Tests for the offline-safe tiktoken cache pre-warm installed by conftest (PR…, conftest pre-warmed the cache, so server import will not download. (+4 more)

### Community 224 - "Path"
Cohesion: 0.08
Nodes (25): first_party_module_paths(), loop_record(), preparation(), fixture, Path, TempPathFactory, Drive the whole work loop once and return what it recorded. Returns: The record…, Resolve the toolchain and lay out a state root under one test's own directory.… (+17 more)

### Community 225 - "Context-Fit Complexity: Adoption Conditions"
Cohesion: 0.13
Nodes (19): Context-Fit Complexity: Adoption Conditions, Adoption Sequence (C4→C7→C10→C1/C2→C3→C5/C6→C8/C9→C11), C10: Classify tasks by context-fit spectrum before choosing strategy, C11: Iterative knowledge discovery via speculation detection, C1: Measure complexity as context-fit, not implementation difficulty, C2: Three-term equation (knowledge + uncertainty + overhead), C3: Decompose at knowledge boundaries, not code boundaries, C4: Hardcode stable constraints; discover volatile constraints dynamically (+11 more)

### Community 226 - "test_backlog_groom_sections.py"
Cohesion: 0.11
Nodes (24): _call(), parametrize, Tests for the sections parameter of the backlog_groom MCP tool. Covers: -…, backlog_groom forwards the sections dict unchanged to groom_item. Tests:…, backlog_groom forwards sections=None when parameter is omitted. Tests:…, backlog_groom with sections={} still calls groom_item (no short-circuit in…, backlog_groom with sections propagates BacklogError as error dict. Tests:…, backlog_groom returns error dict when sections is combined with any per-section… (+16 more)

### Community 227 - "test_rtica_verdict_vocabulary_drift.py"
Cohesion: 0.11
Nodes (24): _assigned_verdicts(), _labelled_verdicts(), Path, Guards the RT-ICA verdict vocabulary against producer/consumer drift. Two…, Extract the verdict tokens a label introduces. Handles a single token…, Collect every verdict-labelled token in a file. A label is only reported when…, Collect every pseudocode-assignment verdict token in a file. Complements…, Return the text of a skill's verdict-vocabulary section. Args: path: Skill file… (+16 more)

### Community 228 - "beads_models.py"
Cohesion: 0.11
Nodes (21): Return a mapping of open beads issue titles to beads IDs. This is the beads-…, BeadsCommentRaw, BeadsDependencyRaw, BeadsIssueRaw, BeadsLabelRaw, parse_dependency_list(), parse_issue_list(), parse_ready_list() (+13 more)

### Community 229 - "view_result_from_local_item"
Cohesion: 0.13
Nodes (11): _parse_yaml_item_file(), Path, Build view result from a local backlog item. Returns: ViewItemResult with…, Load a per-item ``.yaml`` file into a BacklogItem using ruamel.yaml.…, view_result_from_local_item(), Tests for view_result_from_local_item(item: BacklogItem) -> ViewItemResult., View helper uses description from BacklogItem model, not file re-read. Tests:…, BacklogItem with status="open" produces result.status == "open". Tests: Status… (+3 more)

### Community 230 - "_patch_backend"
Cohesion: 0.18
Nodes (14): _patch_backend(), MockerFixture, A failed live lookup cannot confirm numeric-issue filter matches., The refusal degrades the answer, it does not shrink the backlog., A normalized cached status remains unconfirmed after the live query fails., A cached needs-grooming value remains unconfirmed after live failure., A filter that matched on the cached status must render that same status., Reproduction (P2, PR #3552 Codex review): the render path bypassed… (+6 more)

### Community 231 - "Blind completeness audit — the workflow multigraph"
Cohesion: 0.08
Nodes (23): Blind completeness audit — the workflow multigraph, COMPLETENESS-10 — Hierarchy is nominal; `subgraph_ref` has no referent, COMPLETENESS-11 — No entry or terminal marking, and unused outputs are uncovered, COMPLETENESS-12 — Unnecessary path length cannot be reported at all, COMPLETENESS-13 — `ExtractionStatus.ASSUMED` and `ABSENT` cannot be recorded without inventing a span, COMPLETENESS-14 — Revision checking passes silently when either side is unversioned; no snapshot or fingerprint entity, COMPLETENESS-15 — A failure signal is not something an edge can carry, COMPLETENESS-16 — One-time versus recurring work has no carrier (+15 more)

### Community 232 - "TestTaskFieldValidators"
Cohesion: 0.08
Nodes (13): Verify Task.validate_task_id_list field validator. Tests: dependencies and…, Verify list of task IDs accepted., Verify comma-separated string parsed into list., Verify None dependency returns empty list., Verify 'none' string returns empty list., Verify 'n/a' string returns empty list., Verify '-' string returns empty list., Verify empty string returns empty list. (+5 more)

### Community 233 - "test_agent_profile/conftest.py"
Cohesion: 0.17
Nodes (23): circular_plugin_root(), _clear_manifest_index_cache(), domain_plugin_root(), manifest_plugin_root(), multi_plugin_root(), fixture, Path, Shared fixtures for agent_profile unit tests. All fixtures use tmp_path and… (+15 more)

### Community 234 - "_trace"
Cohesion: 0.12
Nodes (14): Tests for gap-edge wiring and gap_count computation in assemble_graph.py.…, Regression coverage: completes_workflow's existing deliberate design (routes_to…, A completes_workflow target that is a workflow-internal heading phrase (not a…, A completes_workflow trace with no terminal_target (observed in the shipped L1…, Build a minimal L1 trace dict, overridable per test., A trace with no terminal_type at all is not a transition to represent -- must…, The stub node _process_trace creates for an unresolved gap target must be…, When the target skill IS independently confirmed, hands_off_to_skill must emit… (+6 more)

### Community 235 - "_seed_wave"
Cohesion: 0.10
Nodes (15): Integration tests for the dispatch_item_status MCP tool. Tests the…, dispatch_item_status records completion for an existing item. Tests:…, dispatch_item_status records failure for an existing item. Tests:…, dispatch_item_status treats skipped as a failed terminal state. Tests:…, dispatch_item_status returns error dict when issue not found in any wave.…, dispatch_item_status returns error dict for an unrecognised status value.…, Integration tests for the dispatch_wave_status MCP tool. Verifies the wave…, dispatch_wave_status returns aggregated item counts for a known wave. Tests:… (+7 more)

### Community 236 - "test_paginate_body.py"
Cohesion: 0.14
Nodes (23): _make_body(), _make_entry(), Tests for entry-block-aware pagination in _paginate_body_result. Covers: -…, offset=0, limit=0 (unlimited) returns all entry blocks unchanged., offset larger than block count yields an empty body with no truncation flag., A body with no entry blocks uses line-based offset/limit (no regression)., Line-based fallback sets body_remaining_lines, not body_remaining_entries., Line-based fallback sets no truncation flag when all lines fit in limit. (+15 more)

### Community 237 - "TestBuildIssueBodyFromFileDict"
Cohesion: 0.14
Nodes (11): skip, fixture, Tests for _build_issue_body_from_file(item: dict) -> str | None. This is the…, Narrow *build_fn* for ty; body never runs while the class is skipped., Skip — scripts/backlog.py was intentionally deleted; class is skipped. The…, Dict item without '## Groomed' in _raw_body returns None. Tests: Gate logic for…, Dict item with '## Groomed' in _raw_body returns stripped body + newline.…, All sections from _raw_body appear exactly once — no duplication. Tests:… (+3 more)

### Community 238 - "test_scenarios.py"
Cohesion: 0.10
Nodes (15): provider_state(), fixture, MonkeyPatch, Scenario-based integration tests for the backlog MCP FastMCP server. Tests are…, Scenarios for backlog_view with include_content=False (compact mode). Verifies…, Scenario C1b: backlog_view(include_content=False) omits body and sections keys.…, Scenario C1c: backlog_view(include_content=False) returns all metadata fields.…, Scenario C1e: backlog_view without include_content returns full body (backward… (+7 more)

### Community 239 - "TestMainIntegration"
Cohesion: 0.12
Nodes (17): hook_input_subagent_stop(), Any, CaptureFixture, fixture, MockerFixture, Tests for the disabled-hook control in task_status_hook.py. Tests: disabled-…, Integration tests for main() covering SubagentStop dispatch and disable…, No env vars + SubagentStop -> handle_subagent_stop called. Tests: main()… (+9 more)

### Community 240 - "_load_frontmatter_from_path"
Cohesion: 0.12
Nodes (22): _load_frontmatter_from_path(), _load_md_frontmatter(), _normalize_skills(), Any, Path, Parse YAML frontmatter and body from a markdown string. Args: text: Markdown…, Load frontmatter from a file path. Args: path: Path to a markdown file with…, Normalise raw YAML skills value to a flat list of stripped strings. Args: raw:… (+14 more)

### Community 241 - "bundle_requires_relaxed_verification"
Cohesion: 0.12
Nodes (13): bundle_requires_relaxed_verification(), Decide whether ca_bundle adds an anchor that VERIFY_X509_STRICT would reject. A…, Only a locally added anchor that strict verification rejects earns the…, Nix and conda point these variables at a copy of the public roots. The public…, The proxy CA shape this module exists for: verify code 92., Verify code 89: Basic Constraints of CA cert not marked critical., Verify code 79: invalid CA certificate., Verify code 86: CA certificate missing a SubjectKeyIdentifier extension.… (+5 more)

### Community 242 - "parse_jsonl_events"
Cohesion: 0.16
Nodes (20): find_first_event(), _iter_json_lines(), parse_jsonl_events(), Any, Path, Shared JSONL parsing utilities for Claude Code session transcript handling., Yield each well-formed JSON object in a JSONL file. Skips blank lines and lines…, Parse a JSONL file and optionally filter by event type. Handles missing files… (+12 more)

### Community 243 - "handle_subagent_stop"
Cohesion: 0.15
Nodes (23): handle_subagent_stop(), Settle the attempt the stopping sub-agent was launched for; write no status.…, _launch_transcript(), CaptureFixture, MonkeyPatch, Path, terminate_process_tree must resolve from inside the plugin package, not repo-…, Write a transcript in the JSONL shape the hook parses, carrying *prompt* as the… (+15 more)

### Community 244 - "test_github_tools_labels.py"
Cohesion: 0.13
Nodes (22): _call(), _make_label(), MonkeyPatch, Tests for backlog_list_labels MCP tool and list_labels operation. Tests are…, list_labels maps None description to empty string., backlog_list_labels tool returns labels list with count and output keys., backlog_list_labels calls list_labels with default limit=100 when omitted., backlog_list_labels returns dict with error key on BacklogError. (+14 more)

### Community 245 - "build_issue_body_from_file"
Cohesion: 0.15
Nodes (14): build_issue_body_from_file(), Build GitHub issue body from local per-item file content. For ``.yaml`` items,…, Write a minimal .md item file to tmp_path and return a BacklogItem with…, Tests for build_issue_body_from_file(item: BacklogItem) -> str | None. Verifies…, Ungroomed items return None — they should not be synced to GitHub. Tests: Gate…, Groomed items return file body.strip() + newline. Tests: Passthrough behavior…, All sections from file body appear exactly once in output. Tests: Content…, Output must NOT contain synthetic 'As a developer, I want to' text. Tests:… (+6 more)

### Community 246 - "Final Verification Skill (SAM Stage 7)"
Cohesion: 0.22
Nodes (9): Discovery Skill (SAM Stage 1), ARTIFACT:DISCOVERY, Discovery Human Touchpoint Gate, Self-Initialization from Backlog Item, Final Verification Skill (SAM Stage 7), ARTIFACT:VERIFICATION, Goal-Backward Verification Principle, NOT_CERTIFIED Remediation Loop (+1 more)

### Community 247 - "_item"
Cohesion: 0.13
Nodes (13): _item(), ``count_only`` must surface a genuine operations-layer degradation…, A real BackendUnavailableError from batch_fetch_statuses (B1's swallow-point…, A healthy refresh populates out.info() (routine reconcile prose) but that must…, A requested refresh must report incomplete reconciliation and queued mutations., ``count_only`` surfaces #3546 B5's typed degradation-provenance fields the same…, A successful live batch fetch is not a degradation -- must not appear., A backend with no live batch-fetch support reports status_source='cache', a… (+5 more)

### Community 248 - "TestSelectorAndSlugGeneration"
Cohesion: 0.09
Nodes (12): Selectors encode heading depth and sibling index; slugs are URL-safe., First (and only) h1 gets selector 'h1.1'., Title' heading produces slug 'title'., First h2 (child of h1.1) gets selector 'h2.1.1'., Section A' heading produces slug 'section-a'., h3 under h2.1.1 gets selector 'h3.1.1.1'., Sub A' heading produces slug 'sub-a'., Second h2 sibling gets selector 'h2.1.2' (sibling index 2, not 1). (+4 more)

### Community 249 - "exit_with_json_error"
Cohesion: 0.12
Nodes (15): exit_with_json_error(), NoReturn, Emit ``payload`` as JSON to stdout, then exit nonzero. Unlike :func:`err`,…, CaptureFixture, Tests for the ``cli_output`` JSON-on-error contract. Tests:…, A mapping without an ``error`` key still returns normally. Tests: Regression…, ``exit_with_json_error`` writes JSON to stdout before exiting., The payload reaches stdout as compact JSON, not stderr text. Tests: stdout… (+7 more)

### Community 250 - "TestTaskBookendFields"
Cohesion: 0.09
Nodes (12): Verify Task model bookend field defaults and construction. Tests: is_bookend…, Verify is_bookend defaults to False on a minimal Task. Tests: Backward…, Verify bookend_type defaults to None on a minimal Task. Tests: Backward…, Verify Task with is_bookend=True and bookend_type='t0-baseline'. Tests: T0…, Verify Task with is_bookend=True and bookend_type='tn-verification'. Tests: TN…, Verify bookend fields accept kebab-case alias keys. Tests: YAML kebab-case…, Verify model_dump(exclude_defaults=True) omits default bookend fields. Tests:…, Verify model_dump includes bookend fields when explicitly set. Tests:… (+4 more)

### Community 251 - "TestStatusMap"
Cohesion: 0.09
Nodes (12): Verify STATUS_MAP contains expected normalization mappings., Verify 'NOT STARTED' maps to 'not-started'., Verify 'IN PROGRESS' maps to 'in-progress'., Verify 'COMPLETE' maps to 'complete'., Verify ':white_check_mark:' emoji maps to 'complete'., Verify ':x:' emoji maps to 'not-started'., Verify '[DEFERRED]' title marker maps to 'deferred'., Verify '[SKIPPED]' title marker maps to 'skipped'. (+4 more)

### Community 252 - "TestBackendStatusDefaults"
Cohesion: 0.09
Nodes (12): BackendStatus default construction produces a valid model with…, BackendStatus() defaults availability to NOT_CHECKED. Tests:…, BackendStatus() defaults name to 'GitHub'. Tests: BackendStatus.name default…, BackendStatus() defaults open_count to None. Tests: BackendStatus.open_count…, BackendStatus() defaults total_count to None. Tests: BackendStatus.total_count…, BackendStatus() defaults cache_open_count to 0. Tests:…, BackendStatus() defaults cache_total_count to 0. Tests:…, BackendStatus.cache_open_count accepts None distinct from its 0 default. Tests:… (+4 more)

### Community 253 - "_item"
Cohesion: 0.17
Nodes (14): _item(), _patch_repo(), Exception, MockerFixture, parametrize, ``get_github`` raising is the no-token path, not an environment-wide refusal., Build a minimal backlog item carrying the given issue reference., Minimal stand-in for the PyGithub repository ``get_github`` returns. (+6 more)

### Community 254 - "test_ledger_spec.py"
Cohesion: 0.10
Nodes (4): Status, parametrize, Closure tests over ``dh_core.ledger_spec``. Each test names one way the…, test_every_task_command_handles_every_status_exactly_once()

### Community 255 - "new_ledger"
Cohesion: 0.16
Nodes (21): accept_accepted_and_incomplete(), accept_accepted_and_unreported(), dispatch_archived_and_unready(), imported(), new_ledger(), Path, Open an empty ledger in a temporary directory. Args: tmp_path: The test's…, Import a one-task plan in a state the task commands cannot reach on their own.… (+13 more)

### Community 256 - "_call"
Cohesion: 0.15
Nodes (9): _call(), Scenario 11: backlog_close closes an item with a reason and no blocking PRs., Scenario 8: backlog_update sets a plan path and returns title + plan field., Scenario 9: backlog_update with status=in-progress calls…, Scenario 10: backlog_update creates a GitHub issue when the item lacks one., Scenario 12: backlog_resolve marks item resolved and calls resolve_github_issue., Call MCP tool via in-memory transport and parse JSON response. Delegates to…, Scenarios consumed by /work-backlog-item skill. Covers browse/list, view,… (+1 more)

### Community 257 - "_populated_cache_state"
Cohesion: 0.21
Nodes (19): _content_mutation_key(), PendingMutation, _PendingWorkItemMutation, Reproducible idempotency key for a queued content write. Shared by…, Reproducible idempotency key for a queued work-item mutation. Shared by…, Durable provider mutation awaiting acknowledgement., _work_item_mutation_key(), _populated_cache_state() (+11 more)

### Community 258 - "issue_to_local_fields"
Cohesion: 0.16
Nodes (13): issue_to_local_fields(), Extract backlog-relevant fields from a GraphQL IssueNode dict. Accepts an…, make_parsed_issue_node(), Return an already-parsed IssueNode-shaped dict with flat label/assignee lists.…, issue_to_local_fields accepts IssueNode TypedDict instead of a PyGithub Issue…, issue_to_local_fields extracts priority from 'priority:*' label. Tests:…, issue_to_local_fields extracts item_type from 'type:*' label. Tests:…, issue_to_local_fields sets status='done' for CLOSED issues. Tests:… (+5 more)

### Community 259 - "Technical Researcher"
Cohesion: 0.13
Nodes (15): API State Skill, Codebase Auditor Skill, Ecosystem Research Skill, Impact Measurement Skill, Research Note Skill, Impact Analyst Agent, RT-ICA Assessor Agent, Technical Researcher (+7 more)

### Community 260 - "merge_integration_branch"
Cohesion: 0.14
Nodes (14): merge_integration_branch(), MergeResult, Merge ``head_branch`` into ``base_branch``. Uses PyGithub's ``repo.merge()``…, _make_github_exception(), GithubException, merge_integration_branch merges head into base and handles conflicts., Test successful merge returns MergeResult with sha and message. Tests:…, Test repo.merge() is called with base, head, and commit_message. Tests:… (+6 more)

### Community 261 - "_validate_slug"
Cohesion: 0.14
Nodes (12): Validate slug against the required pattern. Args: slug: Hyphenated slug string…, _validate_slug(), _validate_slug enforces ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ pattern., Test valid simple slug passes without raising. Tests: _validate_slug — valid…, Test valid slug with dots and underscores passes. Tests: _validate_slug — valid…, Test empty string raises BacklogError. Tests: _validate_slug — empty string…, Test slug starting with hyphen raises BacklogError. Tests: _validate_slug —…, Test slug starting with dot raises BacklogError. Tests: _validate_slug — first… (+4 more)

### Community 262 - "groom_item"
Cohesion: 0.15
Nodes (19): groom_item(), _is_section_entry_metadata(), TypeGuard, Write groomed content through the configured backend. Delegates to update_item.…, Return ``True`` when *value* is a :class:`SectionEntryMetadata` TypedDict.…, Integration test: full entry block lifecycle. Tests the round-trip: create item…, Create item -> groom with entries -> strike one -> view -> verify., Real write -> render -> parse cycle through operations, not entry_blocks… (+11 more)

### Community 263 - "find_content_duplicates"
Cohesion: 0.21
Nodes (8): find_content_duplicates(), Find existing backlog items whose content overlaps the given title/description.…, _candidate(), parametrize, The real #3169 failure case: reworded duplicate the old SequenceMatcher…, Real, resolved, unrelated backlog_core/backlog-mcp issues must never match. See…, Tests for find_content_duplicates(title, description, candidates, max_results)., TestFindContentDuplicates

### Community 264 - "_item"
Cohesion: 0.14
Nodes (11): _item(), A numeric-issue item's cache may hold the bare lifecycle value, not the label.…, "open"/"done"/"closed" have no ``status:*`` label counterpart — leave them bare., Reproduction (P1, PR #3552 Codex review): unlike every other bare lifecycle…, Build an open backlog item carrying the given issue reference and cached status., ``_item_derived_status`` must not invent a status for an issue nobody asked…, A successful query that omitted the issue did not establish its status., Reproduction: a live status map entry carrying the literal ``"status:needs-… (+3 more)

### Community 265 - "_warnings"
Cohesion: 0.13
Nodes (10): _CacheBackend, _NativeBackend, Backend stub whose cache is fed by an external provider. Deliberately does not…, Backend stub that owns its own storage, with no provider to lag behind., Narrow the heterogeneous ``list_items`` result to its warning strings., ``count: 0`` from a cache that never synced is not the same answer as an empty…, A genuine zero against a populated cache is an answer, not an ambiguity., SQLite, memory and beads own their storage — an empty read is authoritative. (+2 more)

### Community 266 - "TestCodeBlocks"
Cohesion: 0.10
Nodes (11): Code blocks are attributed to sections with correct language and spans., Document with two fenced code blocks produces exactly two CodeBlock entries., First code block (code_0001) has language 'python'., Python block section_id resolves to 'Section A'., Python block fence occupies lines 8-10 inclusive (0-based)., Second code block (code_0002) has language 'bash'., Bash block section_id resolves to 'Section B'., Bash block fence occupies lines 20-22 inclusive (0-based). (+3 more)

### Community 267 - "_build_all_nodes"
Cohesion: 0.11
Nodes (19): build_agent_nodes(), _build_all_nodes(), build_backend_nodes(), build_mcp_tool_nodes(), build_reference_file_nodes(), build_skill_nodes(), collect_all_skill_names(), LayerData (+11 more)

### Community 268 - "Model fidelity — the workflow multigraph against `ledger_spec.py` and `sam_schema/core/models.py`"
Cohesion: 0.10
Nodes (19): A note on the contract, stated rather than worked around, FIDELITY-10 — a specification's quantified rules have no representation in a ground graph, FIDELITY-11 — ordered checks, waivers, and the refusal/noop/outcome trichotomy are lost, FIDELITY-12 — type satisfaction is string equality, so a value range is invisible, FIDELITY-13 — half the declared edge types are inert, and the semantic queries read node attributes, FIDELITY-14 — thirteen required node-record fields are read by nothing, and the extraction defaults them, FIDELITY-15 — every source span in the extraction is a bare 1220-line file path, FIDELITY-1 — the D1 fragment is `OBSERVED` from a source that states the opposite (+11 more)

### Community 269 - ".__init__"
Cohesion: 0.10
Nodes (10): Initialize with the plan ID and the bookend validation failures. Args: plan_id:…, Initialize with the plan ID and failure reason. Args: plan_id: The plan…, Initialize with a descriptive configuration guidance message., Initialize with the plan ID that cannot be claimed concurrently. Args: plan_id:…, Initialize with the opaque content reference that failed. Args: content_ref:…, Initialize with the plan ID that could not be found. Args: plan_id: The plan…, Initialize with the duplicate plan ID. Args: plan_id: The plan identifier that…, Initialize with the plan and task identifiers. Args: plan_id: The plan the task… (+2 more)

### Community 270 - "RT-ICA: Reverse Thinking - Information Completeness Assessment"
Cohesion: 0.36
Nodes (8): Planner RT-ICA (Planning-Phase Input Completeness Analysis), SAM Stage 2 — Planning, Instruction Reviewing Checklist, RT-ICA: Reverse Thinking - Information Completeness Assessment, Dhuliawala et al. 2023 — Chain-of-Verification Reduces Hallucination, Liu et al. 2025 — Reverse Thinking Enhances Missing Information Detection in LLMs, RT-ICA Framework, Safe Default Gate

### Community 271 - "test_cli.py"
Cohesion: 0.10
Nodes (19): Tests for sam_schema.cli — Typer CLI commands via CliRunner., List --search with no matching plans returns an empty items array., A UID id spelled with alternating upper/lower hex digits canonicalises to one…, A lowercase ``p`` prefix paired with uppercase hex digits still canonicalises.…, --help output lists the grouped command domains., Flat paths, positional data, and removed flags fail at the parser boundary., Successful plan commands emit compact JSON on stdout., The default is every row, emitted as one line of compact JSON. (+11 more)

### Community 272 - "Path"
Cohesion: 0.10
Nodes (20): Path, append-task rejects --stdin combined with a scalar typed task option. Tests:…, Read P1/T1 returns TaskAssignment JSON with plan context + nested task., Read P1/T99 (task not in plan) exits 1., append-task uses named typed task fields., Ready P1 returns a JSON envelope with ready_tasks (may be empty or contain…, State P1/T3 in-progress updates status and prints old -> new., State P1/T3 complete shows both old and new status in output. (+12 more)

### Community 273 - "test_ledger_check_order.py"
Cohesion: 0.12
Nodes (19): milestone_existing_and_leased(), milestone_plan(), pairs_of(), Ordering tests for the checks ``ledger_spec.TRANSITIONS`` lists against each…, Return every ordered pair of one transition's checks, earlier first. Args:…, Return every ordered pair of checks the specification states, by command.…, Return one pair's identity, independent of which check the specification puts…, Build the plan one milestone item describes. Returns: The source, ready for… (+11 more)

### Community 274 - "TestCommitPrefixRegex"
Cohesion: 0.11
Nodes (6): parametrize, Module-level constants have correct types and values., DEFAULT_REPO is empty before init(); discover_repo() resolves it., COMMIT_PREFIX_RE strips conventional-commit prefixes., TestCommitPrefixRegex, TestConstants

### Community 275 - "TestLegacyPathMap"
Cohesion: 0.10
Nodes (11): Tests for LEGACY_PATH_MAP constant: presence, mapping correctness, callability.…, Verify .claude/backlog key is present in LEGACY_PATH_MAP. Tests:…, Verify plan key is present in LEGACY_PATH_MAP. Tests: LEGACY_PATH_MAP key…, Verify .claude/context key is present in LEGACY_PATH_MAP. Tests:…, Verify .claude/reports key is present in LEGACY_PATH_MAP. Tests:…, Verify .claude/backlog maps to the string 'backlog_dir'. Tests: LEGACY_PATH_MAP…, Verify plan maps to the string 'plan_dir'. Tests: LEGACY_PATH_MAP maps plan…, Verify .claude/context maps to the string 'context_dir'. Tests: LEGACY_PATH_MAP… (+3 more)

### Community 276 - "test_network_guard.py"
Cohesion: 0.16
Nodes (19): plugin_root_probe(), _probe_command(), Path, Proves the session-level socket guard in the root conftest blocks the network.…, An ``@pytest.mark.e2e`` test without the env var is still blocked. The block…, With both the marker and the env var, the policy gate opens. Asserts the guard…, The gate stays open while a class-scoped e2e fixture tears down. A class-scoped…, After a pytest subprocess finishes, the parent process sockets are intact. Runs… (+11 more)

### Community 277 - "test_retired_terms.py"
Cohesion: 0.16
Nodes (19): _find_hits(), _iter_runtime_files(), parametrize, Path, Guards runtime-read plugin files against retired-term regressions (PR #3427).…, Return every file an installed Claude Code agent can read or run at runtime.…, Return `path` relative to whichever scan root owns it, for a readable failure…, Return one `path:line: text` entry per runtime-corpus match of `term`. Matches… (+11 more)

### Community 278 - "TestSemanticMatchingInfrastructure"
Cohesion: 0.10
Nodes (11): Integration tests for the semantic matching strategy chain infrastructure.…, Query for 'login' issue finds auth-related item when filtered by type='Bug'., When substring matches exist, title filter returns them directly without…, type='Bug' combined with title substring finds the correct bug from a mixed…, topic filter narrows candidates using substring match on auto-derived topic…, Items without metadata.type are excluded when type filter is active., type filter performs case-insensitive exact match., topic filter performs case-insensitive substring match. (+3 more)

### Community 279 - "_CacheStateStore"
Cohesion: 0.18
Nodes (17): _CacheState, _CacheStateStore, Serialize state transactions across threads and processes., Union all five queue/dead-letter fields from ``legacy`` into ``current``.…, True when a raw (dict-shaped) checkpoint literally omits scope metadata keys.…, test_a_second_unparsable_legacy_file_does_not_overwrite_the_first_backup(), test_empty_state_round_trips_through_save_and_load(), test_load_dead_letters_pending_entry_from_version_skew_not_just_hand_edits() (+9 more)

### Community 280 - "build_issue_body"
Cohesion: 0.20
Nodes (7): build_issue_body(), Build GitHub issue body from backlog item fields. Emits only sections whose…, Tests for build_issue_body(item: BacklogItem) -> str., No Story section is generated at creation. Tests: A user story is a grooming…, No Acceptance Criteria section is generated at creation. Tests: Acceptance…, No section content is synthesised from the item title. Tests: Root-cause guard…, TestBuildIssueBody

### Community 281 - "_validate_metadata"
Cohesion: 0.13
Nodes (12): Any, Coerce raw YAML metadata values to ``str`` or ``dict[str, str]`` at the parse…, _validate_metadata(), Tests for _validate_metadata — the YAML metadata boundary coercion function., Integer values must be coerced to strings at the YAML boundary. Tests:…, None values (YAML null) must be coerced to empty string. Tests:…, List values must be coerced to their string representation. Tests:…, Boolean values must be coerced to strings. Tests: _validate_metadata bool… (+4 more)

### Community 282 - "test_open_pr_search_failure.py"
Cohesion: 0.19
Nodes (18): _backend_with_failing_pr_search(), _backend_with_network_failing_pr_search(), Exception, MockerFixture, parametrize, close_item and resolve_item refuse when the open-PR search fails. A failed…, close_item raises BacklogError, and does not close the item, when the PR search…, resolve_item(force=True) resolves the item without running the PR search at… (+10 more)

### Community 283 - "Findings — finding verification: the falsified predicates, and the severity rule"
Cohesion: 0.11
Nodes (18): Coverage at a glance, Findings — finding verification: the falsified predicates, and the severity rule, PREDICATES-10 — the four pairwise predicates silently skip any edge that does not bind both descriptors, PREDICATES-11 — descriptor facets are marked OBSERVED against spans that do not state them, PREDICATES-12 — the severity rule: `BROKEN` is reachable where `CONTRACT_UNSPECIFIED` is required, PREDICATES-13 — a `Finding` is not bound to the `Graph` it claims to be about, PREDICATES-14 — three of the eight queries have no test, and the taxonomy-to-contract match is unasserted, PREDICATES-15 — hierarchy: `subgraph_ref` resolves to nothing, and no predicate descends (+10 more)

### Community 284 - "cli.py"
Cohesion: 0.18
Nodes (15): get(), list_artifacts(), command, Option, Provider-neutral artifact command group., Register or update an artifact., List artifacts registered for an item., Get artifact metadata. (+7 more)

### Community 285 - "._load_plan"
Cohesion: 0.11
Nodes (11): Any, Path, Initialize with an optional plan directory. Args: plan_dir: Root directory for…, The filesystem path to the plan directory., Resolve a plan_id to its filesystem path (public API). Args: plan_id: Backend-…, Resolve a plan_id to its filesystem path. Args: plan_id: Backend-assigned plan…, Load a plan from any supported format via the reader pipeline. Delegates to…, Return lightweight summaries for all plans, optionally filtered. Args: search:… (+3 more)

### Community 286 - "Path"
Cohesion: 0.15
Nodes (19): _make_spawn_args(), Path, Build a mock Namespace for cmd_spawn., Verify --worktree {name} appears in the argv passed to tmux new-session., Verify spawn polls until the claude-created tmux session appears., Verify spawn sends the initial prompt to the claude pane via tmux send-keys., Verify spawn fails if claude's tmux session never appears within timeout., test_cmd_spawn_creates_registry_entry() (+11 more)

### Community 287 - "TestRealPluginsIntegration"
Cohesion: 0.11
Nodes (12): fixture, integration, MonkeyPatch, Integration tests using the real plugins/ filesystem. Tests: profile_load and…, Set CLAUDE_PLUGIN_ROOT to the development-harness plugin directory. In the MCP…, profile_list against real plugins returns at least one agent. Tests: Real-…, profile_list filtered to development-harness returns >= 1 agent. Tests: Plugin-…, profile_load for 'task-worker' returns a non-empty instruction body. Tests:… (+4 more)

### Community 288 - "Path"
Cohesion: 0.15
Nodes (11): Path, Returns (True, reason) when a plan file has a task with legacy IN PROGRESS…, Returns (True, reason) when a plan file has a task with YAML status: in-…, Returns (False, '') when plan file exists but all tasks are COMPLETE., Returns (True, reason) when an active-task context file references the item's…, Returns (False, '') when context files exist but reference a different issue., Returns (False, '') when item has no _topic field — skips plan file check., Returns (False, '') when item has a non-numeric _issue field. (+3 more)

### Community 289 - "_is_not_found_error"
Cohesion: 0.15
Nodes (11): _is_not_found_error(), Check if a GraphQL BacklogError is the genuine issue-not-found error.…, Tests for _is_not_found_error() helper. Tests: _is_not_found_error structurally…, _is_not_found_error returns True for the exact synthesized message. Tests:…, _is_not_found_error matches regardless of message casing. Tests:…, _is_not_found_error returns False for unrelated error messages. Tests:…, _is_not_found_error returns False for rate limit errors. Tests:…, _is_not_found_error returns False for a repository-not-found error. Tests:… (+3 more)

### Community 290 - "TestParentChildRelationships"
Cohesion: 0.11
Nodes (10): Parent IDs and child_ids lists reflect heading nesting depth., Title (h1) has exactly two direct children., Title's children are Section A and Section B in document order., Section A has exactly one child: Sub A., Sub A (h3) is a leaf section with an empty child_ids list., Section B (h2) is a leaf section with an empty child_ids list., Both h2 sections have the h1 Title section as their direct parent., Sub A's parent is Section A (not Title). (+2 more)

### Community 292 - "Execution Skill (SAM Stage 5)"
Cohesion: 0.20
Nodes (10): Code Reviewer, dh:task-worker Agent, Choose the Dispatch Target Rule, Execution Skill (SAM Stage 5), ARTIFACT:EXECUTION, Deterministic Backpressure (Quality Gates), Task File IS the Prompt Principle, Forensic Review Skill (SAM Stage 6) (+2 more)

### Community 293 - "Multi-Perspective Review"
Cohesion: 0.22
Nodes (10): Accessibility Reviewer Agent, Performance Reviewer Agent, Quality Reviewer Agent, Security Reviewer Agent, Dispatch Contract, Task agent Field Is Not a Routing Directive, Dispatch Role Vocabulary (Orchestrator/Task Executor/Agent Profile), Acceptance Test Guide — Multi-Perspective Review (+2 more)

### Community 294 - "TestBodySpanBoundaries"
Cohesion: 0.11
Nodes (10): body_span and heading_span encode precise line ranges for each section. The…, h1 'Title' heading occupies only line 0 (start_line == end_line == 0)., h1 body (intro prose) spans lines 1-3, before the first h2 at line 4., Section A heading occupies only line 4., Section A body spans lines 5-11 (line before Sub A heading at 12)., Sub A heading occupies only line 12., Sub A body (leaf, no children) spans lines 13-15., Section B heading occupies only line 16. (+2 more)

### Community 295 - "dh_config.py"
Cohesion: 0.16
Nodes (16): _auto_detect_beads(), _dh_user_root_path(), _get_config_search_paths(), _is_str_dict(), _load_yaml_config(), Path, TypeGuard, DHConfig — unified backend-name resolver using .dh/config.yaml. Resolution… (+8 more)

### Community 296 - "LayeredGraph"
Cohesion: 0.15
Nodes (11): LayeredGraph, BaseModel, Observation, Delegate to :meth:`LedgerGraph.edges_without_workflow_origin`. Returns: One…, Delegate to :meth:`WorkGraph.missing_bookends`. Returns: One observation per…, Delegate to :meth:`DecompositionInput.untraced_planned_nodes`. Returns: One…, Delegate to :meth:`DecompositionInput.unreached_items`. Returns: One…, The ledger, work and workflow graphs together. Layer 1 (ledger), layer 2 (work)… (+3 more)

### Community 297 - "ADR-9: Close/Resolve Semantic Redesign"
Cohesion: 0.50
Nodes (4): ADR-9: Close/Resolve Semantic Redesign, ADR-8: close --reason Semantic Correction (superseded), close = dismissed without completion, resolve = completed with evidence

### Community 298 - "Groomed"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Acceptance Criteria Verification, Agents, Decision, Dependencies, Fact-Check, Files, Groomed (+9 more)

### Community 299 - "Sample Item Groomed Fixture (fact_check, rt_ica, issue_classification, groomed sections)"
Cohesion: 0.40
Nodes (6): Assign Back Details (heavy conflict escalation), Conflict Severity Classification, Sample GitHub Issue Body Fixture (backlog item raw markdown), Sample Item Entries Fixture (struck fact-check round-trip), Sample Item Fixture (ungroomed, empty sections), Sample Item Groomed Fixture (fact_check, rt_ica, issue_classification, groomed sections)

### Community 300 - "command-routes.schema.json"
Cohesion: 0.17
Nodes (11): commands, description, type, additionalProperties, description, type, properties, commands (+3 more)

### Community 301 - "Worktree Worker Full Protocol (M1,M2,M4,M8,M9)"
Cohesion: 0.33
Nodes (7): Merge Slot Lifecycle, Quality Gate Commands (pre_merge / post_merge), Blocker Handling (STATUS: PARTIAL), Completion Report Format (COMPLETE/PARTIAL/FAILED), Constant Commits Protocol, Worktree Worker Full Protocol (M1,M2,M4,M8,M9), Critical Constraint: Worktree Workers Have No Agent Tool

### Community 302 - "TestTaskAliasHandling"
Cohesion: 0.11
Nodes (10): Verify Task model populate_by_name and alias behavior. Tests: Kebab-case YAML…, Verify 'blocked-by' alias populates blocked_by., Verify 'blocked_by' Python name also works., Verify 'last-activity' alias populates last_activity., Verify 'github-issue' alias populates github_issue., Verify 'issue-classification' alias populates issue_classification., Verify 'analysis-method' alias populates analysis_method., Verify 'expected-outputs' alias populates expected_outputs. (+2 more)

### Community 303 - "TestTaskStatusEnum"
Cohesion: 0.11
Nodes (10): Verify TaskStatus StrEnum members and values. Tests: Canonical status values…, Verify NOT_STARTED maps to 'not-started'., Verify IN_PROGRESS maps to 'in-progress'., Verify COMPLETE maps to 'complete'., Verify BLOCKED maps to 'blocked'., Verify DEFERRED maps to 'deferred'., Verify SKIPPED maps to 'skipped'., Verify FAILED maps to 'failed'. (+2 more)

### Community 304 - "MonkeyPatch"
Cohesion: 0.14
Nodes (12): LogCaptureFixture, MonkeyPatch, try_get_github returns None only for the config state; it raises for a real…, try_get_github returns None when no token variable supplies a token. Tests:…, The missing-token path stops at token resolution and opens no connection.…, A missing token is reported at WARNING and carries no exception info. Tests:…, try_get_github raises GitHubUnavailableError when PyGithub raises…, try_get_github raises GitHubUnavailableError when get_repo raises a transport… (+4 more)

### Community 305 - "_make_item"
Cohesion: 0.14
Nodes (12): _make_item(), Construct a minimal BacklogItem suitable for create_issue_for_item., create_issue_for_item creates an issue and returns a positive integer number., create_issue_for_item returns a positive integer issue number. Why: Callers…, An issue created via create_issue_for_item is fetchable by its number. Why: The…, Newly created issues start in OPEN state. Why: The protocol requires new issues…, Two successive create calls return distinct, increasing issue numbers. Why:…, batch_fetch_statuses returns IssueStatus entries for items with issue numbers. (+4 more)

### Community 306 - "TestEndToEndQueryToResult"
Cohesion: 0.11
Nodes (10): End-to-end tests exercising the full path: user query -> backlog_list call ->…, Full e2e path: create items, issue query via backlog_list, receive matched…, Fallback chain e2e: Strategy 1 (substring) finds match immediately — no…, Fallback chain e2e: Strategy 1 (substring) returns zero -> Strategy 2 (filter-…, Fallback chain e2e: Strategy 1 and 2 return zero -> Strategy 3 (LLM semantic)…, Fallback chain e2e: all 3 strategy transitions are observable in sequence.…, Backward compatibility: existing callers using only title= produce identical…, Backward compatibility: calling backlog_list with no params returns all items. (+2 more)

### Community 307 - "resolve_ca_bundle"
Cohesion: 0.17
Nodes (9): Return the CA bundle path an interception proxy has configured, if any.…, resolve_ca_bundle(), A CA bundle counts only when the path it names exists on disk., A stale path is not a configured proxy, so it is skipped rather than trusted., Nix/conda's SSL_CERT_FILE must not shadow a proxy's REQUESTS_CA_BUNDLE. A Nix…, CURL_CA_BUNDLE is requests' own documented cURL-compatibility fallback.…, Finding 2: Requests accepts a hashed CA directory through ``ca_cert_dir``.…, An arbitrary directory is not a CA directory just because it exists. (+1 more)

### Community 308 - "linear_client.py"
Cohesion: 0.18
Nodes (16): _is_dict_of_object(), _is_list_of_dicts(), linear_create_attachment(), linear_get_attachments(), linear_graphql_request(), LinearAttachmentNode, Any, TypedDict (+8 more)

### Community 309 - "Refusal"
Cohesion: 0.15
Nodes (15): Exception, A command refused, carrying the ``ledger_spec.REASONS`` code that names why.…, Store the reason code. Args: reason: A ``ledger_spec.REASONS`` code of kind…, Refusal, _create_plan(), MonkeyPatch, Path, _raise_network_filesystem() (+7 more)

### Community 310 - "RepoResolver"
Cohesion: 0.12
Nodes (10): Path, Resolves Tier-1 referents against a repo checkout and a decomposed…, Initialize the resolver. Args: repo_root: The repository checkout root that…, Resolve ``referent`` per the decomposition-exit gate's tier-1 table. Args:…, Resolve a ``FILE`` referent: a repo-relative path that must exist. Args:…, Resolve a ``RULE`` referent: a rules file, optionally with a ``#section``…, Resolve a ``TASK_OUTPUT`` or ``GRAPH_POSITION`` referent against the work…, Resolve an ``ARTIFACT`` referent: a ``type#id`` pair against the artifact… (+2 more)

### Community 311 - "Findings: producers without consumers between grooming and the bookends"
Cohesion: 0.12
Nodes (15): A dependent waits for completion, not for acceptance, ADR-3460-2: Add the missing relations to the ledger, and finish the migration, rather than replace Task and Plan, Alternatives considered and rejected, Consequences, Context, Decision, The orchestrator loop, What is open (+7 more)

### Community 312 - "Task"
Cohesion: 0.14
Nodes (9): Task, Return tasks that are blocked by unsatisfied dependencies. A task is *blocked*…, Return True when *dep_id* exists and is in a successful status. Args: dep_id:…, Return True when all of *task*'s dependencies are in successful status. Args:…, Return dependency IDs that are not yet in a successful status. Args: task: The…, Return the T0 baseline bookend task, or None if absent. Returns: The task whose…, Return the TN verification bookend task, or None if absent. Returns: The task…, Build the dependency graph from a list of tasks. Constructs an index of all… (+1 more)

### Community 313 - "Human Touchpoint Model"
Cohesion: 0.12
Nodes (17): Available in Context, Bound Constraints, Constraint Types, Domain Knowledge Assessment, Dynamic Escalation Points, Escalation Decision Flowchart, Escalation Format, High Risk (consider escalation) (+9 more)

### Community 314 - "dispatch_task"
Cohesion: 0.15
Nodes (17): add_reports(), burn_attempts(), dispatch_leased_and_unready(), dispatch_task(), Connection, Dispatch one task and return the attempt it opened. Args: conn: An open ledger…, Append every report section for one attempt, so ``report-missing`` passes.…, Spend attempts on a task, leaving it blocked with the last attempt closed.… (+9 more)

### Community 315 - "github_branches.py"
Cohesion: 0.16
Nodes (12): _branch_info_from_branch(), get_integration_branch_status(), _get_repo(), Integration branch lifecycle management for the backlog MCP package. Provides…, Convert a PyGithub Branch object to a ``BranchInfo`` TypedDict. Args: branch:…, Return HEAD SHA and last-commit timestamp for a branch. Non-raising on branch-…, Authenticate and return a PyGithub Repository object. Args: repo:…, get_integration_branch_status returns BranchInfo or None. (+4 more)

### Community 316 - "BranchConflictError"
Cohesion: 0.16
Nodes (10): BranchConflictError, Raised when a merge fails due to conflicts. Attributes: head_branch: Source…, BranchConflictError stores branch names and conflict_files., Test head_branch attribute is stored on BranchConflictError. Tests:…, Test base_branch attribute is stored on BranchConflictError. Tests:…, Test conflict_files defaults to empty list when not provided. Tests:…, Test conflict_files list is stored when provided. Tests: BranchConflictError —…, Test string representation includes both branch names. Tests:… (+2 more)

### Community 317 - "ContentDuplicateMatch"
Cohesion: 0.23
Nodes (9): DuplicateItemError, Raised when a content-based duplicate is detected during item creation., Initialize with the content-duplicate matches found., ContentDuplicateMatch, BaseModel, A single candidate duplicate surfaced by ``find_content_duplicates``., DuplicateItemError formats its message from ContentDuplicateMatch entries. No…, AC3: message and .duplicates expose an actionable item_ref, never a bare file… (+1 more)

### Community 318 - "T-P6-PROTOCOL: Reshape BacklogBackend protocol (generic vs GitHub-specific)"
Cohesion: 0.28
Nodes (9): DEC-1: close/resolve satisfies CRUD delete intent, DEC-2: generic key-based query filter (Jira-style), T-DOC-B1: Document CLI/MCP capability gap, T-P3-FOLLOWUP: SAM primitive to link follow-up item to origin, T-P4-QUERY: Generic key-based query filter on list operations, T-P5-ACTIVE-TASK: sam_active_task CLI equivalent or documented MCP-only decision, T-P5-PARITY: Per-operation CLI/MCP parity tests, T-P6-BEADS: Replace Beads backend NotImplementedError stubs (+1 more)

### Community 319 - "_section_display_title"
Cohesion: 0.17
Nodes (10): Return the human-readable title for a section key. Delegates to the active…, _section_display_title(), _section_display_title returns correct display names., Known key 'fact_check' maps to 'Fact-Check'., Known key 'rt_ica' maps to 'RT-ICA'., groomed' key with a date string returns 'Groomed — {date}'., groomed' key with empty date string returns bare 'Groomed'., unknown__impact_radius' key reconstructs to 'Impact Radius'. (+2 more)

### Community 320 - "_provider_with_mock_runner"
Cohesion: 0.17
Nodes (10): _provider_with_mock_runner(), Regression tests for BeadsArtifactProvider.get_manifest_bd issue_number field.…, Confirm the sentinel 0 value is gone from both empty-manifest paths., A manifest persisted by pre-fix code with issue_number=0 is normalized on read.…, Normalizing issue_number must not drop or alter the existing artifacts list., Return a BeadsArtifactProvider whose runner returns *raw_json* from run_json., get_manifest_bd always returns manifest.issue_number == issue_id., When bd show returns no metadata, issue_number must be the beads ID string.… (+2 more)

### Community 321 - "assemble"
Cohesion: 0.16
Nodes (16): assemble(), build_terminal_stub_node(), _load_json(), load_layers(), _parse_args(), Namespace, Path, Atomically write a JSON payload to output_path. Writes to a uniquely named… (+8 more)

### Community 322 - "terminate_process_tree"
Cohesion: 0.17
Nodes (15): Popen, create_parser(), main(), process_group_is_alive(), Any, ArgumentParser, Run a command and return its exit status, or 124 after a timeout. Args:…, Run the parsed command within the selected timeout. Returns: The wrapped… (+7 more)

### Community 323 - "main"
Cohesion: 0.15
Nodes (16): _extract_prompt_from_transcript(), _extract_text_from_user_record(), _first_text_block(), _last_assistant_text(), main(), parse_hook_input(), Any, Path (+8 more)

### Community 324 - "Verdict Schema — Multi-Perspective Review"
Cohesion: 0.12
Nodes (14): §2.1 Structured Verdict Block, §2.2 Summary Line Format, §2.3 SKIP Detection Rule (Accessibility Perspective), §2.4 Gate Logic, §2.5.1 Prompt Injection Security Surface, §2.5.2 Quality Correctness for Tier 3 Files, §2.5 Prose File Classification (All Perspectives), §2.6 Punch-List Block (+6 more)

### Community 325 - "write_test_item"
Cohesion: 0.15
Nodes (9): write_test_item(), link_followup raises ItemNotFoundError for an unknown selector., test_link_followup_missing_item_raises(), Combined filters narrow results correctly through the full MCP path., Topic filter narrows candidates for semantic matching via topic slug., Scenarios consumed by the /work-backlog-item groom route., Scenario 17: backlog_update with section/content param sets groomed content., Lifecycle 3: item with issue #100, batch_fetch_statuses returns empty → stale… (+1 more)

### Community 326 - "plan_with"
Cohesion: 0.17
Nodes (16): finish_closed_and_unreported(), finish_stale_and_closed(), plan_with(), Create a plan holding some tasks. Args: conn: An open ledger connection. tasks:…, Dispatch and settle a task, leaving it in-progress with its attempt closed.…, Read a settled in-progress task with an attempt number that is not its current…, Update a settled in-progress task with an attempt number that is not its…, Renew a settled in-progress task with an attempt number that is not its current… (+8 more)

### Community 327 - "TestAcceptanceCriterionModel"
Cohesion: 0.12
Nodes (9): Verify AcceptanceCriterion Pydantic model construction and aliases. Tests:…, Verify AcceptanceCriterion with only required fields constructs. Tests: Minimal…, Verify AcceptanceCriterion with all fields populated. Tests: Full…, Verify AcceptanceCriterion accepts kebab-case alias keys. Tests: YAML kebab-…, Verify missing criterion_id raises ValidationError. Tests: Required field…, Verify missing check_command raises ValidationError. Tests: Required field…, Verify model_dump with by_alias=True produces kebab-case keys. Tests:…, Verify model_dump then model_validate roundtrip preserves data. Tests:… (+1 more)

### Community 328 - "TestBackendAvailabilityEnum"
Cohesion: 0.12
Nodes (9): All five named members exist on the enum. Tests: BackendAvailability member…, BackendAvailability has exactly 5 members with correct string values. Tests:…, BackendAvailability defines exactly 5 availability states. Tests:…, REACHABLE serialises to the string 'reachable'. Tests:…, NOT_CHECKED serialises to 'not_checked'. Tests: BackendAvailability.NOT_CHECKED…, NEEDS_AUTHENTICATION serialises to 'needs_authentication'. Tests:…, RATE_LIMITED serialises to 'rate_limited'. Tests:…, ERROR serialises to 'error'. Tests: BackendAvailability.ERROR value How: Direct… (+1 more)

### Community 329 - "test_placeholder_vocabulary_drift.py"
Cohesion: 0.14
Nodes (15): _iter_workflow_files(), Path, Guards the work-backlog-item placeholder vocabulary and adjacent doc-drift…, Every file that extracts Impact Radius data also names a `Resources` fallback.…, `work/start.md` never mandates `TodoWrite` bare — a fallback chain rides with…, Each `artifact list --artifact-type X` count check is followed by a content…, Every remaining `<mode/>` occurrence sits on a line that says `auto` or…, The six files the C2 rename cleared entirely never reacquire `<mode/>`. (+7 more)

### Community 330 - "test_high_level_storage_boundaries.py"
Cohesion: 0.45
Nodes (10): ModuleType, _attributes_by_function(), _imports(), parametrize, _source(), test_github_client_has_no_cache_filesystem_access(), test_non_local_context_backend_has_no_task_file_path(), test_operations_has_no_high_level_storage_bypass() (+2 more)

### Community 331 - "TestRepoDiscoveryError"
Cohesion: 0.12
Nodes (9): Error message includes actionable fix instructions. Tests: RepoDiscoveryError…, error.message attribute equals str(error). Tests: RepoDiscoveryError.message…, RepoDiscoveryError is catchable as a plain Exception. Tests: Exception…, RepoDiscoveryError can be raised and caught by its own type. Tests: raise /…, RepoDiscoveryError stores context and formats actionable messages. Tests the…, methods_tried attribute preserves the list of attempted methods. Tests:…, Error message includes 'Tried:' section header. Tests: RepoDiscoveryError…, Each detail string appears in the formatted error message. Tests:… (+1 more)

### Community 332 - "test_github_branches.py"
Cohesion: 0.15
Nodes (11): _branch_name(), Build the canonical branch name for a milestone. Args: milestone_number:…, mock_repo(), fixture, Tests for backlog_core/github_branches.py. Covers: create_integration_branch,…, _branch_name builds canonical milestone branch names., Test canonical branch name format milestone/{N}-{slug}. Tests: _branch_name…, Test that _branch_name uses the BRANCH_PREFIX module constant. Tests:… (+3 more)

### Community 333 - "Groom Milestone"
Cohesion: 0.22
Nodes (9): dh:complete-implementation Skill, Gate Push Skill, Branch → Backlog Lookup Algorithm, Dispatch Plan Schema, Groom Milestone, Group Items to Milestone, Implement Feature (SAM Workflow Execution), Stream-JSON Protocol Reference (+1 more)

### Community 334 - "struck_view_result"
Cohesion: 0.15
Nodes (15): _body_sections_block(), _entry_dict(), _load_fixture(), multi_entry_view_result(), fixture, Minimal SectionEntryDict for test fixtures. ``struck`` defaults to ``False``…, Two-entry section where entry 0 is struck and entry 1 is live (#3187 shape).…, SectionEntryMetadata from a list of entry content strings. (+7 more)

### Community 336 - "_canonicalize_patch_keys"
Cohesion: 0.16
Nodes (11): _canonicalize_patch_keys(), BaseModel, Remap every key in *raw_fields* to its model field's canonical (Python) name. A…, Validate raw JSON patch fields through the Pydantic Plan model. Reads the…, _validated_plan_patch(), Unit coverage for the merge-key normalizer used by the *_validated_*_patch*…, A kebab-case alias key is remapped to the field's snake_case name., A snake_case key (already canonical) passes through unchanged. (+3 more)

### Community 337 - "Work Phase 4: Plan"
Cohesion: 0.17
Nodes (13): dh:discovery skill, Step 4.1: Compose Feature Request, Work Phase 4: Plan, Step 4.4: Simplify (code review gate), Step 4.3: Update Backlog with Plan Reference, Step 3.1: Auto-Groom, Step 3.4: Feasibility Gate, Work Phase 3: Prepare (+5 more)

### Community 338 - "work-milestone Skill Command"
Cohesion: 0.22
Nodes (9): work-milestone Skill Command, Discovery Relay Between Waves, dispatch_item_status tool, Milestone Dispatch Plan, dispatch_read tool, dispatch_spawn tool, dispatch_wave_start tool, dispatch_wave_status tool (+1 more)

### Community 339 - "Harness facts: Hermes Agent (Nous Research)"
Cohesion: 0.13
Nodes (14): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment for a shell command, Can a plugin or skill collection ship hooks?, Event names (+6 more)

### Community 340 - "Path"
Cohesion: 0.05
Nodes (61): _agent_name_from_path(), _build_manifest_name_index(), find_agent(), _find_bare(), _find_plugin_qualified(), _get_manifest_name_for_dir(), get_plugins_root(), _looks_like_semver() (+53 more)

### Community 341 - "Harness facts: Kilo Code (Kilo CLI / Kilo Code VS Code extension, Kilo-Org/kilocode)"
Cohesion: 0.13
Nodes (14): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables set for a shell command, Are hooks shell commands?, Can a plugin or a skill collection ship them? (+6 more)

### Community 342 - "TestParentIssueNumberValidator"
Cohesion: 0.13
Nodes (8): parent_issue_number=None must be accepted., A positive integer issue number must be accepted., Zero is a non-negative integer and must be accepted., A valid beads ID string (bd-xxxx pattern) must be accepted., True/False must be rejected as parent_issue_number. The validator raises…, Negative integers must be rejected., Strings that are not valid beads IDs must be rejected. The pattern…, TestParentIssueNumberValidator

### Community 343 - "scripts/task_format.py"
Cohesion: 0.16
Nodes (14): _format_yaml_value(), has_yaml_frontmatter(), normalize_status(), parse_yaml_frontmatter(), Any, Shared YAML frontmatter utilities for task file parsing and manipulation.…, Detect if content uses YAML frontmatter format. Checks for opening ``---``…, Extract YAML frontmatter and markdown body from content. .. deprecated:: Use… (+6 more)

### Community 344 - "_make_item_with_section"
Cohesion: 0.16
Nodes (11): _make_item_with_section(), MockerFixture, _render_section_index includes ``Reproducibility`` when section key is…, Integration tests for sections_index via view_item(include_content=False). Uses…, sections_index from view_item must contain ``RT-ICA`` when section key is…, sections_index from view_item contains ``Reproducibility`` when section key…, Return a BacklogItem whose sections dict contains exactly one entry under…, Unit tests for _render_section_index with section names as stored by groom.… (+3 more)

### Community 345 - "TestGitCommonRootHangProtection"
Cohesion: 0.17
Nodes (8): Tests that a hung GitPython Repo() construction times out with an actionable…, Clear module-level root cache before each test., _git_common_root bounds a hung Repo() construction and raises an actionable…, _git_root_if_directory treats a hang as a failed candidate, not a fatal error.…, infer_project_root turns a final-fallback git hang into the documented…, A timed-out worker must be exempt from being joined at interpreter shutdown.…, A genuine GitPython error raised inside the worker reaches the caller's thread…, TestGitCommonRootHangProtection

### Community 346 - "_backlog_ops"
Cohesion: 0.17
Nodes (10): _backlog_ops(), Any, Return backlog_core.operations as Any so ty does not flag unimplemented symbols., Verify _filter_closed_items filters terminal-status items correctly. NOTE:…, When include_closed=True, all items are returned unfiltered., When include_closed=False, items with done/resolved/closed status are excluded., Items using _status key instead of **Status** are also filtered., Items with empty or missing status are not filtered out. (+2 more)

### Community 347 - "TestResolveVerifiedGate"
Cohesion: 0.13
Nodes (8): Integration tests for the status:verified gate on resolve (Gap 4) and full…, Resolve with plan but no status:verified label is blocked at the view gate.…, Resolve proceeds when status:verified label is present on the issue. After…, Items without a Plan field skip the verification gate entirely. Non-SAM items…, force=True bypasses the verification gate even with a plan and no verified…, force=True bypasses both the verified gate and the open-PR gate., Full pipeline flow: create item with issue, attach plan, apply verified label,…, TestResolveVerifiedGate

### Community 348 - "test_server_sam.py"
Cohesion: 0.19
Nodes (14): _call(), Tests for the SAM MCP tools added to backlog_core/server.py in Phase 2. Four…, backlog_get_sam_tasks returns {"tasks": [...], "count": N} shape on success.…, backlog_update_sam_task_status returns {"updated": False} when status…, backlog_get_ready_sam_tasks returns shape with "feature", "ready_tasks",…, Call an MCP tool through the in-memory FastMCP transport and parse result.…, backlog_create_sam_task returns a dict (not raises) on success. Tests:…, backlog_create_sam_task returns {"error": "..."} when BacklogError is raised.… (+6 more)

### Community 349 - "_build_artifact_content_comment"
Cohesion: 0.14
Nodes (14): _build_artifact_content_comment(), Build a structured GitHub comment body for storing artifact content. The…, Verify the opening artifact-content HTML comment tag is present. Tests:…, Verify the closing artifact-content HTML comment tag is present. Tests:…, Verify the comment wraps content in an HTML details/summary block. Tests:…, Verify the artifact content is embedded verbatim in the comment. Tests:…, Verify oversized content is truncated to stay within GitHub's limit. Tests:…, Verify content within the size limit is stored unmodified. Tests:… (+6 more)

### Community 350 - "Path"
Cohesion: 0.19
Nodes (8): BaseModel, OSError, Path, Result of enumerating every durable work-item snapshot beneath the cache root.…, Fold a directory-level traversal failure into ``skipped`` as ``os.walk``'s…, Return every durable work-item snapshot beneath the cache root. An orphaned…, Initialize durable cache state beneath the provider-owned root., WorkItemSnapshotBatch

### Community 351 - "SAM Pipeline Stages (S1-S7)"
Cohesion: 0.32
Nodes (8): SAM Pipeline Stages (S1-S7), S1 Discovery Agent, S2 Planning Agent (RT-ICA), S3 Context Integration Agent, S4 Task Decomposition Agent, S5 Execution Agent, S6 Forensic Review Agent, S7 Final Verification Agent

### Community 352 - "Workflow: Work Backlog Item"
Cohesion: 0.40
Nodes (5): Work Stage Scope Boundary, STOP Notification Protocol, Workflow: Work Backlog Item, Kage-Bunshin Session (independent claude -p orchestrator), Wave Dispatch Loop

### Community 353 - "_parse_comment_node"
Cohesion: 0.20
Nodes (8): _parse_comment_node(), Parse a raw GraphQL comment dict into a typed IssueCommentNode. Args: node: Raw…, A guessed number addresses some other comment, so nothing is guessed., A decimal string is a valid BigInt encoding; a non-digit string means the…, GitHub never emits a sign for this field; a negative-looking string is not a…, bool subclasses int, so True would otherwise be carried as comment 1., The field is declared BigInt (whole numbers only); a float means the response…, TestAnAbsentOrUnusableValueStaysAbsent

### Community 354 - "delete_integration_branch"
Cohesion: 0.19
Nodes (9): delete_integration_branch(), Delete a branch by name. Idempotent: returns True even if already deleted.…, delete_integration_branch is idempotent and returns bool., Test successful delete returns True. Tests: delete_integration_branch — happy…, Test 404 on get_git_ref returns True (idempotent delete). Tests:…, Test unexpected GithubException returns False without re-raising. Tests:…, Test output.warn called when unexpected error occurs. Tests:…, Test get_git_ref called with 'heads/{branch_name}' (no 'refs/' prefix). Tests:… (+1 more)

### Community 355 - "TestRetryableErrorBoundedBackoff"
Cohesion: 0.13
Nodes (9): On a successful sync, completed_at must be set and retry_count reset to 0.…, completed_at is set to a non-None UTC datetime on success., retry_count is reset to 0 after a successful sync. When a transient failure is…, Retryable errors use bounded exponential backoff and stop after MAX_RETRIES., HTTP 5xx errors are retried at most MAX_RETRIES times, then ERROR. The…, Backoff delays between retries must be positive (not zero). Zero-delay retries…, If a retryable error is followed by success, status returns to IDLE., TestRetryableErrorBoundedBackoff (+1 more)

### Community 356 - "DH work ledger — plan"
Cohesion: 0.14
Nodes (13): DH work ledger — plan, Layers, Slice 0 — measure, Slice 1 — decide, Slice 2 — build, Slice 3 — MCP parity, Slice 4 — the loop in the skills, Slice 5 — milestones on the same path (+5 more)

### Community 357 - "Artifact Conventions"
Cohesion: 0.14
Nodes (14): Artifact Conventions, Artifact Lifecycle, Artifact System, Backlog System, Cross-Reference Token Pattern, Cross-Referencing Between Artifacts, Feature-Level Artifacts, Logical Identifier Conventions (+6 more)

### Community 358 - "TestArtifactEntryModelValidation"
Cohesion: 0.14
Nodes (8): Unit tests for ArtifactEntry Pydantic model and AliasChoices field interop.…, ArtifactEntry accepts snake_case field names at construction. Tests:…, ArtifactEntry accepts kebab-case field name via model_validate. Tests:…, ArtifactEntry accepts short 'type' alias via model_validate. Tests:…, ArtifactEntry defaults status to CURRENT when not provided. Tests:…, All ArtifactType enum members can be used in ArtifactEntry. Tests: ArtifactType…, All ArtifactStatus enum members can be used in ArtifactEntry. Tests:…, TestArtifactEntryModelValidation

### Community 359 - "TestParseManifestSection"
Cohesion: 0.14
Nodes (8): Unit tests for parse_manifest_section. Tests: Parsing from valid issue bodies,…, parse_manifest_section extracts a valid entry from a real issue body. Tests:…, parse_manifest_section returns empty manifest when no section found. Tests:…, parse_manifest_section handles completely empty issue body. Tests: Edge case —…, parse_manifest_section skips the table header and separator rows. Tests:…, parse_manifest_section silently skips rows with unknown artifact types. Tests:…, parse_manifest_section parses all valid rows in a multi-entry section. Tests:…, TestParseManifestSection

### Community 360 - "TestLazyRunnerConstruction"
Cohesion: 0.14
Nodes (11): mock_runner(), provider(), fixture, MockerFixture, Return a mock BdRunner with spec; no subprocess is ever invoked., The runner is lazily constructed; the constructor is filesystem-free., When runner is injected, _runner property returns it directly., When no runner is provided, BdRunner() is created lazily on first _runner… (+3 more)

### Community 361 - "register"
Cohesion: 0.19
Nodes (14): complete_and_accept(), Register one scenario against the transition entry and pair of checks it…, Take a task through a reported attempt to complete and accepted. Args: conn: An…, Reclaim an accepted task whose dependent has already spent an attempt., Reclaim an accepted task that has already spent every attempt it was allowed., Reclaim a leased task whose dependent has already spent an attempt., Move an accepted task to a status no ``Status`` names., Move an accepted task without a reason. (+6 more)

### Community 362 - "TestBookendVerificationModel"
Cohesion: 0.14
Nodes (8): Verify BookendVerification with status=regressed. Tests: T0 pass + TN fail =…, Verify BookendVerification with status=pre-existing-fail. Tests: T0 fail + TN…, Verify BookendVerification with status=newly-passing. Tests: T0 fail + TN pass…, Verify BookendVerification accepts kebab-case alias keys. Tests: YAML alias…, Verify model_dump then model_validate roundtrip preserves data. Tests:…, Verify BookendVerification model construction for all 4 status values. Tests:…, Verify BookendVerification with status=passed. Tests: T0 pass + TN pass =…, TestBookendVerificationModel

### Community 363 - "TestCriterionStatusEnum"
Cohesion: 0.14
Nodes (8): Verify CriterionStatus StrEnum members and values. Tests: Bookend criterion…, Verify PASSED maps to 'passed'., Verify REGRESSED maps to 'regressed'., Verify PRE_EXISTING_FAIL maps to 'pre-existing-fail'., Verify NEWLY_PASSING maps to 'newly-passing'., Verify the total number of status values. Tests: CriterionStatus completeness.…, Verify CriterionStatus members serialize to their string values. Tests: StrEnum…, TestCriterionStatusEnum

### Community 364 - "TestModels"
Cohesion: 0.14
Nodes (8): Sanity checks on the Pydantic models., SourceSpan can be constructed with valid values., SourceSpan raises ValidationError for negative start_line., SourceSpan raises ValidationError when end_line < start_line., CodeBlock can be constructed and serialised., MarkdownDocument can be constructed with defaults., NavigatorOptions default_budget equals _DEFAULT_BUDGET (env-derived)., TestModels

### Community 365 - "setup-github Command"
Cohesion: 0.29
Nodes (7): backlog create-milestone, backlog create-project, backlog list-labels, backlog list-milestones, backlog list-projects, backlog sync, setup-github Command

### Community 366 - ".mcp.json"
Cohesion: 0.33
Nodes (6): npx, uv, backlog, sam, sequential_thinking, @modelcontextprotocol/server-sequential-thinking

### Community 367 - "Fact Check Skill"
Cohesion: 0.15
Nodes (13): Fact Checker, Fact Check Skill, Chain of Verification (CoVe) Requirement, Fact-Check Evidence Rules, Verdict Format (VERIFIED/REFUTED/INCONCLUSIVE), Find Cause Skill, Evidence Chain (Symptom to Root Cause), Evidence-Chain Protocol (+5 more)

### Community 368 - "_write_item_file"
Cohesion: 0.37
Nodes (6): _backlog_dir(), MockerFixture, Path, TestHandleBatchGroomedAcWiring, TestHandleUpdateGroomedAcWiring, _write_item_file()

### Community 369 - "Step 4.5: Post-Planning Output"
Cohesion: 0.38
Nodes (7): dh:complete-implementation skill, dh:implement-feature skill, Step 4.5: Post-Planning Output, Post-Planning Auto Mode Continuation, backlog_resolve as terminal step (issue closure rule), Post-Planning Interactive Mode Summary, Auto Mode Checklist

### Community 370 - "TestBacklogItemReferenceHealing"
Cohesion: 0.14
Nodes (8): BacklogItem.reference self-heals at construction time (backlog item #2909).…, An item constructed with an issue but no reference adopts the issue., With neither reference nor issue set, reference is a SHA-256 of the title., Even a fully-default BacklogItem() ends up with a non-empty reference., Two independent constructions of the same title resolve to the same key. This…, An explicitly supplied reference is never overwritten by healing., A healed reference is stable under a model_dump/model_validate round-trip. Read…, TestBacklogItemReferenceHealing

### Community 371 - "TestResolveItem"
Cohesion: 0.14
Nodes (8): resolve_item requires a non-empty summary and validates the selector., Verify resolve_item raises ValidationError when summary is empty string. Tests:…, Verify resolve_item raises ValidationError when summary is whitespace-only.…, Verify resolve_item raises ItemNotFoundError when selector matches nothing.…, Verify resolve_item returns resolved=True for a valid item with a reason.…, Verify resolve_item raises BacklogError when open PRs reference the issue.…, Verify resolve_item with force=True succeeds despite open PRs. Tests:…, TestResolveItem

### Community 372 - "TestComputeSlug"
Cohesion: 0.14
Nodes (8): Verify underscores in path components are preserved unchanged. Tests:…, Verify a single-segment path produces a minimal slug. Tests: compute_slug with…, Verify every slug starts with a dash due to leading slash replacement. Tests:…, Verify no forward slashes remain in the slug output. Tests: compute_slug…, Tests for compute_slug(): slug format for various path inputs. Strategy: Pass…, Verify simple nested path produces the correct slug. Tests: compute_slug with a…, Verify every slash in the path is replaced with a dash. Tests: compute_slug…, TestComputeSlug

### Community 373 - "TestReconcileOpenItem"
Cohesion: 0.14
Nodes (8): Verify _reconcile_open_item handles divergence scenarios for open GitHub issues., Returns no_change when local and GitHub statuses are identical., Returns flagged_divergence with stateless void warning when GitHub has no…, Returns auto_corrected when divergence is DAG-valid (reachable via state…, When auto-correcting, _update_item_metadata is called to persist the change., When file_path_str is None, auto-correction returns result but does not persist., Returns flagged_divergence when no valid DAG path exists between states., TestReconcileOpenItem

### Community 374 - "infer_type"
Cohesion: 0.26
Nodes (4): infer_type(), Infer issue type label from description and title keywords. Returns: Type label…, Tests for infer_type(description, title) -> str. Verifies the keyword heuristic…, TestInferType

### Community 375 - "_parse_frontmatter"
Cohesion: 0.26
Nodes (4): _parse_frontmatter(), Parse frontmatter and metadata from item text. ``loads_frontmatter`` guarantees…, Tests for _parse_frontmatter(text) -> (fm_dict, meta_dict, body)., TestParseFrontmatter

### Community 376 - "Backlog Core Domain"
Cohesion: 0.40
Nodes (5): Backlog Core Domain, GraphQL Sync Issues Guide, MCP Progressive-Disclosure Ordinal Grammar, Progressive Markdown Engine, SAM Schema Domain

### Community 377 - "SAM 7-Stage Pipeline"
Cohesion: 0.33
Nodes (6): @dh:code-reviewer, Development Harness Plugin, @dh:feature-researcher, Role Resolution Protocol, SAM 7-Stage Pipeline, @dh:swarm-task-planner

### Community 378 - "NormalizedEntry"
Cohesion: 0.17
Nodes (6): NormalizedEntry, NormalizedSection, Protocol, Source-neutral generated entry consumed by ordinal navigation., Initialise the mapper. Args: sections: Ordered list from…, Source-neutral generated section consumed by ordinal navigation.

### Community 379 - ".read_plan"
Cohesion: 0.17
Nodes (7): TaskData, Return tasks ready for dispatch, routing through Gist-first :meth:`read_plan`.…, Return plan status summary, routing through Gist-first :meth:`read_plan`. Calls…, Return ``True`` when local YAML is known to be ahead of the Gist copy. Checks…, Read a plan by identifier using Gist-first dual-read. Read flow: 1. Resolve…, Write Gist YAML content to the local filesystem cache (best-effort). Parses the…, Read a single task, routing through Gist-first :meth:`read_plan`. Calls…

### Community 380 - "Per-Stage Detail"
Cohesion: 0.15
Nodes (12): Per-Stage Detail, S1 — `discovery`, S2 — `planning`, S3 — `context-integration`, S4 — `task-decomposition`, S5 — `execution`, S6 — `forensic-review`, S7 — `final-verification` (+4 more)

### Community 381 - "SAM (Stateless Agent Methodology)"
Cohesion: 0.20
Nodes (10): dh:add-new-feature skill, dh:rt-ica skill, Step 4.2: Invoke SAM Planning, RT-ICA Freshness Check Flowchart, RT-ICA Staleness Policy (7-day threshold), Canonical SAM Spec (bitflight-devops/stateless-agent-methodology), SAM Core Insight: Claude as stateless computation engine, Human Escalation Criteria (per-agent) (+2 more)

### Community 382 - "test_server_pep723_header_omits_typer"
Cohesion: 0.21
Nodes (12): _extract_pep723_block(), parametrize, Path, unit, Regression test: MCP servers disable FastMCP's Rich logging/tracebacks. Why:…, Extract the TOML content from a PEP 723 '# /// script' block. Mirrors…, Importing dh_mcp_preinit sets both FASTMCP_ENABLE_RICH_* vars to false., setdefault semantics: an operator-set value survives the import. (+4 more)

### Community 383 - "test_the_first_failing_check_is_the_one_the_spec_puts_first"
Cohesion: 0.15
Nodes (12): Return the bare no-op code the command printed instead of a result, when it did., OrderCase, outcome_of(), Any, BaseModel, parametrize, Return a pair of checks in the order the specification evaluates them. Args:…, One transition entry, the two checks a scenario makes fail, and the scenario. (+4 more)

### Community 384 - "MonkeyPatch"
Cohesion: 0.21
Nodes (8): MonkeyPatch, Verify _reconcile_batch handles GitHub availability and batch processing., When _try_get_github returns None, returns items unchanged with warning., When GitHub API raises GithubException, returns items unchanged with warning., When an item is auto-corrected, its in-memory status is updated., Divergence warnings from _reconcile_item are collected in the warnings list., Pull requests are excluded from the GitHub issue map., TestReconcileBatch

### Community 385 - "test_server_descriptions.py"
Cohesion: 0.19
Nodes (12): _extract_selector_descriptions(), _param_description(), parametrize, AST-based regression test: every beads-capable selector Field description…, Return the ``Field(description=...)`` string of *param* on the MCP tool *tool*., Each beads-capable tool's selector Field description must contain 'beads…, Each beads-capable tool's selector description must not be a bare generic…, The ``plan`` value is stored verbatim as a plan address, so its description… (+4 more)

### Community 386 - "test_status_token_vocabulary_drift.py"
Cohesion: 0.18
Nodes (12): _collect_status_tokens(), Guards the sub-agent STATUS reporting vocabulary against drift. Two files in…, No file under skills/ or agents/ writes a retired STATUS spelling. This is the…, The contract file this module cites still pins exactly the tokens it says it…, The agent-orchestration contract keeps PARTIAL, which this module's docstring…, Every STATUS token written in skills/ or agents/ is one this plugin's contract…, Map each STATUS token found to the paths that write it. Returns: Token (upper-…, test_contract_pins_the_tokens_this_module_guards() (+4 more)

### Community 387 - "create_integration_branch"
Cohesion: 0.20
Nodes (8): create_integration_branch(), Create a branch named ``milestone/{N}-{slug}`` from the HEAD of…, Test 404 on base branch lookup raises BacklogError. Tests:…, create_integration_branch validates slug and milestone_number before API calls., Test invalid slug raises BacklogError without calling GitHub API. Tests:…, Test milestone_number=0 raises BacklogError without calling GitHub API. Tests:…, Test negative milestone_number raises BacklogError. Tests:…, TestCreateIntegrationBranchValidation

### Community 388 - "_validate_milestone_number"
Cohesion: 0.21
Nodes (8): Validate milestone_number is a positive integer. Args: milestone_number:…, _validate_milestone_number(), _validate_milestone_number enforces milestone_number > 0., Test positive milestone number passes without raising. Tests:…, Test milestone_number=0 raises BacklogError. Tests: _validate_milestone_number…, Test negative milestone_number raises BacklogError. Tests:…, Test error message includes the invalid milestone_number value. Tests:…, TestValidateMilestoneNumber

### Community 389 - "_make_connection_class"
Cohesion: 0.18
Nodes (9): _make_connection_class(), Build the HTTPS connection class PyGithub should use. Args: ca_bundle: Path…, The substituted class must remain a drop-in for the one PyGithub ships., PyGithub builds connections from it, so it has to satisfy that contract., force depends on a rebuild, so the factory must not cache one class., New Finding 1 (P1, PR #3551 second review round): the connection's own…, TestConnectionClassFactory, TestConnectionVerifyMatchesSelectedBundle (+1 more)

### Community 390 - ".__init__"
Cohesion: 0.17
Nodes (6): Initialise with discovery context. Args: methods_tried: Method names tried in…, Initialize with the selector that failed to match., Initialize with the unmatched ID and the IDs that were available., Initialize with the colliding reference and the shared title. Args: reference:…, Initialize with the missing capability, backend name, and attempted operation.…, Initialize with merge conflict details. Args: head_branch: Source branch being…

### Community 391 - "_assemble_view_compact"
Cohesion: 0.20
Nodes (10): _assemble_view_compact(), _build_sections_compact(), _build_sections_index_from_body(), r"""Build a ``## Sections`` index block from a raw body string. Produces the…, Extract section names and entry counts without parsing entry content. Returns a…, Populate *result* for summary (non-content) view mode. Sets…, Finding 1: _build_sections_compact must recognise both ## and ### headers.…, _build_sections_compact returns three sections for a mixed ## / ### body.… (+2 more)

### Community 392 - "development-harness/conftest.py"
Cohesion: 0.19
Nodes (16): _Address, AF_INET, AF_INET6, _guarded_connect(), _guarded_connect_ex(), _guarded_getaddrinfo(), _is_local(), pytest_configure() (+8 more)

### Community 393 - "build_concept_query"
Cohesion: 0.23
Nodes (7): build_concept_query(), Build an OR search query from the significant words in title and description.…, Tests for backlog_core/search.py content-based duplicate detection. Replaces…, Tests for build_concept_query(title, description, max_concepts)., Tests for the ContentDuplicateMatch.item_ref invariant (spec §6.2)., TestBuildConceptQuery, TestContentDuplicateMatchInvariant

### Community 394 - "_token_count"
Cohesion: 0.17
Nodes (12): _compute_match_tokens(), _paginate_match_items(), Resolve the effective page limit for a ``backlog_list`` response. When ``limit…, Count cl100k_base tokens in an already-serialized JSON string. Args:…, Token-count the delivered ``backlog_view`` payload without double-counting. The…, Return a copy of *section* with each entry's ``content`` blanked. Used by…, Count tokens for the match_context output of a single enriched item. Counts…, Split enriched match-context items into token-sized pages. Partitions… (+4 more)

### Community 395 - ".test_a_closed_fetched_issue_without_a_status_label_is_not_fabricated_as_needs_grooming"
Cohesion: 0.17
Nodes (8): The bare documented ``--status needs-grooming`` filter must match every issue…, Reproduction: a live GraphQL answer for issue #42 carries the literal…, Unchanged behavior: an issue the live query answered for, but with no status…, A cached closed item included in the listing keeps the fetched blank status., The query ran and named no label for this issue, so blank is the honest render., Narrow the heterogeneous ``list_items`` result to its per-item status strings., _statuses(), TestStatusFilterWithALiveAnswer

### Community 396 - "TestSyncStatePercent"
Cohesion: 0.17
Nodes (7): SyncState.percent computes correctly across edge cases., percent is None while items_total is unknown (initial fetch phase)., percent is 0 when items_done=0 and items_total is known., percent is 50 when half the items are done., percent never exceeds 100 even if items_done > items_total., percent is None when items_total is 0 (avoids division-by-zero)., TestSyncStatePercent

### Community 397 - "_filter_sections_isolated"
Cohesion: 0.21
Nodes (8): _filter_sections_isolated(), Run ``_filter_view_sections`` in isolation over a hand-built result. Builds a…, Codex P2 (#2495): the ``sections=[...]`` dict filter must match case-…, ``sections=['rt-ica']`` against an ``RT-ICA`` key / ``## RT-ICA`` header. RED…, ``sections=['RT-ICA']`` (upper) against a lowercase ``rt-ica`` key / ``## rt-…, Compact ``sections_metadata`` arm: a case-differing valid name stays a non-…, A name absent from the dict, body headers, AND metadata still sets…, TestSectionsDictFilterIsCaseInsensitive

### Community 398 - "_build_graph_dict"
Cohesion: 0.21
Nodes (7): _build_graph_dict(), _count_types(), Count occurrences of each value of ``key`` across a list of dicts. Returns:…, Construct the top-level graph output dict from sorted nodes and edges.…, A gap edge and an orphan edge are different concepts -- an edge must never be…, TestGapCountComputedNotHardcoded, TestOrphanCountComputedNotHardcoded

### Community 399 - "OpenAI Codex CLI harness facts"
Cohesion: 0.17
Nodes (11): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables for a shell command, Can a plugin ship hooks?, Lifecycle events (+3 more)

### Community 400 - "OpenCode harness facts"
Cohesion: 0.17
Nodes (11): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills (SKILL.md), 5. MCP from project config, 6. Environment variables for a shell command, JS function or shell command, OpenCode harness facts (+3 more)

### Community 401 - "._handle_create"
Cohesion: 0.20
Nodes (6): Any, JsonValue, Parse bd create args and add to _issues store., Wrap ``show`` output in ``[{...}]``; delegate all other commands., Handle ``list --parent`` (with optional ``--all``) locally; delegate all other…, Simulate bd commands that produce JSON output.

### Community 402 - "File Classification for Review Skill"
Cohesion: 0.40
Nodes (5): File Classification for Review Skill, Tier 1 — Documentation Only, Tier 2 — Process Documentation, Tier 3 — LLM Prompt Engineering Artifact, multi-perspective-review verdict-schema.md

### Community 403 - "should_skip_hook"
Cohesion: 0.21
Nodes (8): Return True if the hook for this event should be skipped. Args: event_name:…, should_skip_hook(), Unit tests for should_skip_hook(). Tests: SubagentStop runs by default, is…, SubagentStop with an empty disabled set -> False (run). Tests:…, SubagentStop disabled by ID -> True. Tests: should_skip_hook() disabled set for…, A disabled set naming an unrelated hook ID does not skip SubagentStop. Tests:…, Unknown event name -> False (let dispatch handle it). Tests: should_skip_hook()…, TestShouldSkipHook

### Community 404 - "Arranged"
Cohesion: 0.17
Nodes (12): accept_incomplete_and_unreported(), Arranged, finish_stale_and_unreported(), One ledger in a state where two checks of a transition fail, and the run that…, Finish an unreported open attempt complete, with an attempt number that is not…, Accept a task whose runner has neither returned nor written a report., Move a leased task to a status no ``Status`` names., Move a task to a status no ``Status`` names, without a reason. (+4 more)

### Community 405 - "_run_probe"
Cohesion: 0.24
Nodes (11): CompletedProcess, Path, Contract tests for the autouse ``_isolated_backend`` fixture in…, A non-e2e class still has its backend replaced by the in-memory double., Write a temp pytest file under the tests directory and yield its path. The…, Run the probe in its own pytest session with this repo's addopts cleared., An e2e class keeps its own backend for every test in the class. Guards the…, _run_probe() (+3 more)

### Community 406 - "TestConflictGroupConstruction"
Cohesion: 0.17
Nodes (7): ConflictGroup construction including alias and constraint checks., ConflictGroup constructs correctly with snake_case field names. Tests:…, ConflictGroup.model_validate accepts 'group-id' kebab-case alias. Tests:…, ConflictGroup rejects an items list with fewer than two elements. Tests:…, ConflictGroup rejects group_id values below ge=1. Tests: ge=1 constraint on…, ConflictGroup rejects an empty reason string. Tests: min_length=1 constraint on…, TestConflictGroupConstruction

### Community 407 - "create_backend"
Cohesion: 0.02
Nodes (103): create_backend(), Instantiate and return a backend by name. When *name* is ``None``, resolution…, WorkItemBackend, BranchBackend, MergeResult, Protocol, Optional capability: report whether a cache has ever completed a sync.…, Optional capability: report whether the last snapshot load skipped any file.… (+95 more)

### Community 408 - "TN Verification Gate"
Cohesion: 0.67
Nodes (4): Complete Implementation, Swarm Task Planner, T0 Baseline Capture, TN Verification Gate

### Community 409 - "Layer 0: SDLC-Agnostic"
Cohesion: 0.67
Nodes (3): ARL Meta-Layer, Layer 0: SDLC-Agnostic, Layer 1: Language-Specific

### Community 411 - "TestDispatchPlanConstruction"
Cohesion: 0.17
Nodes (7): DispatchPlan top-level model construction and defaults., DispatchPlan constructs correctly given a minimal valid set of fields. Tests:…, DispatchPlan constructs with conflict_groups and quality_gates populated.…, DispatchPlan raises ValidationError when milestone is absent. Tests: Required…, DispatchPlan raises ValidationError when waves is absent. Tests: Required field…, DispatchPlan.model_validate accepts 'conflict-groups' kebab-case alias. Tests:…, TestDispatchPlanConstruction

### Community 412 - "TestMCPIncludeClosedPropagation"
Cohesion: 0.17
Nodes (7): Verify the MCP server forwards include_closed to operations.list_items., backlog_list MCP tool defaults include_closed to False., backlog_list MCP tool forwards include_closed=True to operations., backlog_list with include_closed=True returns items with terminal status., backlog_list without include_closed returns only non-terminal items., backlog_list forwards include_closed alongside other filter params., TestMCPIncludeClosedPropagation

### Community 413 - "test_prepare_clean_worktree.py"
Cohesion: 0.45
Nodes (11): _init_git_repo(), _parse_stash_ref(), CompletedProcess, Path, _repo_slug(), _run(), _script_path(), test_prepare_clean_worktree_decline_exits_non_zero() (+3 more)

### Community 414 - "TestReconcileItem"
Cohesion: 0.20
Nodes (7): Verify _reconcile_item dispatches correctly based on item and GitHub state., Create a mock GitHub issue with the given state and labels., Items without an _issue field return no_change with issue_number=0., Items whose issue number is not in the GitHub map return no_change with warning., When GitHub issue is open, delegates to _reconcile_open_item., When GitHub issue is closed, delegates to _reconcile_closed_item., TestReconcileItem

### Community 415 - "SOP"
Cohesion: 0.18
Nodes (10): Boundaries, Input, Review Synthesizer, SOP, Step 1 — Collect the four verdicts, Step 2 — Record coverage, Step 3 — Merge findings that name the same defect, Step 4 — Order the entries (+2 more)

### Community 416 - "TestFactoryIntegration"
Cohesion: 0.18
Nodes (8): BackendName, StrEnum, Canonical identifiers for pluggable artifact storage backends., MonkeyPatch, create_artifact_provider('beads') returns a BeadsArtifactProvider instance., BackendName.beads enum value is accepted by create_artifact_provider., BACKLOG_BACKEND=beads env var selects BeadsArtifactProvider via factory., TestFactoryIntegration

### Community 417 - ".get_wave_items"
Cohesion: 0.18
Nodes (7): Row, Retrieve a wave with all nested items. Args: milestone: GitHub milestone…, Retrieve all waves for a milestone in insertion order. Args: milestone: GitHub…, Retrieve a single item by its primary key. Args: milestone: GitHub milestone…, Retrieve all items for a wave. Args: milestone: GitHub milestone number.…, Convert a sqlite3.Row from the items table to a DispatchItemRecord. Args: row:…, _row_to_item()

### Community 418 - "_resolve_section_indices"
Cohesion: 0.22
Nodes (8): Resolve a *section* filter expression to ordered candidate indices. Shared by…, _resolve_section_indices(), parametrize, ``_resolve_section_indices(candidates, "")`` returns [] not all indices.…, ``_resolve_section_indices(candidates, whitespace)`` returns []. Parameterised…, ``_resolve_section_indices([], "")`` returns [] regardless of the fix. Non-…, ``_resolve_section_indices`` with a blank or whitespace-only filter. A blank…, TestResolveBlankSectionReturnsNoIndices

### Community 419 - "bd Invalid JSON Stdout Fixture"
Cohesion: 0.50
Nodes (4): bd Dependency Add Success Fixture, bd Invalid JSON Stdout Fixture, bd Invocation Error Stderr Fixture (issue not found), bd Not Installed Stderr Fixture

### Community 420 - "build_body_extra_only"
Cohesion: 0.29
Nodes (4): build_body_extra_only(), Build body with only extra fields (no duplication) and ## Groomed if present.…, Tests for build_body_extra_only(...) -> str. Verifies conditional inclusion of…, TestBuildBodyExtraOnly

### Community 421 - ".test_github_enriched_view_item_returns_real_entry_id_not_zero"
Cohesion: 0.20
Nodes (9): _collect_entry_ids(), MockerFixture, M1 regression: GitHub-enriched body overwrites provider entry IDs with zero…, view_item with GitHub enrichment must return the real provider entry ID.…, M2 regression: pagination overwrites structured-item entry IDs with zero…, view_item with pagination on a provider item must return the real entry ID.…, Collect (section_name, entry_id) pairs from result.sections. Args: result: The…, TestMechanism1GitHubEnrichedZeroId (+1 more)

### Community 422 - "_make_local_item"
Cohesion: 0.25
Nodes (8): _make_local_item(), MockerFixture, Integration tests: view_item response carries section_filter_miss. Tests 3 and…, view_item full response has section_filter_miss=True when section absent.…, view_item full response has section_filter_miss=False when section present.…, view_item compact response has section_filter_miss=True when section absent.…, Return a minimal BacklogItem with one section., TestViewItemSectionFilterMissExposedInResponse

### Community 423 - "close_sqlite_connections"
Cohesion: 0.20
Nodes (11): close_sqlite_connections(), _disable_startup_sync(), Connection, fixture, FixtureRequest, MonkeyPatch, _P, Disable the background startup sync loop for all non-e2e tests. Patches… (+3 more)

### Community 424 - "ReferentResolver"
Cohesion: 0.20
Nodes (8): Protocol, Initialize the gate. Args: resolver: Resolves Tier-1 referents. reader: Reads…, Resolves a Tier-1 :class:`Referent` to what it names, or ``None`` when it does…, Return what ``referent`` resolves to, or ``None`` when it does not resolve.…, Reads the text a :class:`~dh_core.workflow_multigraph.descriptors.SourceSpan`…, Return the text at ``ref``, or ``None`` when ``ref`` does not exist. Args: ref:…, ReferentResolver, SourceReader

### Community 425 - "self_check"
Cohesion: 0.25
Nodes (6): Annotate orphan edges; warn about overlay types with zero instances. An orphan…, self_check(), Covers plugins/development-harness/docs/graph-schema.md "Orphan edges": an edge…, An edge whose endpoints both exist must come back byte-identical -- no 'status'…, Running self_check twice on its own output must be a no-op -- the same edges,…, TestOrphanEdgesPreservedNotDeleted

### Community 426 - "Harness facts: pi (pi coding agent)"
Cohesion: 0.18
Nodes (10): 1. Shell command, read file, write file, 2. Hooks (Extension API), 3. Sub-agents, 4. Skills, 5. MCP, 6. Environment variables set for a shell command, Fields on the after-tool events (verbatim from `src/core/extensions/types.ts`), Harness facts: pi (pi coding agent) (+2 more)

### Community 427 - "Work: Locate (Phase 1)"
Cohesion: 0.50
Nodes (4): Find Item Fallback Chain, Interactive Browser, Issue-First Path, Work: Locate (Phase 1)

### Community 428 - "Task T1 (Pure YAML)"
Cohesion: 0.67
Nodes (4): Directory-based YAML Plan, Task T1 (Pure YAML), Task T2 (Pure YAML), Task T3 (Pure YAML)

### Community 429 - "Task Worker"
Cohesion: 0.20
Nodes (9): Completion Report, Cross-References, Identity, Step 1 — Read the Task, Step 2 — Load Agent Profile (if specified), Step 3 — Load start-task and run it, Task Worker, /dh:implement-feature (+1 more)

### Community 430 - "/dh:complete-implementation"
Cohesion: 0.67
Nodes (3): Feature Verifier Agent, Integration Checker Agent, /dh:complete-implementation

### Community 431 - "The work loop"
Cohesion: 0.18
Nodes (9): Codes a command may print to you, Sequence, The runner contract, Your two facts, Each turn, Export, The judge, The work loop (+1 more)

### Community 432 - "_normalize_status"
Cohesion: 0.18
Nodes (11): _normalize_status(), Any, Normalize a raw status value to a canonical TaskStatus string. Args: raw: Raw…, _normalize_status raises ValueError for arbitrary unrecognized strings. Tests:…, _normalize_status raises ValueError when STATUS_MAP maps to a non-TaskStatus…, _normalize_status returns 'not-started' for None (field not provided). Tests:…, _normalize_status returns canonical form for known values. Tests: Happy-path…, test_normalize_status_none_returns_not_started() (+3 more)

### Community 433 - "NetworkBlocked"
Cohesion: 0.18
Nodes (10): NetworkBlocked, RuntimeError, Network guard exception type. Shared between conftest.py and…, Raised when a test attempts a network connection while the guard is armed., A direct outbound TCP connect raises instead of reaching the internet. Uses RFC…, Name resolution for a non-loopback host raises., ``connect_ex`` raises instead of returning a platform error code., test_connect_ex_is_blocked() (+2 more)

### Community 434 - "TestParseAddressPNNN"
Cohesion: 0.20
Nodes (7): parametrize, Test parse_address with P{NNN}/T{M} format strings. Tests: Address parsing for…, Various address formats parse correctly. Tests: Address parsing for multiple…, Invalid address formats raise ValueError. Tests: Input validation. How: Pass…, Slug address 'my-slug/T3' parses correctly. Tests: Slug-based address parsing.…, Slug-only address 'my-slug' returns None task_ref. Tests: Plan-only slug…, TestParseAddressPNNN

### Community 435 - "Audit Partition D: artifacts-durability-cross-surface-integration"
Cohesion: 0.67
Nodes (3): Clause B2: MCP Gist durability vs CLI local-only (current boundary), Clause B4: artifact remote-manifest/local-content boundary (current boundary), Audit Partition D: artifacts-durability-cross-surface-integration

### Community 436 - "Audit Partition B: backlog-logical-objects-providers"
Cohesion: 0.67
Nodes (3): Clause P2: logical objects, no provider IDs/paths, Clause P6: provider-neutral canonical backend semantics, Audit Partition B: backlog-logical-objects-providers

### Community 438 - "_extract_import_roots"
Cohesion: 0.22
Nodes (8): _extract_import_roots(), parametrize, Path, Assert frontend files contain no business logic. Frontends are thin adapters:…, Parse a Python file and extract all import root module names. For ``from…, Frontend files must not contain business logic., Every import in a frontend file must be on the allowlist., TestFrontendLogicFree

### Community 439 - "_RejectedMutation"
Cohesion: 0.20
Nodes (8): Durable provider mutation whose precondition can never be satisfied by retrying., Durable work-item mutation whose idempotency_key doesn't match its own content.…, Union two pending-write queues, keeping at most one entry per reference.…, Union two pending-work-item queues, keeping at most one entry per ``key``.…, _RejectedMutation, _RejectedWorkItemMutation, test_load_does_not_key_check_rejected_entries(), test_transaction_merges_dead_lettered_entries_from_a_recreated_legacy_file()

### Community 440 - "_parse_full_database_id"
Cohesion: 0.31
Nodes (4): _parse_full_database_id(), Normalize a raw GraphQL fullDatabaseId value to int | None. GitHub's…, Unit coverage for the normalizer itself, independent of the surrounding node…, TestParseFullDatabaseIdDirectly

### Community 441 - "_run_spawn_item"
Cohesion: 0.22
Nodes (10): _build_spawn_cmd(), _poll_until_done(), Semaphore, Mutable counters shared across concurrent item coroutines in one wave. Using a…, Construct the spawn.py subprocess command for one dispatch item. Args:…, Poll until a spawned item completes or its PID dies. Args: mgr: State manager…, Spawn one dispatch item, monitor it, and update shared counters. Args: mgr:…, _run_spawn_item() (+2 more)

### Community 442 - "Work Backlog Item"
Cohesion: 0.67
Nodes (3): Verification Protocol, Workflow: Groom Backlog Item, Work Backlog Item

### Community 443 - "T0 Baseline Sample"
Cohesion: 0.67
Nodes (3): Plan with Bookends Fixture, T0 Baseline Sample, TN Verification Sample

### Community 445 - "Output"
Cohesion: 0.01
Nodes (468): get_config(), Return the active BacklogConfig, auto-initialising on first call. Resolution…, Shared capability gates for optional backend protocol subsets. ``GitHubExtras``…, Return ``backend`` narrowed to ``GitHubExtras``, or raise if unsupported. Args:…, Return ``backend``, or raise if it does not support milestones. Unlike…, require_github_extras(), require_milestone_support(), apply_status_blocked() (+460 more)

### Community 447 - "development-harness/progressive_markdown/__init__.py"
Cohesion: 0.04
Nodes (81): TDD tests for AmbiguousSectionRefError on slug collision in resolve_section().…, document(), fixture, TEST C3: MarkdownIndexer.build() decomposition gate + behavioral equivalence.…, Build and return a MarkdownDocument from _CHARACTERIZATION_MD., Agent Memory — python-cli-architect, CodeBlockExtractor, CodeBlockStubRenderer (+73 more)

### Community 451 - "ARCHITECTURE.md"
Cohesion: 0.22
Nodes (7): Adding a type, Artifact Type Registry, Ownership rule, Registration and discovery, Task plans, Hero Image (Interlocking Rings), Development Harness Purpose

### Community 452 - "Backlog Item Lifecycle — Canonical Reference"
Cohesion: 0.22
Nodes (6): Backlog Item Lifecycle — Canonical Reference, blocked-grooming vs blocked-work disambiguation (same status value), Pipeline stages: create → groom → work (prerequisite-checked), Severity counting policy: HIGH > MEDIUM > LOW-MEDIUM > LOW, Backlog state machine (needs-grooming→groomed→in-milestone→in-progress→done/resolved→closed), verified marker (cross-route signal, not a lifecycle state)

### Community 453 - "addressing.py"
Cohesion: 0.20
Nodes (8): _parse_prefix(), Path, Pattern, Plan addressing module for SAM task/plan files. Resolves human-readable address…, Sort key that places ``.yaml`` files before ``.md`` for the same stem. Args: p:…, Extract the plan-type prefix, numeric/slug ref, and filename regex from an…, Initialize AddressingError with the unresolvable address and search directory., _yaml_first_key()

### Community 454 - "_load_sentinel_issue"
Cohesion: 0.24
Nodes (10): _config_search_paths(), _is_str_dict(), _load_sentinel_issue(), _load_yaml_file(), Path, TypeGuard, Return True when *obj* is a dict with exclusively string keys., Read the sentinel issue number from ``.dh/config.yaml``. Looks for… (+2 more)

### Community 455 - "TestPlanNumberResolutionPropertyBased"
Cohesion: 0.29
Nodes (7): given, settings, A plan number with no matching file raises AddressingError. Tests: Negative…, Property-based tests for P{NNN} plan number resolution. Tests: Plan number…, Any valid plan number 1-9999 resolves to the correct P{NNN} file. Tests:…, Zero-padded input '001' matches file P001-*.yaml. Tests: Zero-padded string…, TestPlanNumberResolutionPropertyBased

### Community 457 - "TestSlugResolutionPNNN"
Cohesion: 0.20
Nodes (6): Test slug-based resolution against P{NNN}-{slug} files. Tests: Slug substring…, Slug 'auth-system' matches P001-auth-system.yaml. Tests: Exact slug match. How:…, Partial slug 'auth' matches P001-auth-system.yaml. Tests: Substring slug…, Non-matching slug raises AddressingError. Tests: Slug resolution failure. How:…, When slug matches multiple P-files, returns first sorted match. Tests: Multi-…, TestSlugResolutionPNNN

### Community 458 - "TestPriorityEnum"
Cohesion: 0.20
Nodes (4): Verify Priority IntEnum values., Verify CRITICAL is 1., Verify CRITICAL < LOWEST for sort ordering. Tests: Priority comparison…, TestPriorityEnum

### Community 459 - "TestPlanAcceptanceCriteriaStructured"
Cohesion: 0.20
Nodes (6): Verify Plan.acceptance_criteria_structured field behavior. Tests: Structured…, Verify acceptance_criteria_structured defaults to empty list. Tests: Backward…, Verify both acceptance criteria fields can be set independently. Tests: Prose…, Verify acceptance-criteria-structured alias works via model_validate. Tests:…, Verify multiple AcceptanceCriterion objects are stored correctly. Tests: List…, TestPlanAcceptanceCriteriaStructured

### Community 463 - "TestBookendResultModel"
Cohesion: 0.20
Nodes (6): Verify BookendResult model construction and serialization. Tests: T0/TN command…, Verify BookendResult with required fields constructs. Tests: Minimal valid…, Verify BookendResult with all fields populated. Tests: Full BookendResult…, Verify BookendResult accepts kebab-case alias keys. Tests: YAML alias…, Verify model_dump then model_validate roundtrip preserves data. Tests:…, TestBookendResultModel

### Community 464 - "test_cross_backend.py"
Cohesion: 0.20
Nodes (7): Cross-backend protocol compliance tests for the generic WorkItemBackend…, resolve_github_issue closes an issue with a resolution comment., resolve_github_issue transitions the issue state to CLOSED. Why: Resolve is…, fetch_open_issues_by_title returns a title-to-number dict for open issues., fetch_open_issues_by_title maps open issue titles to their numbers. Why: The…, TestFetchByTitle, TestResolveItem

### Community 465 - "TestWaveItemDefaults"
Cohesion: 0.20
Nodes (6): WaveItem default values for optional fields., WaveItem.conflict_group defaults to None when not provided. Tests: Default…, WaveItem.depends_on defaults to an empty list when not provided. Tests: Default…, WaveItem.status defaults to ItemStatus.PENDING when not provided. Tests:…, WaveItem.depends_on uses default_factory, so each instance gets its own list.…, TestWaveItemDefaults

### Community 466 - "TestWaveConstruction"
Cohesion: 0.20
Nodes (6): Wave construction and constraint validation., Wave constructs correctly with wave number, parallel flag, and items. Tests:…, Wave rejects wave numbers below ge=1. Tests: ge=1 constraint on wave field.…, Wave rejects an empty items list. Tests: min_length=1 constraint on items…, Wave.parallel defaults to True when not supplied. Tests: Default value for…, TestWaveConstruction

### Community 467 - "TestCreateWave"
Cohesion: 0.20
Nodes (6): Tests for DispatchStateManager.create_wave., create_wave returns a DispatchWaveRecord with pending status. Tests:…, create_wave writes all item rows with status='pending'. Tests:…, create_wave raises sqlite3.IntegrityError for duplicate (milestone, wave_num).…, create_wave with no items creates a wave row with zero children. Tests:…, TestCreateWave

### Community 468 - "TestErrorPaths"
Cohesion: 0.20
Nodes (6): Error path tests: close without checklist, view nonexistent, add duplicate,…, Scenario 22: backlog_close returns error for an invalid reason value., Scenario 23: backlog_view returns error for a selector that matches no item., Scenario 24: backlog_add returns duplicate error when similar item exists and…, Scenario 25: backlog_list returns empty items list when no items exist — not an…, TestErrorPaths

### Community 469 - "TestRecursionGuardScenarios"
Cohesion: 0.20
Nodes (6): Tests for recursion guard routing paths. These tests verify that backlog_add…, Guard 1: depth-limit source pattern creates a backlog item with source…, Guard 2: BLOCKED-FOR-PLANNING source — second add with same title is rejected…, Out-of-scope quality gate source — item created with out-of-scope pattern…, In-scope default: item with no explicit scope section proceeds normally as in-…, TestRecursionGuardScenarios

### Community 470 - "field_validator"
Cohesion: 0.22
Nodes (5): field_validator, Normalise and accept priority values, preserving unknown strings verbatim.…, Normalise and accept item_type values, preserving unknown strings verbatim.…, Accept any non-empty status string, preserving unknown values verbatim. Writers…, Allow empty or a YYYY-MM-DD date string. Args: v: Raw added date value from…

### Community 471 - "merge_sections"
Cohesion: 0.33
Nodes (4): merge_sections(), Merge GitHub issue body into local body by section. For each section in GitHub…, Tests for merge_sections(local_body, github_body) -> tuple[str, bool]., TestMergeSections

### Community 472 - "title_to_slug"
Cohesion: 0.33
Nodes (4): Convert item title to filename slug. Returns: Slug string suitable for…, title_to_slug(), Tests for title_to_slug(title) -> str., TestTitleToSlug

### Community 473 - "SyncClaim"
Cohesion: 0.22
Nodes (6): BaseModel, Atomically claim the sync slot, returning the state held before the claim. The…, Restore the status that prevailed before a matching ``try_claim()``. Args:…, Atomically claim the sync slot, returning True when claimed. Thread-safe…, State captured atomically when a caller claims the sync slot., SyncClaim

### Community 474 - "test_comment_database_id.py"
Cohesion: 0.22
Nodes (4): Tests that a comment carries the numeric identifier REST addresses it by.…, An unselected field is absent from the response, so the query/mutation is the…, ``databaseId: Int`` silently overflows for a real comment ID; nothing should…, TestAllThreeOperationsSelectTheField

### Community 475 - "TestParsingCarriesTheIdentifier"
Cohesion: 0.22
Nodes (4): REST needs the number and the GraphQL mutations still need the node ID., The node reaches callers through this parser, so it has to survive it., GitHub's BigInt scalar serializes as a decimal string on the wire. This is the…, TestParsingCarriesTheIdentifier

### Community 476 - "TestTheModelItselfRejectsANonIntDatabaseId"
Cohesion: 0.22
Nodes (4): ``IssueCommentNode``'s own ``strict=True`` config is the second line of…, Strict mode refuses ``True``/``False`` for an ``int`` field — no silent 1/0., Strict mode refuses a numeric string — no silent coercion to int. (The string-…, TestTheModelItselfRejectsANonIntDatabaseId

### Community 477 - "test_list_status_filter_refusal.py"
Cohesion: 0.22
Nodes (5): _Backend, Tests for what a ``--status`` filter means when the live status query never…, Every failed live lookup must exclude unconfirmed numeric statuses., Backend stub exposing only what ``list_items`` reads., TestStatusFilterUnderOtherLookupFailures

### Community 478 - "TestSectionDisplayTitleConsistency"
Cohesion: 0.22
Nodes (7): parametrize, unknown_key_to_heading strips the ``unknown__`` prefix and title-cases the…, Strips the ``unknown__`` prefix, replaces underscores with spaces, title-cases.…, section_display_title on all four backends produces identical output.…, Each backend's section_display_title matches the canonical rendering module…, TestSectionDisplayTitleConsistency, TestUnknownKeyToHeading

### Community 479 - "Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code)"
Cohesion: 0.22
Nodes (8): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables set for a shell command, Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code), Identity: which product "Kimi" is

### Community 480 - "Amendments to the findings files"
Cohesion: 0.22
Nodes (8): A-1 — the predicate counts in `predicates.md` and `completeness.md` are superseded, A-2 — `fidelity.md`'s `ledger_spec.py` element counts are a 2026-09-06 measurement, A-3 — the ADR these findings were scored against was withdrawn as an unreviewed draft, A-4 — the findings assess a three-layer model the design has replaced, A-5 — `ASSESSOR-CONTRACT.md`, the authority these findings cite, has been deleted, A-6 — the citations named in A-5 have now been repointed, not merely documented as broken, A-7 — `graph_ir` is renamed to `workflow_multigraph`, and "IR" no longer names the subject, Amendments to the findings files

### Community 481 - "Default Development Flow"
Cohesion: 0.22
Nodes (9): ARL Touchpoint Gates, Artifact Flow (Linear), Artifact Logical Identifier Conventions, Complete-Implementation Pre-Phase Gates, Default Development Flow, Design Principles, Pipeline Overview, Related Documents (+1 more)

### Community 482 - "Agent Resolution Protocol"
Cohesion: 0.22
Nodes (9): Agent Resolution Protocol, Error Handling, Overview, Resolution Process, Sources, Step 1 — Classify the Task, Step 2 — List Installed Agents, Step 3 — Resolve Roles (+1 more)

### Community 483 - "test_cli_ledger_holds.py"
Cohesion: 0.31
Nodes (8): _create_plan(), MockerFixture, ``sam_plan.ledger_holds`` must answer through the shared…, Create one ledger plan with a single task and return its id. Returns: The…, ``sam_plan.ledger_holds`` must call ``dh_core.ledger.holds``, not scan…, A plan id the ledger never saw answers False through the same shared check., test_ledger_holds_answers_false_for_a_plan_the_ledger_does_not_hold(), test_ledger_holds_delegates_to_the_shared_dh_core_check()

### Community 484 - "The work graph"
Cohesion: 0.25
Nodes (8): Edge types, Falsified predicates, Mechanical checks, Node record, Projections, Provenance: one rule, three sites, Severity rule, The work graph

### Community 485 - "_extract_content_from_comment"
Cohesion: 0.25
Nodes (8): _extract_content_from_comment(), Extract the raw content from an artifact content comment body. Parses the…, Verify inner content is extracted from a well-formed comment body. Tests:…, Verify extracted content has surrounding whitespace stripped. Tests:…, Verify malformed comments return the full body rather than raising. Tests:…, test_extract_content_from_comment_returns_full_body_when_malformed(), test_extract_content_from_comment_returns_inner_content(), test_extract_content_from_comment_strips_surrounding_whitespace()

### Community 486 - "_BdRunnerLike"
Cohesion: 0.25
Nodes (4): _BdRunnerLike, JsonValue, Protocol, Store the runner; do not touch the filesystem or spawn processes.

### Community 487 - "parse_sam_task_metadata"
Cohesion: 0.39
Nodes (3): parse_sam_task_metadata(), Extract SAM task metadata from the ``<!-- sam:task ... -->`` block in an issue…, TestParseSamTaskMetadata

### Community 488 - "_WireSchema"
Cohesion: 0.25
Nodes (6): BaseModel, Use a response model's JSON schema without changing dict serialization., Generate the advertised schema from the response model. Returns: The response…, _WireSchema, GetJsonSchemaHandler, JsonSchemaValue

### Community 489 - "_live_issue_wearing_an_emoji_label"
Cohesion: 0.25
Nodes (7): _live_issue_wearing_an_emoji_label(), fixture, MockerFixture, Minimal stand-in for the PyGithub repository ``get_github`` returns., Report the status label as already present, so no REST creation runs., The issue carries a label name that came from the repository, not from a caller., _Repo

### Community 490 - "TestProbeBackendStatusHonorsEveryTokenVariable"
Cohesion: 0.29
Nodes (4): MockerFixture, A missing GITHUB_TOKEN must not be reported as "no token" when a later…, GH_TOKEN (gh CLI's own variable) must not be treated as absent., TestProbeBackendStatusHonorsEveryTokenVariable

### Community 491 - "TestErrorTypeRelationships"
Cohesion: 0.25
Nodes (5): Existing handlers must keep working, and the new type must stay distinguishable., `except BacklogError` sites predate this type and must still catch it., The condition is a backend surface being unavailable, not a malformed request., A refused query says nothing about whether the item exists., TestErrorTypeRelationships

### Community 492 - "TestFixtureHasThePathology"
Cohesion: 0.25
Nodes (5): Step 1 (design §3): assert the INPUT has the defect's precondition first. A…, The fixture is the real ~72KB resolved body, not a small stand-in., The fixture contains the timestamped entry-block wrappers the defect depends on., The fixture contains the phantom ``## Claim `` headings nested in an entry.…, TestFixtureHasThePathology

### Community 493 - "TestSyncStateToDict"
Cohesion: 0.25
Nodes (5): SyncState.to_dict() returns a JSON-serialisable representation., to_dict() includes all fields from the design spec section 3.2., to_dict() must not expose the asyncio.Lock field (not JSON-serialisable)., to_dict() serialises status as a plain string (not StrEnum instance)., TestSyncStateToDict

### Community 494 - "TestNarrowBodyToNamedSectionsUnit"
Cohesion: 0.25
Nodes (5): Finding 8/10: direct unit coverage for narrow_body_to_named_sections., No matching name → (body, False) with body returned unchanged., Names match case-insensitively against ``## ``/``### `` headers., Matched sections are concatenated in DOCUMENT order, not request order., TestNarrowBodyToNamedSectionsUnit

### Community 495 - "TestRootSectionOrdering"
Cohesion: 0.25
Nodes (5): root_section_ids reflects insertion order of top-level headings., A document with one h1 has exactly one root section id., The sole root section id resolves to the 'Title' heading., Document with h1/h2/h3/h2 headings has exactly 4 sections., TestRootSectionOrdering

### Community 496 - ".test_code_ordinal_matches_pattern"
Cohesion: 0.32
Nodes (6): given, settings, Property: every ordinal string the generators can produce matches…, A sub-heading ordinal, at any nesting depth, matches the validator regex., A code-fence ordinal, attached to the root or any nested heading, matches the…, TestOrdinalGeneratorValidatorAgreement

### Community 497 - "Harness facts: Claude Code"
Cohesion: 0.25
Nodes (7): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables for a shell command, Harness facts: Claude Code

### Community 498 - "_open_pr_refusal"
Cohesion: 0.29
Nodes (6): _open_pr_refusal(), Build a side effect that warns and raises like the operations-layer open-PR…, ``backlog close`` and ``backlog resolve`` report the open-PR refusal as JSON., The open-PR ``BacklogError`` from ``close_item`` reaches stdout as JSON with…, The open-PR ``BacklogError`` from ``resolve_item`` reaches stdout as JSON with…, TestBacklogCloseResolveErrorContract

### Community 499 - "Artifact Types"
Cohesion: 0.25
Nodes (8): Artifact Types, CONTEXT, DISCOVERY, EXECUTION, PLAN, REVIEW, TASK, VERIFICATION

### Community 500 - "Stage Descriptions"
Cohesion: 0.25
Nodes (8): S1 — Discovery, S2 — Planning + RT-ICA, S3 — Context Integration, S4 — Task Decomposition, S5 — Execution, S6 — Forensic Review, S7 — Final Verification, Stage Descriptions

### Community 501 - "get_available_features"
Cohesion: 0.32
Nodes (7): get_active_task(), get_available_features(), main(), Any, Get list of features with task files. Returns: Dictionary containing features…, Get active task context if any. Reads from the DH state context directory…, Print task context information.

### Community 502 - "TestArtifactManifestModelValidation"
Cohesion: 0.25
Nodes (5): Unit tests for ArtifactManifest Pydantic model. Tests: ArtifactManifest…, ArtifactManifest requires issue_number at construction. Tests:…, ArtifactManifest.artifacts defaults to an empty list. Tests: ArtifactManifest…, ArtifactManifest accepts 'last-updated' and 'last_updated' aliases. Tests:…, TestArtifactManifestModelValidation

### Community 503 - "TestComplexityEnum"
Cohesion: 0.25
Nodes (5): Verify MEDIUM maps to 'medium'., Verify HIGH maps to 'high'., Verify Complexity StrEnum values., Verify LOW maps to 'low'., TestComplexityEnum

### Community 504 - "TestIssueClassification"
Cohesion: 0.25
Nodes (5): Verify IssueClassification StrEnum values., Verify PROCEDURAL maps to 'procedural'., Verify DEFECT maps to 'defect'., Verify RECURRING_PATTERN maps to 'recurring-pattern'., TestIssueClassification

### Community 505 - "TestTaskEnumCoercion"
Cohesion: 0.25
Nodes (5): Verify Task model coerces string values to enum values. Tests: use_enum_values…, Verify 'not-started' string is accepted as TaskStatus., Verify integer priority is accepted as Priority., Verify 'high' string is accepted as Complexity., TestTaskEnumCoercion

### Community 506 - "TestBackendStatusAllFieldsPopulated"
Cohesion: 0.25
Nodes (5): BackendStatus with all fields populated produces expected model_dump output.…, model_dump() includes all BackendStatus field names. Tests:…, model_dump() returns each field value as provided. Tests:…, model_dump() serialises BackendAvailability enum to its string value. Tests:…, TestBackendStatusAllFieldsPopulated

### Community 507 - "TestParseCommentNode"
Cohesion: 0.25
Nodes (5): _parse_comment_node returns empty strings for absent optional fields. Tests:…, Unit tests for _parse_comment_node helper., _parse_comment_node maps all GraphQL fields to IssueCommentNode keys. Tests:…, _parse_comment_node returns empty string author when author is absent. Tests:…, TestParseCommentNode

### Community 508 - "TestBackendStatus"
Cohesion: 0.25
Nodes (5): probe_backend_status returns a valid BackendStatus with REACHABLE for local…, probe_backend_status returns REACHABLE for memory and SQLite backends. Why:…, probe_backend_status result has a non-empty name field. Why: Clients display…, try_get_github returns None for local (non-GitHub) backends. Why: Local…, TestBackendStatus

### Community 509 - "TestListItems"
Cohesion: 0.25
Nodes (5): fetch_open_issues_by_title returns open issues filtered by state., fetch_open_issues_by_title returns only open issues after a close. Why: State-…, fetch_open_issues_by_title excludes closed issues. Why: Closed issues must not…, fetch_open_issues_by_title on an empty backend returns an empty dict. Why:…, TestListItems

### Community 510 - "TestViewEnrich"
Cohesion: 0.25
Nodes (5): view_enrich_from_github populates a ViewItemResult from stored issue data., view_enrich_from_github returns True for a known issue number. Why: True…, view_enrich_from_github populates result.number with the issue number. Why:…, view_enrich_from_github returns False for an issue number that does not exist.…, TestViewEnrich

### Community 511 - "TestQualityGatesConstruction"
Cohesion: 0.25
Nodes (5): QualityGates construction and defaults., QualityGates constructs with empty pre_merge and post_merge lists by default.…, QualityGates.model_validate accepts 'pre-merge' kebab-case alias. Tests:…, QualityGates.model_validate accepts 'post-merge' kebab-case alias. Tests:…, TestQualityGatesConstruction

### Community 512 - "TestEnsureSchema"
Cohesion: 0.25
Nodes (5): Verify that __init__ creates required tables and indices idempotently., DispatchStateManager constructor creates the waves table. Tests:…, DispatchStateManager constructor creates the items table. Tests:…, Calling ensure_schema multiple times does not raise. Tests:…, TestEnsureSchema

### Community 513 - "TestSemanticQueryCorpus"
Cohesion: 0.32
Nodes (5): 10-query semantic corpus achieves at least 80% success rate (8/10 matches)., Each corpus query returns at least one result (no empty result sets)., Corpus-based integration tests verifying the filter infrastructure supports…, Create all corpus items in the test backlog directory., TestSemanticQueryCorpus

### Community 514 - "test_tool_output_schemas.py"
Cohesion: 0.36
Nodes (7): Asserts every backlog_core MCP tool advertises a real output schema, not an…, No tool_responses.py model field name collides with an Output method.…, _schema_tokens(), test_all_typed_tools_advertise_a_real_output_schema(), test_no_response_model_field_shadows_an_output_method(), test_output_schemas_stay_within_token_budget(), _tool_schemas()

### Community 515 - "Development Harness Architecture"
Cohesion: 0.29
Nodes (7): Automation Boundary, Development Harness Architecture, Storage and routing, The backend guarantee, The frontend contract, The logical model, What a hook may write

### Community 516 - "_try_register_dispatch_plan_artifact"
Cohesion: 0.38
Nodes (7): _load_manifest(), _manifest_reference(), ItemId, Return the manifest identity for a backlog item, refusing as a…, _try_register_dispatch_plan_artifact(), The one already-fixed site, kept under test beside the rest of the…, test_the_manifest_reference_boundary_still_converts()

### Community 517 - "Claims register — development-harness"
Cohesion: 0.29
Nodes (6): Claims register — development-harness, `dh_paths.py` claims, Harness capability matrix (read 2026-09-06), Lease, n8n as a reference for the graph model (read 2026-09-07), SQLite

### Community 518 - "_poll_until_done"
Cohesion: 0.33
Nodes (7): _check_pid_alive(), _poll_until_done(), Path, Poll until a spawned item completes or its PID dies. Returns: ``(succeeded,…, Read the result file, record completion, and return cost. Returns: USD cost…, Return True if *pid* is still running (or unknown)., _read_result_cost()

### Community 519 - "report"
Cohesion: 0.33
Nodes (7): Print every unsatisfied observation and return the run's exit status. Args:…, report(), CaptureFixture, The one line a hand run prints on success names the plan, so the ledger can be…, Recording rather than asserting is only worth it if the verdict still names the…, test_a_clean_run_ends_by_naming_the_plan_that_reached_progress_done(), test_an_unsatisfied_observation_fails_the_run_and_names_the_step_that_broke()

### Community 520 - "plan_dir"
Cohesion: 0.29
Nodes (7): plan_dir(), plan_dir_with_p_files(), plan_dir_with_qg_files(), fixture, Return a temporary plan/ directory., Populate plan/ with P{NNN}-{slug}.yaml files and a legacy tasks-* file.…, Populate plan/ with a QG{NNN}-{slug}.yaml file alongside P-prefix files.…

### Community 521 - "MonkeyPatch"
Cohesion: 0.29
Nodes (7): MonkeyPatch, sam-task-create accepts --repo and forwards it to operations., sam-task-create omitting --skill forwards an empty skills list, not a CLI…, sam-task-status accepts --repo and forwards it to operations., test_sam_task_create_accepts_and_forwards_repo(), test_sam_task_create_without_skill_succeeds(), test_sam_task_status_accepts_and_forwards_repo()

### Community 523 - "TestCloseItem"
Cohesion: 0.29
Nodes (4): close_github_issue transitions an issue to CLOSED state., close_github_issue transitions the issue state to CLOSED. Why: Closing is the…, close_github_issue with '#N' issue_ref format closes the issue. Why: Callers…, TestCloseItem

### Community 524 - ".test_git_common_root_closes_repo_object"
Cohesion: 0.29
Nodes (5): MockerFixture, Tests that the GitPython Repo object constructed internally is closed., Clear module-level root cache before each test., _git_common_root closes the GitPython Repo it constructs. Tests: resource…, TestGitCommonRootResourceCleanup

### Community 525 - "._validate_artifact_path"
Cohesion: 0.33
Nodes (3): Read artifact file content from the root worktree. Args: path: Repo-relative…, Read artifact file content from the local filesystem. Same as…, Raise ``ValueError`` when *path* fails the path traversal check. The resolved…

### Community 526 - "_GraphQLCapable"
Cohesion: 0.40
Nodes (4): _GraphQLCapable, _GraphQLRequester, Protocol, Structural minimum _graphql_request needs -- narrower than the full Repository…

### Community 527 - "_github_reachable"
Cohesion: 0.33
Nodes (6): _github_reachable(), fixture, MockerFixture, Minimal stand-in for the PyGithub repository ``get_github`` returns., Every site resolves a repository before it parses the ref., _Repo

### Community 528 - ".test_a_live_labeled_needs_grooming_entry_renders_bare"
Cohesion: 0.33
Nodes (4): The render path must agree with the filter path on the live side too.…, Reproduction (P2, PR #3552 Codex review, third finding): a live status map…, The rendered entry must agree with the documented post-render filter that…, TestRenderedStatusWithALiveAnswer

### Community 529 - ".test_a_numeric_issue_falls_back_to_the_backend_owned_status"
Cohesion: 0.33
Nodes (4): A backend that never queries is in the same position as one that was refused., No query ran, so the backend-owned field is authoritative — not "needs-…, Nothing degraded: this backend has no live statuses to lose., TestBackendsWithoutABatchStatusFetch

### Community 530 - "TestFalsification"
Cohesion: 0.33
Nodes (4): Step 4 (design §3): falsification checks that must fail to fail. A test that…, The deleted ``_SECTION_BOUNDARY_RE`` pattern, run inline against the real body.…, The fix changes entry-block behaviour only, not plain-heading behaviour. This…, TestFalsification

### Community 535 - "DispatchStateManager"
Cohesion: 0.08
Nodes (19): DispatchStateManager, Close the underlying SQLite connection., Mark an item as in-progress and record the spawned PID. Args: milestone: GitHub…, Record the Claude Code session UUID for a spawned item. Args: milestone: GitHub…, Mark an item as complete and record the result. Args: milestone: GitHub…, SQLite state backend for dispatch orchestration. Creates the database and…, Mark an item as failed and record the error message. Args: milestone: GitHub…, Detect in-progress items whose spawned processes have died. Queries all items… (+11 more)

### Community 537 - ".test_over_budget_drift_section_returns_directory"
Cohesion: 0.33
Nodes (4): Codex P2 (#2495): a cleared body must not let the sole section copy escape the…, ``_view_payload_token_count`` must reflect the SOLE section copy when body is…, backlog_view(sections=['RT-ICA']) on a drift item returns the over-budget…, TestOverBudgetMeasurementCountsClearedBodySoleContent

### Community 549 - "_resolve_repo_with_timeout"
Cohesion: 0.33
Nodes (6): GitResolutionTimeoutError, Repo, RuntimeError, Raised when GitPython does not resolve a repository within the timeout., Construct a ``git.Repo`` bounded by a hang guard. GitPython's ``Repo()``…, _resolve_repo_with_timeout()

### Community 550 - "Layer 1 Overview"
Cohesion: 0.33
Nodes (5): CoVe Bypass Anti-Pattern, Inheritance from Layer 0, Layer 1 ≠ Layer 0 Boundary, Layer 1 Overview, Non-Typed Languages

### Community 552 - "Dispatch — Orchestrator as Manager"
Cohesion: 0.33
Nodes (6): agent-orchestration:agent-orchestration Skill, Dispatch — Orchestrator as Manager, Ad-Hoc Dispatch Mode, Handle Blockers Flow, Relay Discoveries Between Waves, SAM Dispatch Mode

### Community 575 - ".__init__"
Cohesion: 0.33
Nodes (3): Initialise with an optional pre-constructed provider. Args: provider: Artifact…, Initialize the unavailable index read details., Initialize the unavailable plan-content read details.

### Community 576 - "Backend Resolution"
Cohesion: 0.33
Nodes (5): Acting on the answer, Backend Resolution, Do not re-derive this, Identifier shapes, The chain

### Community 577 - "Read the Code Review Verdict"
Cohesion: 0.33
Nodes (5): Read the Code Review Verdict, Step A — Read by identifier, Step B — Step A found no such entry, Step C — No `code-review` entry for this quality-gate plan, Step D — Neither type yields a report

### Community 593 - "Which Shape `plan status` Answered In"
Cohesion: 0.33
Nodes (5): The content shape — no `row` key, The ledger shape — a top-level `row` key is present, Where each shape appears in this skill, Which Shape `plan status` Answered In, Why the discriminator is not optional

### Community 595 - "TestParseTableRowEdgeCases"
Cohesion: 0.33
Nodes (4): Additional tests targeting _parse_table_row branches not covered by other…, parse_manifest_section skips table rows with fewer than five columns. Tests:…, parse_manifest_section defaults status to CURRENT for unknown status values.…, TestParseTableRowEdgeCases

### Community 598 - "test_backend_factory_import_order"
Cohesion: 0.33
Nodes (5): parametrize, unit, Regression coverage for acyclic backlog backend imports., Both import orders construct every backend and satisfy the contract., test_backend_factory_import_order()

### Community 599 - "TestAnalysisMethod"
Cohesion: 0.33
Nodes (4): Verify AnalysisMethod StrEnum values., Verify NONE maps to 'none'., Verify FIVE_WHYS maps to '5-whys'., TestAnalysisMethod

### Community 602 - "TestTaskFailedStatus"
Cohesion: 0.33
Nodes (4): Verify Task model accepts and stores FAILED status correctly. Tests:…, Verify Task can be constructed with FAILED status., Verify Task accepts 'failed' string for status field., TestTaskFailedStatus

### Community 603 - "TestSchemaGapModel"
Cohesion: 0.33
Nodes (4): Verify SchemaGap model construction. Tests: SchemaGap data model for gap…, Verify SchemaGap with all fields., Verify SchemaGap with actual value populated., TestSchemaGapModel

### Community 604 - ".test_read_result_with_gaps"
Cohesion: 0.33
Nodes (4): Verify ReadResult model construction. Tests: ReadResult wrapping a Plan with…, Verify ReadResult wraps a Plan correctly., Verify ReadResult includes schema gaps., TestReadResultModel

### Community 605 - "TestToolRegistration"
Cohesion: 0.33
Nodes (4): Tests for MCP tool registration on the agent_profile server. Tests: Both tools…, agent_profile server exposes 'load' and 'list' as registered tools. Tests: Tool…, agent_profile server exposes exactly two tools: load and list. Tests: No…, TestToolRegistration

### Community 606 - "TestDryRun"
Cohesion: 0.33
Nodes (4): create_issue_for_item with dry_run=True returns None and creates no issue., dry_run=True returns None without persisting the issue. Why: Dry-run mode is…, dry_run=True leaves the backend with no new issues. Why: Side-effect-free dry…, TestDryRun

### Community 611 - "TestFetchBody"
Cohesion: 0.33
Nodes (4): fetch_github_issue_body returns the stored body string or None., fetch_github_issue_body returns the issue body for a known issue. Why: Body…, fetch_github_issue_body returns None for an issue number that does not exist.…, TestFetchBody

### Community 612 - "fixtures_dir"
Cohesion: 0.33
Nodes (6): fixtures_dir(), minimal_wave_item(), fixture, Path, Return the path to the fixtures directory., A minimal valid WaveItem with only required fields.

### Community 613 - "TestWaveItemKebabCaseAliases"
Cohesion: 0.33
Nodes (4): WaveItem accepts kebab-case keys for aliased fields via model_validate., WaveItem.model_validate accepts 'conflict-group' kebab-case alias. Tests:…, WaveItem.model_validate accepts 'depends-on' kebab-case alias. Tests:…, TestWaveItemKebabCaseAliases

### Community 614 - "TestWaveItemConstraints"
Cohesion: 0.33
Nodes (4): WaveItem field constraint violations raise ValidationError., WaveItem rejects issue numbers below ge=1. Tests: ge=1 constraint on issue…, WaveItem rejects an empty title string. Tests: min_length=1 constraint on title…, TestWaveItemConstraints

### Community 642 - "TestGetWave"
Cohesion: 0.33
Nodes (4): Tests for DispatchStateManager.get_wave., get_wave returns the wave record with nested items. Tests:…, get_wave returns None when the wave does not exist. Tests:…, TestGetWave

### Community 645 - "TestGetWaveItems"
Cohesion: 0.33
Nodes (4): Tests for DispatchStateManager.get_wave_items., get_wave_items returns items sorted ascending by issue number. Tests:…, get_wave_items returns an empty list for a wave with no items. Tests:…, TestGetWaveItems

### Community 647 - ".test_merge_different_branches_proceeds_to_api"
Cohesion: 0.33
Nodes (4): merge_integration_branch rejects head_branch == base_branch before API calls., Test head_branch == base_branch raises BacklogError without API call. Tests:…, Test distinct head and base branches are accepted and reach the API. Tests:…, TestMergeIntegrationBranchValidation

### Community 650 - "ProgressCallback"
Cohesion: 0.40
Nodes (4): ProgressCallback, Protocol, Protocol for incremental progress reporting during a sync pass., Update sync progress. Args: items_done: Number of issues written to cache so…

### Community 651 - "_apply_key_filter"
Cohesion: 0.40
Nodes (5): _apply_key_filter(), _item_value(), _T, Filter ``items`` by generic key=value pairs (AND logic). An item matches when…, Return the value for *key* from a mapping or Pydantic model. Supports both…

### Community 666 - "session-end-kage-bunshin-child-notify.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 667 - "session-end-kage-bunshin-cleanup.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 668 - "stop-kage-bunshin-child-notify.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 669 - "stop-kage-bunshin-idle-check.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 670 - "task-completed-kage-bunshin-reminder.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 671 - ".validate_parent_issue_number"
Cohesion: 0.40
Nodes (3): field_validator, Normalize documented status aliases before enum validation. Returns: A…, Accept None, int >= 0, or a beads nanoid string; reject everything else.…

### Community 672 - ".update_plan_fields"
Cohesion: 0.40
Nodes (3): PlanUpdateValue, Delete a key from bd remember. No-op when the key is absent. Args: key:…, Update top-level fields on the beads epic for a plan. Supported ``set_fields``…

### Community 673 - "apply_project_dir_from_argv"
Cohesion: 0.40
Nodes (3): apply_project_dir_from_argv(), Shared MCP entrypoint pre-init: runs before any ``fastmcp``-importing module.…, If argv contains ``--project-dir``, set ``DH_PROJECT_ROOT`` when unset.

### Community 674 - "_find_project_root"
Cohesion: 0.50
Nodes (4): _find_project_root(), main(), Walk up from cwd looking for .claude/ to find the project root. Returns:…, Parse arguments, run query, exit with result code.

### Community 675 - "Issue Sync (Steps 2.2–2.4)"
Cohesion: 0.40
Nodes (4): Issue Sync (Steps 2.2–2.4), Step 2.2: Issue Link Check, Step 2.3: Create Linked Issue, Step 2.4: Set In-Progress

### Community 677 - "test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case"
Cohesion: 0.40
Nodes (5): _CASE_SPELLINGS, A plan id spelled in another case routes to the ledger that holds the plan. The…, A ledger-only command finds the plan when its id is spelled in another case., test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case(), test_a_plan_address_differing_only_in_case_reads_the_ledger()

### Community 678 - "test_default_test_paths_match_pyproject_testpaths"
Cohesion: 0.40
Nodes (4): skipif, Drift guard for run_pytest.py's standalone test-path duplication.…, This plugin's *existing* entries in root ``testpaths`` must equal…, test_default_test_paths_match_pyproject_testpaths()

### Community 679 - ".test_pull_updates_local"
Cohesion: 0.40
Nodes (3): Scenarios for backlog_sync and backlog_pull tools., Scenario 20: backlog_sync creates GitHub issues for items that lack them., TestSyncAndPull

### Community 680 - "test_call_sam_cli_delegates_timeout_cleanup_to_terminate_process_tree"
Cohesion: 0.40
Nodes (5): _popen_timeout(), MockerFixture, On timeout, _call_sam_cli delegates process-tree cleanup to…, Build a fake Popen instance whose communicate() times out once, then reaps…, test_call_sam_cli_delegates_timeout_cleanup_to_terminate_process_tree()

### Community 681 - "test_an_attempt_clause_in_free_text_is_not_a_launch"
Cohesion: 0.40
Nodes (5): parametrize, Each prompt shape the orchestrator skills write must yield plan, task AND…, A sub-agent of any plugin may discuss a dispatch; discussing one must not…, test_an_attempt_clause_in_free_text_is_not_a_launch(), test_every_shipped_launch_shape_yields_address_and_attempt()

### Community 682 - "The workflow"
Cohesion: 0.50
Nodes (4): Acceptance criteria, Naming, Relation to the SAM stage numbering, The workflow

### Community 683 - "The decomposition-exit gate"
Cohesion: 0.50
Nodes (4): An unresolved referent is an upstream task, not a deletion, Authority of a task's instructions, at runtime, The decomposition-exit gate, The judgement tier blocks, and demotion clears it

### Community 684 - "The orchestration loop"
Cohesion: 0.50
Nodes (4): Invariants, The loop nests, and that is what a wave is, The orchestration loop, What reaches the Orchestrator

### Community 685 - "The model"
Cohesion: 0.50
Nodes (4): The model, What belongs to a node, What belongs to an edge, What the model must carry

### Community 686 - "test_import_boundaries.py"
Cohesion: 0.50
Nodes (3): Import-order regressions for development-harness module boundaries., The operations-first import order completes in a fresh interpreter., test_operations_imports_before_server_without_cycle()

### Community 688 - "TestOperationsDoesNotImportFromGithubSync"
Cohesion: 0.50
Nodes (3): operations.py must not import rendering symbols from github_sync at module…, Verify via AST that operations.py has no github_sync rendering imports. After…, TestOperationsDoesNotImportFromGithubSync

### Community 689 - "TestRenderGroomedSectionConsistency"
Cohesion: 0.50
Nodes (3): render_groomed_section on all three backends produces the same markdown., Each backend's render_groomed_section matches the canonical rendering module…, TestRenderGroomedSectionConsistency

### Community 690 - ".test_progress_callback_updates_state_visible_from_event_loop"
Cohesion: 0.50
Nodes (3): Progress mutations from the asyncio.to_thread worker must be marshalled back to…, State fields updated via the progress callback are visible after the sync. The…, TestCrossThreadProgressCallback

### Community 691 - "TestPLRLintGate"
Cohesion: 0.50
Nodes (3): ruff PLR0915/PLR0914 gate on indexer.py. This class is deliberately RED before…, ruff --select PLR0915,PLR0914 must exit 0 on indexer.py after decomposition.…, TestPLRLintGate

### Community 692 - "test_init_docstring.py"
Cohesion: 0.50
Nodes (3): TDD test that every name in __all__ is documented in the module docstring.…, Every name in __all__ must appear as a substring in the module docstring.…, test_all_exports_appear_in_module_docstring()

### Community 693 - "Hook Subprocess Invocation"
Cohesion: 0.50
Nodes (3): Hook Subprocess Invocation, Never call `fastmcp call` from here, Use the plain CLI instead

### Community 694 - "pytest_runtest_protocol"
Cohesion: 0.50
Nodes (4): pytest_runtest_protocol(), Compute the per-test network policy from the e2e marker + env var. No public…, hookimpl, Item

### Community 695 - "Config"
Cohesion: 0.50
Nodes (4): pytest_unconfigure(), Restore the real socket functions at session teardown. Args: config: The pytest…, Config, One ``.dh/config.yaml`` key the ledger reads.

### Community 696 - "Backlog Item Groomed Schema"
Cohesion: 0.67
Nodes (4): Backlog Item Groomed Schema, Issue Classification section (procedural/defect/recurring-pattern/missing-guardrail/unbounded-design), Root-Cause Analysis section (5-whys / 6-sigma variants), RT-ICA APPROVED/BLOCKED integration with grooming

### Community 697 - "Agent Health Check Procedure"
Cohesion: 0.50
Nodes (3): Agent Health Check Procedure, Ask the ledger first, Transcript check

### Community 698 - "Groom finalize hardening provenance"
Cohesion: 0.50
Nodes (3): Carried from the retired `groom-backlog-item` skill, Groom finalize hardening provenance, Output Validation Gate retry — same model only

### Community 699 - "_patch_gh_client_batch_fetch"
Cohesion: 0.50
Nodes (4): _patch_gh_client_batch_fetch(), fixture, MockerFixture, Patch ``gh_client.batch_fetch_statuses`` to return an empty dict. Applied to…

### Community 700 - "import_existing_and_leased"
Cohesion: 0.50
Nodes (4): import_existing_and_leased(), import_source(), Build a one-task import source, which is where a state the commands cannot…, Import a plan the ledger already holds, one of whose tasks holds an open…

### Community 701 - "reads_as_plan"
Cohesion: 0.50
Nodes (4): Report whether a path under :data:`FIXTURES` reads as a plan with tasks. Args:…, :data:`PLAN_FIXTURES` names every fixture the readers turn into a plan with…, reads_as_plan(), test_every_plan_fixture_is_covered()

### Community 702 - "test_guard_covers_testpath"
Cohesion: 0.50
Nodes (4): integration, parametrize, The root conftest guard applies to every configured testpath. Writes a probe…, test_guard_covers_testpath()

### Community 703 - ".test_list_for_milestone_selection"
Cohesion: 0.50
Nodes (3): Scenarios consumed by /group-items-to-milestone skill., Scenario 18: list returns items with status/milestone keys for milestone…, TestGroupItemsToMilestone

### Community 704 - ".test_groomer_list_then_view"
Cohesion: 0.50
Nodes (3): Scenarios consumed by @backlog-item-groomer agent., Scenario 19: groomer lists items then views a specific item by title., TestBacklogItemGroomer

### Community 705 - "TestCreateBacklogItem"
Cohesion: 0.50
Nodes (3): Scenarios consumed by the /work-backlog-item create route., backlog_add creates a file, syncs a GitHub issue, and returns all expected…, TestCreateBacklogItem

### Community 707 - "SectionMeta"
Cohesion: 0.67
Nodes (3): Compact section inventory entry — section name plus entry counts, no body…, SectionMeta, ExtTypedDict

### Community 709 - "_mock_get_encoding"
Cohesion: 0.67
Nodes (3): _mock_get_encoding(), Encoding, Return the byte-level mock encoder used when real BPE tables are unavailable.…

### Community 716 - "test_canonical_plan_id_leaves_a_non_uid_id_unchanged"
Cohesion: 0.67
Nodes (3): parametrize, An id that is not ``P`` plus exactly eight hex digits passes through unchanged.…, test_canonical_plan_id_leaves_a_non_uid_id_unchanged()

### Community 717 - "test_artifact_mcp_surface_matches_the_operations_signature"
Cohesion: 0.67
Nodes (3): parametrize, Each MCP tool must accept the same parameters as its operations counterpart.…, test_artifact_mcp_surface_matches_the_operations_signature()

## Knowledge Gaps
- **702 isolated node(s):** `npx`, `@modelcontextprotocol/server-sequential-thinking`, `STYLE_GUIDE`, `{ execFileSync }`, `fs` (+697 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **196 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Output` connect `Output` to `backlog_core/models.py`, `create_integration_branch`, `merge_integration_branch`, `test_tool_output_schemas.py`, `groom_item`, `test_backlog_core_server.py`, `GitHubBackend`, `_Repository`, `_warnings`, `BacklogItem`, `.test_a_closed_fetched_issue_without_a_status_label_is_not_fabricated_as_needs_grooming`, `test_status_filter_fabrication.py`, `backlog_list`, `.test_a_live_labeled_needs_grooming_entry_renders_bare`, `.test_a_numeric_issue_falls_back_to_the_backend_owned_status`, `MockerFixture`, `InMemoryBackend`, `create_backend`, `Any`, `BeadsBackend`, `backlog_core/server.py`, `BacklogViewDisclosureHandler`, `MockerFixture`, `_write_item_file`, `test_github_tools_prs.py`, `MockerFixture`, `test_status_source_wire.py`, `test_section_registry.py`, `BacklogConfig`, `ArtifactType`, `github_branches.py`, `Section`, `WorkItemBackend`, `_CheckpointedBackend`, `test_github_branches.py`, `DispatchItemRecord`, `view_item`, `sam_plan.py`, `backlog.py`, `_write_item`, `test_list_status_filter_refusal.py`, `add_item`, `delete_integration_branch`, `_patch_backend`, `_item`, `_write_item_file`, `test_github_tools_labels.py`, `MockerFixture`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `BacklogError` connect `Output` to `backlog_core/models.py`, `ContentRef`, `create_integration_branch`, `merge_integration_branch`, `_validate_milestone_number`, `_validate_slug`, `_try_register_dispatch_plan_artifact`, `_Repository`, `GitHubBackend`, `BacklogItem`, `parsing.py`, `test_backlog_core_server.py`, `backlog_list`, `MockerFixture`, `InMemoryBackend`, `GistTaskLayer`, `test_open_pr_search_failure.py`, `test_github_tools_projects.py`, `backlog_core/server.py`, `BacklogViewDisclosureHandler`, `MockerFixture`, `_is_not_found_error`, `test_github_tools_prs.py`, `artifact_provider.py`, `parse_entries`, `test_startup_sync.py`, `test_section_registry.py`, `BacklogConfig`, `ArtifactType`, `linear_client.py`, `MockerFixture`, `github_branches.py`, `BranchConflictError`, `ContentDuplicateMatch`, `test_linear_artifact_provider.py`, `GitHubGistArtifactProvider`, `test_github_branches.py`, `get_repo_root`, `sam_plan.py`, `migrate_tasks_to_github.py`, `helpers.py`, `backlog.py`, `find_item`, `test_server_sam.py`, `dh_migrate.py`, `test_backlog_groom_sections.py`, `_resolve_labels_graphql`, `_item`, `test_github_tools_milestones.py`, `_open_pr_refusal`, `sync_issues_graphql`, `test_github_tools_labels.py`, `_item`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `BacklogItem` connect `BacklogItem` to `ItemContentNormalizer`, `_populated_cache_state`, `backlog_core/models.py`, `ContentRef`, `_assemble_view_compact`, `GitHubBackend`, `_Repository`, `_item`, `_warnings`, `parsing.py`, `test_status_filter_fabrication.py`, `TestCloseItem`, `MockerFixture`, `parse_item_file`, `InMemoryBackend`, `load_item`, `build_issue_body`, `test_open_pr_search_failure.py`, `BeadsBackend`, `MockerFixture`, `_write_item_file`, `GroomedData`, `_make_local_item`, `call_mcp_tool`, `MockerFixture`, `test_section_registry.py`, `BacklogConfig`, `_patch_github_body`, `_ViewBackend`, `ArtifactType`, `_make_item`, `_RejectedMutation`, `Output`, `Section`, `IssueCommentNode`, `test_backlog_core_parsing.py`, `_make_mixed_items`, `WorkItemBackend`, `_CheckpointedBackend`, `view_item`, `test_cross_backend.py`, `_make_local_item`, `CacheCheckpoint`, `Entry`, `find_item`, `_make_item_with_section`, `_write_item`, `test_list_status_filter_refusal.py`, `Path`, `add_item`, `view_result_from_local_item`, `_patch_backend`, `_item`, `parse_issue_body`, `_write_item_file`, `TestBacklogItemReferenceHealing`, `TestResolveItem`, `test_file_cache.py`, `build_issue_body_from_file`, `_item`, `migrate_backlog_to_yaml.py`, `MockerFixture`, `_item`, `render_issue_body`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 75 inferred relationships involving `BacklogItem` (e.g. with `WorkItemBackend` and `FileCache`) actually correct?**
  _`BacklogItem` has 75 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `Output` (e.g. with `migrate_live_run()` and `_migrate_queue_manifest_only()`) actually correct?**
  _`Output` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 58 inferred relationships involving `InMemoryBackend` (e.g. with `AddedCommentNode` and `IssueCommentNode`) actually correct?**
  _`InMemoryBackend` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ContentRef` (e.g. with `load_manifest()` and `publish_artifact()`) actually correct?**
  _`ContentRef` has 6 INFERRED edges - model-reasoned connections that need verification._