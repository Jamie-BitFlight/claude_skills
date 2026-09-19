# Graph Report - development-harness  (2026-09-20)

## Corpus Check
- 805 files · ~1,370,635 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: .xml 1, .typed 1)

## Summary
- 23995 nodes · 53400 edges · 736 communities (604 shown, 102 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 4571 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `256e15ad`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- backlog_core/models.py
- ._mutate
- Entry
- _ContentsRepository
- TaskStatus
- gh_client.py
- Output
- ContentTaskProvider
- GitHubBackend
- ContentRef
- cli_active_task.py
- LocalYamlTaskProvider
- GistTaskLayer
- SyncState
- test_beads_models.py
- backlog_list
- Section
- sam_schema/core/models.py
- FileCache
- test_ledger_port.py
- _entry_ordinal_for_sub_heading
- test_ledger_conformance.py
- OrdinalPathMapper
- verify_migration_fidelity.py
- ArtifactManifest
- BacklogError
- BeadsBackend
- BeadsArtifactProvider
- InMemoryBackend
- navigator.py
- test_disclosure_handler.py
- BacklogConfig
- WorkItemBackend
- dh_paths.py
- make_task
- _Repository
- beads.py
- BacklogItemMetadata
- store.py
- test_task_status_hook.py
- _extract_response_dict
- transitions.py
- ContentUnavailableError
- BeadsTaskProvider
- FormatType
- backlog_core/operations.py
- BacklogViewDisclosureHandler
- progressive_markdown/__init__.py
- WaveItem
- ArtifactType
- LocalFilesystemArtifactProvider
- test_artifact_provider.py
- run_quality_gates
- ProgressiveMarkdownNavigator
- test_consolidated_tools.py
- classify_sync_error
- ContentConflictError
- call_mcp_tool
- _call
- BdRunner
- DHConfig
- TokenBoundedExtractor
- test_scripted_runner.py
- DisclosureRequestParser
- test_dh_paths_integration.py
- ViewItemResult
- test_spawn.py
- artifact_provider.py
- IssueCommentNode
- load_item
- test_backlog_core_server.py
- test_server_sam_taskbackend.py
- .parse
- conn
- _item
- read_manifest_plan
- LinearArtifactProvider
- test_validator.py
- test_frontmatter_reader.py
- open_ledger
- find_item
- _make_view_result
- dispatch.py
- ._bd_id_for_task
- test_mcp_call_shape_drift.py
- parse_entries
- test_file_cache.py
- _paginate
- backlog.py
- monitor.py
- scripted_runner.py
- create_backend
- test_agent_portability_and_verdict_drift.py
- model.py
- test_readers/test_yaml_reader.py
- test_ledger_fold.py
- spawn.py
- Path
- dh_migrate.py
- merge_layer.py
- get_repo_root
- _resolve_labels_graphql
- _call_view
- DispatchPlan
- test_artifact_registry_ownership.py
- test_cli_active_task.py
- fetch_task
- Path
- entry_blocks.py
- test_decomposition_gate.py
- split_body_sections
- .from_markdown
- save_item
- test_known_failure_types.py
- sync_issues_graphql
- cli_inputs.py
- migrate_backlog_to_yaml.py
- test_github_tools_milestones.py
- test_frontend_parity_ops.py
- Path
- tool_responses.py
- _item
- Graph
- MonkeyPatch
- _extract_log_messages
- _call
- detect_format
- Backlog MCP Package — Architecture Spec
- test_dh_migrate.py
- Path
- parse_md_body_sections
- issue-3152-resolved-body.md
- PRD: DH Workflow Extractor System
- sam_plan.py
- test_github_tools_issues.py
- test_cli_migrate_fallback.py
- PullRequestRef
- _github_exception
- Observation
- LoopDriver
- BranchInfo
- test_epoch_timestamp_bug.py
- TokenBudgeter
- register
- install_proxy_tls_support
- enumerate_scope.py
- test_github_tools_prs.py
- _build_task_dict
- test_view_sections_metadata_sync.py
- MockerFixture
- test_backward_compat_local_plans.py
- analyze_impact_radius_conflicts
- parse_item_file
- Claim Inventory
- Path
- Any
- test_addressing.py
- _build_sections_metadata
- test_batch_section_writes.py
- test_view_pagination_section_index.py
- test_github_client.py
- WorkGraph
- test_github_gist_artifact_provider.py
- queries.py
- ReconcileResult
- implementation_manager.py
- RT-ICA: Reverse Thinking - Information Completeness Assessment
- run_cli_subprocess
- Path
- test_scenarios.py
- test_integration_reconciliation.py
- test_ledger_cascade_ancestors.py
- /work-milestone
- parse_manifest_section
- BdInvocationError
- _search_aware_list_items
- groom/start.md
- github_context_backend.py
- read_dispatch_plan
- ADR-3082-1: The control set is one SQLite database, content-keyed, with periodic global eviction
- _call
- CommandResult
- wrap_entry
- _paginate_body_result
- _patch_github_body
- properties
- Path
- test_ledger_check_order.py
- plan-validator.md
- The work graph
- workflow_multigraph/__init__.py
- CallableMarkdownContentProvider
- Path
- codebase-analyzer.md
- feature-verifier.md
- _process_trace
- migrate
- test_github_flag.py
- beads_artifact_provider.py
- resolve_plan_address
- migrate_plan_artifacts.py
- test_plan_store_routing.py
- _build_parser
- Path
- Multi-Perspective Review
- Backlog Item Groomer Agent
- discover_repo
- Check
- sam_task_create
- _Predicate
- assemble_graph.py
- Backlog Item Lifecycle — Canonical Reference
- github_client.py
- _RECONCILIATION_NOT_IMPLEMENTED
- _build_ssl_context
- ledger_spec.py
- cli.py
- _InMemoryArtifactBackend
- test_backlog_groom_sections.py
- test_migrate_tasks_to_github.py
- test_rtica_verdict_vocabulary_drift.py
- MockerFixture
- RepoDiscoveryError
- backlog_core/tests/conftest.py
- _make_snippet_parts
- DH Workflow Graph — Data Schema
- Blind completeness audit — the workflow multigraph
- TestTaskFieldValidators
- test_agent_profile/conftest.py
- test_github_tools_labels.py
- SOP (Code Review)
- bundle_requires_relaxed_verification
- parse_jsonl_events
- test_single_item_status_refusal.py
- test_status_source_wire.py
- Instruction
- Node
- TestBuildIssueBodyFromFileDict
- Groom Milestone
- dispatch_task
- Context Refinement Agent
- ecosystem-researcher.md
- feature-researcher.md
- dispatch_state.py
- TestSelectorAndSlugGeneration
- Artifact Conventions
- TestStatusMap
- _load_frontmatter_from_path
- Planner RT-ICA (Planning-Phase Input Completeness Analysis)
- test_ledger_spec.py
- Path
- Context-Gathering Agent
- .verify_legacy_item
- merge_integration_branch
- _validate_slug
- make_github_client
- find_content_duplicates
- TestCodeBlocks
- Cursor agent (IDE Agent mode + `agent` / `cursor-agent` CLI) — harness facts
- Model fidelity — the workflow multigraph against `ledger_spec.py` and `sam_schema/core/models.py`
- .__init__
- Structured SAM Commands
- Groom: Swarm
- test_cli.py
- Path
- TestChunkText
- TestCommitPrefixRegex
- TestLegacyPathMap
- test_network_guard.py
- test_retired_terms.py
- Development Harness Plugin - AI-Facing Documentation
- Performance Reviewer Agent
- _validate_metadata
- _make_struck_sections
- Any
- Findings — finding verification: the falsified predicates, and the severity rule
- ledger_holds
- SAM Stage 5 — Execution
- Workflow: Create Backlog Item
- TestRealPluginsIntegration
- Path
- Documentation Drift Auditor
- _discover_via_env
- TestParentChildRelationships
- TestBodySpanBoundaries
- dh_config.py
- validator.py
- Groomed
- TestTaskStatusEnum
- _call
- TestEndToEndQueryToResult
- SOP
- resolve_ca_bundle
- Refusal
- Findings: producers without consumers between grooming and the bookends
- MCP Progressive-Disclosure Contract
- Backlog Lifecycle Process Audit
- DH Workflow Trace — Collection Methodology
- run_bounded.py
- field_validator
- What You Get
- Complete Implementation (Quality Gates + Recursion)
- Default Development Flow
- Human Touchpoint Model
- TestMilestoneHeaderConstruction
- SOP
- github_branches.py
- BranchConflictError
- ContentDuplicateMatch
- _provider_with_mock_runner
- TestUnknownTimestampSurvivesSinceFilter
- compute_slug
- Normative requirements
- Package map
- development-harness
- _CommentEntryLike
- SAM Stage 7 — Final Verification
- Verdict Schema — Multi-Perspective Review
- Setup Skill Discovery Wizard
- test_ac_overlap_warning.py
- TestBackendAvailabilityEnum
- TestIsNotFoundError
- test_placeholder_vocabulary_drift.py
- contract-verification.md
- _build_artifact_content_comment
- test_github_branches.py
- search.py
- Development Harness Backend Providers
- Harness facts: Hermes Agent (Nous Research)
- Harness facts: Kilo Code (Kilo CLI / Kilo Code VS Code extension, Kilo-Org/kilocode)
- test_high_level_storage_boundaries.py
- Working in dh Workflow Files
- NormalizedEntry
- TestParentIssueNumberValidator
- SAM Stage 1 — Discovery
- scripts/task_format.py
- Investigation Procedure
- _backlog_ops
- test_server_sam.py
- Classifier
- scan_all_agents
- Fact Checker Agent
- Security Reviewer Agent
- resolve_token
- _parse_comment_node
- delete_integration_branch
- bundle_adds_new_anchor
- _ProxyAwareAdapter
- model_validator
- build_concept_query
- assemble
- Context-Fit Complexity: Adoption Conditions
- evidence-discipline.md
- DH work ledger — plan
- Fact Check — Primary Source Claim Verification
- SAM Stage 6 — Forensic Review
- Verification Protocol
- Groom: Finalize
- Work: Validate (Phase 2)
- TestArtifactEntryModelValidation
- run_loop
- test_the_first_failing_check_is_the_one_the_spec_puts_first
- TestModels
- test_reconciliation.py
- TestReconcileOpenItem
- setup-github/start.md
- helpers.py
- TestResolveVerifiedGate
- integration-checker.md
- RT-ICA Assessor
- infer_type
- _parse_frontmatter
- Per-Stage Detail
- SAM Stage 2 — Planning
- work/start.md
- test_server_pep723_header_omits_typer
- Task
- MonkeyPatch
- test_server_descriptions.py
- test_status_token_vocabulary_drift.py
- Alignment Analyst
- create_integration_branch
- _validate_milestone_number
- _make_connection_class
- MockerFixture
- test_section_boundary_scanner_live_3152.py
- _token_count
- _filter_sections_isolated
- track_sqlite_connections
- _build_graph_dict
- Plan and Artifact Lifecycle
- Operational Principles
- conftest.py
- OpenAI Codex CLI harness facts
- OpenCode harness facts
- Workflow
- Kage Bunshin — Persistent Peer Claude Sessions
- test_main_explicit_session_id_overrides_env_var
- _run_probe
- TestConflictGroupConstruction
- TestMCPIncludeClosedPropagation
- test_prepare_clean_worktree.py
- SOP
- service-docs-maintainer.md
- test_artifact_migration.py
- _validate_repo_slug
- build_body_extra_only
- BacklogItem
- _manifest_reference
- ARL Meta-Layer: Observation Layer (Improvement Meta-Process)
- layer-1/README.md
- self_check
- Harness facts: pi (pi coding agent)
- Workflow
- /dh:interop — Superpowers Plan Interop Adapter
- command-routes.schema.json
- NetworkBlocked
- TestParseAddressPNNN
- _extract_import_roots
- test_sync_groomed_entry_block_roundtrip.py
- _parse_full_database_id
- _entry_owning_headers
- test_since_filter_bad_entry_id.py
- TestItemDerivedStatusUnavailableMap
- ADR-9: Close/Resolve Semantic Redesign
- ADR-1770-1: Single-Writer Contract for TaskBackend.append_task and finalize_plan
- Backlog Item Groomed Schema
- locate.md
- GraphQL Usage Guide — Backlog MCP Sync
- Task Worker
- addressing.py
- run_sam_server.py
- Ecosystem Research
- TestPlanNumberResolutionPropertyBased
- TestSlugResolutionPNNN
- test_sam_task_create_without_skill_succeeds
- TestPriorityEnum
- TestErrorPaths
- TestRecursionGuardScenarios
- TestShouldSkipHook
- workflow-extractor-reducer.md
- _UnionFind
- Work: Plan (Phase 4)
- extract_description_from_issue_body
- AI Agent Swarm Coordination Planner
- build_issue_body
- merge_sections
- SyncClaim
- layer-0/README.md
- Evaluation Checklist
- test_comment_database_id.py
- TestParsingCarriesTheIdentifier
- TestTheModelItselfRejectsANonIntDatabaseId
- Plugin Deployment Model — The Zip-and-Move Test
- Design Brief: Unified Section Layer for `backlog_core`
- Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code)
- Amendments to the findings files
- get_task_context.py
- Close / Resolve Procedure (Phase 5)
- TestTaskIdPattern
- Persistent Agent Memory
- Technical Researcher
- _extract_content_from_comment
- .view_enrich_from_github
- _run_spawn_item
- _live_issue_wearing_an_emoji_label
- TestProbeBackendStatusHonorsEveryTokenVariable
- TestFixtureHasThePathology
- _drift_view_result
- TestNarrowBodyToNamedSectionsUnit
- TestRootSectionOrdering
- Claims register — development-harness
- LayerData
- Development Harness Purpose
- Harness facts: Claude Code
- Gate Push
- Subcommand Reference
- Research Note
- Workflow: Groom Backlog Item
- TestArtifactManifestModelValidation
- TestComplexityEnum
- TestTaskEnumCoercion
- TestParseCommentNode
- TestEmptyCommandList
- TestQualityGatesConstruction
- TestSemanticQueryCorpus
- test_tool_output_schemas.py
- tn-verification-gate.md
- TestViewItemReturnsTenSectionsNotFortySix
- test_a_plan_update_reports_a_dropped_connection_instead_of_raising
- Workflow Extraction Rules
- _resolve_repo_with_timeout
- .list_plans
- .validate_parent_issue_number
- resolve_task_id
- Recursive Follow-up Handling: Steps 2–5
- Groomed items — staleness check
- SAM (Stateless Agent Methodology) — Definition
- plan_dir
- TestBacklogErrorIsBase
- .test_git_common_root_closes_repo_object
- t0-baseline-capture.md
- TestPrewrappedContentSurvivesBodyRoundTrip
- TestFalsification
- .test_compact_valid_section_name_not_miss_and_metadata_filtered
- ADR-3113-1: Dispatch roles name scope, not capability, and enforcement sits with the dispatcher
- _emit_skill_handoff
- Beads and development-harness usage
- run_live_validation_skill.py
- Backend Resolution
- Read the Code Review Verdict
- Output Event Types
- Error Categories
- Workflow: Groom Drift Check
- test_backend_factory_import_order
- sample_github_body.md
- TestSamClaimParser
- TestToolRegistration
- test_backlog_list_passes_output_instance_to_operations
- TestMergeIntegrationBranchValidation
- ADR-3072-1: Budget applies only at the Navigation stage
- session-end-kage-bunshin-child-notify.cjs
- session-end-kage-bunshin-cleanup.cjs
- stop-kage-bunshin-child-notify.cjs
- stop-kage-bunshin-idle-check.cjs
- task-completed-kage-bunshin-reminder.cjs
- Planning Tools
- Quality Gate Plan Creation
- Generate Task (Worker Task Prompt)
- TestParseTaskContentRawYaml
- Stream-JSON Protocol Reference
- complete-implementation/SKILL.md
- Development Harness — Plugin Overview and Skill Router
- Experiment Log: Sequential Resume (2026-03-22)
- Experiment Log: Stream-JSON Multi-Turn (2026-03-22)
- DispatchStateManager
- Team Health Check
- Monitoring spawned sessions
- test_cmd_list_shows_alive_and_dead_sessions
- test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case
- test_output_fields_always_present_on_error
- test_default_test_paths_match_pyproject_testpaths
- AGENTS.md
- .__get_pydantic_json_schema__
- _reset_config
- TestZeroIdSentinelIsDetectable
- test_import_boundaries.py
- TestOperationsDoesNotImportFromGithubSync
- TestPLRLintGate
- test_init_docstring.py
- Hook Subprocess Invocation
- SDLC Layer Separation Architecture
- DH Workflow Map — Coverage Manifest
- DH Plugin Known Entities
- SCOPE.md
- pytest_runtest_protocol
- Config
- MCP Servers
- Recursive Follow-up Handling
- gen_run_stamp.py
- Groom finalize hardening provenance
- test_unknown_backend_name_refuses_as_a_backlog_error
- run_pytest.py
- milestone_existing_and_leased
- test_artifact_provider_fallback.py
- test_guard_covers_testpath
- TestCreateBacklogItem
- .discard_pending
- _OrPred
- _parse_args
- TestInitAlias
- TestBacklogConfigDataclass
- _mock_get_encoding
- .code
- .check_reference_integrity
- .has_more
- .__init__
- Apply status:verified Label
- dh Glossary
- Milestone Dispatch Patterns
- Skill maintenance
- test_canonical_plan_id_leaves_a_non_uid_id_unchanged
- test_backlog_add_output_messages_included
- test_resolve_all_entry_ids_property_ids_are_always_pairwise_distinct
- test_resolve_all_entry_ids_never_produces_duplicate_ids
- backlog_core/backends/__init__.py
- _read_enabled_from_config_file
- backlog_core/tests/__init__.py
- integration/__init__.py
- TestUnknownAttributeRaises
- dh_core/__init__.py
- dispatch_schema/core/__init__.py
- dispatch_schema/readers/__init__.py
- dispatch_schema/writers/__init__.py
- inject-style-guide.cjs
- session-start-session-id.cjs
- core/backends/__init__.py
- sam_schema/core/__init__.py
- .__init__
- sam_schema/readers/__init__.py
- sam_schema/writers/__init__.py
- prepare_clean_worktree.sh
- dispatch-contract/SKILL.md
- file-classification/SKILL.md
- file-classification/SKILL-GOALS.md
- meta-workflow-graph-refresh/SKILL.md
- github-integration-validation.md
- progress/start.md
- Add New Feature (SAM Workflow)
- Analyze Test Failures
- Workflow
- resume/start.md
- loop-plan/README.md
- tests_sam/__init__.py
- scripted_runner_lib/__init__.py
- CLEAR + CoVe Task Design for Agent Swarms
- SOP (Architecture Audit)
- Claude Skills and Agent Code Review Patterns
- CLI Application Code Review Patterns
- LLM Integration Code Review Patterns
- Node.js Code Review Patterns
- Python Code Review Patterns
- TypeScript Code Review Patterns
- Web Frontend Code Review Patterns
- Codebase Auditor
- Codemod Runner
- plan_dir
- test_append_task_stdin_combined_with_typed_option_is_rejected
- Workflow
- Comprehensive Test Review
- SAM Stage 3 — Context Integration
- Create Artifact
- test_list_returns_json_with_items_count_total
- File-to-Stack Mappings
- skill_discovery.yaml — Schema Reference
- Skill Marketplace Search Reference
- Wizard Questions Reference
- test_list_items_contain_expected_fields
- Implement Feature (SAM Workflow Execution)
- SAM Stage 4 — Task Decomposition
- Test Failure Analysis Mindset
- Fix Validation Protocol
- test_list_search_filters_by_feature_name
- impact-analyst.md
- test_list_search_no_match_returns_empty_items
- test_read_returns_task_assignment_json_with_task_address
- test_read_task_assignment_includes_plan_fields
- test_read_uses_slug_address
- work/rt-ica-gate.md
- test_read_plan_only_address_returns_plan_json
- test_read_plan_only_address_reads_the_ledger_once_it_holds_the_plan
- test_read_nonexistent_plan_exits_with_code_1
- test_read_nonexistent_task_exits_with_code_1
- Data Pipeline Optimization - Task Plan
- Bold Fields Test Plan
- test_read_missing_plan_dir_exits_with_code_1
- test_status_returns_json_summary
- test_status_nonexistent_plan_exits_with_code_1
- Enhance Skill Research Process
- Complete ty Skill Implementation
- test_ready_nonexistent_plan_exits_with_code_1
- Context Manifest
- yaml_frontmatter_single.md
- Tasks: Widget Overhaul Follow-up
- test_state_missing_task_component_exits_with_code_1
- test_state_nonexistent_task_exits_with_code_1
- test_state_output_shows_old_and_new_status
- test_migrate_nonexistent_plan_exits_with_code_1
- test_validate_canonical_plan_reports_valid
- test_agent_profile/__init__.py
- test_backlog_sync_success_returns_counts
- test_backlog_sync_backlog_error_returns_error_key
- test_backlog_close_success_returns_closed_item
- test_backlog_close_backlog_error_returns_error_key
- test_backlog_resolve_success_returns_resolved_item
- test_backlog_resolve_passes_cleanup_and_force
- test_backlog_update_passes_status
- test_backlog_update_passes_title
- test_backlog_groom_backlog_error_returns_error_key
- test_backlog_normalize_success_returns_count
- test_backlog_normalize_backlog_error_returns_error_key
- test_backlog_pull_passes_dry_run_and_force
- test_backlog_pull_backlog_error_returns_error_key
- test_backlog_pull_with_issue_number_selector_calls_pull_by_selector
- test_backlog_pull_selector_error_returns_error_key
- test_backlog_add_backlog_error_returns_error_key
- test_backlog_sync_no_error_key_on_success
- test_backlog_list_type_and_topic_default_to_none
- test_backlog_list_count_only_carries_provenance_with_pending_writes
- test_backlog_list_count_only_false_returns_full_response
- test_backlog_list_match_context_true_returns_matches_key_per_item
- test_backlog_list_match_context_body_match_attributed_to_named_section
- test_backlog_list_match_context_match_entry_has_required_keys
- test_backlog_list_snippet_context_parameter_accepted
- test_backlog_list_item_depth_one_adds_description_snippet
- test_backlog_list_item_depth_one_adds_section_names
- test_backlog_list_item_depth_two_adds_section_first_lines
- test_backlog_list_dedup_same_issue_number_appears_once
- test_backlog_list_dedup_hash_prefix_stripped
- test_backlog_list_pagination_last_page_has_more_false
- test_backlog_list_match_pagination_message_on_page1
- test_backlog_list_fields_nonexistent_field_returns_warning_or_error
- test_backlog_create_sam_task_forwards_repo
- .setup_method
- .setup_method
- .setup_method

## God Nodes (most connected - your core abstractions)
1. `BacklogItem` - 702 edges
2. `Output` - 570 edges
3. `BacklogError` - 327 edges
4. `InMemoryBackend` - 283 edges
5. `ContentRef` - 282 edges
6. `ViewItemResult` - 262 edges
7. `ContentRecord` - 243 edges
8. `ContentWrite` - 240 edges
9. `GitHubBackend` - 234 edges
10. `ArtifactManifest` - 219 edges

## Surprising Connections (you probably didn't know these)
- `test_patch_result_rejects_unknown_status()` --uses--> `PatchResult`  [INFERRED]
  tests_backlog/test_reconciliation_models.py → backlog_core/models.py
- `tracked_connect()` --calls--> `connect()`  [INFERRED]
  conftest.py → dh_core/ledger/store.py
- `fetch_milestones()` --indirect_call--> `milestones()`  [INFERRED]
  tests/test_github_tools_milestones.py → sam_schema/backlog.py
- `TestProfileList` --uses--> `AgentMetadata`  [INFERRED]
  tests/test_agent_profile/test_server.py → agent_profile/models.py
- `dispatch_stale_check()` --calls--> `require_github_extras()`  [INFERRED]
  dh_core/operations.py → backlog_core/_capability_gates.py

## Import Cycles
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/github_backend.py -> backlog_core/github_sync.py -> backlog_core/__init__.py`
- 5-file cycle: `backlog_core/__init__.py -> backlog_core/_branch_delegates.py -> backlog_core/backend_protocol.py -> backlog_core/backends/beads_backend.py -> backlog_core/github_sync.py -> backlog_core/__init__.py`

## Communities (736 total, 102 thin omitted)

### Community 0 - "backlog_core/models.py"
Cohesion: 0.01
Nodes (365): Backend-agnostic contracts for backlog implementations., In-memory test double implementing the backend Protocols. This module provides…, Upsert a work item under its stable reference. ``BacklogItem``'s…, _now(), _P, _T, SQLite-backed implementation of the backend Protocols. Stores all backlog state…, Update a comment's body. Args: repo: Ignored. comment_node_id: UUID string of… (+357 more)

### Community 1 - "._mutate"
Cohesion: 0.12
Nodes (11): _MutationResult, PlanUpdateValue, Atomically reassign plan ownership., Update and persist plan fields., Claim and persist a task. Returns: Whether the task was claimed., Update and persist task status., Update and persist task fields., Replace and persist a task. (+3 more)

### Community 2 - "Entry"
Cohesion: 0.01
Nodes (278): Render a GroomedData as ``## Groomed ({date})`` with subsection children. Args:…, _deduplicate_timestamps(), Suffix duplicate IDs in-place with ``-0``, ``-1``, etc. A generated suffix must…, Suffix duplicate timestamp IDs in-place with ``-0``, ``-1``, etc. Returns:…, Return *stored_ids* with duplicate-id collisions suffixed the way backlog_view…, Reconstruct the raw HTML entry block from a parsed Entry. Used when the…, _render_entry_raw(), resolve_all_entry_ids() (+270 more)

### Community 3 - "_ContentsRepository"
Cohesion: 0.07
Nodes (13): _Branch, _Commit, _ContentsFile, _ContentsRepository, _GitHubContentIntegrityError, _GitTree, _GitTreeEntry, ContentRecords (+5 more)

### Community 4 - "TaskStatus"
Cohesion: 0.01
Nodes (279): LiteralScalarString, PlanUpdateValue, Update top-level fields on a plan. Args: plan_id: Backend-assigned plan…, Dependency graph with cycle detection and task readiness queries. Builds a…, Lifecycle status values for a SAM task., TaskStatus, claim_task(), create_plan() (+271 more)

### Community 5 - "gh_client.py"
Cohesion: 0.01
Nodes (280): AssigneeNode, IssueNode, LabelNode, MilestoneFullNode, MilestoneNode, datetime, TypedDict, Milestone from GraphQL query with issue counts. (+272 more)

### Community 6 - "Output"
Cohesion: 0.01
Nodes (178): Raise NotImplementedError — beads does not use PyGithub Repository. The…, Raise NotImplementedError — beads IDs are strings. The Protocol signature uses…, Return the current status string for a beads issue. Uses ``item.issue`` as the…, Claim a beads issue via ``bd update --claim``. Args: item: BacklogItem whose…, No-op — beads has no dedicated verified lifecycle state. Args: item: Ignored.…, No-op — beads has no dedicated groomed lifecycle state. Args: item: Ignored.…, No-op — string-ID backends get blocked status written locally.…, Create a backend issue from a BacklogItem. Returns: Issue number on success, or… (+170 more)

### Community 7 - "ContentTaskProvider"
Cohesion: 0.01
Nodes (320): _ActionConfigBase, AppendTaskConfig, ClaimTaskConfig, ClearActiveTaskConfig, CreatePlanConfig, FinalizePlanConfig, GetActiveTaskConfig, BaseModel (+312 more)

### Community 8 - "GitHubBackend"
Cohesion: 0.02
Nodes (130): AddedCommentNode, Result of creating a comment via the ``addComment`` mutation. ``id`` is…, GitHubBackend, datetime, Return a PyGithub Repository (raises GitHubUnavailableError on failure).…, Check backend availability and return a status report. Returns: BackendStatus…, Report whether a GitHub token is configured for this backend. This provider-…, List work items from the provider-private cache. Returns: Persisted work items. (+122 more)

### Community 9 - "ContentRef"
Cohesion: 0.02
Nodes (201): Return a bounded cache-backed discovery page for GitHub content. Returns: The…, Read authoritative GitHub content or an explicitly stale cached copy. Returns:…, Write GitHub content, durably queueing it while GitHub is offline. Returns: The…, Enumerate authoritative content merged with the legacy stores. Returns: Every…, Read authoritative content, falling back to the legacy stores. Returns: The…, Write content, migrating a legacy record into the Contents API when needed.…, _OnlineContent, _PlanPersistence (+193 more)

### Community 10 - "cli_active_task.py"
Cohesion: 0.12
Nodes (29): Reject a missing, empty, or sentinel session id for an active-task operation.…, require_session_id(), active_task_clear(), active_task_get(), active_task_set(), active_task_update(), _context_backend(), _plan_backend() (+21 more)

### Community 11 - "LocalYamlTaskProvider"
Cohesion: 0.01
Nodes (205): DocumentBackend, GitHubTaskProvider, _has_cycles(), dfs(), _is_ready(), _node_to_task_data(), _parse_metadata(), Any (+197 more)

### Community 12 - "GistTaskLayer"
Cohesion: 0.01
Nodes (226): ArtifactRegistryClient, _get_provider(), PlanContentUnavailableError, PlanIndexUnavailableError, Thin wrapper decoupling GistTaskLayer from the backlog_core artifact surface.…, Initialise with an optional pre-constructed provider. Args: provider: Artifact…, Return the provider, creating it lazily on first call. Returns: The configured…, Upload plan YAML to GitHub Gist via the artifact registry. Registers a manifest… (+218 more)

### Community 13 - "SyncState"
Cohesion: 0.02
Nodes (122): allow_startup_sync, _backlog_lifespan(), _build_sync_state_block(), _log_sync_task_exc(), Task, Done-callback: log any unexpected exception that escapes the sync task. An…, Retain a strong reference to *task* and wire its done-callbacks. Args: task:…, Return True when the startup sync should run (default: True). Reads… (+114 more)

### Community 14 - "test_beads_models.py"
Cohesion: 0.04
Nodes (111): Fetch a beads issue and extract its artifact manifest in one call. Issues a…, Return a mapping of open beads issue titles to beads IDs. This is the beads-…, Create a beads milestone issue via ``bd create --type milestone``. Args: title:…, BeadsCommentRaw, BeadsDependencyRaw, BeadsIssueRaw, BeadsIssueType, BeadsLabelRaw (+103 more)

### Community 15 - "backlog_list"
Cohesion: 0.03
Nodes (83): alias, _apply_fields_projection(), _apply_item_depth(), _apply_sync_state_to_response(), _assert_config(), backlog_list(), _build_count_only_response(), _dedup_by_issue_number() (+75 more)

### Community 16 - "Section"
Cohesion: 0.01
Nodes (219): A named section within a backlog item containing an ordered list of entries., Section, _assemble_view_compact(), _build_sections_from_yaml_item(), _compact_entry_count(), _filter_sections(), groom_item(), _int_field() (+211 more)

### Community 17 - "sam_schema/core/models.py"
Cohesion: 0.01
Nodes (198): clear_active_task(), get_active_task(), Retrieve the active task context for a session. This is the unified operation…, Store a task address as the active task for a session. This is the unified…, Remove the active task context for a session. This is the unified operation…, set_active_task(), ListPlansConfig, field_validator (+190 more)

### Community 18 - "FileCache"
Cohesion: 0.03
Nodes (200): GitHubBackend — the composition root for the GitHub work-item provider. This…, Fetch one normalized bounded GitHub snapshot for reconciliation. Returns:…, Apply optimistic GitHub body patches and return one outcome per patch. Returns:…, _GitHubReconciliation, _GitHubWorkItemSync, Work-item snapshot and reconciliation collaborators for the GitHub backend. Two…, Provider snapshot and patch operations the reconciliation cycle drives.…, Translate GitHub issues into provider snapshots and apply provider patches. (+192 more)

### Community 19 - "test_ledger_port.py"
Cohesion: 0.02
Nodes (198): Return a placeholder string proportional to the token count., check_commands(), The map from a ``ledger_spec.COMMANDS`` name to the callable that implements…, Reject a surface that does not match ``ledger_spec.COMMANDS`` one to one.…, The DH work ledger: one SQLite database per repository holding every SAM plan…, clear_plan(), clearable_tables(), conflict_groups_for() (+190 more)

### Community 20 - "_entry_ordinal_for_sub_heading"
Cohesion: 0.16
Nodes (12): _heading_path(), given, settings, Build a nested heading ordinal the way OrdinalPathMapper does. Mirrors the…, Property: every ordinal string the generators can produce matches…, A sub-heading ordinal, at any nesting depth, matches the validator regex., A code-fence ordinal, attached to the root or any nested heading, matches the…, TestOrdinalGeneratorValidatorAgreement (+4 more)

### Community 21 - "test_ledger_conformance.py"
Cohesion: 0.03
Nodes (198): Read one plan's tasks with their derived columns and the plan's progress. Args:…, status(), What one command does from one status: checks in order, then effects and events., Transition, accept_complete(), accept_refusal(), build(), accept_returned() (+190 more)

### Community 22 - "OrdinalPathMapper"
Cohesion: 0.02
Nodes (127): NormalizedSection, One section in document-order, with its ordered entries., StatusSource, Fetch item content and dispatch to the appropriate disclosure handler. Calls…, Build a structural map response. ``MapResponse.total_est_tokens`` sums LEVEL-1…, Resolve an ordinal to full section/entry content (§4.4 NAVIGATE). Implements…, Extract a token-bounded window from a section/entry (§4.4 EXTRACT). For sub-…, BoundedResponse (+119 more)

### Community 23 - "verify_migration_fidelity.py"
Cohesion: 0.06
Nodes (51): ClassificationT, _classify(), _classify_by_token_sets(), _compute_diff(), _extract_bak_body(), _extract_content_tokens(), FileResult, main() (+43 more)

### Community 24 - "ArtifactManifest"
Cohesion: 0.02
Nodes (145): artifact_content_reference(), Return the immutable content identity referenced by an artifact entry. The…, ArtifactRegistry, Render an ``ArtifactManifest`` as a delimited markdown section. Produces the…, Replace the manifest section in an issue body, or append it if absent.…, Stateless business-logic layer for artifact manifest operations. All methods…, Upsert an artifact entry into the manifest. Upsert logic: - If an existing…, Return all entries matching *artifact_type*. Args: manifest: Manifest to query.… (+137 more)

### Community 25 - "BacklogError"
Cohesion: 0.03
Nodes (195): BacklogError, Response shape returned by the ``artifact_register`` MCP tool. Indicates…, General backlog operation error., RegisterResult, artifact_get(), artifact_list(), artifact_read(), artifact_register() (+187 more)

### Community 26 - "BeadsBackend"
Cohesion: 0.02
Nodes (128): _BdRunnerLike, _beads_content_lock(), _beads_priority_for_item_priority(), _beads_status_for_item_status(), _beads_type_for_item_type(), _beads_workspace_path(), BeadsBackend, JsonValue (+120 more)

### Community 27 - "BeadsArtifactProvider"
Cohesion: 0.02
Nodes (91): BackendName, create_artifact_provider(), StrEnum, Create an ArtifactBackend provider based on backend config. Args: backend_name:…, Canonical identifiers for pluggable artifact storage backends., BeadsArtifactProvider, ItemId, Path (+83 more)

### Community 28 - "InMemoryBackend"
Cohesion: 0.02
Nodes (91): InMemoryBackend, datetime, In-memory backend for use in tests. All state lives in plain Python dicts and…, Report whether any mutation is queued and unacknowledged. Always ``False`` —…, Initialise empty in-memory storage for all backend state., List native in-memory work items., Get a work item by its stable reference., Return REACHABLE status — in-memory backend is always available. (+83 more)

### Community 29 - "navigator.py"
Cohesion: 0.03
Nodes (93): TDD tests for AmbiguousSectionRefError on slug collision in resolve_section().…, document(), fixture, TEST C3: MarkdownIndexer.build() decomposition gate + behavioral equivalence.…, Build and return a MarkdownDocument from _CHARACTERIZATION_MD., CodeBlockExtractor, CodeBlockStubRenderer, Code block extraction and stub rendering. Provides CodeBlockExtractor for post-… (+85 more)

### Community 30 - "test_disclosure_handler.py"
Cohesion: 0.03
Nodes (126): _build_entries(), _is_entry_section_metadata(), ItemContentNormalizer, NormalizedEntry, _parse_section_titles(), TypeGuard, Normalize ViewItemResult into an ordered list[NormalizedSection]. Single…, Return ``True`` when *section* is ``SectionEntryMetadata``. Discriminates the… (+118 more)

### Community 31 - "BacklogConfig"
Cohesion: 0.02
Nodes (118): Register the active BacklogConfig. Args: config: BacklogConfig instance…, Clear the cached BacklogConfig singleton. Intended for test teardown — call…, reset_config(), set_config(), BacklogConfig, Container for the active backend instance. This dataclass replaces direct…, BacklogConfig, Immutable configuration bundle set once at server startup. Attributes:… (+110 more)

### Community 32 - "WorkItemBackend"
Cohesion: 0.02
Nodes (77): Protocol, Generic work-item surface every backend must implement. Methods take and return…, Report whether the most recent listing includes locally-queued mutations. Every…, Optional capability: report whether a cache has ever completed a sync.…, Optional capability: report whether the last snapshot load skipped any file.…, SnapshotCheckpointProvider, SnapshotCompletenessProvider, WorkItemBackend (+69 more)

### Community 33 - "dh_paths.py"
Cohesion: 0.03
Nodes (96): Read ``backlog.startup_sync.enabled`` from .dh/config.yaml files. Returns the…, _read_startup_sync_enabled_from_yaml(), context_dir(), _dh_user_root(), ensure_dirs(), _first_git_ancestor(), _get_dh_user_root(), _git_common_root() (+88 more)

### Community 34 - "make_task"
Cohesion: 0.03
Nodes (100): BookendValidator, DependencyGraph, dfs(), _dfs(), Check whether the dependency graph contains any cycles. Uses a DFS-based three-…, Return all dependency cycles as lists of task IDs. Each cycle is represented as…, Return tasks that are blocked by unsatisfied dependencies. A task is *blocked*…, Mark transitive downstream tasks as skipped after an upstream failure. Performs… (+92 more)

### Community 35 - "_Repository"
Cohesion: 0.02
Nodes (59): GitHubExtras, Any, GitHub-specific surface only ``GitHubBackend`` implements. Backends that are…, Return None — beads does not use PyGithub Repository., Raise NotImplementedError — beads IDs are strings. Use…, Raise NotImplementedError — beads does not use PyGithub Repository. No beads…, Any, Return a PyGithub Repository, or None when credentials are absent. Returns:… (+51 more)

### Community 36 - "beads.py"
Cohesion: 0.02
Nodes (80): BdJsonDecodeError, BdNotInstalledError, Lazy subprocess wrapper for the bd (beads) CLI. All subprocess I/O is…, ``bd`` stdout could not be parsed as JSON. Attributes: raw_output: Raw stdout…, ``bd`` binary is not on ``PATH``. Callers catching this exception should…, BeadsContextBackend, BeadsTaskProvider and BeadsContextBackend — beads (bd CLI) backend for SAM.…, ContextBackend persisting active-task context via bd remember. Context is… (+72 more)

### Community 37 - "BacklogItemMetadata"
Cohesion: 0.02
Nodes (67): Parse a markdown body into a BacklogItem. Returns existing unchanged when…, Deserialise a JSON body string into a BacklogItem. Args: body: Raw body string…, BacklogItemMetadata, field_validator, Typed metadata fields for a backlog item, persisted to YAML frontmatter. All…, Normalise and accept priority values, preserving unknown strings verbatim.…, Normalise and accept item_type values, preserving unknown strings verbatim.…, Accept any non-empty status string, preserving unknown values verbatim. Writers… (+59 more)

### Community 38 - "store.py"
Cohesion: 0.03
Nodes (128): Cursor, Read one plan and report its structural problems. Nothing here refuses: a…, validate(), Column, One column of a materialised table., add_column_ddl(), admits_integer(), affinity() (+120 more)

### Community 39 - "test_task_status_hook.py"
Cohesion: 0.03
Nodes (125): _call_sam_cli(), _call_sam_plan_settle(), extract_launch_from_prompt(), _extract_prompt_from_transcript(), _extract_text_from_user_record(), _first_nonempty_line(), _first_text_block(), _get_uv_executable() (+117 more)

### Community 40 - "_extract_response_dict"
Cohesion: 0.05
Nodes (55): _extract_response_dict(), _find_rt_ica_ordinal(), _find_subheading_entry_ordinal(), MockerFixture, _skip_without_2515, _skip_without_real_enc, navigate=N.M.code.0 content is raw fence body without ``` delimiters. Verifies…, TC-T9: navigate=N.M.code.99 produces the same error shape as numeric miss. ADR… (+47 more)

### Community 41 - "transitions.py"
Cohesion: 0.04
Nodes (124): json_list(), now(), Return the current instant as naive UTC at second precision. Returns: The…, Decode a JSON array column into a list of strings. Args: raw: The stored column…, Run a block inside one ``BEGIN IMMEDIATE`` transaction. The write lock is taken…, transaction(), accept(), append() (+116 more)

### Community 42 - "ContentUnavailableError"
Cohesion: 0.03
Nodes (77): Return the requested bounded page from the native Beads KV store., Initialise with an optional default repo string. Args: repo: Optional…, _GitHubContentCache, _GitHubContentMigration, Content migration orchestration for the GitHub backend. Two collaborators split…, Enumerate authoritative content for a query, merged with legacy records.…, Read authoritative content, falling back to the legacy stores. Returns: The…, Read one content record from the stores that predate the Contents API. Returns:… (+69 more)

### Community 43 - "BeadsTaskProvider"
Cohesion: 0.04
Nodes (78): BeadsTaskProvider, TaskBackend implementation routing SAM plan/task operations to the bd CLI.…, fake_runner(), _FakeBdRunner, list_show_runner(), _ListParentBdRunner, _ListShowBdRunner, make_task_record() (+70 more)

### Community 44 - "FormatType"
Cohesion: 0.03
Nodes (113): A missing or invalid field detected during legacy format reading. Schema gaps…, SchemaGap, FormatType, StrEnum, Supported task/plan file formats., detect_gaps(), _detect_gaps(), normalize_plan() (+105 more)

### Community 45 - "backlog_core/operations.py"
Cohesion: 0.01
Nodes (397): get_config(), Return the active BacklogConfig, auto-initialising on first call. Resolution…, Optional one-method reconciliation capability for remote backends., SyncProvider, Shared capability gates for optional backend protocol subsets. ``GitHubExtras``…, Return ``backend`` narrowed to ``GitHubExtras``, or raise if unsupported. Args:…, Return ``backend``, or raise if it does not support milestones. Unlike…, require_github_extras() (+389 more)

### Community 46 - "BacklogViewDisclosureHandler"
Cohesion: 0.04
Nodes (74): BacklogViewDisclosureHandler, Orchestrate progressive disclosure modes from un-gated item content.…, NavigateResponse, BaseModel, Response for ``navigate=ordinal`` without ``head``. When ``has_children`` is…, _find_rt_ica_ordinal(), MockerFixture, _skip_without_2515 (+66 more)

### Community 47 - "progressive_markdown/__init__.py"
Cohesion: 0.03
Nodes (88): disclosure(), fixture, Pin NavigationResult return contract for ProgressiveDisclosure.select() and…, page() must return NavigationResult (architect §4.1.1). PRE-FIX STATE: FAILS.…, paginate_results() must retain its legacy dict return shape — unchanged by C1.…, NavigationResult.model_dump() must produce a complete serialisable dict.…, ProgressiveDisclosure instance over three sample task items., select() must return NavigationResult when the item is found (architect… (+80 more)

### Community 48 - "WaveItem"
Cohesion: 0.03
Nodes (84): CommandResult, _DispatchBase, GateResult, GateRunMode, ItemPriority, ItemStatus, MilestoneHeader, BaseModel (+76 more)

### Community 49 - "ArtifactType"
Cohesion: 0.05
Nodes (72): _get_migrate_yaml(), _migrate_classify_plan_file(), _migrate_coerce_issue(), _migrate_discover_candidates(), migrate_dry_run(), _migrate_extract_issue(), _migrate_find_issue_via_backlog(), migrate_live_run() (+64 more)

### Community 50 - "LocalFilesystemArtifactProvider"
Cohesion: 0.03
Nodes (71): LocalFilesystemArtifactProvider, ItemId, Path, Local filesystem implementation of the ArtifactBackend protocol. Stores…, Persist *manifest* for *item_id* atomically. Acquires an exclusive advisory…, Read artifact file content from the root worktree. Args: path: Repo-relative…, Store artifact content as a file in the repository worktree. Writes content…, Read artifact content. This provider has no remote backend. Delegates to… (+63 more)

### Community 51 - "test_artifact_provider.py"
Cohesion: 0.03
Nodes (71): ArtifactBackend, Stub sync — this provider stores artifacts locally only. No remote backend is…, Protocol, Protocol defining the storage contract for artifact manifest backends.…, Retrieve the artifact manifest for *item_id*. Args: item_id: Backlog item…, Persist *manifest* for *item_id*. Replaces any existing manifest section;…, Read artifact file content from the root worktree. Args: path: Repo-relative…, Store artifact content as a GitHub issue comment. Creates a structured… (+63 more)

### Community 52 - "run_quality_gates"
Cohesion: 0.04
Nodes (67): Path, Return the full path of *name* on PATH, or None if not found. Result is cached…, Execute a list of gate command strings and return an aggregate result. Each…, _resolve_executable(), run_quality_gates(), _make_completed_process(), CompletedProcess, integration (+59 more)

### Community 53 - "ProgressiveMarkdownNavigator"
Cohesion: 0.03
Nodes (58): ProgressiveMarkdownNavigator, Load and parse markdown from the provider. Args: source: Source identifier…, Token-budget-aware navigator over a parsed markdown document. Provides document…, Tests for the NavigationResult Pydantic model., NavigationResult.model_dump_json() produces valid JSON that roundtrips., current_content() returns the content of the current page., current_content() returns empty string when no pages., model_dump() includes kind, title, pages, current_page, total_pages, has_more. (+50 more)

### Community 54 - "test_consolidated_tools.py"
Cohesion: 0.03
Nodes (97): make_task_def(), Return a minimal TaskDefinition suitable for TaskBackend.create_plan and…, client(), ctx_backend(), fixture, parametrize, MCP-layer tests for the 3 consolidated SAM tools. Covers sam_task, sam_plan,…, sam_active_task stores separate contexts for different session_ids. Tests:… (+89 more)

### Community 55 - "classify_sync_error"
Cohesion: 0.03
Nodes (70): _attempt_sync(), _compute_backoff_delay(), _count(), _make_progress_callback(), _callback(), ProgressCallback, Protocol, Background sync engine for the backlog MCP server. Provides the startup sync… (+62 more)

### Community 56 - "ContentConflictError"
Cohesion: 0.04
Nodes (75): load_manifest(), publish_artifact(), Revision-safe persistence for artifact manifests., Publish immutable content before atomically advancing its manifest entry.…, Load a manifest and the revision required for its next write. Returns: The…, Register one entry with bounded compare-and-swap retries. Returns: The…, register_manifest_entry(), Backend Protocol — implementation-agnostic abstraction for backlog storage.… (+67 more)

### Community 57 - "call_mcp_tool"
Cohesion: 0.04
Nodes (88): call_mcp_tool(), Call a tool through the in-memory FastMCP transport and parse the result. Args:…, parametrize, An invalid status must produce an error response, not a success envelope.…, test_artifact_register_rejects_a_status_outside_the_enum(), backlog_link_followup catches BacklogError and includes error key., backlog_list_followups passes followup_to to operations., backlog_list_followups catches BacklogError and includes error key. (+80 more)

### Community 58 - "_call"
Cohesion: 0.02
Nodes (88): _call(), backlog_add passes params to operations.add_item and merges output., backlog_close forwards cleanup and force flags., backlog_resolve catches BacklogError when resolution fails., backlog_update forwards section and content for groomed update., backlog_update forwards description to operations.update_item., backlog_groom calls operations.groom_item with section and content., backlog_add forwards source, type_, and force to operations. (+80 more)

### Community 59 - "BdRunner"
Cohesion: 0.05
Nodes (76): _bd_env(), BdRunner, JsonValue, Lazy subprocess wrapper for the ``bd`` CLI. Parameters ----------…, Run ``bd`` with *argv*, inject ``--json`` if absent, parse output. Parameters…, Run ``bd`` with *argv* and return raw stdout. Parameters ---------- argv:…, Return ``True`` if ``bd`` is on ``PATH`` and responds to ``version``. The…, Return the filtered base environment merged with instance-level overrides.… (+68 more)

### Community 60 - "DHConfig"
Cohesion: 0.12
Nodes (51): _ALL_SUBSYSTEMS, DHConfig, Unified backend-name resolver using .dh/config.yaml. Resolution order per…, _TASK_AND_CONTEXT, _clear_all_backend_env_vars(), MonkeyPatch, Path, TDD tests for DHConfig — unified backend-name resolver using .dh/config.yaml.… (+43 more)

### Community 61 - "TokenBoundedExtractor"
Cohesion: 0.04
Nodes (54): Initialise handler with optional injected collaborators. Args: normalizer:…, _decode_window(), Tests for TokenBoundedExtractor.extract() — TDD, authored before T18…, returned_tokens == head_tokens when content is larger than the window., content is the decoded first-head-tokens window, not a character slice., total_tokens is the full content count even when head_tokens truncates output., Passing skip_tokens=0 explicitly must produce identical results to the default., extract() returns all content without truncation when head_tokens ≥… (+46 more)

### Community 62 - "test_scripted_runner.py"
Cohesion: 0.04
Nodes (84): LoopRecord, Everything one run of the loop did and saw., Print every unsatisfied observation and return the run's exit status. Args:…, report(), assert_satisfied(), CaptureFixture, Observation, parametrize (+76 more)

### Community 63 - "DisclosureRequestParser"
Cohesion: 0.04
Nodes (81): DisclosureRequestParser, Parse disclosure parameters and return a validated ``DisclosureRequest``. Args:…, Validate and parse four optional MCP parameters into a ``DisclosureRequest``.…, DisclosureMode, DisclosureParamError, Exception, StrEnum, Operating mode resolved from disclosure parameters in a single MCP call. (+73 more)

### Community 64 - "test_dh_paths_integration.py"
Cohesion: 0.03
Nodes (53): isolated_project(), project_with_dirs(), fixture, MonkeyPatch, parametrize, Path, Final integration tests for the three-tier DH state architecture. T13: Full…, Audit: no hardcoded .claude/backlog, .claude/context, or .claude/reports in… (+45 more)

### Community 65 - "ViewItemResult"
Cohesion: 0.04
Nodes (46): Enrich a ViewItemResult from stored issue data., Result of viewing a single backlog item, optionally enriched with GitHub data., ViewItemResult, _apply_body_section_filter(), Narrow *body* and *result.body* to the requested section(s). Resolves *section*…, Edge-case coverage for _apply_body_section_filter filter-form dispatch (#2495).…, Comma-separated index forms with surrounding whitespace., Regex boundary conditions: invalid patterns and multiple section matches. (+38 more)

### Community 66 - "test_spawn.py"
Cohesion: 0.03
Nodes (37): _make_stop_ns(), CaptureFixture, parametrize, Tests for kage-bunshin spawn.py — bidirectional session manager., Ctrl-C causes session to exit within timeout — success without force., Ctrl-C causes session to exit within timeout — tmux kill-session NOT called for…, Session does not exit within timeout — force kill and forced=true in output., Session tmux is already gone — registry cleaned, already_dead=true reported. (+29 more)

### Community 67 - "artifact_provider.py"
Cohesion: 0.02
Nodes (108): GitHubGistArtifactProvider, GitLabArtifactProvider, _make_github_client(), Github, ItemId, Backend abstraction for artifact manifest storage. Defines the…, GitLab Snippets-backed implementation of :class:`ArtifactBackend`. Stores the…, Retrieve the artifact manifest for *item_id*. Lists issue notes and scans for a… (+100 more)

### Community 68 - "IssueCommentNode"
Cohesion: 0.08
Nodes (52): IssueCommentNode, BaseModel, Comment node returned from issue comments listing query. ``id`` is GitHub's…, _body_digest(), _CommentMetadata, parse_work_item_comment(), parse_work_item_head(), BaseModel (+44 more)

### Community 69 - "load_item"
Cohesion: 0.04
Nodes (49): detect_format(), load_item(), load_item_text(), Path, Pure YAML file I/O for backlog items. Primary read/write module for ``.yaml``…, Load a backlog item from an in-memory string. Useful for testing without disk…, Return the file format based on path suffix. Args: path: Path to the backlog…, Load a backlog item from a file. Detects format from the file suffix and… (+41 more)

### Community 70 - "test_backlog_core_server.py"
Cohesion: 0.02
Nodes (81): _make_output_dict(), Tests for the FastMCP 3.x server layer in backlog_core/server.py. All 10 MCP…, backlog_update_sam_task_status forwards repo to the operations layer., backlog_view signature includes 'summary' parameter. Tests: MCP tool schema…, backlog_sync passes dry_run=True to operations.sync_items., backlog_update calls operations.update_item and merges result., backlog_update forwards section and content for incremental update., backlog_update catches BacklogError. (+73 more)

### Community 71 - "test_server_sam_taskbackend.py"
Cohesion: 0.04
Nodes (73): ContextBackend, Protocol, ContextBackend Protocol — implementation-agnostic abstraction for session…, Protocol defining the backend contract for session-to-task context storage. All…, Remove the active task context for a session. Args: session_id: Claude Code…, get_backend(), get_context_backend(), The content backend every MCP action falls back to when the ledger does not… (+65 more)

### Community 72 - ".parse"
Cohesion: 0.23
Nodes (10): _extract_heading_text(), collect(), _PositionedHeading, Match, Record the source position, then parse the heading normally. Returns: The match…, Attach the recorded source position to the parsed heading., Reconstruct heading text from all inline descendants of a marko Heading node.…, A ``Heading`` that records where its own source line begins. marko 2.2.2… (+2 more)

### Community 73 - "conn"
Cohesion: 0.08
Nodes (78): canonical_plan_id(), Give the one spelling every store records a UID-derived plan id under. Every…, FormatDetectionError, Exception, Raised when no known format can be identified for a path. Args: path: File or…, accept(), _address(), append_task() (+70 more)

### Community 74 - "_item"
Cohesion: 0.05
Nodes (46): _Backend, _item(), _patch_backend(), MockerFixture, Tests for what a ``--status`` filter means when the live status query never…, A numeric-issue item's cache may hold the bare lifecycle value, not the label.…, "open"/"done"/"closed" have no ``status:*`` label counterpart — leave them bare., Reproduction (P1, PR #3552 Codex review): unlike every other bare lifecycle… (+38 more)

### Community 75 - "read_manifest_plan"
Cohesion: 0.04
Nodes (76): _extract_prose_sections(), _is_single_followup_format(), Path, Extract prose content per task from the markdown body. Looks for headings…, Return True when the file is a single-task follow-up with flat body prose. A…, Read a global-manifest format plan file. The global manifest format has: - A…, read_manifest_plan(), Path (+68 more)

### Community 76 - "LinearArtifactProvider"
Cohesion: 0.04
Nodes (58): _is_dict_of_object(), LinearArtifactProvider, Path, TypeGuard, Read artifact file content from the local filesystem. Validates the path for…, Raise ``ValueError`` when *path* fails the path traversal check. Args: path:…, Initialise provider with GitLab credentials and state root path. Args:…, Initialise provider with GitHub repository slug and state root path. Args:… (+50 more)

### Community 77 - "test_validator.py"
Cohesion: 0.08
Nodes (73): ConflictGroup, A set of backlog items whose Impact Radii overlap at the file level., An ordered execution wave containing parallelizable items., Wave, detect_stale_plan(), Result of plan integrity validation. Attributes: is_valid: True if all checks…, Validate structural integrity of a dispatch plan. Runs five independent checks:…, Detect whether a dispatch plan matches the current milestone state. Compares… (+65 more)

### Community 78 - "test_frontmatter_reader.py"
Cohesion: 0.05
Nodes (72): _load_yaml_block(), _parse_embedded_task_blocks(), _parse_frontmatter_content(), _parse_prose_fields(), _parse_tasks_list_block(), Any, Path, YAML-frontmatter-in-markdown reader for SAM task/plan files. Reads ``.md``… (+64 more)

### Community 79 - "open_ledger"
Cohesion: 0.06
Nodes (70): check_local_filesystem(), connect(), database_path(), filesystem_type(), holds(), open_ledger(), Path, Return the ledger's path for one repository. ``dh_paths.state_root`` derives… (+62 more)

### Community 80 - "find_item"
Cohesion: 0.05
Nodes (32): AmbiguousSelectorError, Initialise with discovery context. Args: methods_tried: Method names tried in…, Initialize with the selector that failed to match., Initialize with the unmatched ID and the IDs that were available., Raised when a title substring selector matches multiple backlog items. The…, Initialize with the ambiguous selector and the items it matched., Initialize with the colliding reference and the shared title. Args: reference:…, Initialize with the missing capability, backend name, and attempted operation.… (+24 more)

### Community 81 - "_make_view_result"
Cohesion: 0.03
Nodes (68): _build_over_budget_view(), r"""Build a ``## Sections`` index string from a populated ViewItemResult.…, Build a compact section-directory response for an over-budget backlog_view…, _sections_index_from_result(), _make_view_result(), backlog_view with include_content=False response has 'sections_metadata' list.…, backlog_view with summary=True (default) returns 5-field routing manifest.…, backlog_view summary=True _hint embeds the exact selector the caller passed.… (+60 more)

### Community 82 - "dispatch.py"
Cohesion: 0.06
Nodes (59): emit_result(), Emit an operation result as JSON to stdout, then exit nonzero on error.…, _ConflictGroupInput, conflicts(), create_plan(), _group_plan_items(), item_status(), _parse_conflict_group() (+51 more)

### Community 83 - "._bd_id_for_task"
Cohesion: 0.04
Nodes (39): _beads_to_task_status(), _build_plan_data(), _issue_to_task_data(), Any, PlanUpdateValue, Append markdown content under a named heading in the task notes. Fetches the…, Append a single validated Task to an existing plan. Creates a new child issue…, Finalize a drafting plan. Beads issues are live after creation, so this is a… (+31 more)

### Community 84 - "test_mcp_call_shape_drift.py"
Cohesion: 0.06
Nodes (61): _artifact_call_spans(), _artifact_register_cli_defects(), _artifact_register_cli_starts(), _call_span(), _cli_command_span(), _cli_scan_character(), Defect, find_artifact_enum_defects() (+53 more)

### Community 85 - "parse_entries"
Cohesion: 0.05
Nodes (62): generate_diff(), parse_entries(), Parse entry blocks from a section body. Args: section_body: Raw section text to…, Orchestrate section content modifications using entry blocks. Returns: Modified…, Generate a git-diff style comparison of entry blocks between local and remote.…, rewrite_section(), The rejected-and-wrapped form keeps the prose reachable through parse_entries., The guard is not over-broad — a matching ID still replaces that entry only. (+54 more)

### Community 86 - "test_file_cache.py"
Cohesion: 0.03
Nodes (145): acknowledge(), replace(), replace(), queue(), reject(), BaseModel, Private durable cache for remote-capable backlog providers., Durably replace one provider-observed content record. A reference with a… (+137 more)

### Community 87 - "_paginate"
Cohesion: 0.05
Nodes (47): _assert_calibration(), _find_item2_exact_body(), _find_normal_body(), _find_oversized_body(), _make_item(), _paginate(), Any, given (+39 more)

### Community 88 - "backlog.py"
Cohesion: 0.09
Nodes (63): add(), assign_milestone(), close(), comment_issue(), comments(), create_milestone(), create_project(), _emit() (+55 more)

### Community 89 - "monitor.py"
Cohesion: 0.05
Nodes (59): agent_last_actions(), capture_pane_by_id(), extract_actions(), jsonl_dir_for_project(), latest_team(), Path, Health subcommand — team member JSONL action inspection and tmux pane capture., Find the agent's JSONL session and return last N actions. For the team-lead:… (+51 more)

### Community 90 - "scripted_runner.py"
Cohesion: 0.07
Nodes (51): The loop itself: the order ``work-loop.md`` and ``runner-contract.md`` put the…, Bind the driver to one CLI, one fixture set and one workspace. Args: cli: How…, CommandTimeoutError, FixtureMissingError, RuntimeError, Failing loudly: every reason a run stops, named rather than left to a traceback., A program the run needs is not resolvable on PATH., A loop-plan fixture file the loop reads is absent. (+43 more)

### Community 91 - "create_backend"
Cohesion: 0.04
Nodes (90): _auto_detect_beads(), create_backend(), Return ``"beads"`` when the explicit opt-in marker ``.beads/dh-backend``…, Instantiate and return a backend by name. When *name* is ``None``, resolution…, create_integration_branch(), delete_integration_branch(), get_integration_branch_status(), list_integration_branches() (+82 more)

### Community 92 - "test_agent_portability_and_verdict_drift.py"
Cohesion: 0.05
Nodes (63): agent_files(), chain_steps_named(), cli_definition_tag_offenders(), _extract_tag_block(), governed_files(), guide_relocation_scan_files(), matching_lines(), plugin_root_variable_offenders() (+55 more)

### Community 93 - "model.py"
Cohesion: 0.07
Nodes (50): The decomposition input: what layer 3 consumes to produce a layer-2 work graph.…, Descriptor, Freshness, BaseModel, Source anchors and the descriptor: the facets an input or output must carry.…, One place in the sources an element was read from., The freshness and version facet of a value., One declared input or output, carrying every facet the contract requires of… (+42 more)

### Community 94 - "test_readers/test_yaml_reader.py"
Cohesion: 0.06
Nodes (57): Format detection and plan read routing for SAM task/plan files. The…, _extract_body_task_blocks(), _parse_body_prose_fields(), _parse_manifest_frontmatter(), Global-manifest reader for SAM task/plan files. Reads ``.md`` files with a…, Split a markdown body on ``---`` delimiters, ignoring those inside code fences.…, Extract named content sections from a markdown prose segment. Delegates to the…, Attempt to parse ``text`` as a YAML mapping. Returns the coerced plain dict on… (+49 more)

### Community 95 - "test_ledger_fold.py"
Cohesion: 0.07
Nodes (56): Checkpoint, all_events(), Read the whole log, oldest first, with each payload decoded. Args: conn: An…, A plan-level ``--set`` on an absent plan raises before any event is appended., test_update_of_a_missing_plan_refuses_and_appends_nothing(), accepted_then_forced(), assert_rebuilt(), build_all() (+48 more)

### Community 96 - "spawn.py"
Cohesion: 0.07
Nodes (58): _build_spawn_record(), _build_spawn_shell_cmd(), check_session_limit(), _claude_tmux_session_name(), cmd_list(), cmd_spawn(), _count_active_sessions(), _delete_entry() (+50 more)

### Community 97 - "Path"
Cohesion: 0.07
Nodes (39): _make_agent_entry(), _make_metadata(), MockerFixture, Path, profile_load populates name and plugin from the discovered agent entry. Tests:…, profile_load includes the agent instruction body in the response. Tests: body…, profile_load returns an empty skills list when the agent declares no skills.…, profile_load returns skills as raw URI strings, not resolved dicts. Tests:… (+31 more)

### Community 98 - "dh_migrate.py"
Cohesion: 0.06
Nodes (55): err(), output_json(), NoReturn, Shared CLI output helpers for development-harness migration scripts.…, Print an error message to stderr and exit. Args: msg: Error message for the…, Print *data* as compact JSON to stdout. No indentation — see…, _build_registration_rows(), _build_slug_index() (+47 more)

### Community 99 - "merge_layer.py"
Cohesion: 0.07
Nodes (46): _bootstrap_layer_meta(), ExtractionFragment, LayerJSON, merge_fragment(), MergeResult, parse_extraction_fragment(), parse_layer_json(), Path (+38 more)

### Community 100 - "get_repo_root"
Cohesion: 0.07
Nodes (34): _get_migrate_artifact_provider(), Create the artifact provider used by a migration run. Returns: An artifact…, get_backlog_dir(), get_config(), get_default_repo(), get_repo_root(), __getattr__(), init_paths() (+26 more)

### Community 101 - "_resolve_labels_graphql"
Cohesion: 0.07
Nodes (39): Resolve label names via a single GraphQL query. Returns label name strings that…, _resolve_labels_graphql(), _graphql_response(), _make_mock_repo(), Any, MockerFixture, Tests for _resolve_labels_graphql() in backlog_core/gh_client.py. Covers: all-…, _resolve_labels_graphql omits null aliases and returns only existing labels. (+31 more)

### Community 102 - "_call_view"
Cohesion: 0.07
Nodes (36): _patch_issue_2521(), MockerFixture, RED tests: section-filter miss returns an explicit error dict. These tests MUST…, Patch operations layer so view_item enriches with the #2521 fixture body. Args:…, section= miss with include_content=True returns an error dict. Exercises…, section= miss response contains an 'error' key. Arrange: GitHub enrichment…, section= miss response contains a non-empty 'valid_sections' list. Arrange:…, section= miss error response does not include a 'body' field. No content is… (+28 more)

### Community 103 - "DispatchPlan"
Cohesion: 0.08
Nodes (45): DispatchPlan, Root model for plan/milestone-{N}-dispatch.yaml., _keys_to_kebab(), _make_yaml(), Any, BaseException, Path, YAML (+37 more)

### Community 104 - "test_artifact_registry_ownership.py"
Cohesion: 0.06
Nodes (52): ArtifactTypeRow, BaseModel, model_validator, One artifact type, the writers permitted to register it, and whether a gate…, Reject a gate-read row that names other than exactly one registering agent.…, _cli_flags(), _cli_registration(), declared_agents() (+44 more)

### Community 105 - "test_cli_active_task.py"
Cohesion: 0.06
Nodes (52): ContextConfig, Container for the active ContextBackend instance. This dataclass replaces…, Register the active ContextConfig. Args: config: ContextConfig instance…, Clear the cached ContextConfig singleton. Intended for test teardown — call…, reset_context_config(), set_context_config(), _configured_content_backend(), _invoke() (+44 more)

### Community 106 - "fetch_task"
Cohesion: 0.07
Nodes (52): attempt_open(), check_progress_values(), expired(), expired_row(), outstanding(), Progress, Any, Connection (+44 more)

### Community 107 - "Path"
Cohesion: 0.05
Nodes (32): plan_dir(), fixture, parametrize, Path, Tests for sam CLI ``create`` command. Tests: Plan creation via CLI with typed…, Two consecutive creates produce distinct UUID plan_ids. Tests: UUID uniqueness…, Test task creation through the named, typed create options., Typed task options persist all supported task fields. (+24 more)

### Community 108 - "entry_blocks.py"
Cohesion: 0.05
Nodes (45): _apply_show_filter(), _entry_from_span(), EntrySpan, _find_balanced_close(), find_entry_spans(), _is_entry_id(), _match_struck(), _opaque_mask() (+37 more)

### Community 109 - "test_decomposition_gate.py"
Cohesion: 0.06
Nodes (40): The artifact-type registry this plugin declares: which agent may register which…, Path, The decomposition-exit gate: checks a task's instructions against the referents…, Resolves Tier-1 referents against a repo checkout and a decomposed…, Initialize the resolver. Args: repo_root: The repository checkout root that…, Resolve ``referent`` per the decomposition-exit gate's tier-1 table. Args:…, Resolve a ``FILE`` referent: a repo-relative path that must exist. Args:…, Resolve a ``RULE`` referent: a rules file, optionally with a ``#section``… (+32 more)

### Community 110 - "split_body_sections"
Cohesion: 0.06
Nodes (32): Split *body* into ``## ``/``### ``-delimited sections, entry-block aware. The…, split_body_sections(), parametrize, Regression tests for the ``_build_sections_metadata`` boundary-scanner defect…, Heading positions come from marko, not from re-scanning the source lines. The…, A commented-out heading is invisible to marko and must be invisible here. Why:…, Fence tracking must respect CommonMark delimiter length. Why: A boolean toggle…, A ``<div><sub>`` that never closes must not consume to end of document. Why:… (+24 more)

### Community 111 - ".from_markdown"
Cohesion: 0.05
Nodes (34): resolve_section raises AmbiguousSectionRefError when two sections share a slug.…, resolve_section returns the SectionNode when the slug is unambiguous. This is a…, test_resolve_section_raises_on_slug_collision(), test_resolve_section_unique_slug_returns_section_node(), Construct a navigator and immediately load the given markdown. Args: markdown:…, fenced_nav(), nav(), fixture (+26 more)

### Community 112 - "save_item"
Cohesion: 0.05
Nodes (39): Write a backlog item to a YAML file. Always writes ``.yaml`` format regardless…, save_item(), Path, parse_item_file wires body sections into BacklogItem.sections., groomed' key is present in sections when ## Groomed heading exists., rt_ica' key is present in sections when ## RT-ICA heading exists., Wiring body sections does not break existing frontmatter fields., Sections present after .md load survive save/reload as .yaml. (+31 more)

### Community 113 - "test_known_failure_types.py"
Cohesion: 0.06
Nodes (49): _check_codes_unique(), failure_type(), FailureCategory, FailureTypeRow, KnownFailureTypesPage, page(), BaseModel, StrEnum (+41 more)

### Community 114 - "sync_issues_graphql"
Cohesion: 0.08
Nodes (36): datetime, Fetch issues with optional filtering and a per-issue callback. Pagination is…, sync_issues_graphql(), slow, _make_issue_node(), _make_mock_repo(), Any, MockerFixture (+28 more)

### Community 115 - "cli_inputs.py"
Cohesion: 0.06
Nodes (40): AppendTaskInput, _CliInput, CreatePlanInput, PlanUpdateFields, PlanUpdateInput, BaseModel, field_validator, model_validator (+32 more)

### Community 116 - "migrate_backlog_to_yaml.py"
Cohesion: 0.08
Nodes (46): _dry_run_section_info(), _has_frontmatter(), main(), migrate_file_dry_run(), migrate_file_live(), MigrationReport, command, help (+38 more)

### Community 117 - "test_github_tools_milestones.py"
Cohesion: 0.06
Nodes (48): make_milestone_full_node(), Return a MilestoneFullNode-shaped dict with sensible defaults. Args:…, _call(), _inject_milestones(), fetch_milestones(), MonkeyPatch, Tests for backlog milestone MCP tools and operations. Covers four tools and…, list_milestones forwards the state parameter to get_milestones. Tests:… (+40 more)

### Community 118 - "test_frontend_parity_ops.py"
Cohesion: 0.07
Nodes (48): _assert_compact_result(), _mint_plan_id_with_a_letter_in_its_hex_suffix(), Any, _CASE_SPELLINGS, integration, MonkeyPatch, parametrize, Per-operation CLI/MCP parity tests (T-P5-PARITY). Proves the same logical… (+40 more)

### Community 119 - "Path"
Cohesion: 0.11
Nodes (20): AgentMetadata, Structured frontmatter extracted from an agent definition file. Corresponds to…, parse_agent_file(), parse_skill_frontmatter(), Frontmatter parsing and skill content reading for agent definition files.…, Read only the frontmatter of a SKILL.md to extract sub-skill URIs. Looks for a…, Read a skill's SKILL.md and all Markdown reference files. Reads ``SKILL.md``…, Read an agent ``.md`` file and return its structured metadata and body. The… (+12 more)

### Community 120 - "tool_responses.py"
Cohesion: 0.06
Nodes (48): DispatchSpawnSummary, DispatchWaveSummary, Aggregated wave status returned by the dispatch_wave_status tool., Final summary returned when the dispatch_spawn background task completes., AccumulatedUsage, ArtifactEntryOut, CommentEntry, DispatchConflictsResponse (+40 more)

### Community 121 - "_item"
Cohesion: 0.10
Nodes (28): _item(), _patch_backend(), MockerFixture, parametrize, Tests for how a refused GraphQL query reaches the listing path.…, A network error/500/rate limit resolving the repo itself is not a refusal…, Closed and unlabeled issues remain distinguishable from absent issues., The single-item fallback must not swallow the same refusal batch_fetch_statuses… (+20 more)

### Community 122 - "Graph"
Cohesion: 0.10
Nodes (44): ContractBasis, Finding, Predicate, Projection, computed_field, SourceSpan, StrEnum, The finding record and its severity taxonomy. A finding is one falsified… (+36 more)

### Community 123 - "MonkeyPatch"
Cohesion: 0.07
Nodes (32): parse_disabled_hooks(), Read CLAUDE_SKILLS_DISABLED_HOOKS and return the set of disabled hook IDs.…, hook_input_subagent_stop(), Any, CaptureFixture, fixture, MockerFixture, MonkeyPatch (+24 more)

### Community 124 - "_extract_log_messages"
Cohesion: 0.04
Nodes (45): _extract_log_messages(), backlog_sync emits ctx.info with start message before the operation., backlog_sync emits ctx.info with '(dry-run)' suffix when dry_run=True., backlog_sync emits ctx.info with completion summary including counts., backlog_sync surfaces each out.warnings entry via ctx.warning., backlog_groom emits ctx.info with 'Grooming item: {selector}' before operation., backlog_groom emits ctx.info with 'Groomed: {title}' after operation., backlog_groom surfaces out.warnings via ctx.warning. (+37 more)

### Community 125 - "_call"
Cohesion: 0.06
Nodes (24): _call(), Scenario C1b: backlog_view(include_content=False) omits body and sections keys.…, Scenario C1e: backlog_view without include_content returns full body (backward…, Combined filters narrow results correctly through the full MCP path., Topic filter narrows candidates for semantic matching via topic slug., Scenario 11: backlog_close closes an item with a reason and no blocking PRs., Scenario 8: backlog_update sets a plan path and returns title + plan field., Scenario 9: backlog_update with status=in-progress calls… (+16 more)

### Community 126 - "detect_format"
Cohesion: 0.07
Nodes (47): _classify_frontmatter(), detect_format(), Path, Detect the task/plan file format for a given path. Detection flowchart: 1. If…, Read a plan from any supported format. Detects the format via…, Classify a YAML frontmatter block into a FormatType. Returns ``None`` when the…, read_plan(), Path (+39 more)

### Community 127 - "Backlog MCP Package — Architecture Spec"
Cohesion: 0.04
Nodes (47): Backends: backends/, Backlog MCP Package — Architecture Spec, Bootstrap Decision Tree, CLI wrapper: backlog.py (rewritten), Error Handling Pattern, Execution Paths, GitHub writable records, Historical Source File (+39 more)

### Community 128 - "test_dh_migrate.py"
Cohesion: 0.08
Nodes (46): backlog_dir(), Return ``~/.dh/projects/{slug}/backlog/``. Args: project_root: Explicit project…, _artifact_manifest_instructions(), _detect_layout(), _merge_dir(), _old_dirs(), Return mapping of old-relative-path → absolute path for each legacy directory., Return presence flags for old and new layout indicators. Returns: Dict with… (+38 more)

### Community 129 - "Path"
Cohesion: 0.06
Nodes (28): Path, Update --context does not alter feature, goal, or tasks. Tests: Field isolation…, Update returns JSON with ``updated: true`` and the address. Tests: CLI output…, A task-address update combined with --context applies both changes. Tests:…, Test ``sam plan update`` with typed field options flag for arbitrary field…, Update typed field options priority=1 on a task changes priority value. Tests:…, Update typed field options status=in-progress changes the task status. Tests:…, Update typed field options on one field does not alter other task fields.… (+20 more)

### Community 130 - "parse_md_body_sections"
Cohesion: 0.06
Nodes (45): parse_md_body_sections(), Parse markdown body sections from a legacy ``.md`` backlog file body. Splits…, Tests for parse_md_body_sections and the .md → BacklogItem → .yaml round-trip.…, Plain ## sections without entry blocks produce Section objects. "Description"…, Plain-text sections become Section instances with one synthetic entry., Synthetic entry id uses the supplied added_date., Section content is captured verbatim in the entry., Entry block HTML produces individual Entry objects, not a synthetic one. (+37 more)

### Community 131 - "issue-3152-resolved-body.md"
Cohesion: 0.04
Nodes (45): Acceptance Criteria, Agent Instructions (instruct AI to use current interface), Claim A: Generated sections before fix, removed after, Claim A: Generated sections before fix, removed after, Claim A: Generated sections before fix, removed after, Claim B: parsing.py template-fills from title, Claim B: parsing.py template-fills Story and Acceptance Criteria from title, Claim B: parsing.py template-fills Story and Acceptance Criteria from title at creation (+37 more)

### Community 132 - "PRD: DH Workflow Extractor System"
Cohesion: 0.04
Nodes (46): Component Inventory, Corroboration reform (reduce.py changes), Design Decisions (Resolved 2026-06-19), Edge types, Entry points, Evidence sources: body content only, Existing L0–G8 data: enrichment role, Extraction Architecture (+38 more)

### Community 133 - "sam_plan.py"
Cohesion: 0.06
Nodes (45): _attempt_backlog_sync(), body_section(), branch_head(), _canonical_output_path(), check_groomed_fields(), check_import_sources(), check_surface(), _extract_fallback_metadata() (+37 more)

### Community 134 - "test_github_tools_issues.py"
Cohesion: 0.06
Nodes (43): _call(), configured_github_backend(), fixture, MonkeyPatch, Tests for backlog_list_issues and backlog_comment_issue MCP tools. Tests are…, list_issues stops collecting once limit is reached. Tests: list_issues limit…, list_issues returns empty list when repository has no matching issues. Tests:…, list_issues raises ValidationError for unrecognised state values. Tests:… (+35 more)

### Community 135 - "test_cli_migrate_fallback.py"
Cohesion: 0.08
Nodes (44): _migrate_one_fallback(), Preserve an unparseable legacy plan as canonical YAML. Returns: Written path…, _load_yaml(), _make_nonstandard_plan_dir(), _make_pure_markdown_plan_dir(), CaptureFixture, parametrize, Path (+36 more)

### Community 136 - "PullRequestRef"
Cohesion: 0.08
Nodes (36): Return empty list — SQLite backend has no pull requests. Args: issue_num:…, PullRequestRef, Reference to an open pull request., close_item(), _pull_if_issue_selector(), Fetch a GitHub issue into the provider-backed record when selector resolves to…, Search for issue-referencing PRs, translating search failures into a refusal.…, Dismiss an item without completion. Requires a categorized reason. Use for… (+28 more)

### Community 137 - "_github_exception"
Cohesion: 0.08
Nodes (25): _github_exception_message(), is_graphql_unavailable(), GithubException, Return the human-readable message a GithubException carries. Args: exc: The…, Report whether this failure means GraphQL is refused environment-wide. A 403…, _FakeRepo, _FakeRequester, _github_exception() (+17 more)

### Community 138 - "Observation"
Cohesion: 0.06
Nodes (25): Observation, One thing a graph query found, phrased as expected against observed., Return the node with this id, raising ``KeyError`` when none carries it. Args:…, Yield each edge that joins a declared output to a declared input, with both…, Find required inputs that no incoming edge fills. Returns: One observation per…, Find edges whose producer type does not satisfy the consumer's declared input…, Find edges where the supplied trust classification is below the required one.…, Find edges whose producer holds an authority other than the one the consumer… (+17 more)

### Community 139 - "LoopDriver"
Cohesion: 0.12
Nodes (26): LoopDriver, Return the ``--plan-address`` flag naming the plan this run built., Return the ``--address`` flag naming one task of the plan this run built. Args:…, Create the plan, append its three tasks, finalize it and validate it. ``--base-…, Add one task to the drafting plan and set the fields the fixture gives it.…, Read the dispatchable set and write down what it holds and what it withholds.…, Open an attempt on one task and return the attempt number ``dispatch`` printed.…, Record what the launch of one attempt returned. Args: task: The task… (+18 more)

### Community 140 - "BranchInfo"
Cohesion: 0.06
Nodes (24): BranchBackend, Optional Git branch-operation surface. Backends that do not support Git branch…, Create an integration branch for a milestone. Returns: BranchInfo TypedDict…, Get the current status of an integration branch. Returns: BranchInfo TypedDict,…, List all integration branches in the repository. Returns: List of BranchInfo…, Return stored branch info, or None if the branch does not exist., Return all stored branch records., Raise RuntimeError — branch operations require GitHub backend. Args:… (+16 more)

### Community 141 - "test_epoch_timestamp_bug.py"
Cohesion: 0.07
Nodes (41): _new_entry_block(), Wrap ``content`` in a freshly timestamped entry block. Returns: HTML div string…, Wrap content with a specific timestamp (for legacy migration and overwrites).…, wrap_entry_with_timestamp(), _apply_groomed_entries(), Mutate a Section's entry list according to the requested grooming operation.…, now_iso(), UTC timestamp helper shared by parsing.py and entry_blocks.py. Extracted to… (+33 more)

### Community 142 - "TokenBudgeter"
Cohesion: 0.07
Nodes (30): _chunks_to_pages(), _make_page(), Paginator, Pagination of text and block lists into token-budget-bounded pages., Convert a list of text chunks into Page objects. Args: chunks: Text chunks to…, Construct a Page with computed token count. Args: content: Page text content.…, Split text or block lists into Page objects respecting a token budget. Args:…, Initialise with a TokenBudgeter. Args: token_budgeter: TokenBudgeter used for… (+22 more)

### Community 143 - "register"
Cohesion: 0.12
Nodes (43): accept_accepted_and_incomplete(), accept_incomplete_and_unreported(), Arranged, dispatch_archived_and_unready(), dispatch_leased_and_unready(), finish_closed_and_unreported(), finish_stale_and_closed(), finish_stale_and_unreported() (+35 more)

### Community 144 - "install_proxy_tls_support"
Cohesion: 0.08
Nodes (22): install_proxy_tls_support(), Teach every PyGithub client in this process to trust a custom CA bundle.…, _installed_https_connection_class(), Read the HTTPS connection class Requester currently builds instances from.…, Installation is conditional, idempotent, and process-wide., On an ordinary network PyGithub keeps its own strict default., A no-op call must not mark the process as installed., Repeat calls neither reinstall nor report failure. (+14 more)

### Community 145 - "enumerate_scope.py"
Cohesion: 0.11
Nodes (36): ReferenceType, _derive_entry_point_name(), enumerate_scope(), _extract_agent_refs(), _extract_mermaid_refs(), _extract_prose_file_refs(), extract_references(), _extract_skill_refs() (+28 more)

### Community 146 - "test_github_tools_prs.py"
Cohesion: 0.09
Nodes (40): list_merged_prs(), Return merged pull requests, optionally filtered by a search query. Fetches…, _call(), _make_pr(), datetime, MonkeyPatch, Tests for backlog_list_merged_prs MCP tool and list_merged_prs operation. Tests…, list_merged_prs stops collecting once limit is reached. (+32 more)

### Community 147 - "_build_task_dict"
Cohesion: 0.06
Nodes (32): _build_task_dict(), _extract_bold_fields(), _extract_task_id_title_from_entry(), _merge_prose_fields(), _parse_dependency_value(), _parse_skills_value(), Any, Extract ``**FieldName**: value`` patterns from task prose text. Parses lines… (+24 more)

### Community 148 - "test_view_sections_metadata_sync.py"
Cohesion: 0.08
Nodes (28): _body_section_names(), MockerFixture, G3 — sections/body metadata sync, miss handling, malformed regex, key drift…, ``result.sections`` must mirror the narrowed ``result.body`` for ALL forms.…, section='2' (numeric, in range) narrows body AND populates sections. RED: body…, section='/Impact.*/' (regex) narrows body AND populates sections in sync. RED:…, section='Issue' (substring) matches two headers; sections holds both in sync.…, section='RT-ICA' (exact name) keeps body and sections in sync (regression… (+20 more)

### Community 149 - "MockerFixture"
Cohesion: 0.06
Nodes (28): _open_pr_refusal(), _refuse(), MockerFixture, Build a side effect that warns and raises like the operations-layer open-PR…, ``backlog close`` and ``backlog resolve`` report the open-PR refusal as JSON., The open-PR ``BacklogError`` from ``close_item`` reaches stdout as JSON with…, The open-PR ``BacklogError`` from ``resolve_item`` reaches stdout as JSON with…, ``backlog view`` forwards the ``--refresh`` flag to ``operations.view_item``. (+20 more)

### Community 150 - "test_backward_compat_local_plans.py"
Cohesion: 0.08
Nodes (31): _create_local_only_plan(), _EmptyArtifactRegistryClient, _EmptyArtifactStore, _make_empty_client(), _make_layer_with_empty_gist(), Path, Task, Backward-compatibility tests for pre-fix local plans (AC4). Verifies that plans… (+23 more)

### Community 151 - "analyze_impact_radius_conflicts"
Cohesion: 0.11
Nodes (39): analyze_impact_radius_conflicts(), _collect_items_with_paths(), ImpactRadiusItem, _parse_impact_radius_paths(), Extract normalised file paths from an Impact Radius markdown body. Args:…, Typed structure for items passed to :func:`analyze_impact_radius_conflicts`.…, Filter items to those with a non-empty impact_radius and parse their paths.…, Compute conflict groups from Impact Radius file-path overlap. Each item dict… (+31 more)

### Community 152 - "parse_item_file"
Cohesion: 0.11
Nodes (15): _fm_str(), parse_item_file(), Resolve a string field from metadata dict with frontmatter fallback. Returns:…, Parse a single per-item backlog file (frontmatter + body). Handles both flat…, Path, Tests for parse_item_file(text, path) -> BacklogItem., Body content below frontmatter is no longer stored on the item. LEGACY:…, When no frontmatter is found, an empty BacklogItem is returned. LEGACY:… (+7 more)

### Community 153 - "Claim Inventory"
Cohesion: 0.05
Nodes (40): C10: The context-fit spectrum has three distinct regions, C11: A sparse-plan + auditor loop identifies minimum viable seeded knowledge, C1: Complexity is context-fit, not implementation difficulty, C2: The three-term equation is sufficient, C3: Decomposition should follow knowledge boundaries, not code boundaries, C4: Stable constraints should be encoded; volatile constraints should be discovered dynamically, C5: Progressive disclosure improves agent reliability, C6: Context garbage collection improves agent reliability (+32 more)

### Community 154 - "Path"
Cohesion: 0.08
Nodes (21): _add_plugin_root_to_path(), fake_project_root(), isolated_state(), fixture, MonkeyPatch, Path, Tests for backlog_core path resolution via dh_paths. Verifies that: -…, Test ensure_dirs creates the expected directory tree. (+13 more)

### Community 155 - "Any"
Cohesion: 0.11
Nodes (25): list_integration_branches(), List all branches matching the ``milestone/`` prefix. Args: repo: Repository in…, _make_mock_branch(), Any, datetime, MockerFixture, create_integration_branch creates a branch from a base SHA., Test successful branch creation returns correct BranchInfo. Tests:… (+17 more)

### Community 156 - "test_addressing.py"
Cohesion: 0.09
Nodes (38): parse_address(), Raise AddressingError-compatible ValueError if address contains traversal…, Parse a task address string into its plan and task components. Args: address:…, _reject_path_traversal(), Tests for sam_schema.core.addressing module. Covers P{NNN}-{slug} primary…, test_parse_address_empty_string_raises_value_error(), test_parse_address_empty_task_component_raises_value_error(), test_parse_address_extension_error_message_suggests_correct_form() (+30 more)

### Community 157 - "_build_sections_metadata"
Cohesion: 0.07
Nodes (27): _assemble_view_content(), _build_sections_compact(), _build_sections_index_from_body(), _build_sections_metadata(), r"""Build a ``## Sections`` index block from a raw body string. Produces the…, Extract ``### ``- or ``## ``-delimited sections from *body* into a metadata…, Extract section names and entry counts without parsing entry content. Returns a…, Return section metadata preferring body-parsed IDs, falling back to YAML.… (+19 more)

### Community 158 - "test_batch_section_writes.py"
Cohesion: 0.16
Nodes (14): _backlog_dir(), MockerFixture, parametrize, Path, Tests for batch section writes in backlog_core/operations.py. Covers…, BacklogItem.reference self-heals at construction time (see models.py). A never-…, An item with a healed but never-persisted reference surfaces a KeyError. This…, _stored_text() (+6 more)

### Community 159 - "test_view_pagination_section_index.py"
Cohesion: 0.08
Nodes (26): _entry_block_body_under_budget_with_dup_overflow(), _many_heading_body(), MockerFixture, G4 — Pagination, entry-block metadata, and ``## Sections`` index displacement…, Finding #4: a body under budget on its own must not be gated by content…, A ``## ``-headed entry-block body under budget on its own is delivered INLINE.…, Finding #5: paged entry-block body must keep its describing section metadata., view_item(section=None, limit=1) on a ``## Log`` entry-block body keeps… (+18 more)

### Community 160 - "test_github_client.py"
Cohesion: 0.08
Nodes (33): ca_directory(), ca_file(), clean_env(), compliant_ca_directory(), compliant_ca_file(), mixed_trusted_and_compliant_bundle(), _pem_encode(), fixture (+25 more)

### Community 161 - "WorkGraph"
Cohesion: 0.07
Nodes (23): DecompositionInput, DecompositionItem, BaseModel, Observation, One piece of grooming or architecture output offered to layer 3's decomposition., The grooming and architecture output layer 3 decomposes into a layer-2 work…, Return the named item, or None when no item carries this id. Args: item_id: The…, Find planned work-graph nodes whose ``decomposition_source`` names no item… (+15 more)

### Community 162 - "test_github_gist_artifact_provider.py"
Cohesion: 0.07
Nodes (29): _make_graphql_return(), mock_gist_user(), mock_github_repo(), provider(), fixture, MockerFixture, Path, Tests for GitHubGistArtifactProvider — gist creation, naming, migration, error… (+21 more)

### Community 163 - "queries.py"
Cohesion: 0.07
Nodes (33): Autonomy, check_finding_codes(), cycles(), dependency_findings(), Finding, FindingCode, list_plans(), PlanStatus (+25 more)

### Community 164 - "ReconcileResult"
Cohesion: 0.08
Nodes (18): Completed reconciliation outcomes and optional changed-item details., ReconcileResult, Satisfy the ``SyncProvider`` protocol; never called by ``list_items``., Record a successful reconciliation and establish the checkpoint., MockerFixture, Regression suite for Failure 2: phantom flush_only parameter (Path B doc-only…, backlog_sync must not expose a flush_only parameter in its MCP schema. FastMCP…, finally.md must not contain any reference to the phantom flush_only parameter.… (+10 more)

### Community 165 - "implementation_manager.py"
Cohesion: 0.02
Nodes (143): exists, FeatureSlug, ProjectPath, resolve_path, _claim_fail(), claim_task(), _coerce_timestamp(), _create_task_from_dict() (+135 more)

### Community 166 - "RT-ICA: Reverse Thinking - Information Completeness Assessment"
Cohesion: 0.06
Nodes (33): Condition Categories, Decision Rule, Fact-Check Integration, planner-rt-ica vs rt-ica, RT-ICA Gate, Source, Status Values, Activation Triggers (+25 more)

### Community 167 - "run_cli_subprocess"
Cohesion: 0.08
Nodes (26): CompletedProcess, Run a CLI subprocess (e.g. ``uv run <script>``) with whole-process-group…, run_cli_subprocess(), dh_state_home(), _get_project_slug(), Any, fixture, integration (+18 more)

### Community 168 - "Path"
Cohesion: 0.08
Nodes (20): Path, Successful claim includes the task_id in JSON output. Tests: Task ID echo. How:…, Successful claim includes a ``started`` ISO timestamp. Tests: Timestamp…, Claiming T1 does not change T2 or T3 status. Tests: Task isolation during…, Test ``plan claim`` on a task already in ``in-progress`` state. Tests: Double-…, Claiming an in-progress task exits 0 with claimed=false. Tests: Guard against…, Claiming a complete task exits 0 with claimed=false. Tests: Guard against…, Claiming an in-progress task includes a status warning in JSON. Tests: Error… (+12 more)

### Community 169 - "test_scenarios.py"
Cohesion: 0.07
Nodes (22): provider_state(), fixture, MonkeyPatch, Scenario-based integration tests for the backlog MCP FastMCP server. Tests are…, Scenario C1c: backlog_view(include_content=False) returns all metadata fields.…, Scenarios consumed by the /work-backlog-item groom route., Scenario 17: backlog_update with section/content param sets groomed content., Scenarios consumed by /group-items-to-milestone skill. (+14 more)

### Community 170 - "test_integration_reconciliation.py"
Cohesion: 0.09
Nodes (23): _filter_closed_items(), Filter out items whose local status is a terminal state. Terminal states are…, test_memory_revalidates_metadata_mutations_before_persisting(), _make_item(), _make_mixed_items(), Integration tests for CLI --include-closed flag and MCP include_closed…, Verify list_items function respects include_closed parameter end-to-end., list_items without include_closed filters out terminal status items. (+15 more)

### Community 171 - "test_ledger_cascade_ancestors.py"
Cohesion: 0.15
Nodes (33): holding_cascades(), Return the ``cascade-reversed`` outcome reason for one reclaimed task. Args:…, Return the failed tasks whose cascade currently holds one dependent skipped. A…, reversal_code(), fail(), Connection, parametrize, A dependent two failures block, in both directions of the cascade.… (+25 more)

### Community 172 - "/work-milestone"
Cohesion: 0.06
Nodes (31): Assign Back Details, Conflict Severity Classification, Integration Branch Landing, Merge Queue Protocol, Merge Slot Lifecycle, Quality Gate Commands, Blocker Handling, Completion Report Format (+23 more)

### Community 173 - "parse_manifest_section"
Cohesion: 0.08
Nodes (21): parse_manifest_section(), ItemId, Extract and parse the artifact manifest section from an issue body. Returns an…, Additional tests targeting _parse_table_row branches not covered by other…, parse_manifest_section skips table rows with fewer than five columns. Tests:…, parse_manifest_section defaults status to CURRENT for unknown status values.…, Unit tests for parse_manifest_section. Tests: Parsing from valid issue bodies,…, parse_manifest_section extracts a valid entry from a real issue body. Tests:… (+13 more)

### Community 174 - "BdInvocationError"
Cohesion: 0.07
Nodes (17): BdInvocationError, Initialise with the unparseable raw output. Args: message: Human-readable…, Store configuration only. Does not touch the filesystem., ``bd`` returned a non-zero exit code, timed out, or failed to start.…, Initialise with structured invocation details. Args: message: Human-readable…, Any, JsonValue, Simulate bd commands that produce text output. (+9 more)

### Community 175 - "_search_aware_list_items"
Cohesion: 0.06
Nodes (33): apply_search_filter(), Filter items using the full-text search query syntax. Query syntax (operator…, backlog_list search with NOT operator excludes items containing the negated…, backlog_list search with parenthetical grouping returns correct items. How:…, backlog_list count_only=True reflects the filtered item count, not the raw list…, backlog_list search= matches items where any of title, description, topic, or…, backlog_list search= comparison is case-insensitive., backlog_list search='auth OR deploy' matches items containing either term. (+25 more)

### Community 176 - "groom/start.md"
Cohesion: 0.13
Nodes (11): Discovery Gate, Groom: Analyze, Outputs, RT-ICA Initial Snapshot, Groom: Finally, Steps, Extract Item Details, Groom: Intake (+3 more)

### Community 177 - "github_context_backend.py"
Cohesion: 0.11
Nodes (19): IssueComment, _build_comment_body(), _closing_tag(), GitHubContextBackend, _opening_tag(), _parse_comment_body(), GitHubContextBackend — GitHub issue comment-based ContextBackend…, Initialise the backend with GitHub credentials. Args: github_token: GitHub… (+11 more)

### Community 178 - "read_dispatch_plan"
Cohesion: 0.12
Nodes (16): _coerce_to_plain(), _load_yaml(), Any, Path, Parse YAML text using ruamel.yaml round-trip mode. Args: content: Raw YAML text…, Recursively coerce ruamel.yaml CommentedMap/CommentedSeq to plain Python types.…, Read and validate a dispatch plan YAML file. Args: path: Path to a…, read_dispatch_plan() (+8 more)

### Community 179 - "ADR-3082-1: The control set is one SQLite database, content-keyed, with periodic global eviction"
Cohesion: 0.07
Nodes (28): ADR-3075-1: Content identity and cache scope for paginated responses (R8), Considered alternatives, Context, Decision, ADR-3075-2: Stale control-set entries requery instead of erroring; writes invalidate, Consequences, Considered alternative, Context (+20 more)

### Community 180 - "_call"
Cohesion: 0.10
Nodes (17): _call(), usefixtures, Live validation lifecycle: L1 creates an item, L2-L10 operate on it, L11…, L1: backlog_add creates a real GitHub issue., L2: backlog_list returns the item created in L1., L3: backlog_view by issue number returns full item data., L4: backlog_update attaches a plan path to the item., L5: backlog_update sets status to in-progress via GitHub label. (+9 more)

### Community 181 - "CommandResult"
Cohesion: 0.07
Nodes (18): CommandResult, Any, Return the columns the command wrote., Return the task row the command rendered, when it rendered one., Return the task rows a listing command rendered., Return how many rows a listing command counted., Return the report sections the command rendered., Return the bare no-op code the command printed instead of a result, when it did. (+10 more)

### Community 182 - "wrap_entry"
Cohesion: 0.08
Nodes (20): Normalize content into a sequence of complete, well-formed entry blocks.…, wrap_entry(), The guard adopts input only when it is ENTIRELY complete, well-formed entry…, Interstitial prose between two entry blocks is not silently swallowed. Tests:…, A non-entry ``<div>`` after a valid block is content, not part of the entry…, The guard is not over-tight — blank lines between blocks are not content., A shape-valid but calendar-impossible ID is rejected before it can be…, A section seeded with a calendar-impossible wrapper stays filterable by… (+12 more)

### Community 183 - "_paginate_body_result"
Cohesion: 0.11
Nodes (31): _paginate_body_result(), Apply offset/limit pagination to the ``body`` field of *result* in-place.…, Negative offset clamps to 0 (all entries) and must NOT report truncation. RED…, Intended contract: offset past the last entry → empty body, no flag. Mirrors…, A normal in-range page still reports remaining entries (no behavior change)., test_in_range_middle_page_reports_remaining(), test_negative_offset_returns_all_without_false_truncation(), test_offset_past_end_returns_empty_without_truncation_flag() (+23 more)

### Community 184 - "_patch_github_body"
Cohesion: 0.10
Nodes (22): MockerFixture, G2 — Over-budget gate honouring narrowing, directory fallback, token…, ``backlog_view`` must deliver the requested slice even when the item is large.…, section='RT-ICA' on an over-budget raw body returns that section's body.…, section='2' on an over-budget raw body returns the index-2 section, not a miss.…, offset/limit on an over-budget raw body must return the paged content. Arrange:…, sections=['RT-ICA','Issue Classification'] must return those sections' content.…, Locks the M1 fallback, substring widening, and m1 no-match signal. (+14 more)

### Community 185 - "properties"
Cohesion: 0.06
Nodes (31): type, additionalProperties, description, properties, type, type, description, type (+23 more)

### Community 186 - "Path"
Cohesion: 0.08
Nodes (22): plan_dir(), fixture, Path, Tests for P{NNN} addressing scheme -- plan number resolution and backward…, Test edge cases in P{NNN} numeric plan resolution. Tests: Variable padding,…, P1 resolves to P001-*.yaml (3-digit padding). Tests: Minimal input matching…, P1 resolves to P1-*.yaml (no padding). Tests: Unpadded file matching. How:…, Plan number 9999 resolves correctly. Tests: Large plan number boundary. How:… (+14 more)

### Community 187 - "test_ledger_check_order.py"
Cohesion: 0.08
Nodes (31): accept_accepted_and_unreported(), import_existing_and_leased(), import_source(), imported(), pairs_of(), Ordering tests for the checks ``ledger_spec.TRANSITIONS`` lists against each…, Return every ordered pair of one transition's checks, earlier first. Args:…, Return every ordered pair of checks the specification states, by command.… (+23 more)

### Community 188 - "plan-validator.md"
Cohesion: 0.06
Nodes (30): Aggregated Issue Reporting, Categorization (Pre-Validation), Decision Table: Drafting vs Ready Validation Modes, Dimension 10: Impact Radius Coverage, Dimension 1: Requirement Coverage, Dimension 2: Task Completeness, Dimension 3: Dependency Correctness, Dimension 4: Agent Capability Match (+22 more)

### Community 189 - "The work graph"
Cohesion: 0.06
Nodes (31): Acceptance criteria, An unresolved referent is an upstream task, not a deletion, Authority of a task's instructions, at runtime, Automation Boundary, Development Harness Architecture, Edge types, Falsified predicates, Invariants (+23 more)

### Community 190 - "workflow_multigraph/__init__.py"
Cohesion: 0.08
Nodes (27): DecompositionSourceKind, Protocol, Initialize the gate. Args: resolver: Resolves Tier-1 referents. reader: Reads…, Resolves a Tier-1 :class:`Referent` to what it names, or ``None`` when it does…, Return what ``referent`` resolves to, or ``None`` when it does not resolve.…, Reads the text a :class:`~dh_core.workflow_multigraph.descriptors.SourceSpan`…, Return the text at ``ref``, or ``None`` when ``ref`` does not exist. Args: ref:…, ReferentResolver (+19 more)

### Community 191 - "CallableMarkdownContentProvider"
Cohesion: 0.08
Nodes (20): Construct a navigator and load markdown via the provider. Args: provider:…, CallableMarkdownContentProvider, MarkdownContentProvider, Protocol, Protocol for objects that supply markdown content given a source string., Return the markdown content for the given source. Args: source: Source…, Wrap any callable that returns a string as a MarkdownContentProvider. Args: fn:…, Initialise with a callable that returns markdown text. Args: fn: Callable with… (+12 more)

### Community 192 - "Path"
Cohesion: 0.12
Nodes (14): find_agent(), Locate a single agent by name and return its…, Path, _build_manifest_name_index must return a dict mapping manifest name 'dh' to the…, A malformed JSON manifest must be skipped, not raise, so sibling plugins remain…, Two plugins declaring the same manifest name must raise ValueError. Why:…, find_agent('dh:tn-verification-gate') must resolve when the plugin directory is…, find_agent('development-harness:tn-verification-gate') must resolve and return… (+6 more)

### Community 193 - "codebase-analyzer.md"
Cohesion: 0.07
Nodes (29): Always Include File Paths, Analysis Blocked, Analysis Complete, ARCHITECTURE.md Template, Artifact Verification (3-Level), Be Prescriptive, Not Descriptive, CONCERNS.md Template, CONVENTIONS.md Template (+21 more)

### Community 194 - "feature-verifier.md"
Cohesion: 0.07
Nodes (29): Context Loading (Step 1), Evaluate Live Invocation Result, Evidence Block, Feature Verified, Find the Delivery Surface, Function Stubs, Gap: No Runtime Entry Point Found, Gaps Found (+21 more)

### Community 195 - "_process_trace"
Cohesion: 0.11
Nodes (20): build_branch_edges_from_l1(), _ensure_fork_stub(), _process_trace(), Add a stub decision node to *stubs* when *fork_id* is absent from *known*. Does…, Emit edges and stub nodes for a single L1 trace into mutable dicts. Routes_to…, Build branch and routes_to edges from L1 traces. Uses L1 directly rather than…, Tests for gap-edge wiring and gap_count computation in assemble_graph.py.…, Regression coverage: completes_workflow's existing deliberate design (routes_to… (+12 more)

### Community 196 - "migrate"
Cohesion: 0.10
Nodes (30): derive_slug(), migrate(), _parse_directory(), _parse_frontmatter(), parse_task_file(), _parse_task_from_block(), _patch_frontmatter_field(), _patch_segment_in_multi_task() (+22 more)

### Community 197 - "test_github_flag.py"
Cohesion: 0.12
Nodes (29): _make_cache_file(), _make_mock_task(), _make_task_file(), MockerFixture, Path, Task, Unit tests for the --github flag added to implementation_manager.py. Tests: CLI…, Write a minimal SAM tasks cache file. Args: tmp_path: Base directory; cache is… (+21 more)

### Community 198 - "beads_artifact_provider.py"
Cohesion: 0.09
Nodes (20): _extract_content_block(), _extract_manifest_from_metadata(), _is_dict_of_object(), _parse_manifest_value(), TypeGuard, Beads CLI artifact provider — full implementation (T09). Stores artifact…, Decode a raw manifest value into an ``ArtifactManifest``. Parameters ----------…, Extract content between sentinel markers from a notes string. Parameters… (+12 more)

### Community 199 - "resolve_plan_address"
Cohesion: 0.14
Nodes (29): AddressingError, Exception, Resolve a plan address string to a file system path. Resolution order: 1.…, Raised when an address cannot be resolved to a file system path. Args: address:…, resolve_plan_address(), Path, test_resolve_plan_address_collision_error_message_suggests_disambiguation(), test_resolve_plan_address_collision_raises_addressing_error_with_paths() (+21 more)

### Community 200 - "migrate_plan_artifacts.py"
Cohesion: 0.11
Nodes (28): Candidate, _classify(), _classify_codebase(), discover_candidates(), _extract_issue_from_file(), _find_issue_via_slug(), _load_backlog_items(), _log_candidate_summary() (+20 more)

### Community 201 - "test_plan_store_routing.py"
Cohesion: 0.10
Nodes (25): absent(), check_routing_defaults(), named(), Report whether a value is the one the parser leaves for a flag nobody passed.…, Return the flags of *flags* the caller actually passed. Args: flags: Flag name,…, Reject a routed flag whose parser default is a value a caller could pass.…, one_command_group(), parametrize (+17 more)

### Community 202 - "_build_parser"
Cohesion: 0.10
Nodes (28): _build_parser(), cmd_kill(), cmd_read(), cmd_send(), cmd_status(), cmd_stop(), _format_age(), main() (+20 more)

### Community 203 - "Path"
Cohesion: 0.09
Nodes (25): _make_spawn_args(), Path, Build a mock Namespace for cmd_spawn., Verify --worktree {name} appears in the argv passed to tmux new-session., Verify spawn polls until the claude-created tmux session appears., Verify spawn sends the initial prompt to the claude pane via tmux send-keys., Verify spawn fails if claude's tmux session never appears within timeout., Verify send calls _tmux_run_in_session with the message directly. (+17 more)

### Community 204 - "Multi-Perspective Review"
Cohesion: 0.07
Nodes (25): AC4 — Security REJECT on Hardcoded Secret, AC5 — Accessibility SKIP When No UI Changes, AC6 — Canonical Summary Line Format, Acceptance Test Guide — Multi-Perspective Review, Cleanup, Contents, Prerequisites, Dispatch Flow — Multi-Perspective Review (+17 more)

### Community 205 - "Backlog Item Groomer Agent"
Cohesion: 0.07
Nodes (26): Agent-Specific Grooming Rules, Backlog Item Groomer Agent, Bad Skill Characteristics, Core Principle, Efficiency Rules, Good Skill Characteristics, Input, MCP-Tool-Specific Grooming Rules (+18 more)

### Community 206 - "discover_repo"
Cohesion: 0.11
Nodes (17): discover_repo(), Discover the current repository's ``owner/repo`` slug. Resolution priority…, MonkeyPatch, discover_repo() respects the documented priority chain. Tests: GITHUB_REPO env…, GITHUB_REPO env var returns immediately without calling GitPython. Tests:…, GitPython remote parsing is called when GITHUB_REPO is absent. Tests:…, RepoDiscoveryError is raised when both methods fail. Tests: discover_repo…, RepoDiscoveryError.methods_tried contains both method names. Tests:… (+9 more)

### Community 207 - "Check"
Cohesion: 0.10
Nodes (17): Check, Observation, ObservationLog, BaseModel, StrEnum, Return every observation recorded under one check. Args: check: The behaviour…, Return every observation the loop left unsatisfied., Writes down what each check expected and what the loop saw, in the order it saw… (+9 more)

### Community 208 - "sam_task_create"
Cohesion: 0.15
Nodes (13): max, _emit_sam_result(), Validate repeatable string options at the CLI boundary. Returns: The validated…, Emit operation data on stdout and collected diagnostics on stderr., Create one SAM task under a parent issue., List SAM tasks under a parent issue., Update a SAM task status., List SAM tasks ready to start. (+5 more)

### Community 209 - "_Predicate"
Cohesion: 0.15
Nodes (14): _AndPred, _NotPred, _Predicate, Base class for search predicates. Subclasses implement ``__call__(item,…, Evaluate the predicate against a single backlog item. Args: item: Backlog item…, Conjunction: both sub-predicates must match., Negation: the sub-predicate must not match., Always-true predicate used as a safe no-op fallback. (+6 more)

### Community 210 - "assemble_graph.py"
Cohesion: 0.17
Nodes (25): _build_all_edges(), build_artifact_nodes(), build_calls_edges(), build_decision_nodes(), build_dispatches_edges(), build_reads_edges(), build_stores_in_edges(), build_writes_edges() (+17 more)

### Community 211 - "Backlog Item Lifecycle — Canonical Reference"
Cohesion: 0.08
Nodes (26): 1. Status Model, 2. Pipeline Stages, 3. State persistence and provider outcomes, 4. Route Reference, 5. Priority, 6. Groomed Item Content, Backend selection, Backlog Item Lifecycle — Canonical Reference (+18 more)

### Community 212 - "github_client.py"
Cohesion: 0.11
Nodes (23): _cert_fails_strict_checks(), _configured_ca_bundles(), _der_sequence_length(), _InstallState, _is_openssl_hashed_ca_directory(), _load_certificates(), _new_anchors(), _parse_pem_certificate_blocks() (+15 more)

### Community 213 - "_RECONCILIATION_NOT_IMPLEMENTED"
Cohesion: 0.13
Nodes (10): _RECONCILIATION_NOT_IMPLEMENTED, Verify _reconcile_closed_item handles closed GitHub issues correctly., Returns wip_protected when GitHub is closed but active local work exists., Returns closed and updates to terminal status when no active work exists., When GitHub has a terminal status label (e.g. 'done'), uses that instead of…, Verify ReconcileResult dataclass has all required fields and is constructible., ReconcileResult stores issue_number, action, old_status, new_status, and…, ReconcileResult can hold a non-empty warning string. (+2 more)

### Community 214 - "_build_ssl_context"
Cohesion: 0.11
Nodes (15): _build_ssl_context(), Build a context that trusts ca_bundle, clearing strict checks only when asked.…, The relaxation clears one flag. Every other guarantee must survive it., This is the whole point: the proxy CA carries no keyUsage extension., Finding 1: loading a compliant bundle must not also clear VERIFY_X509_STRICT.…, Clearing the strict flag must not weaken chain verification to optional or off., A relaxed extension check must not become a licence to accept any host., A context trusting nothing would fail closed rather than verify. (+7 more)

### Community 215 - "ledger_spec.py"
Cohesion: 0.11
Nodes (24): Check, _clear_attempt_effects(), _cols(), Command, Effect, EventKind, Flag, Provenance (+16 more)

### Community 216 - "cli.py"
Cohesion: 0.10
Nodes (17): ``sam known-failure-types`` -- the work-failure vocabulary, as JSON. Mirrors…, exit_with_json_error(), _is_result_mapping(), NoReturn, TypeGuard, Shared CLI output helpers used across the ``sam`` command modules. Extracted…, Narrow operation results to the mapping shape used for diagnostics. Returns:…, Emit ``payload`` as JSON to stdout, then exit nonzero. Unlike :func:`err`,… (+9 more)

### Community 217 - "_InMemoryArtifactBackend"
Cohesion: 0.10
Nodes (15): _InMemoryArtifactBackend, Any, artifact_list returns empty artifacts list when the issue has no manifest.…, artifact_read returns an error when the artifact type has no entry. Tests:…, Minimal in-memory ContentProvider double for MCP integration tests. Implements…, Initialise with empty storage., Return stored manifest or empty manifest. Args: issue_number: GitHub issue…, Store the manifest, stamping a fresh revision like a real put_content would.… (+7 more)

### Community 218 - "test_backlog_groom_sections.py"
Cohesion: 0.11
Nodes (24): _call(), parametrize, Tests for the sections parameter of the backlog_groom MCP tool. Covers: -…, backlog_groom forwards the sections dict unchanged to groom_item. Tests:…, backlog_groom forwards sections=None when parameter is omitted. Tests:…, backlog_groom with sections={} still calls groom_item (no short-circuit in…, backlog_groom with sections propagates BacklogError as error dict. Tests:…, backlog_groom returns error dict when sections is combined with any per-section… (+16 more)

### Community 219 - "test_migrate_tasks_to_github.py"
Cohesion: 0.12
Nodes (23): _make_mock_issue(), _make_task_file(), _make_two_task_file(), parametrize, Path, Tests for migrate_tasks_to_github.py migration script. migrate_tasks_to_github…, Create a minimal IssueNode dict with the given issue number. The production…, create_task_issue/get_github/SamTask are non-None in this environment.… (+15 more)

### Community 220 - "test_rtica_verdict_vocabulary_drift.py"
Cohesion: 0.11
Nodes (24): _assigned_verdicts(), _labelled_verdicts(), Path, Guards the RT-ICA verdict vocabulary against producer/consumer drift. Two…, Extract the verdict tokens a label introduces. Handles a single token…, Collect every verdict-labelled token in a file. A label is only reported when…, Collect every pseudocode-assignment verdict token in a file. Complements…, Return the text of a skill's verdict-vocabulary section. Args: path: Skill file… (+16 more)

### Community 221 - "MockerFixture"
Cohesion: 0.16
Nodes (16): _discover_via_git(), Parse the ``origin`` remote URL via GitPython to extract ``owner/repo``. Opens…, _make_mock_repo(), MockerFixture, Path, Return a mock git.Repo whose origin remote URL is set to *url*., _discover_via_git parses the git remote origin URL via GitPython. Priority 2 in…, Returns None when git.Repo raises InvalidGitRepositoryError. Tests:… (+8 more)

### Community 222 - "RepoDiscoveryError"
Cohesion: 0.11
Nodes (16): Exception, Raised when all repository discovery methods fail. Attributes: methods_tried:…, RepoDiscoveryError, clear_discover_repo_cache(), fixture, Tests for repository discovery in backlog_core.models. Covers: discover_repo()…, Error message includes actionable fix instructions. Tests: RepoDiscoveryError…, error.message attribute equals str(error). Tests: RepoDiscoveryError.message… (+8 more)

### Community 223 - "backlog_core/tests/conftest.py"
Cohesion: 0.14
Nodes (13): AbstractSet, _ensure_cl100k_cached(), Offline-safe ``tiktoken`` for backlog_core view tests (PR #2496 Codex finding).…, Deterministic ~4-chars-per-token stand-in for cl100k_base (offline only).…, Return a token list whose length tracks the input length monotonically., Pre-warm tiktoken's encoding cache so importing ``server`` never downloads.…, _StubEncoder, Tests for the offline-safe tiktoken cache pre-warm installed by conftest (PR… (+5 more)

### Community 224 - "_make_snippet_parts"
Cohesion: 0.10
Nodes (24): _format_match_text(), _make_snippet(), _make_snippet_parts(), _parse_body_sections(), Tokenize a search query into a flat list of tokens. Tokens are one of: ``(``,…, Parse a markdown body string into (section_slug, text) tuples. Splits on ``##…, Extract a snippet around a match position with sliding-window budget. The total…, Compute snippet parts for a match, enabling both plain and formatted output.… (+16 more)

### Community 225 - "DH Workflow Graph — Data Schema"
Cohesion: 0.08
Nodes (24): agent, artifact, backend, Cytoscape.js consumption, DH Workflow Graph — Data Schema, Edge type enum, Edge types, Extraction Pipeline Files (+16 more)

### Community 226 - "Blind completeness audit — the workflow multigraph"
Cohesion: 0.08
Nodes (23): Blind completeness audit — the workflow multigraph, COMPLETENESS-10 — Hierarchy is nominal; `subgraph_ref` has no referent, COMPLETENESS-11 — No entry or terminal marking, and unused outputs are uncovered, COMPLETENESS-12 — Unnecessary path length cannot be reported at all, COMPLETENESS-13 — `ExtractionStatus.ASSUMED` and `ABSENT` cannot be recorded without inventing a span, COMPLETENESS-14 — Revision checking passes silently when either side is unversioned; no snapshot or fingerprint entity, COMPLETENESS-15 — A failure signal is not something an edge can carry, COMPLETENESS-16 — One-time versus recurring work has no carrier (+15 more)

### Community 227 - "TestTaskFieldValidators"
Cohesion: 0.08
Nodes (13): Verify Task.validate_task_id_list field validator. Tests: dependencies and…, Verify list of task IDs accepted., Verify comma-separated string parsed into list., Verify None dependency returns empty list., Verify 'none' string returns empty list., Verify 'n/a' string returns empty list., Verify '-' string returns empty list., Verify empty string returns empty list. (+5 more)

### Community 228 - "test_agent_profile/conftest.py"
Cohesion: 0.17
Nodes (23): circular_plugin_root(), _clear_manifest_index_cache(), domain_plugin_root(), manifest_plugin_root(), multi_plugin_root(), fixture, Path, Shared fixtures for agent_profile unit tests. All fixtures use tmp_path and… (+15 more)

### Community 229 - "test_github_tools_labels.py"
Cohesion: 0.12
Nodes (22): _call(), _make_label(), MonkeyPatch, Tests for backlog_list_labels MCP tool and list_labels operation. Tests are…, list_labels maps None description to empty string., backlog_list_labels tool returns labels list with count and output keys., backlog_list_labels calls list_labels with default limit=100 when omitted., backlog_list_labels returns dict with error key on BacklogError. (+14 more)

### Community 230 - "SOP (Code Review)"
Cohesion: 0.09
Nodes (22): API Contract Compliance, BLOCKED Format, Code Reviewer Agent, Correctness, Error Handling, Important Output Note, Naming and Readability, Output Format (+14 more)

### Community 231 - "bundle_requires_relaxed_verification"
Cohesion: 0.12
Nodes (13): bundle_requires_relaxed_verification(), Decide whether ca_bundle adds an anchor that VERIFY_X509_STRICT would reject. A…, Only a locally added anchor that strict verification rejects earns the…, Nix and conda point these variables at a copy of the public roots. The public…, The proxy CA shape this module exists for: verify code 92., Verify code 89: Basic Constraints of CA cert not marked critical., Verify code 79: invalid CA certificate., Verify code 86: CA certificate missing a SubjectKeyIdentifier extension.… (+5 more)

### Community 232 - "parse_jsonl_events"
Cohesion: 0.16
Nodes (20): find_first_event(), _iter_json_lines(), parse_jsonl_events(), Any, Path, Shared JSONL parsing utilities for Claude Code session transcript handling., Yield each well-formed JSON object in a JSONL file. Skips blank lines and lines…, Parse a JSONL file and optionally filter by event type. Handles missing files… (+12 more)

### Community 233 - "test_single_item_status_refusal.py"
Cohesion: 0.17
Nodes (15): _item(), _patch_repo(), Exception, MockerFixture, parametrize, Tests for how a refused GraphQL query reaches the single-item status path.…, ``get_github`` raising is the no-token path, not an environment-wide refusal., Build a minimal backlog item carrying the given issue reference. (+7 more)

### Community 234 - "test_status_source_wire.py"
Cohesion: 0.12
Nodes (12): BacklogViewResponse, Response for ``backlog_view`` -- covers all seven of its disclosure-mode shapes., _call(), Wire-level regression tests for #3546's typed degradation-provenance fields.…, ``backlog_view`` over the in-memory FastMCP transport, both response shapes., The default call path -- _build_compact_manifest must not drop the field., Direct proof that ``_respond`` preserves the new fields., The independent response model must declare the provenance fields explicitly. (+4 more)

### Community 235 - "Instruction"
Cohesion: 0.13
Nodes (15): DecompositionGate, normalize(), The decomposition-exit gate over a task's instructions. Constructed against a…, Check every instruction against the tier it declares. Args: instructions: The…, Return whether any finding over ``instructions`` is severity ``BROKEN``. Args:…, Check one ``DELEGATING`` instruction's referents against Tier 1. Args:…, Check one ``ASSERTING`` instruction's spans against Tier 2. Args: instruction:…, Return whether ``quote`` appears verbatim (whitespace-normalized) in the text… (+7 more)

### Community 236 - "Node"
Cohesion: 0.13
Nodes (20): Node, Return the named output descriptor, or None when the node declares no such…, Return the named required or optional input, or None when the node declares no…, One node of the layer-3 (workflow) graph, as the contract's node record states…, Authority, ErrorRoute, EvidenceRequirement, Operation (+12 more)

### Community 237 - "TestBuildIssueBodyFromFileDict"
Cohesion: 0.14
Nodes (11): skip, fixture, Tests for _build_issue_body_from_file(item: dict) -> str | None. This is the…, Narrow *build_fn* for ty; body never runs while the class is skipped., Skip — scripts/backlog.py was intentionally deleted; class is skipped. The…, Dict item without '## Groomed' in _raw_body returns None. Tests: Gate logic for…, Dict item with '## Groomed' in _raw_body returns stripped body + newline.…, All sections from _raw_body appear exactly once — no duplication. Tests:… (+3 more)

### Community 238 - "Groom Milestone"
Cohesion: 0.09
Nodes (21): `conflict_groups`, Creating Plans via MCP, Dispatch Plan Schema, Field Definitions, Full Schema Example, Integration Branch Naming, `milestone`, Ordering Rules (+13 more)

### Community 239 - "dispatch_task"
Cohesion: 0.13
Nodes (23): add_reports(), burn_attempts(), complete_and_accept(), dispatch_task(), Connection, Dispatch one task and return the attempt it opened. Args: conn: An open ledger…, Append every report section for one attempt, so ``report-missing`` passes.…, Dispatch and settle a task, leaving it in-progress with its attempt closed.… (+15 more)

### Community 240 - "Context Refinement Agent"
Cohesion: 0.09
Nodes (21): Context About Your Invocation, Context Refinement Agent, Examples, If Blocked, Inputs, On Success - Context Updated, On Success - Intent Divergence Found, On Success - No Updates Needed (+13 more)

### Community 241 - "ecosystem-researcher.md"
Cohesion: 0.09
Nodes (21): Comparison Analysis Template, Ecosystem Discovery Template, Feasibility Assessment Template, If Blocked, Mode 1: Ecosystem Discovery, Mode 2: Feasibility Assessment, Mode 3: Comparison Analysis, On Success (+13 more)

### Community 242 - "feature-researcher.md"
Cohesion: 0.09
Nodes (21): Behavior Gaps, Discovery is Understanding, Not Design, Discovery Quality (Core Deliverables), Feature Context Document Structure, Honest Reporting, Integration Gaps, Large Document Strategy, Scope Gaps (+13 more)

### Community 243 - "dispatch_state.py"
Cohesion: 0.12
Nodes (13): BeadsDispatchAdapter, dispatch_stale_check(), SQLite-backed state manager for dispatch orchestration. This module is…, Thin adapter that records wave membership in beads molecule epics. SQLite…, Initialise adapter and load the wave→molecule ID sidecar. Args: db_path: Path…, Return the sidecar dict key for a (milestone, wave_num) pair., Read the sidecar JSON file into a mapping. Returns: Mapping of…, Persist the in-memory wave→molecule map to the sidecar file. (+5 more)

### Community 244 - "TestSelectorAndSlugGeneration"
Cohesion: 0.09
Nodes (12): Selectors encode heading depth and sibling index; slugs are URL-safe., First (and only) h1 gets selector 'h1.1'., Title' heading produces slug 'title'., First h2 (child of h1.1) gets selector 'h2.1.1'., Section A' heading produces slug 'section-a'., h3 under h2.1.1 gets selector 'h3.1.1.1'., Sub A' heading produces slug 'sub-a'., Second h2 sibling gets selector 'h2.1.2' (sibling index 2, not 1). (+4 more)

### Community 245 - "Artifact Conventions"
Cohesion: 0.09
Nodes (22): Artifact Conventions, Artifact Lifecycle, Artifact System, Artifact Types, Backlog System, CONTEXT, Cross-Reference Token Pattern, Cross-Referencing Between Artifacts (+14 more)

### Community 246 - "TestStatusMap"
Cohesion: 0.09
Nodes (12): Verify STATUS_MAP contains expected normalization mappings., Verify 'NOT STARTED' maps to 'not-started'., Verify 'IN PROGRESS' maps to 'in-progress'., Verify 'COMPLETE' maps to 'complete'., Verify ':white_check_mark:' emoji maps to 'complete'., Verify ':x:' emoji maps to 'not-started'., Verify '[DEFERRED]' title marker maps to 'deferred'., Verify '[SKIPPED]' title marker maps to 'skipped'. (+4 more)

### Community 247 - "_load_frontmatter_from_path"
Cohesion: 0.13
Nodes (20): _load_frontmatter_from_path(), _load_md_frontmatter(), _normalize_skills(), Any, Path, Parse YAML frontmatter and body from a markdown string. Args: text: Markdown…, Load frontmatter from a file path. Args: path: Path to a markdown file with…, Normalise raw YAML skills value to a flat list of stripped strings. Args: raw:… (+12 more)

### Community 248 - "Planner RT-ICA (Planning-Phase Input Completeness Analysis)"
Cohesion: 0.10
Nodes (20): 1. Completeness Summary, 2. Missing Inputs (By Dependency), 3. Autonomous Decisions and Derivations, 3A. Report Back For Review, 4. Required Unblock Actions, 5. Planning Annotations to Apply, Ambiguity Escalation Rules, Behavioral Rules for the Planner (+12 more)

### Community 249 - "test_ledger_spec.py"
Cohesion: 0.10
Nodes (5): Status, parametrize, Closure tests over ``dh_core.ledger_spec``. Each test names one way the…, test_every_task_command_handles_every_status_exactly_once(), test_model_fields_match_models()

### Community 250 - "Path"
Cohesion: 0.10
Nodes (21): first_party_module_paths(), preparation(), Path, Resolve the toolchain and lay out a state root under one test's own directory.…, Return the file of every module inside :data:`PACKAGE_ROOT` that one source…, ``rules/python-development.md``: the modules a split PEP 723 script imports are…, A module added outside the library package must not fall out of the scans above., The runner must run on Windows, so nothing below the shebang may assume a POSIX… (+13 more)

### Community 251 - "Context-Gathering Agent"
Cohesion: 0.10
Nodes (19): Code Organization, Common Python CLI Patterns, Context-Gathering Agent, CRITICAL CONTEXT: Why You've Been Invoked, CRITICAL RESTRICTION, Examples of What You're Looking For, External Framework Artifacts, If Blocked (+11 more)

### Community 252 - ".verify_legacy_item"
Cohesion: 0.14
Nodes (10): LegacyMigrationError, OSError, Path, ValueError, Legacy item cannot be migrated without data loss., Parse a legacy item and verify its YAML representation without persisting it.…, Persist one verified legacy item as a YAML snapshot beside its source. Args:…, Fold a directory-level traversal failure into ``skipped`` as ``os.walk``'s… (+2 more)

### Community 253 - "merge_integration_branch"
Cohesion: 0.14
Nodes (14): merge_integration_branch(), MergeResult, Merge ``head_branch`` into ``base_branch``. Uses PyGithub's ``repo.merge()``…, _make_github_exception(), GithubException, merge_integration_branch merges head into base and handles conflicts., Test successful merge returns MergeResult with sha and message. Tests:…, Test repo.merge() is called with base, head, and commit_message. Tests:… (+6 more)

### Community 254 - "_validate_slug"
Cohesion: 0.14
Nodes (12): Validate slug against the required pattern. Args: slug: Hyphenated slug string…, _validate_slug(), _validate_slug enforces ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ pattern., Test valid simple slug passes without raising. Tests: _validate_slug — valid…, Test valid slug with dots and underscores passes. Tests: _validate_slug — valid…, Test empty string raises BacklogError. Tests: _validate_slug — empty string…, Test slug starting with hyphen raises BacklogError. Tests: _validate_slug —…, Test slug starting with dot raises BacklogError. Tests: _validate_slug — first… (+4 more)

### Community 255 - "make_github_client"
Cohesion: 0.14
Nodes (11): make_github_client(), Build a PyGithub client that works on a normal network and behind a TLS proxy.…, Finding 3's chosen resolution: make_github_client always installs first. Since…, The documented default reaches the client rather than PyGithub's own 15s., Read the HTTPS connection class one already-built Requester instance captured.…, Client construction resolves the token and the API root., Construction fails fast rather than deferring to an opaque 401., GitHub Enterprise installs are configured through the environment. (+3 more)

### Community 256 - "find_content_duplicates"
Cohesion: 0.21
Nodes (8): find_content_duplicates(), Find existing backlog items whose content overlaps the given title/description.…, _candidate(), parametrize, The real #3169 failure case: reworded duplicate the old SequenceMatcher…, Real, resolved, unrelated backlog_core/backlog-mcp issues must never match. See…, Tests for find_content_duplicates(title, description, candidates, max_results)., TestFindContentDuplicates

### Community 257 - "TestCodeBlocks"
Cohesion: 0.10
Nodes (11): Code blocks are attributed to sections with correct language and spans., Document with two fenced code blocks produces exactly two CodeBlock entries., First code block (code_0001) has language 'python'., Python block section_id resolves to 'Section A'., Python block fence occupies lines 8-10 inclusive (0-based)., Second code block (code_0002) has language 'bash'., Bash block section_id resolves to 'Section B'., Bash block fence occupies lines 20-22 inclusive (0-based). (+3 more)

### Community 258 - "Cursor agent (IDE Agent mode + `agent` / `cursor-agent` CLI) — harness facts"
Cohesion: 0.10
Nodes (19): 1. Can the agent run a shell command, read a file, write a file? (tool names), 2. Hooks: events, payload fields, `hooks.json` location, plugin-shipped hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP: can project config or a plugin register an MCP server? — **Both, yes.**, 6. Environment variables set for a shell command the harness runs, After-tool and stop events — full field lists, Can a plugin ship hooks? — **Yes.** (+11 more)

### Community 259 - "Model fidelity — the workflow multigraph against `ledger_spec.py` and `sam_schema/core/models.py`"
Cohesion: 0.10
Nodes (19): A note on the contract, stated rather than worked around, FIDELITY-10 — a specification's quantified rules have no representation in a ground graph, FIDELITY-11 — ordered checks, waivers, and the refusal/noop/outcome trichotomy are lost, FIDELITY-12 — type satisfaction is string equality, so a value range is invisible, FIDELITY-13 — half the declared edge types are inert, and the semantic queries read node attributes, FIDELITY-14 — thirteen required node-record fields are read by nothing, and the extraction defaults them, FIDELITY-15 — every source span in the extraction is a bare 1220-line file path, FIDELITY-1 — the D1 fragment is `OBSERVED` from a source that states the opposite (+11 more)

### Community 260 - ".__init__"
Cohesion: 0.11
Nodes (10): Initialize with the plan ID and the bookend validation failures. Args: plan_id:…, Initialize with the plan ID and failure reason. Args: plan_id: The plan…, Initialize with a descriptive configuration guidance message., Initialize with the plan ID that cannot be claimed concurrently. Args: plan_id:…, Initialize with the opaque content reference that failed. Args: content_ref:…, Initialize with the plan ID that could not be found. Args: plan_id: The plan…, Initialize with the duplicate plan ID. Args: plan_id: The plan identifier that…, Initialize with the plan and task identifiers. Args: plan_id: The plan the task… (+2 more)

### Community 261 - "Structured SAM Commands"
Cohesion: 0.10
Nodes (20): CLAUDE_SKILLS_DISABLED_HOOKS, Dependency Resolution, dispatch, Example, Hook Configuration, Hook Integration, Hook Runtime Controls, How It Works (+12 more)

### Community 262 - "Groom: Swarm"
Cohesion: 0.10
Nodes (20): Agents, Description / AC separation, Dispatch sequence, Fact-Checker output contract, Groom: Swarm, Groomer prompt, Impact Radius — what the impact-analyst produces, Issue Classification (+12 more)

### Community 263 - "test_cli.py"
Cohesion: 0.10
Nodes (19): Tests for sam_schema.cli — Typer CLI commands via CliRunner., List --offset 0 --limit 1 returns at most one item., Read with completely invalid address exits 1 with error message., A UID id spelled with alternating upper/lower hex digits canonicalises to one…, A lowercase ``p`` prefix paired with uppercase hex digits still canonicalises.…, --help output lists the grouped command domains., Flat paths, positional data, and removed flags fail at the parser boundary., The default is every row, emitted as one line of compact JSON. (+11 more)

### Community 264 - "Path"
Cohesion: 0.10
Nodes (20): Path, An attempt belongs to a task, so ``--attempt`` with a plan-only address exits 1…, Status with non-existent plan_dir exits 1., append-task uses named typed task fields., Ready P1 returns a JSON envelope with ready_tasks (may be empty or contain…, State P1/T3 in-progress updates status and prints old -> new., State rejects an invalid typed status before execution., Successful plan commands emit compact JSON on stdout. (+12 more)

### Community 265 - "TestChunkText"
Cohesion: 0.10
Nodes (11): Tests for the module-level chunk_text function from list_navigator., chunk_text('') returns ['']., Text that fits within the budget is returned as-is., Joining all chunks reproduces the original text exactly., Every chunk produced fits within the specified budget., Splits occur at blank-line breaks before single newlines., The double-newline paragraph delimiter appears in the chunks., A single word-dense line is split via char bisection. (+3 more)

### Community 266 - "TestCommitPrefixRegex"
Cohesion: 0.11
Nodes (6): parametrize, Module-level constants have correct types and values., DEFAULT_REPO is empty before init(); discover_repo() resolves it., COMMIT_PREFIX_RE strips conventional-commit prefixes., TestCommitPrefixRegex, TestConstants

### Community 267 - "TestLegacyPathMap"
Cohesion: 0.10
Nodes (11): Tests for LEGACY_PATH_MAP constant: presence, mapping correctness, callability.…, Verify .claude/backlog key is present in LEGACY_PATH_MAP. Tests:…, Verify plan key is present in LEGACY_PATH_MAP. Tests: LEGACY_PATH_MAP key…, Verify .claude/context key is present in LEGACY_PATH_MAP. Tests:…, Verify .claude/reports key is present in LEGACY_PATH_MAP. Tests:…, Verify .claude/backlog maps to the string 'backlog_dir'. Tests: LEGACY_PATH_MAP…, Verify plan maps to the string 'plan_dir'. Tests: LEGACY_PATH_MAP maps plan…, Verify .claude/context maps to the string 'context_dir'. Tests: LEGACY_PATH_MAP… (+3 more)

### Community 268 - "test_network_guard.py"
Cohesion: 0.16
Nodes (19): plugin_root_probe(), _probe_command(), Path, Proves the session-level socket guard in the root conftest blocks the network.…, An ``@pytest.mark.e2e`` test without the env var is still blocked. The block…, With both the marker and the env var, the policy gate opens. Asserts the guard…, The gate stays open while a class-scoped e2e fixture tears down. A class-scoped…, After a pytest subprocess finishes, the parent process sockets are intact. Runs… (+11 more)

### Community 269 - "test_retired_terms.py"
Cohesion: 0.16
Nodes (19): _find_hits(), _iter_runtime_files(), parametrize, Path, Guards runtime-read plugin files against retired-term regressions (PR #3427).…, Return every file an installed Claude Code agent can read or run at runtime.…, Return `path` relative to whichever scan root owns it, for a readable failure…, Return one `path:line: text` entry per runtime-corpus match of `term`. Matches… (+11 more)

### Community 270 - "Development Harness Plugin - AI-Facing Documentation"
Cohesion: 0.11
Nodes (19): Agents Overview, ARL Human Touchpoints, Artifact Manifest System, Backend Providers, Composition Model, Development Harness Plugin - AI-Facing Documentation, Dispatch Orchestration System, Documentation Update Triggers (+11 more)

### Community 271 - "Performance Reviewer Agent"
Cohesion: 0.11
Nodes (18): BLOCKED Format, Blocking I/O in Async Paths, Hot-Loop Allocations, Important Output Note, Input, N+1 Query Detection, Output Format, Performance Reviewer Agent (+10 more)

### Community 272 - "_validate_metadata"
Cohesion: 0.13
Nodes (12): Any, Coerce raw YAML metadata values to ``str`` or ``dict[str, str]`` at the parse…, _validate_metadata(), Tests for _validate_metadata — the YAML metadata boundary coercion function., Integer values must be coerced to strings at the YAML boundary. Tests:…, None values (YAML null) must be coerced to empty string. Tests:…, List values must be coerced to their string representation. Tests:…, Boolean values must be coerced to strings. Tests: _validate_metadata bool… (+4 more)

### Community 273 - "_make_struck_sections"
Cohesion: 0.11
Nodes (15): _make_struck_sections(), NormalizedSection, ``build_map()``'s level-1 aggregate content must flag struck entries in-band…, resolve('0').content must contain '[struck:{entry_id}]' immediately before the…, ``format_map_line()`` must prefix a struck marker before the title (§3.3). The…, A struck level-2 entry's map line starts with '{ordinal} [struck] ', and the…, Build ``list[NormalizedSection]`` with per-entry struck flags and entry IDs.…, A sub-heading node inside a struck entry inherits the parent's struck flag and… (+7 more)

### Community 274 - "Any"
Cohesion: 0.16
Nodes (19): build_agent_nodes(), _build_all_nodes(), build_backend_nodes(), build_mcp_tool_nodes(), build_reference_file_nodes(), build_skill_nodes(), build_terminal_stub_node(), _emit_unroutable_trace() (+11 more)

### Community 275 - "Findings — finding verification: the falsified predicates, and the severity rule"
Cohesion: 0.11
Nodes (18): Coverage at a glance, Findings — finding verification: the falsified predicates, and the severity rule, PREDICATES-10 — the four pairwise predicates silently skip any edge that does not bind both descriptors, PREDICATES-11 — descriptor facets are marked OBSERVED against spans that do not state them, PREDICATES-12 — the severity rule: `BROKEN` is reachable where `CONTRACT_UNSPECIFIED` is required, PREDICATES-13 — a `Finding` is not bound to the `Graph` it claims to be about, PREDICATES-14 — three of the eight queries have no test, and the taxonomy-to-contract match is unasserted, PREDICATES-15 — hierarchy: `subgraph_ref` resolves to nothing, and no predicate descends (+10 more)

### Community 276 - "ledger_holds"
Cohesion: 0.13
Nodes (18): ledger_holds(), _noop(), _open(), Connection, NoReturn, Answer whether the ledger already carries a plan, the way…, Print a refusal's reason code on stderr and exit non-zero. Args: reason: A…, Print a no-op's reason code on stdout and exit zero. Args: reason: A… (+10 more)

### Community 277 - "SAM Stage 5 — Execution"
Cohesion: 0.11
Nodes (18): Behavioral Rules, Core Principle, Dependency Ordering, Input, Key Constraints, Output, Process, Role (+10 more)

### Community 278 - "Workflow: Create Backlog Item"
Cohesion: 0.11
Nodes (17): Create - backlog item - Scope boundary, Rule: Behavioral/process items — preserve the procedural description, Rule: To create an excellent backlog item, describe the problem, not the solution, Step 0: Classify the item type, Completion criteria, Error handling, Inputs, Mode: `auto` (+9 more)

### Community 279 - "TestRealPluginsIntegration"
Cohesion: 0.11
Nodes (12): fixture, integration, MonkeyPatch, Integration tests using the real plugins/ filesystem. Tests: profile_load and…, Set CLAUDE_PLUGIN_ROOT to the development-harness plugin directory. In the MCP…, profile_list against real plugins returns at least one agent. Tests: Real-…, profile_list filtered to development-harness returns >= 1 agent. Tests: Plugin-…, profile_load for 'task-worker' returns a non-empty instruction body. Tests:… (+4 more)

### Community 280 - "Path"
Cohesion: 0.15
Nodes (11): Path, Returns (True, reason) when a plan file has a task with legacy IN PROGRESS…, Returns (True, reason) when a plan file has a task with YAML status: in-…, Returns (False, '') when plan file exists but all tasks are COMPLETE., Returns (True, reason) when an active-task context file references the item's…, Returns (False, '') when context files exist but reference a different issue., Returns (False, '') when item has no _topic field — skips plan file check., Returns (False, '') when item has a non-numeric _issue field. (+3 more)

### Community 281 - "Documentation Drift Auditor"
Cohesion: 0.11
Nodes (17): Analysis Techniques, BLOCKED Format (use when you cannot proceed), Documentation Drift Auditor, Documentation Locations, For Documentation Claims, For Git History, For Python Code Structure, For Typer/Click CLI Commands (+9 more)

### Community 282 - "_discover_via_env"
Cohesion: 0.14
Nodes (12): _discover_repo_with_root(), _discover_via_env(), Return the ``GITHUB_REPO`` environment variable value if set and valid.…, Discover the ``owner/repo`` slug using an already-resolved *repo_root*.…, _discover_via_env reads GITHUB_REPO from the environment. Priority 1 in the…, Returns validated slug when GITHUB_REPO is set to a valid value. Tests:…, Returns None when GITHUB_REPO is absent from the environment. Tests:…, Returns None when GITHUB_REPO is set to an empty string. Tests:… (+4 more)

### Community 283 - "TestParentChildRelationships"
Cohesion: 0.11
Nodes (10): Parent IDs and child_ids lists reflect heading nesting depth., Title (h1) has exactly two direct children., Title's children are Section A and Section B in document order., Section A has exactly one child: Sub A., Sub A (h3) is a leaf section with an empty child_ids list., Section B (h2) is a leaf section with an empty child_ids list., Both h2 sections have the h1 Title section as their direct parent., Sub A's parent is Section A (not Title). (+2 more)

### Community 284 - "TestBodySpanBoundaries"
Cohesion: 0.11
Nodes (10): body_span and heading_span encode precise line ranges for each section. The…, h1 'Title' heading occupies only line 0 (start_line == end_line == 0)., h1 body (intro prose) spans lines 1-3, before the first h2 at line 4., Section A heading occupies only line 4., Section A body spans lines 5-11 (line before Sub A heading at 12)., Sub A heading occupies only line 12., Sub A body (leaf, no children) spans lines 13-15., Section B heading occupies only line 16. (+2 more)

### Community 285 - "dh_config.py"
Cohesion: 0.16
Nodes (16): _auto_detect_beads(), _dh_user_root_path(), _get_config_search_paths(), _is_str_dict(), _load_yaml_config(), Path, TypeGuard, DHConfig — unified backend-name resolver using .dh/config.yaml. Resolution… (+8 more)

### Community 286 - "validator.py"
Cohesion: 0.12
Nodes (16): Shared constants for dispatch_schema. Kept in a leaf module (no imports from…, _build_issue_wave_map(), _check_conflict_group_refs(), _check_conflict_group_wave_placement(), _check_depends_on_existence(), _check_duplicate_issues(), _check_wave_ordering(), _parallel_conflict_group_has_violation() (+8 more)

### Community 287 - "Groomed"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Acceptance Criteria Verification, Agents, Decision, Dependencies, Fact-Check, Files, Groomed (+9 more)

### Community 288 - "TestTaskStatusEnum"
Cohesion: 0.11
Nodes (10): Verify TaskStatus StrEnum members and values. Tests: Canonical status values…, Verify NOT_STARTED maps to 'not-started'., Verify IN_PROGRESS maps to 'in-progress'., Verify COMPLETE maps to 'complete'., Verify BLOCKED maps to 'blocked'., Verify DEFERRED maps to 'deferred'., Verify SKIPPED maps to 'skipped'., Verify FAILED maps to 'failed'. (+2 more)

### Community 289 - "_call"
Cohesion: 0.11
Nodes (16): _call(), backlog_list_projects tool returns projects list with count and output keys.…, backlog_list_projects forwards owner and limit to list_projects. Tests:…, backlog_list_projects returns dict with error key on BacklogError. Tests:…, backlog_list_projects returns count=0 and empty list when no projects exist.…, backlog_create_project tool returns project_id, title, url, and number. Tests:…, backlog_create_project forwards title and owner to create_project. Tests:…, Call an MCP tool through the in-memory FastMCP transport and parse result.… (+8 more)

### Community 290 - "TestEndToEndQueryToResult"
Cohesion: 0.11
Nodes (10): End-to-end tests exercising the full path: user query -> backlog_list call ->…, Full e2e path: create items, issue query via backlog_list, receive matched…, Fallback chain e2e: Strategy 1 (substring) finds match immediately — no…, Fallback chain e2e: Strategy 1 (substring) returns zero -> Strategy 2 (filter-…, Fallback chain e2e: Strategy 1 and 2 return zero -> Strategy 3 (LLM semantic)…, Fallback chain e2e: all 3 strategy transitions are observable in sequence.…, Backward compatibility: existing callers using only title= produce identical…, Backward compatibility: calling backlog_list with no params returns all items. (+2 more)

### Community 291 - "SOP"
Cohesion: 0.12
Nodes (16): Accessibility Reviewer Agent, BLOCKED Format, Important Output Note, Output Format, Role, SOP, Status Output (MANDATORY), Step 1: Read Verdict Schema (+8 more)

### Community 292 - "resolve_ca_bundle"
Cohesion: 0.17
Nodes (9): Return the CA bundle path an interception proxy has configured, if any.…, resolve_ca_bundle(), A CA bundle counts only when the path it names exists on disk., A stale path is not a configured proxy, so it is skipped rather than trusted., Nix/conda's SSL_CERT_FILE must not shadow a proxy's REQUESTS_CA_BUNDLE. A Nix…, CURL_CA_BUNDLE is requests' own documented cURL-compatibility fallback.…, Finding 2: Requests accepts a hashed CA directory through ``ca_cert_dir``.…, An arbitrary directory is not a CA directory just because it exists. (+1 more)

### Community 293 - "Refusal"
Cohesion: 0.15
Nodes (15): Exception, A command refused, carrying the ``ledger_spec.REASONS`` code that names why.…, Store the reason code. Args: reason: A ``ledger_spec.REASONS`` code of kind…, Refusal, _create_plan(), MonkeyPatch, Path, _raise_network_filesystem() (+7 more)

### Community 294 - "Findings: producers without consumers between grooming and the bookends"
Cohesion: 0.12
Nodes (15): A dependent waits for completion, not for acceptance, ADR-3460-2: Add the missing relations to the ledger, and finish the migration, rather than replace Task and Plan, Alternatives considered and rejected, Consequences, Context, Decision, The orchestrator loop, What is open (+7 more)

### Community 295 - "MCP Progressive-Disclosure Contract"
Cohesion: 0.12
Nodes (17): Backward Compatibility, Code-block node (`has_children=False`, code fence body), Degradation and Diagnostic Fields, EXTRACT-on-parent (with `head=N`), Generic Backend Error, In-band markers, Leaf node (`has_children=False`, not a code block), MCP Progressive-Disclosure Contract (+9 more)

### Community 296 - "Backlog Lifecycle Process Audit"
Cohesion: 0.12
Nodes (16): Backlog Lifecycle Process Audit, Excellence Checklist Results, Finding 10: Draft Lifecycle Doc Exists But Isn't Promoted, Finding 1: No Feasibility Assessment Step Exists, Finding 2: "Discussion" Phase Is Absent, Finding 3: RT-ICA Runs Twice (Redundantly), Finding 4: Vague Conditions in Groom Step 2, Finding 5: Step Numbering Is Non-Sequential and Fragmented (+8 more)

### Community 297 - "DH Workflow Trace — Collection Methodology"
Cohesion: 0.12
Nodes (16): Actor topology (the field pass 1 lacked entirely), Collection protocol (correct order), Conditional topology, DH Workflow Trace — Collection Methodology, Execution model: spans, not steps, How this maps to overlays, Ordering rule (enforced), Phase 0 — Validation gate (mandatory before any fan-out) (+8 more)

### Community 298 - "run_bounded.py"
Cohesion: 0.15
Nodes (16): Popen, create_parser(), main(), process_group_is_alive(), Any, ArgumentParser, Run a command and return its exit status, or 124 after a timeout. Args:…, Run the parsed command within the selected timeout. Returns: The wrapped… (+8 more)

### Community 299 - "field_validator"
Cohesion: 0.12
Nodes (9): field_validator, Validate end_line >= start_line. Args: v: Value to validate. info: Pydantic…, Validate level is between 1 and 6. Args: v: Value to validate. Returns: The…, Validate page_number >= 1. Args: v: Value to validate. Returns: The validated…, Validate total_pages >= 1. Args: v: Value to validate. Returns: The validated…, Validate budget > 0. Args: v: Value to validate. Returns: The validated value.…, Validate current_page >= 1. Args: v: Value to validate. Returns: The validated…, Validate total_pages >= 1. Args: v: Value to validate. Returns: The validated… (+1 more)

### Community 300 - "What You Get"
Cohesion: 0.12
Nodes (17): Backlog Management, Core Workflow (3 Commands), `/dh:add-new-feature`, `/dh:analyze-test-failures`, `/dh:complete-implementation`, `/dh:comprehensive-test-review`, `/dh:groom-milestone`, `/dh:implement-feature` (+9 more)

### Community 301 - "Complete Implementation (Quality Gates + Recursion)"
Cohesion: 0.12
Nodes (17): Complete Implementation (Quality Gates + Recursion), Completion Verification Gate, Confirm All Workers Finished, Dispatch Loop, Final Handoff Output, Final Step: Commit and Push Remaining Changes, Input Format Detection, Post-Phase-6: Surface Divergence Findings (+9 more)

### Community 302 - "Default Development Flow"
Cohesion: 0.12
Nodes (17): ARL Touchpoint Gates, Artifact Flow (Linear), Artifact Logical Identifier Conventions, Complete-Implementation Pre-Phase Gates, Default Development Flow, Design Principles, Pipeline Overview, Related Documents (+9 more)

### Community 303 - "Human Touchpoint Model"
Cohesion: 0.12
Nodes (17): Available in Context, Bound Constraints, Constraint Types, Domain Knowledge Assessment, Dynamic Escalation Points, Escalation Decision Flowchart, Escalation Format, High Risk (consider escalation) (+9 more)

### Community 304 - "TestMilestoneHeaderConstruction"
Cohesion: 0.12
Nodes (10): parametrize, MilestoneHeader construction with snake_case and kebab-case aliases., MilestoneHeader accepts snake_case field names at construction time. Tests:…, MilestoneHeader.model_validate accepts kebab-case 'integration-branch' key.…, MilestoneHeader rejects number values below the ge=1 constraint. Tests: ge=1…, MilestoneHeader rejects an empty title string. Tests: min_length=1 constraint…, MilestoneHeader raises ValidationError when required fields are absent. Tests:…, WaveItem raises ValidationError for a priority value not in ItemPriority.… (+2 more)

### Community 305 - "SOP"
Cohesion: 0.12
Nodes (15): BLOCKED Format, Input, Output Format, Quality Perspective Reviewer, Role, SOP, Step 1: Read Changed Files, Step 2: Check for Exception Swallowing (BLOCKER patterns) (+7 more)

### Community 306 - "github_branches.py"
Cohesion: 0.16
Nodes (12): _branch_info_from_branch(), get_integration_branch_status(), _get_repo(), Integration branch lifecycle management for the backlog MCP package. Provides…, Convert a PyGithub Branch object to a ``BranchInfo`` TypedDict. Args: branch:…, Return HEAD SHA and last-commit timestamp for a branch. Non-raising on branch-…, Authenticate and return a PyGithub Repository object. Args: repo:…, get_integration_branch_status returns BranchInfo or None. (+4 more)

### Community 307 - "BranchConflictError"
Cohesion: 0.17
Nodes (10): BranchConflictError, Raised when a merge fails due to conflicts. Attributes: head_branch: Source…, BranchConflictError stores branch names and conflict_files., Test head_branch attribute is stored on BranchConflictError. Tests:…, Test base_branch attribute is stored on BranchConflictError. Tests:…, Test conflict_files defaults to empty list when not provided. Tests:…, Test conflict_files list is stored when provided. Tests: BranchConflictError —…, Test string representation includes both branch names. Tests:… (+2 more)

### Community 308 - "ContentDuplicateMatch"
Cohesion: 0.24
Nodes (9): DuplicateItemError, Raised when a content-based duplicate is detected during item creation., Initialize with the content-duplicate matches found., ContentDuplicateMatch, BaseModel, A single candidate duplicate surfaced by ``find_content_duplicates``., DuplicateItemError formats its message from ContentDuplicateMatch entries. No…, AC3: message and .duplicates expose an actionable item_ref, never a bare file… (+1 more)

### Community 309 - "_provider_with_mock_runner"
Cohesion: 0.17
Nodes (10): _provider_with_mock_runner(), Regression tests for BeadsArtifactProvider.get_manifest_bd issue_number field.…, Confirm the sentinel 0 value is gone from both empty-manifest paths., A manifest persisted by pre-fix code with issue_number=0 is normalized on read.…, Normalizing issue_number must not drop or alter the existing artifacts list., Return a BeadsArtifactProvider whose runner returns *raw_json* from run_json., get_manifest_bd always returns manifest.issue_number == issue_id., When bd show returns no metadata, issue_number must be the beads ID string.… (+2 more)

### Community 310 - "TestUnknownTimestampSurvivesSinceFilter"
Cohesion: 0.12
Nodes (9): An entry whose write time is unknown must never be silently withheld by…, A section of legacy unwrapped content is filterable by ``since``. Tests:…, ``since`` returns an unknown-timestamp entry rather than excluding it. Tests:…, The returned entry carries the sentinel ID, so the caller can see the age is…, The include-unknown rule is scoped to unknown timestamps — real ones still…, ``_parse_entry_timestamp`` reports the timestamp as unavailable, not as year…, The fix is scoped to the zero-date sentinel — other bad IDs remain loud., The empty ID produced by the old orphan-entry corruption is not silently… (+1 more)

### Community 311 - "compute_slug"
Cohesion: 0.17
Nodes (10): compute_slug(), Compute project slug from absolute path. Algorithm: replace every ``/`` in…, Verify underscores in path components are preserved unchanged. Tests:…, Verify a single-segment path produces a minimal slug. Tests: compute_slug with…, Verify every slug starts with a dash due to leading slash replacement. Tests:…, Verify no forward slashes remain in the slug output. Tests: compute_slug…, Tests for compute_slug(): slug format for various path inputs. Strategy: Pass…, Verify simple nested path produces the correct slug. Tests: compute_slug with a… (+2 more)

### Community 312 - "Normative requirements"
Cohesion: 0.12
Nodes (16): Agent Markdown Consumption — Behaviour Specification, Design decisions, Implementation appendix — shape to code, Normative requirements, Purpose, R1 — One markdown engine, all consumption, R2 — Everything paginates, including the table of contents, R3 — Threshold triggers the compact form, automatically (+8 more)

### Community 313 - "Package map"
Cohesion: 0.12
Nodes (16): `agent_profile`, `backlog_core`, Content model, Development Harness — Component Architecture, `dh_core`, `dispatch_schema`, Documentation layout, `hooks` (+8 more)

### Community 314 - "development-harness"
Cohesion: 0.12
Nodes (16): Agents, ARL Human Touchpoints, Cursor IDE, development-harness, Example: Full Feature Workflow, Example: Milestone Execution, How the Pipeline Works, Installation (+8 more)

### Community 315 - "_CommentEntryLike"
Cohesion: 0.16
Nodes (10): _CommentEntryLike, BaseModel, CaptureFixture, ``database_id`` is reachable as ``comments[0]["database_id"]``. Tests: The…, ``exclude_none`` applies to nested models, not just the top level. Tests: A…, ``exclude_none=False`` keeps an explicit ``null`` on a nested model. Tests: The…, A bare top-level ``BaseModel`` is unaffected by the fix. Tests: Regression…, A value that is neither JSON-native nor a ``BaseModel`` stringifies. Tests: The… (+2 more)

### Community 316 - "SAM Stage 7 — Final Verification"
Cohesion: 0.12
Nodes (15): Behavioral Rules, Core Principle, Input, NOT_CERTIFIED Loop, Output, Process, Role, SAM Stage 7 — Final Verification (+7 more)

### Community 317 - "Verdict Schema — Multi-Perspective Review"
Cohesion: 0.12
Nodes (14): §2.1 Structured Verdict Block, §2.2 Summary Line Format, §2.3 SKIP Detection Rule (Accessibility Perspective), §2.4 Gate Logic, §2.5.1 Prompt Injection Security Surface, §2.5.2 Quality Correctness for Tier 3 Files, §2.5 Prose File Classification (All Perspectives), §2.6 Punch-List Block (+6 more)

### Community 318 - "Setup Skill Discovery Wizard"
Cohesion: 0.12
Nodes (15): AUTO_MODE vs Interactive Mode, Output Schema, References, Setup Skill Discovery Wizard, Step 1: Scan Repo, Step 2: Inventory Installed Skills, Step 3: Search Marketplace for Skill Candidates, Step 4: Build Draft Config (+7 more)

### Community 319 - "test_ac_overlap_warning.py"
Cohesion: 0.33
Nodes (7): _backlog_dir(), MockerFixture, Path, Tests for _check_ac_overlap and its wiring in both groomed write paths. Covers:…, TestHandleBatchGroomedAcWiring, TestHandleUpdateGroomedAcWiring, _write_item_file()

### Community 320 - "TestBackendAvailabilityEnum"
Cohesion: 0.12
Nodes (9): All five named members exist on the enum. Tests: BackendAvailability member…, BackendAvailability has exactly 5 members with correct string values. Tests:…, BackendAvailability defines exactly 5 availability states. Tests:…, REACHABLE serialises to the string 'reachable'. Tests:…, NOT_CHECKED serialises to 'not_checked'. Tests: BackendAvailability.NOT_CHECKED…, NEEDS_AUTHENTICATION serialises to 'needs_authentication'. Tests:…, RATE_LIMITED serialises to 'rate_limited'. Tests:…, ERROR serialises to 'error'. Tests: BackendAvailability.ERROR value How: Direct… (+1 more)

### Community 321 - "TestIsNotFoundError"
Cohesion: 0.12
Nodes (9): Tests for _is_not_found_error() helper. Tests: _is_not_found_error structurally…, _is_not_found_error returns True for the exact synthesized message. Tests:…, _is_not_found_error matches regardless of message casing. Tests:…, _is_not_found_error returns False for unrelated error messages. Tests:…, _is_not_found_error returns False for rate limit errors. Tests:…, _is_not_found_error returns False for a repository-not-found error. Tests:…, _is_not_found_error returns False even when the repo name contains 'issue'.…, _is_not_found_error tolerates incidental leading/trailing whitespace. Tests:… (+1 more)

### Community 322 - "test_placeholder_vocabulary_drift.py"
Cohesion: 0.14
Nodes (15): _iter_workflow_files(), Path, Guards the work-backlog-item placeholder vocabulary and adjacent doc-drift…, Every file that extracts Impact Radius data also names a `Resources` fallback.…, `work/start.md` never mandates `TodoWrite` bare — a fallback chain rides with…, Each `artifact list --artifact-type X` count check is followed by a content…, Every remaining `<mode/>` occurrence sits on a line that says `auto` or…, The six files the C2 rename cleared entirely never reacquire `<mode/>`. (+7 more)

### Community 323 - "contract-verification.md"
Cohesion: 0.13
Nodes (14): Contract Extraction Process, Delivery, Inputs, Operating Rules, Output Format, Role, Step 1 — Component Design Contracts, Step 2 — Type System Design Contracts (+6 more)

### Community 324 - "_build_artifact_content_comment"
Cohesion: 0.13
Nodes (14): _build_artifact_content_comment(), Build a structured GitHub comment body for storing artifact content. The…, Verify the opening artifact-content HTML comment tag is present. Tests:…, Verify the closing artifact-content HTML comment tag is present. Tests:…, Verify the comment wraps content in an HTML details/summary block. Tests:…, Verify the artifact content is embedded verbatim in the comment. Tests:…, Verify oversized content is truncated to stay within GitHub's limit. Tests:…, Verify content within the size limit is stored unmodified. Tests:… (+6 more)

### Community 325 - "test_github_branches.py"
Cohesion: 0.15
Nodes (11): _branch_name(), Build the canonical branch name for a milestone. Args: milestone_number:…, mock_repo(), fixture, Tests for backlog_core/github_branches.py. Covers: create_integration_branch,…, _branch_name builds canonical milestone branch names., Test canonical branch name format milestone/{N}-{slug}. Tests: _branch_name…, Test that _branch_name uses the BRANCH_PREFIX module constant. Tests:… (+3 more)

### Community 326 - "search.py"
Cohesion: 0.18
Nodes (13): _build_haystack(), _candidate_item_ref(), _candidate_matched_field_and_snippet(), _item_field_text(), _item_matches_term(), Full-text search engine for backlog item dicts. Operates on the…, Match a single leaf term against an item., Return the casefolded text for a single field of an item dict. (+5 more)

### Community 327 - "Development Harness Backend Providers"
Cohesion: 0.13
Nodes (15): Backlog Persistence Boundary, Capability flags, CLI vs MCP Capability Surface, Configuration and troubleshooting, Consumer workflow, Development Harness Backend Providers, GitHub contract, Listing provenance (+7 more)

### Community 328 - "Harness facts: Hermes Agent (Nous Research)"
Cohesion: 0.13
Nodes (14): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment for a shell command, Can a plugin or skill collection ship hooks?, Event names (+6 more)

### Community 329 - "Harness facts: Kilo Code (Kilo CLI / Kilo Code VS Code extension, Kilo-Org/kilocode)"
Cohesion: 0.13
Nodes (14): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables set for a shell command, Are hooks shell commands?, Can a plugin or a skill collection ship them? (+6 more)

### Community 330 - "test_high_level_storage_boundaries.py"
Cohesion: 0.45
Nodes (10): ModuleType, _attributes_by_function(), _imports(), parametrize, _source(), test_github_client_has_no_cache_filesystem_access(), test_non_local_context_backend_has_no_task_file_path(), test_operations_has_no_high_level_storage_bypass() (+2 more)

### Community 331 - "Working in dh Workflow Files"
Cohesion: 0.13
Nodes (14): Before You Touch Any File, Checking Skip Conditions, Checking the Dispatch Sequence, Mapping the Data Contract, Reference: groom pipeline stage files, Step 1 — Name the change precisely, Step 2 — Read the prior stage file, Step 3 — Read the downstream stage file (+6 more)

### Community 332 - "NormalizedEntry"
Cohesion: 0.14
Nodes (8): _entry_block_text(), NormalizedEntry, NormalizedSection, Protocol, r"""Return entry content, prefixed with an in-band struck marker when struck.…, Source-neutral generated entry consumed by ordinal navigation., Initialise the mapper. Args: sections: Ordered list from…, Source-neutral generated section consumed by ordinal navigation.

### Community 333 - "TestParentIssueNumberValidator"
Cohesion: 0.13
Nodes (8): parent_issue_number=None must be accepted., A positive integer issue number must be accepted., Zero is a non-negative integer and must be accepted., A valid beads ID string (bd-xxxx pattern) must be accepted., True/False must be rejected as parent_issue_number. The validator raises…, Negative integers must be rejected., Strings that are not valid beads IDs must be rejected. The pattern…, TestParentIssueNumberValidator

### Community 334 - "SAM Stage 1 — Discovery"
Cohesion: 0.13
Nodes (14): Human Touchpoint Gate, Input, Output, Process, Role, SAM Stage 1 — Discovery, Self-Initialization from Backlog Item, Step 1 — Identify Problem Domain (+6 more)

### Community 335 - "scripts/task_format.py"
Cohesion: 0.16
Nodes (14): _format_yaml_value(), has_yaml_frontmatter(), normalize_status(), parse_yaml_frontmatter(), Any, Shared YAML frontmatter utilities for task file parsing and manipulation.…, Detect if content uses YAML frontmatter format. Checks for opening ``---``…, Extract YAML frontmatter and markdown body from content. .. deprecated:: Use… (+6 more)

### Community 336 - "Investigation Procedure"
Cohesion: 0.13
Nodes (15): A. List unknowns and fastest verification paths, B. Classify reproduction constraints, C. Determine execution mode, Evidence-Chain Protocol, Inputs, Investigation Procedure, Prohibited Behaviors, Root-Cause Tracing Process (+7 more)

### Community 337 - "_backlog_ops"
Cohesion: 0.17
Nodes (10): _backlog_ops(), Any, Return backlog_core.operations as Any so ty does not flag unimplemented symbols., Verify _filter_closed_items filters terminal-status items correctly. NOTE:…, When include_closed=True, all items are returned unfiltered., When include_closed=False, items with done/resolved/closed status are excluded., Items using _status key instead of **Status** are also filtered., Items with empty or missing status are not filtered out. (+2 more)

### Community 338 - "test_server_sam.py"
Cohesion: 0.19
Nodes (14): _call(), Tests for the SAM MCP tools added to backlog_core/server.py in Phase 2. Four…, backlog_get_sam_tasks returns {"tasks": [...], "count": N} shape on success.…, backlog_update_sam_task_status returns {"updated": False} when status…, backlog_get_ready_sam_tasks returns shape with "feature", "ready_tasks",…, Call an MCP tool through the in-memory FastMCP transport and parse result.…, backlog_create_sam_task returns a dict (not raises) on success. Tests:…, backlog_create_sam_task returns {"error": "..."} when BacklogError is raised.… (+6 more)

### Community 339 - "Classifier"
Cohesion: 0.14
Nodes (13): Behavioral Constraints, Classifier, Decision boundaries, If type is `defect`, If type is `procedural`, `missing-guardrail`, or `unbounded-design`, If type is `recurring-pattern`, Input, Persistent Memory (+5 more)

### Community 340 - "scan_all_agents"
Cohesion: 0.06
Nodes (47): _agent_name_from_path(), _build_manifest_name_index(), _find_bare(), _find_plugin_qualified(), _get_manifest_name_for_dir(), get_plugins_root(), _looks_like_semver(), Path (+39 more)

### Community 341 - "Fact Checker Agent"
Cohesion: 0.14
Nodes (12): Boundaries, Fact Checker Agent, Input Format, Mandatory Tool Usage, Persistent Memory, Prohibited Behaviors, Step 1: Understand the Claim, Step 2: Gather Evidence from Primary Source (+4 more)

### Community 342 - "Security Reviewer Agent"
Cohesion: 0.14
Nodes (13): 1. Structured Verdict Block (JSON), 2. STATUS Block, 3. Verdict Delivery (MANDATORY), Input, Output Format, Role, Security Reviewer Agent, SOP (+5 more)

### Community 343 - "resolve_token"
Cohesion: 0.21
Nodes (9): has_github_credentials(), Report whether a GitHub token is configured in this process's environment.…, MissingGitHubTokenError, RuntimeError, Raised when no environment variable supplies a GitHub token., Return the GitHub token to authenticate with. Args: token: An explicit token.…, resolve_token(), Token precedence, and the failure when nothing supplies one. (+1 more)

### Community 344 - "_parse_comment_node"
Cohesion: 0.20
Nodes (8): _parse_comment_node(), Parse a raw GraphQL comment dict into a typed IssueCommentNode. Args: node: Raw…, A guessed number addresses some other comment, so nothing is guessed., A decimal string is a valid BigInt encoding; a non-digit string means the…, GitHub never emits a sign for this field; a negative-looking string is not a…, bool subclasses int, so True would otherwise be carried as comment 1., The field is declared BigInt (whole numbers only); a float means the response…, TestAnAbsentOrUnusableValueStaysAbsent

### Community 345 - "delete_integration_branch"
Cohesion: 0.19
Nodes (9): delete_integration_branch(), Delete a branch by name. Idempotent: returns True even if already deleted.…, delete_integration_branch is idempotent and returns bool., Test successful delete returns True. Tests: delete_integration_branch — happy…, Test 404 on get_git_ref returns True (idempotent delete). Tests:…, Test unexpected GithubException returns False without re-raising. Tests:…, Test output.warn called when unexpected error occurs. Tests:…, Test get_git_ref called with 'heads/{branch_name}' (no 'refs/' prefix). Tests:… (+1 more)

### Community 346 - "bundle_adds_new_anchor"
Cohesion: 0.22
Nodes (6): bundle_adds_new_anchor(), Decide whether ca_bundle supplies any certificate the baseline trust store…, Whether a bundle supplies anything beyond the baseline store — the gate for…, Finding 2: directory-supplied anchors go through the same new-anchor test., Finding 2 regression: a ``BEGIN TRUSTED CERTIFICATE`` bundle is not empty.…, TestBundleAddsNewAnchor

### Community 347 - "_ProxyAwareAdapter"
Cohesion: 0.19
Nodes (10): __init__(), _ProxyAwareAdapter, An HTTPAdapter that applies its SSL context on the proxied path as well.…, Store the bundle before delegating, because the base __init__ builds the pools.…, Attach the context to the direct connection pool. Args: connections: Number of…, Attach the context to the proxied connection pool. Args: proxy: Proxy URL that…, The outer TLS connection to an HTTPS proxy uses the configured context too., TestHttpsProxyContext (+2 more)

### Community 348 - "model_validator"
Cohesion: 0.14
Nodes (6): model_validator, Synchronise flat accessor fields and the metadata sub-model. Priority chain…, Reject statuses that could not have come from an attempted fetch. Returns: The…, Reject successful enrichment when no provider request was attempted. Returns:…, Require struck_at to be non-empty when struck is True. Returns: The validated…, Populate ``milestone_info`` from legacy flat milestone fields on load. Existing…

### Community 349 - "build_concept_query"
Cohesion: 0.19
Nodes (9): build_concept_query(), _extract_concept_words(), Return casefolded, deduplicated, stopword-filtered words from ``text``, in…, Build an OR search query from the significant words in title and description.…, Tests for backlog_core/search.py content-based duplicate detection. Replaces…, Tests for build_concept_query(title, description, max_concepts)., Tests for the ContentDuplicateMatch.item_ref invariant (spec §6.2)., TestBuildConceptQuery (+1 more)

### Community 350 - "assemble"
Cohesion: 0.19
Nodes (14): assemble(), _load_json(), load_layers(), _parse_args(), Namespace, Path, Atomically write a JSON payload to output_path. Writes to a uniquely named…, Replace the inline GRAPH_DATA blob in the explorer HTML. The explorer uses an… (+6 more)

### Community 351 - "Context-Fit Complexity: Adoption Conditions"
Cohesion: 0.14
Nodes (14): Adoption Sequence, Concept 10: Classify tasks by context-fit spectrum before choosing strategy, Concept 11: Iterative knowledge discovery via speculation detection, Concept 1: Measure complexity as context-fit, not implementation difficulty, Concept 2: Use the three-term equation (knowledge + uncertainty + overhead), Concept 3: Decompose at knowledge boundaries, not code boundaries, Concept 4: Hardcode stable constraints; discover volatile constraints dynamically, Concept 5: Progressive disclosure — load minimum context per step (+6 more)

### Community 352 - "evidence-discipline.md"
Cohesion: 0.14
Nodes (11): Evidence Discipline, fact-check, find-cause and root-cause-tracing-process, scientific-thinking, Sources, A. Formulate distinct interpretations, B. Define success criteria, Find Cause (+3 more)

### Community 353 - "DH work ledger — plan"
Cohesion: 0.14
Nodes (13): DH work ledger — plan, Layers, Slice 0 — measure, Slice 1 — decide, Slice 2 — build, Slice 3 — MCP parity, Slice 4 — the loop in the skills, Slice 5 — milestones on the same path (+5 more)

### Community 354 - "Fact Check — Primary Source Claim Verification"
Cohesion: 0.14
Nodes (14): Chain of Verification (CoVe) Requirement, Claim Classification, Claim Extraction, Evidence Rules, Fact Check — Primary Source Claim Verification, Post-Actions, References, Report Format (+6 more)

### Community 355 - "SAM Stage 6 — Forensic Review"
Cohesion: 0.14
Nodes (13): Behavioral Rules, Core Principle, Input, NEEDS_WORK Remediation Loop, Process, Role, SAM Stage 6 — Forensic Review, Step 1 — Resolve Task Context (+5 more)

### Community 356 - "Verification Protocol"
Cohesion: 0.14
Nodes (14): 1. Task Type & Strategy, 2. The "WORKS" Check, 3. The "FIXED" Check, 4. Quality Gates, 5. Proportional Response Check, 6. Agent Delegation Verification, 7. Honesty Check, 8. Observations, Gaps, and Backlog Capture (+6 more)

### Community 357 - "Groom: Finalize"
Cohesion: 0.14
Nodes (14): Canonical Write-Back, Clarification batch format (`APPROVED-WITH-GAPS`), Contents, Diagnostic Gate — Before Retry or Direct Write, Groom: Finalize, Handoff, Hypothesis Resolution, Output Validation Gate (+6 more)

### Community 358 - "Work: Validate (Phase 2)"
Cohesion: 0.15
Nodes (11): Already Implemented Check (Step 2.1), Issue Sync (Steps 2.2–2.4), Step 2.2: Issue Link Check, Step 2.3: Create Linked Issue, Step 2.4: Set In-Progress, Step 2.1: Already Implemented Check, Step 2.2: Issue Link Check, Step 2.3: Create Linked Issue (+3 more)

### Community 359 - "TestArtifactEntryModelValidation"
Cohesion: 0.14
Nodes (8): Unit tests for ArtifactEntry Pydantic model and AliasChoices field interop.…, ArtifactEntry accepts snake_case field names at construction. Tests:…, ArtifactEntry accepts kebab-case field name via model_validate. Tests:…, ArtifactEntry accepts short 'type' alias via model_validate. Tests:…, ArtifactEntry defaults status to CURRENT when not provided. Tests:…, All ArtifactType enum members can be used in ArtifactEntry. Tests: ArtifactType…, All ArtifactStatus enum members can be used in ArtifactEntry. Tests:…, TestArtifactEntryModelValidation

### Community 360 - "run_loop"
Cohesion: 0.15
Nodes (14): build_parser(), main(), ArgumentParser, Path, Return every file the runner is built from, entry script first. Derived rather…, Drive the whole work loop once under one work directory and return what it…, Return the hand-run argument parser. Returns: The parser for ``--work-dir``,…, Run the loop by hand, print each unsatisfied observation, and return the run's… (+6 more)

### Community 361 - "test_the_first_failing_check_is_the_one_the_spec_puts_first"
Cohesion: 0.14
Nodes (14): OrderCase, outcome_of(), Any, BaseModel, parametrize, Return a pair of checks in the order the specification evaluates them. Args:…, One transition entry, the two checks a scenario makes fail, and the scenario., Read one task's status through the package's own reader. Args: conn: An open… (+6 more)

### Community 362 - "TestModels"
Cohesion: 0.14
Nodes (8): Sanity checks on the Pydantic models., SourceSpan can be constructed with valid values., SourceSpan raises ValidationError for negative start_line., SourceSpan raises ValidationError when end_line < start_line., CodeBlock can be constructed and serialised., MarkdownDocument can be constructed with defaults., NavigatorOptions default_budget equals _DEFAULT_BUDGET (env-derived)., TestModels

### Community 363 - "test_reconciliation.py"
Cohesion: 0.16
Nodes (8): Tests for reconciliation functions added by T2. Tests: _has_active_work,…, Verify _reconcile_item dispatches correctly based on item and GitHub state., Create a mock GitHub issue with the given state and labels., Items without an _issue field return no_change with issue_number=0., Items whose issue number is not in the GitHub map return no_change with warning., When GitHub issue is open, delegates to _reconcile_open_item., When GitHub issue is closed, delegates to _reconcile_closed_item., TestReconcileItem

### Community 364 - "TestReconcileOpenItem"
Cohesion: 0.14
Nodes (8): Verify _reconcile_open_item handles divergence scenarios for open GitHub issues., Returns no_change when local and GitHub statuses are identical., Returns flagged_divergence with stateless void warning when GitHub has no…, Returns auto_corrected when divergence is DAG-valid (reachable via state…, When auto-correcting, _update_item_metadata is called to persist the change., When file_path_str is None, auto-correction returns result but does not persist., Returns flagged_divergence when no valid DAG path exists between states., TestReconcileOpenItem

### Community 366 - "helpers.py"
Cohesion: 0.05
Nodes (39): FastMCP, npx, uv, backlog, sam, sequential_thinking, @modelcontextprotocol/server-sequential-thinking, Shared test helper functions for development-harness test suites. Centralises… (+31 more)

### Community 367 - "TestResolveVerifiedGate"
Cohesion: 0.14
Nodes (8): Integration tests for the status:verified gate on resolve (Gap 4) and full…, Resolve with plan but no status:verified label is blocked at the view gate.…, Resolve proceeds when status:verified label is present on the issue. After…, Items without a Plan field skip the verification gate entirely. Non-SAM items…, force=True bypasses the verification gate even with a plan and no verified…, force=True bypasses both the verified gate and the open-PR gate., Full pipeline flow: create item with issue, attach plan, apply verified label,…, TestResolveVerifiedGate

### Community 368 - "integration-checker.md"
Cohesion: 0.15
Nodes (12): Integration Gaps Found, Integration Verified, Level 1: Existence - Artifacts Present, Level 2: Substantive - Quality Checks, Level 3: Wired - Integration Verified, Step 1: Build Export/Import Map, Step 2: Verify Export Usage, Step 3: Verify CLI → Core Connection (+4 more)

### Community 369 - "RT-ICA Assessor"
Cohesion: 0.15
Nodes (12): Behavioral Constraints, Input, Persistent Memory, Phase 1 — Load the RT-ICA methodology skill, Phase 2 — Load the inputs, Phase 3 — Enumerate conditions, Phase 4 — Classify each condition, Phase 5 — Re-read the upstream sections before you finalize (+4 more)

### Community 370 - "infer_type"
Cohesion: 0.26
Nodes (4): infer_type(), Infer issue type label from description and title keywords. Returns: Type label…, Tests for infer_type(description, title) -> str. Verifies the keyword heuristic…, TestInferType

### Community 371 - "_parse_frontmatter"
Cohesion: 0.26
Nodes (4): _parse_frontmatter(), Parse frontmatter and metadata from item text. ``loads_frontmatter`` guarantees…, Tests for _parse_frontmatter(text) -> (fm_dict, meta_dict, body)., TestParseFrontmatter

### Community 372 - "Per-Stage Detail"
Cohesion: 0.15
Nodes (12): Per-Stage Detail, S1 — `discovery`, S2 — `planning`, S3 — `context-integration`, S4 — `task-decomposition`, S5 — `execution`, S6 — `forensic-review`, S7 — `final-verification` (+4 more)

### Community 373 - "SAM Stage 2 — Planning"
Cohesion: 0.15
Nodes (12): Behavioral Rules, Input, Output, Process, Role, SAM Stage 2 — Planning, Step 1 — RT-ICA Prerequisite Assessment, Step 2 — Solution Design (+4 more)

### Community 374 - "work/start.md"
Cohesion: 0.15
Nodes (10): Interactive mode (Step 4.5), Post-Planning Output (Steps 4.5 + 4.5a), When <mode/> is `auto` (Step 4.5a), Work - backlog item - Scope boundary, Checklist, Error Routing, Identifier Convention, Inputs (+2 more)

### Community 375 - "test_server_pep723_header_omits_typer"
Cohesion: 0.21
Nodes (12): _extract_pep723_block(), parametrize, Path, unit, Regression test: MCP servers disable FastMCP's Rich logging/tracebacks. Why:…, Extract the TOML content from a PEP 723 '# /// script' block. Mirrors…, Importing dh_mcp_preinit sets both FASTMCP_ENABLE_RICH_* vars to false., setdefault semantics: an operator-set value survives the import. (+4 more)

### Community 376 - "Task"
Cohesion: 0.01
Nodes (195): append_task(), _apply_key_filter(), _build_spawn_cmd(), _build_wave_summary(), _canonicalize_patch_keys(), _check_pid_alive(), claim_task(), create_plan() (+187 more)

### Community 377 - "MonkeyPatch"
Cohesion: 0.21
Nodes (8): MonkeyPatch, Verify _reconcile_batch handles GitHub availability and batch processing., When _try_get_github returns None, returns items unchanged with warning., When GitHub API raises GithubException, returns items unchanged with warning., When an item is auto-corrected, its in-memory status is updated., Divergence warnings from _reconcile_item are collected in the warnings list., Pull requests are excluded from the GitHub issue map., TestReconcileBatch

### Community 378 - "test_server_descriptions.py"
Cohesion: 0.19
Nodes (12): _extract_selector_descriptions(), _param_description(), parametrize, AST-based regression test: every beads-capable selector Field description…, Return the ``Field(description=...)`` string of *param* on the MCP tool *tool*., Each beads-capable tool's selector Field description must contain 'beads…, Each beads-capable tool's selector description must not be a bare generic…, The ``plan`` value is stored verbatim as a plan address, so its description… (+4 more)

### Community 379 - "test_status_token_vocabulary_drift.py"
Cohesion: 0.18
Nodes (12): _collect_status_tokens(), Guards the sub-agent STATUS reporting vocabulary against drift. Two files in…, No file under skills/ or agents/ writes a retired STATUS spelling. This is the…, The contract file this module cites still pins exactly the tokens it says it…, The agent-orchestration contract keeps PARTIAL, which this module's docstring…, Every STATUS token written in skills/ or agents/ is one this plugin's contract…, Map each STATUS token found to the paths that write it. Returns: Token (upper-…, test_contract_pins_the_tokens_this_module_guards() (+4 more)

### Community 380 - "Alignment Analyst"
Cohesion: 0.17
Nodes (11): Alignment Analyst, Behavioral Constraints, Input, Persistent Memory, Phase 1 — Read the proposed change and its affected paths, Phase 2 — Resolve the governing mission sources, nearest-first, Phase 3 — Read historical direction, Phase 4 — Classify mission alignment (+3 more)

### Community 381 - "create_integration_branch"
Cohesion: 0.20
Nodes (8): create_integration_branch(), Create a branch named ``milestone/{N}-{slug}`` from the HEAD of…, Test 404 on base branch lookup raises BacklogError. Tests:…, create_integration_branch validates slug and milestone_number before API calls., Test invalid slug raises BacklogError without calling GitHub API. Tests:…, Test milestone_number=0 raises BacklogError without calling GitHub API. Tests:…, Test negative milestone_number raises BacklogError. Tests:…, TestCreateIntegrationBranchValidation

### Community 382 - "_validate_milestone_number"
Cohesion: 0.21
Nodes (8): Validate milestone_number is a positive integer. Args: milestone_number:…, _validate_milestone_number(), _validate_milestone_number enforces milestone_number > 0., Test positive milestone number passes without raising. Tests:…, Test milestone_number=0 raises BacklogError. Tests: _validate_milestone_number…, Test negative milestone_number raises BacklogError. Tests:…, Test error message includes the invalid milestone_number value. Tests:…, TestValidateMilestoneNumber

### Community 383 - "_make_connection_class"
Cohesion: 0.18
Nodes (9): _make_connection_class(), Build the HTTPS connection class PyGithub should use. Args: ca_bundle: Path…, The substituted class must remain a drop-in for the one PyGithub ships., PyGithub builds connections from it, so it has to satisfy that contract., force depends on a rebuild, so the factory must not cache one class., New Finding 1 (P1, PR #3551 second review round): the connection's own…, TestConnectionClassFactory, TestConnectionVerifyMatchesSelectedBundle (+1 more)

### Community 384 - "MockerFixture"
Cohesion: 0.21
Nodes (12): BacklogListItem, A single backlog item as returned by list_items(). Used by server.py to remove…, _make_list_items_result(), mock_list_items_empty(), mock_list_items_populated(), fixture, MockerFixture, Reset SyncState before each test. Must be async so the asyncio.Lock() is bound… (+4 more)

### Community 385 - "test_section_boundary_scanner_live_3152.py"
Cohesion: 0.20
Nodes (9): narrow_body_to_named_sections(), Concatenate the *body* slices for the given *span* *indices* in order. The…, Return the slices of *body* whose ``## ``/``### `` headers match *names*. Used…, _slice_body_by_header_indices(), Regression tests against the REAL #3152 body — the boundary-scanner defect…, Step 3 (design §3): the two bugs Option A (patching only…, RED before the fix: 178 chars (one phantom ``## Claim`` fragment, not the real…, RED before the fix: 9,786 chars (63% content loss from phantom sub-headings). (+1 more)

### Community 386 - "_token_count"
Cohesion: 0.17
Nodes (12): _compute_match_tokens(), _paginate_match_items(), Resolve the effective page limit for a ``backlog_list`` response. When ``limit…, Count cl100k_base tokens in an already-serialized JSON string. Args:…, Token-count the delivered ``backlog_view`` payload without double-counting. The…, Return a copy of *section* with each entry's ``content`` blanked. Used by…, Count tokens for the match_context output of a single enriched item. Counts…, Split enriched match-context items into token-sized pages. Partitions… (+4 more)

### Community 387 - "_filter_sections_isolated"
Cohesion: 0.21
Nodes (8): _filter_sections_isolated(), Run ``_filter_view_sections`` in isolation over a hand-built result. Builds a…, Codex P2 (#2495): the ``sections=[...]`` dict filter must match case-…, ``sections=['rt-ica']`` against an ``RT-ICA`` key / ``## RT-ICA`` header. RED…, ``sections=['RT-ICA']`` (upper) against a lowercase ``rt-ica`` key / ``## rt-…, Compact ``sections_metadata`` arm: a case-differing valid name stays a non-…, A name absent from the dict, body headers, AND metadata still sets…, TestSectionsDictFilterIsCaseInsensitive

### Community 388 - "track_sqlite_connections"
Cohesion: 0.18
Nodes (12): close_sqlite_connections(), _disable_startup_sync(), Connection, fixture, FixtureRequest, MonkeyPatch, _P, Disable the background startup sync loop for all non-e2e tests. Patches… (+4 more)

### Community 389 - "_build_graph_dict"
Cohesion: 0.21
Nodes (7): _build_graph_dict(), _count_types(), Count occurrences of each value of ``key`` across a list of dicts. Returns:…, Construct the top-level graph output dict from sorted nodes and edges.…, A gap edge and an orphan edge are different concepts -- an edge must never be…, TestGapCountComputedNotHardcoded, TestOrphanCountComputedNotHardcoded

### Community 390 - "Plan and Artifact Lifecycle"
Cohesion: 0.17
Nodes (12): Agent workflow, Artifact classes, Divergence note, Divergence policy, Forward compatibility and migration debt, Freshness report, Generated artifacts, Human-decision artifacts (+4 more)

### Community 391 - "Operational Principles"
Cohesion: 0.17
Nodes (12): 1. Decomposition, 2. Guidance Over Enforcement, 3. Progressive Disclosure, 4. Context Garbage Collection, 5. Unknown Handling, 6. Reuse Over Rediscovery, Context-Fit Complexity Model, Operational Loop (+4 more)

### Community 392 - "conftest.py"
Cohesion: 0.19
Nodes (16): _Address, AF_INET, AF_INET6, _guarded_connect(), _guarded_connect_ex(), _guarded_getaddrinfo(), _is_local(), pytest_configure() (+8 more)

### Community 393 - "OpenAI Codex CLI harness facts"
Cohesion: 0.17
Nodes (11): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables for a shell command, Can a plugin ship hooks?, Lifecycle events (+3 more)

### Community 394 - "OpenCode harness facts"
Cohesion: 0.17
Nodes (11): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills (SKILL.md), 5. MCP from project config, 6. Environment variables for a shell command, JS function or shell command, OpenCode harness facts (+3 more)

### Community 395 - "Workflow"
Cohesion: 0.17
Nodes (11): Arguments, Error Handling, Group Items to Milestone, Step 1: Resolve Milestone, Step 2: Load Backlog Items, Step 3: Present Selection, Step 4: Create Missing Issues, Step 5: Assign Existing Issues (+3 more)

### Community 396 - "Kage Bunshin — Persistent Peer Claude Sessions"
Cohesion: 0.17
Nodes (12): Capability Inheritance, How It Works, Kage Bunshin — Persistent Peer Claude Sessions, Model Selection, Parallel Fleet Management, Quick Start, Reference, Session Lifecycle (+4 more)

### Community 397 - "test_main_explicit_session_id_overrides_env_var"
Cohesion: 0.17
Nodes (9): When --session-id and KB_SESSION_ID are absent, main() sets 'default' for spawn…, KB_SESSION_ID env var is used when --session-id is not supplied., Explicit --session-id takes priority over KB_SESSION_ID., For 'list', main() leaves session_id as None so all registries are shown., test_main_explicit_session_id_overrides_env_var(), test_main_list_subcommand_leaves_session_id_none_when_not_supplied(), test_main_resolves_session_id_from_env_var(), test_main_resolves_session_id_to_default_for_non_list_subcommands() (+1 more)

### Community 398 - "_run_probe"
Cohesion: 0.24
Nodes (11): CompletedProcess, Path, Contract tests for the autouse ``_isolated_backend`` fixture in…, A non-e2e class still has its backend replaced by the in-memory double., Write a temp pytest file under the tests directory and yield its path. The…, Run the probe in its own pytest session with this repo's addopts cleared., An e2e class keeps its own backend for every test in the class. Guards the…, _run_probe() (+3 more)

### Community 399 - "TestConflictGroupConstruction"
Cohesion: 0.17
Nodes (7): ConflictGroup construction including alias and constraint checks., ConflictGroup constructs correctly with snake_case field names. Tests:…, ConflictGroup.model_validate accepts 'group-id' kebab-case alias. Tests:…, ConflictGroup rejects an items list with fewer than two elements. Tests:…, ConflictGroup rejects group_id values below ge=1. Tests: ge=1 constraint on…, ConflictGroup rejects an empty reason string. Tests: min_length=1 constraint on…, TestConflictGroupConstruction

### Community 400 - "TestMCPIncludeClosedPropagation"
Cohesion: 0.17
Nodes (7): Verify the MCP server forwards include_closed to operations.list_items., backlog_list MCP tool defaults include_closed to False., backlog_list MCP tool forwards include_closed=True to operations., backlog_list with include_closed=True returns items with terminal status., backlog_list without include_closed returns only non-terminal items., backlog_list forwards include_closed alongside other filter params., TestMCPIncludeClosedPropagation

### Community 401 - "test_prepare_clean_worktree.py"
Cohesion: 0.45
Nodes (11): _init_git_repo(), _parse_stash_ref(), CompletedProcess, Path, _repo_slug(), _run(), _script_path(), test_prepare_clean_worktree_decline_exits_non_zero() (+3 more)

### Community 402 - "SOP"
Cohesion: 0.18
Nodes (10): Boundaries, Input, Review Synthesizer, SOP, Step 1 — Collect the four verdicts, Step 2 — Record coverage, Step 3 — Merge findings that name the same defect, Step 4 — Order the entries (+2 more)

### Community 403 - "service-docs-maintainer.md"
Cohesion: 0.18
Nodes (10): Documentation Principles, Edge Cases, Operating Protocol, Persistent Agent Memory, Quality Gates, Scope Boundaries, Step 1: Understand the Changes, Step 2: Find All Related Documentation (+2 more)

### Community 404 - "test_artifact_migration.py"
Cohesion: 0.22
Nodes (10): _migration_backlog_items(), Return the minimal backlog data used for slug-based migration matching.…, Path, Regression tests for artifact migration's lower-level backlog lookup., Migration lookup retains the issue field under the expected number key., Migration resolves an issue from the filename when frontmatter lacks one., Dry-run discovers state-plan artifacts stored outside the repository., test_migrate_dry_run_uses_plan_relative_paths_outside_repo() (+2 more)

### Community 405 - "_validate_repo_slug"
Cohesion: 0.24
Nodes (8): Validate that *slug* matches ``owner/repo`` format. Args: slug: Candidate…, _validate_repo_slug(), parametrize, _validate_repo_slug rejects invalid formats and accepts valid ones. All public…, Valid owner/repo slugs are returned as-is. Tests: _validate_repo_slug happy…, Invalid slugs raise RepoDiscoveryError. Tests: _validate_repo_slug rejection…, Error message includes the rejected slug for debuggability. Tests:…, TestValidateRepoSlug

### Community 406 - "build_body_extra_only"
Cohesion: 0.29
Nodes (4): build_body_extra_only(), Build body with only extra fields (no duplication) and ## Groomed if present.…, Tests for build_body_extra_only(...) -> str. Verifies conditional inclusion of…, TestBuildBodyExtraOnly

### Community 407 - "BacklogItem"
Cohesion: 0.01
Nodes (269): BacklogItem, Parsed backlog item from a per-item file. Replaces the untyped ``dict`` that…, add_item(), list_items(), _live_lookup_id(), Add an item through the configured backend and optionally create its native…, List backlog items. Default reads provider-backed record only. Use refresh=True…, Resolve the identifier to pass to view_enrich_from_github() for a live check.… (+261 more)

### Community 408 - "_manifest_reference"
Cohesion: 0.22
Nodes (11): _run(), _run(), _run(), _load_manifest(), _manifest_reference(), ItemId, Raise BacklogError when no artifact entries are found. Args: entries: List of…, Return the manifest identity for a backlog item, refusing as a… (+3 more)

### Community 409 - "ARL Meta-Layer: Observation Layer (Improvement Meta-Process)"
Cohesion: 0.13
Nodes (13): ARL Human-Probing Flow — Design, Integration Points, Open Questions, Probe Design, Project-Local Domain Knowledge Format, Triggers, ARL Flow, ARL Meta-Layer: Observation Layer (Improvement Meta-Process) (+5 more)

### Community 410 - "layer-1/README.md"
Cohesion: 0.08
Nodes (21): Abstract Roles, Agent Archetypes, Fallback, Harness Role ↔ Agent Archetype Mapping, CoVe Bypass Anti-Pattern, Inheritance from Layer 0, Layer 1 ≠ Layer 0 Boundary, Layer 1 Overview (+13 more)

### Community 411 - "self_check"
Cohesion: 0.25
Nodes (6): Annotate orphan edges; warn about overlay types with zero instances. An orphan…, self_check(), Covers plugins/development-harness/docs/graph-schema.md "Orphan edges": an edge…, An edge whose endpoints both exist must come back byte-identical -- no 'status'…, Running self_check twice on its own output must be a no-op -- the same edges,…, TestOrphanEdgesPreservedNotDeleted

### Community 412 - "Harness facts: pi (pi coding agent)"
Cohesion: 0.18
Nodes (10): 1. Shell command, read file, write file, 2. Hooks (Extension API), 3. Sub-agents, 4. Skills, 5. MCP, 6. Environment variables set for a shell command, Fields on the after-tool events (verbatim from `src/core/extensions/types.ts`), Harness facts: pi (pi coding agent) (+2 more)

### Community 413 - "Workflow"
Cohesion: 0.18
Nodes (10): Constraints, Impact Measurement, Step 1 — Scope, Step 2 — Baseline measurement, Step 3 — Delta measurement, Step 4 — Token cost estimation, Step 4b — Performance benchmark search, Step 5 — Context injection cost classification (+2 more)

### Community 414 - "/dh:interop — Superpowers Plan Interop Adapter"
Cohesion: 0.18
Nodes (10): /dh:interop — Superpowers Plan Interop Adapter, Example invocations, Idempotency rules, Step 1 — Validate the argument, Step 2 — Extract fields from the plan file, Step 3 — Ensure a backlog item exists, Step 4 — Invoke /work-backlog-item, Step 5 — Capture the plan address (+2 more)

### Community 415 - "command-routes.schema.json"
Cohesion: 0.18
Nodes (10): description, type, additionalProperties, description, type, properties, commands, required (+2 more)

### Community 416 - "NetworkBlocked"
Cohesion: 0.18
Nodes (10): NetworkBlocked, RuntimeError, Network guard exception type. Shared between conftest.py and…, Raised when a test attempts a network connection while the guard is armed., A direct outbound TCP connect raises instead of reaching the internet. Uses RFC…, Name resolution for a non-loopback host raises., ``connect_ex`` raises instead of returning a platform error code., test_connect_ex_is_blocked() (+2 more)

### Community 417 - "TestParseAddressPNNN"
Cohesion: 0.20
Nodes (7): parametrize, Test parse_address with P{NNN}/T{M} format strings. Tests: Address parsing for…, Various address formats parse correctly. Tests: Address parsing for multiple…, Invalid address formats raise ValueError. Tests: Input validation. How: Pass…, Slug address 'my-slug/T3' parses correctly. Tests: Slug-based address parsing.…, Slug-only address 'my-slug' returns None task_ref. Tests: Plan-only slug…, TestParseAddressPNNN

### Community 418 - "_extract_import_roots"
Cohesion: 0.22
Nodes (8): _extract_import_roots(), parametrize, Path, Assert frontend files contain no business logic. Frontends are thin adapters:…, Parse a Python file and extract all import root module names. For ``from…, Frontend files must not contain business logic., Every import in a frontend file must be on the allowlist., TestFrontendLogicFree

### Community 419 - "test_sync_groomed_entry_block_roundtrip.py"
Cohesion: 0.24
Nodes (7): _insert_named_section(), Insert or replace *section_name* content in *body* for GitHub issue bodies.…, Round-trip tests for _insert_named_section entry-block wrapper behaviour. Fix B…, _insert_named_section must wrap content so the GitHub body is find_entry_spans-…, Content written by _insert_named_section must be a locatable entry block.…, Content written through _insert_named_section round-trips to real entry IDs.…, TestInsertNamedSectionEntryBlockRoundtrip

### Community 420 - "_parse_full_database_id"
Cohesion: 0.31
Nodes (4): _parse_full_database_id(), Normalize a raw GraphQL fullDatabaseId value to int | None. GitHub's…, Unit coverage for the normalizer itself, independent of the surrounding node…, TestParseFullDatabaseIdDirectly

### Community 421 - "_entry_owning_headers"
Cohesion: 0.24
Nodes (8): _entry_owning_headers(), Map each entry block in *body* to the ``## ``/``### `` header that owns it.…, Regression test for entry-content header mis-detection (#2495 C4). Bug:…, A ``## `` line inside an entry's content must not own a later entry. RED before…, A genuine ``### `` header between entries still owns the following entry., test_header_inside_entry_content_is_not_a_section_boundary(), test_real_subsection_header_still_owns_its_entries(), Owning headers are derived from the same entry list parse_entries returns.…

### Community 422 - "test_since_filter_bad_entry_id.py"
Cohesion: 0.20
Nodes (9): A stored entry ID without a timestamp must not escape ``parse_entries`` as a…, The refusal must be catchable by the handler ``backlog_view`` actually has., The second refusal in the same function had to be converted too. A prefix can…, Only the ``since`` filter parses IDs, so the default read still returns the…, Caller-supplied filter errors use the family ``backlog_view`` catches., test_a_since_less_read_is_unaffected(), test_invalid_since_refuses_as_a_backlog_error(), test_since_read_over_a_calendar_impossible_entry_refuses_as_a_backlog_error() (+1 more)

### Community 423 - "TestItemDerivedStatusUnavailableMap"
Cohesion: 0.22
Nodes (6): _item(), Unit-level coverage of the discriminator itself., A successful fetch that omitted the issue did not establish its status., A beads nanoid / issueless item never depended on the live map in the first…, Build an open P1 backlog item with a numeric issue reference. The local…, TestItemDerivedStatusUnavailableMap

### Community 424 - "ADR-9: Close/Resolve Semantic Redesign"
Cohesion: 0.20
Nodes (9): ADR-9: Close/Resolve Semantic Redesign, Backwards compatibility, Callers that need updating, `close` — Dismissed without completion, Consequences, Context, Decision, GitHub interaction (+1 more)

### Community 425 - "ADR-1770-1: Single-Writer Contract for TaskBackend.append_task and finalize_plan"
Cohesion: 0.20
Nodes (9): ADR-1770-1: Single-Writer Contract for TaskBackend.append_task and finalize_plan, Alternatives Considered, Consequences, Context, Decision, File-level locking (fcntl.flock), GitHub API etags, Optimistic concurrency control (YAML version fields) (+1 more)

### Community 426 - "Backlog Item Groomed Schema"
Cohesion: 0.20
Nodes (9): Backlog Item Groomed Schema, Body (No Duplication), Content Rules, Example Groomed Body, Frontmatter (Research-Style), Groomed Sections (Body, under ## Groomed), Issue Classification Section Format, Root-Cause Analysis Section Format (+1 more)

### Community 427 - "locate.md"
Cohesion: 0.12
Nodes (14): Error Handling Reference, Find the Backlog Item — 3-Strategy Fallback Chain, Strategy 1 — Substring Match, Strategy 2 — Filter-First, Strategy 3 — LLM Semantic Match, Zero-match handling after all 3 strategies, Interactive Browser (Step 1.1), Completed Issue Discovery (+6 more)

### Community 428 - "GraphQL Usage Guide — Backlog MCP Sync"
Cohesion: 0.20
Nodes (10): Anti-Patterns, Cursor Pagination vs. GitLab Batch Aliases, Entry Point: `sync_issues_graphql`, GraphQL Usage Guide — Backlog MCP Sync, Incremental Sync via `since`, Must-Stay-REST Operations, Parameters, Per-Issue Callbacks (+2 more)

### Community 429 - "Task Worker"
Cohesion: 0.25
Nodes (7): Completion Report, Cross-References, Identity, Step 1 — Read the Task, Step 2 — Load Agent Profile (if specified), Step 3 — Load start-task and run it, Task Worker

### Community 430 - "addressing.py"
Cohesion: 0.22
Nodes (8): _parse_prefix(), Path, Pattern, Plan addressing module for SAM task/plan files. Resolves human-readable address…, Sort key that places ``.yaml`` files before ``.md`` for the same stem. Args: p:…, Extract the plan-type prefix, numeric/slug ref, and filename regex from an…, Initialize AddressingError with the unresolvable address and search directory., _yaml_first_key()

### Community 431 - "run_sam_server.py"
Cohesion: 0.24
Nodes (7): Run the SAM MCP server., run_server(), apply_project_dir_from_argv(), Shared MCP entrypoint pre-init: runs before any ``fastmcp``-importing module.…, If argv contains ``--project-dir``, set ``DH_PROJECT_ROOT`` when unset., PEP 723 wrapper for the backlog MCP server., PEP 723 wrapper for the SAM MCP server.

### Community 432 - "Ecosystem Research"
Cohesion: 0.20
Nodes (9): Constraints, Ecosystem Research, Output Format, Scope, Step 1 — GitHub Issues and Discussions, Step 2 — Client / Host Compatibility, Step 3 — Community Patterns, Step 4 — Real-World Gotchas (+1 more)

### Community 433 - "TestPlanNumberResolutionPropertyBased"
Cohesion: 0.29
Nodes (7): given, settings, A plan number with no matching file raises AddressingError. Tests: Negative…, Property-based tests for P{NNN} plan number resolution. Tests: Plan number…, Any valid plan number 1-9999 resolves to the correct P{NNN} file. Tests:…, Zero-padded input '001' matches file P001-*.yaml. Tests: Zero-padded string…, TestPlanNumberResolutionPropertyBased

### Community 434 - "TestSlugResolutionPNNN"
Cohesion: 0.20
Nodes (6): Test slug-based resolution against P{NNN}-{slug} files. Tests: Slug substring…, Slug 'auth-system' matches P001-auth-system.yaml. Tests: Exact slug match. How:…, Partial slug 'auth' matches P001-auth-system.yaml. Tests: Substring slug…, Non-matching slug raises AddressingError. Tests: Slug resolution failure. How:…, When slug matches multiple P-files, returns first sorted match. Tests: Multi-…, TestSlugResolutionPNNN

### Community 435 - "test_sam_task_create_without_skill_succeeds"
Cohesion: 0.22
Nodes (8): MonkeyPatch, sam-task-create accepts --repo and forwards it to operations., sam-task-create omitting --skill forwards an empty skills list, not a CLI…, sam-task-status accepts --repo and forwards it to operations., test_sam_task_create_accepts_and_forwards_repo(), fake_create(), test_sam_task_create_without_skill_succeeds(), test_sam_task_status_accepts_and_forwards_repo()

### Community 436 - "TestPriorityEnum"
Cohesion: 0.20
Nodes (4): Verify Priority IntEnum values., Verify CRITICAL is 1., Verify CRITICAL < LOWEST for sort ordering. Tests: Priority comparison…, TestPriorityEnum

### Community 437 - "TestErrorPaths"
Cohesion: 0.20
Nodes (6): Error path tests: close without checklist, view nonexistent, add duplicate,…, Scenario 22: backlog_close returns error for an invalid reason value., Scenario 23: backlog_view returns error for a selector that matches no item., Scenario 24: backlog_add returns duplicate error when similar item exists and…, Scenario 25: backlog_list returns empty items list when no items exist — not an…, TestErrorPaths

### Community 438 - "TestRecursionGuardScenarios"
Cohesion: 0.20
Nodes (6): Tests for recursion guard routing paths. These tests verify that backlog_add…, Guard 1: depth-limit source pattern creates a backlog item with source…, Guard 2: BLOCKED-FOR-PLANNING source — second add with same title is rejected…, Out-of-scope quality gate source — item created with out-of-scope pattern…, In-scope default: item with no explicit scope section proceeds normally as in-…, TestRecursionGuardScenarios

### Community 439 - "TestShouldSkipHook"
Cohesion: 0.20
Nodes (6): Unit tests for should_skip_hook(). Tests: SubagentStop runs by default, is…, SubagentStop with an empty disabled set -> False (run). Tests:…, SubagentStop disabled by ID -> True. Tests: should_skip_hook() disabled set for…, A disabled set naming an unrelated hook ID does not skip SubagentStop. Tests:…, Unknown event name -> False (let dispatch handle it). Tests: should_skip_hook()…, TestShouldSkipHook

### Community 440 - "workflow-extractor-reducer.md"
Cohesion: 0.22
Nodes (8): 1. Role, 2. Input Parsing, 3. Verification Protocol Per Finding, 4. Fragment JSON Output, 5. Miss Log Protocol, 6. Active Evidence Check, 7. Write Discipline, 8. Stop Condition

### Community 441 - "_UnionFind"
Cohesion: 0.25
Nodes (6): _build_conflict_groups(), Path-compressed union-find with union-by-rank (disjoint set union) for integer…, Return canonical root of x with path compression., Merge the sets containing x and y using union-by-rank., Run union-find over path_sets and return ConflictGroup models. Args: titles:…, _UnionFind

### Community 442 - "Work: Plan (Phase 4)"
Cohesion: 0.09
Nodes (17): Quick Mode (Step Q), Auto Mode Rules, Feature Request Template (Step 4.1), 4.3.1: Search for Plan, 4.3.2: Record Issue Number, Step 4.1: Compose Feature Request, Step 4.2: Invoke SAM Planning, Step 4.3: Update Backlog with Plan Reference (+9 more)

### Community 443 - "extract_description_from_issue_body"
Cohesion: 0.33
Nodes (4): extract_description_from_issue_body(), Extract the Description section from a GitHub issue body. Falls back to first…, Tests for extract_description_from_issue_body(body) -> str., TestExtractDescriptionFromIssueBody

### Community 444 - "AI Agent Swarm Coordination Planner"
Cohesion: 0.07
Nodes (28): 1. Dependency-Based Task Decomposition, 2. Swarm Coordination Planning, 3. Project Awareness and Context Gathering, 4. Revision Management, Agent Assignment Rules, AI Agent Swarm Coordination Planner, Bookend Task Generation, Canonical Task Writing Standard: CLEAR + Selective CoVe (+20 more)

### Community 445 - "build_issue_body"
Cohesion: 0.20
Nodes (7): build_issue_body(), Build GitHub issue body from backlog item fields. Emits only sections whose…, Tests for build_issue_body(item: BacklogItem) -> str., No Story section is generated at creation. Tests: A user story is a grooming…, No Acceptance Criteria section is generated at creation. Tests: Acceptance…, No section content is synthesised from the item title. Tests: Root-cause guard…, TestBuildIssueBody

### Community 446 - "merge_sections"
Cohesion: 0.33
Nodes (4): merge_sections(), Merge GitHub issue body into local body by section. For each section in GitHub…, Tests for merge_sections(local_body, github_body) -> tuple[str, bool]., TestMergeSections

### Community 447 - "SyncClaim"
Cohesion: 0.22
Nodes (6): BaseModel, Atomically claim the sync slot, returning the state held before the claim. The…, Restore the status that prevailed before a matching ``try_claim()``. Args:…, Atomically claim the sync slot, returning True when claimed. Thread-safe…, State captured atomically when a caller claims the sync slot., SyncClaim

### Community 448 - "layer-0/README.md"
Cohesion: 0.07
Nodes (22): ARL Touchpoints — Layer 0 Design Reference, Artifact Conventions — Layer 0 Design Reference, Anti-Patterns, CoVe Bypass Anti-Pattern, Orchestrator Discipline, Read Constraints, Source, Documents in This Directory (+14 more)

### Community 449 - "Evaluation Checklist"
Cohesion: 0.10
Nodes (17): Sources, Verdicts, verification-gate (Pre-S5), Verification Protocol, verify Skill (Completion Checklist), 1. Cross-Reference Validation, 2. Doc Completeness, 3. Knowledge-Explorer Layer Filter (+9 more)

### Community 450 - "test_comment_database_id.py"
Cohesion: 0.22
Nodes (4): Tests that a comment carries the numeric identifier REST addresses it by.…, An unselected field is absent from the response, so the query/mutation is the…, ``databaseId: Int`` silently overflows for a real comment ID; nothing should…, TestAllThreeOperationsSelectTheField

### Community 451 - "TestParsingCarriesTheIdentifier"
Cohesion: 0.22
Nodes (4): REST needs the number and the GraphQL mutations still need the node ID., The node reaches callers through this parser, so it has to survive it., GitHub's BigInt scalar serializes as a decimal string on the wire. This is the…, TestParsingCarriesTheIdentifier

### Community 452 - "TestTheModelItselfRejectsANonIntDatabaseId"
Cohesion: 0.22
Nodes (4): ``IssueCommentNode``'s own ``strict=True`` config is the second line of…, Strict mode refuses ``True``/``False`` for an ``int`` field — no silent 1/0., Strict mode refuses a numeric string — no silent coercion to int. (The string-…, TestTheModelItselfRejectsANonIntDatabaseId

### Community 453 - "Plugin Deployment Model — The Zip-and-Move Test"
Cohesion: 0.22
Nodes (8): How Claude Code installs plugins, Plugin Deployment Model — The Zip-and-Move Test, Quick reference — does this path survive?, RT-ICA condition for cross-boundary items, The cross-boundary problem, The test to apply before any change to a plugin script, What breaks the zip-and-move, What survives the zip-and-move

### Community 454 - "Design Brief: Unified Section Layer for `backlog_core`"
Cohesion: 0.22
Nodes (9): Canonical logical contract, Contributor acceptance criteria, Design Brief: Unified Section Layer for `backlog_core`, ID and timestamp rules, Mechanical boundary, Out of scope, Outcome, Read and migration behavior (+1 more)

### Community 455 - "Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code)"
Cohesion: 0.22
Nodes (8): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables set for a shell command, Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code), Identity: which product "Kimi" is

### Community 456 - "Amendments to the findings files"
Cohesion: 0.22
Nodes (8): A-1 — the predicate counts in `predicates.md` and `completeness.md` are superseded, A-2 — `fidelity.md`'s `ledger_spec.py` element counts are a 2026-09-06 measurement, A-3 — the ADR these findings were scored against was withdrawn as an unreviewed draft, A-4 — the findings assess a three-layer model the design has replaced, A-5 — `ASSESSOR-CONTRACT.md`, the authority these findings cite, has been deleted, A-6 — the citations named in A-5 have now been repointed, not merely documented as broken, A-7 — `graph_ir` is renamed to `workflow_multigraph`, and "IR" no longer names the subject, Amendments to the findings files

### Community 457 - "get_task_context.py"
Cohesion: 0.28
Nodes (8): get_active_task(), get_available_features(), main(), Any, Get task context for implementation manager dynamic injection. DEPRECATED: Use…, Get list of features with task files. Returns: Dictionary containing features…, Get active task context if any. Reads from the DH state context directory…, Print task context information.

### Community 458 - "Close / Resolve Procedure (Phase 5)"
Cohesion: 0.22
Nodes (8): Close / Resolve Procedure (Phase 5), --force flag, Step 5.2: Find Item, Step 5.3: Close path — dismiss without completion, Step 5.4: Resolve path — status:verified gate (SAM items only), Step 5.5: Resolve path — checklist verification, Step 5.6: Resolve path — typed acceptance-criteria verification, Step 5.7: Invoke backlog resolve

### Community 459 - "TestTaskIdPattern"
Cohesion: 0.25
Nodes (6): parametrize, Verify the TASK_ID_PATTERN regex matches expected patterns. Tests: Task ID…, Verify valid task IDs match the pattern., Verify invalid task IDs do not match the pattern., Letter-suffixed (T10a) and slash-separated compound (T10a/T10b) IDs are…, TestTaskIdPattern

### Community 460 - "Persistent Agent Memory"
Cohesion: 0.25
Nodes (8): Before recommending from memory, How to save memories, Memory and other forms of persistence, MEMORY.md, Persistent Agent Memory, Types of memory, What NOT to save in memory, When to access memories

### Community 461 - "Technical Researcher"
Cohesion: 0.25
Nodes (7): Input Contract, Step 1 — Scope, Step 2 — Spawn Angles (Parallel), Step 3 — Internal Review Gate (Mandatory), Step 4 — Synthesis, Step 5 — Output, Technical Researcher

### Community 462 - "_extract_content_from_comment"
Cohesion: 0.25
Nodes (8): _extract_content_from_comment(), Extract the raw content from an artifact content comment body. Parses the…, Verify inner content is extracted from a well-formed comment body. Tests:…, Verify extracted content has surrounding whitespace stripped. Tests:…, Verify malformed comments return the full body rather than raising. Tests:…, test_extract_content_from_comment_returns_full_body_when_malformed(), test_extract_content_from_comment_returns_inner_content(), test_extract_content_from_comment_strips_surrounding_whitespace()

### Community 463 - ".view_enrich_from_github"
Cohesion: 0.25
Nodes (6): _collapse_beads_status(), _normalize_due_at(), Collapse beads' seven-value status enum onto the backend-neutral open/closed…, Normalize a beads ``due_at`` timestamp to a UTC ``Z``-suffixed string. ``bd…, Enrich a ViewItemResult with live data from beads via ``bd show``. Populates…, List beads issues of type ``milestone``, with member counts via ``parent``.…

### Community 464 - "_run_spawn_item"
Cohesion: 0.29
Nodes (8): _build_spawn_cmd(), _poll_until_done(), Semaphore, Construct the spawn.py subprocess command for one dispatch item. Args:…, Poll until a spawned item completes or its PID dies. Args: mgr: State manager…, Spawn one dispatch item, monitor it, and update shared counters. Args: mgr:…, _run_spawn_item(), EffortLevel

### Community 465 - "_live_issue_wearing_an_emoji_label"
Cohesion: 0.25
Nodes (7): _live_issue_wearing_an_emoji_label(), fixture, MockerFixture, Minimal stand-in for the PyGithub repository ``get_github`` returns., Report the status label as already present, so no REST creation runs., The issue carries a label name that came from the repository, not from a caller., _Repo

### Community 466 - "TestProbeBackendStatusHonorsEveryTokenVariable"
Cohesion: 0.29
Nodes (4): MockerFixture, A missing GITHUB_TOKEN must not be reported as "no token" when a later…, GH_TOKEN (gh CLI's own variable) must not be treated as absent., TestProbeBackendStatusHonorsEveryTokenVariable

### Community 467 - "TestFixtureHasThePathology"
Cohesion: 0.25
Nodes (5): Step 1 (design §3): assert the INPUT has the defect's precondition first. A…, The fixture is the real ~72KB resolved body, not a small stand-in., The fixture contains the timestamped entry-block wrappers the defect depends on., The fixture contains the phantom ``## Claim `` headings nested in an entry.…, TestFixtureHasThePathology

### Community 468 - "_drift_view_result"
Cohesion: 0.29
Nodes (6): _drift_view_result(), Codex P2 (#2495): a cleared body must not let the sole section copy escape the…, ``_view_payload_token_count`` must reflect the SOLE section copy when body is…, backlog_view(sections=['RT-ICA']) on a drift item returns the over-budget…, Build the structured-key drift ``ViewItemResult`` for the under-count repro.…, TestOverBudgetMeasurementCountsClearedBodySoleContent

### Community 469 - "TestNarrowBodyToNamedSectionsUnit"
Cohesion: 0.25
Nodes (5): Finding 8/10: direct unit coverage for narrow_body_to_named_sections., No matching name → (body, False) with body returned unchanged., Names match case-insensitively against ``## ``/``### `` headers., Matched sections are concatenated in DOCUMENT order, not request order., TestNarrowBodyToNamedSectionsUnit

### Community 470 - "TestRootSectionOrdering"
Cohesion: 0.25
Nodes (5): root_section_ids reflects insertion order of top-level headings., A document with one h1 has exactly one root section id., The sole root section id resolves to the 'Title' heading., Document with h1/h2/h3/h2 headings has exactly 4 sections., TestRootSectionOrdering

### Community 471 - "Claims register — development-harness"
Cohesion: 0.25
Nodes (7): Claims register — development-harness, Claude Code agent teams, `dh_paths.py` claims, Harness capability matrix (read 2026-09-06), Lease, n8n as a reference for the graph model (read 2026-09-07), SQLite

### Community 472 - "LayerData"
Cohesion: 0.25
Nodes (7): collect_all_skill_names(), LayerData, Extract skill names referenced in G2 produced_by and consumed_by. Returns: Set…, Return all skill names referenced as edge endpoints in L0/G2/G4/G8.…, Holds extracted lists from all loaded layer files., Initialise with empty collections., _skills_from_artifacts()

### Community 473 - "Development Harness Purpose"
Cohesion: 0.25
Nodes (8): Audience rule, Contributor and developer frame, Development Harness Purpose, Documentation Frames and Audiences, Domain reach, Installation, configuration, and usage frame, Purpose, What the workflow must deliver

### Community 474 - "Harness facts: Claude Code"
Cohesion: 0.25
Nodes (7): 1. Shell command, read file, write file, 2. Hooks, 3. Sub-agents, 4. Plugins and skills, 5. MCP, 6. Environment variables for a shell command, Harness facts: Claude Code

### Community 475 - "Gate Push"
Cohesion: 0.25
Nodes (7): Branch → backlog lookup algorithm, Execute gate pipeline, Gate Push, No-match / unresolved fallback, Required input, Resolve complete-implementation input, Success check

### Community 476 - "Subcommand Reference"
Cohesion: 0.25
Nodes (8): kill, list, read, send, spawn, status, stop, Subcommand Reference

### Community 477 - "Research Note"
Cohesion: 0.25
Nodes (7): Research Note, Step 1 — Receive Angle Outputs, Step 2 — Cross-Angle Signal Detection, Step 3 — Conflict Detection and Resolution, Step 4 — Gap Aggregation, Step 5 — All-INCONCLUSIVE Gate, Step 6 — Synthesize the Research Note

### Community 478 - "Workflow: Groom Backlog Item"
Cohesion: 0.25
Nodes (8): Batch Grooming, Checklist, Error Routing, Identifier Convention, Inputs, Main Flow, Process Documents, Workflow: Groom Backlog Item

### Community 479 - "TestArtifactManifestModelValidation"
Cohesion: 0.25
Nodes (5): Unit tests for ArtifactManifest Pydantic model. Tests: ArtifactManifest…, ArtifactManifest requires issue_number at construction. Tests:…, ArtifactManifest.artifacts defaults to an empty list. Tests: ArtifactManifest…, ArtifactManifest accepts 'last-updated' and 'last_updated' aliases. Tests:…, TestArtifactManifestModelValidation

### Community 480 - "TestComplexityEnum"
Cohesion: 0.25
Nodes (5): Verify MEDIUM maps to 'medium'., Verify HIGH maps to 'high'., Verify Complexity StrEnum values., Verify LOW maps to 'low'., TestComplexityEnum

### Community 481 - "TestTaskEnumCoercion"
Cohesion: 0.25
Nodes (5): Verify Task model coerces string values to enum values. Tests: use_enum_values…, Verify 'not-started' string is accepted as TaskStatus., Verify integer priority is accepted as Priority., Verify 'high' string is accepted as Complexity., TestTaskEnumCoercion

### Community 482 - "TestParseCommentNode"
Cohesion: 0.25
Nodes (5): _parse_comment_node returns empty strings for absent optional fields. Tests:…, Unit tests for _parse_comment_node helper., _parse_comment_node maps all GraphQL fields to IssueCommentNode keys. Tests:…, _parse_comment_node returns empty string author when author is absent. Tests:…, TestParseCommentNode

### Community 483 - "TestEmptyCommandList"
Cohesion: 0.25
Nodes (5): run_quality_gates with an empty commands list., Empty command list returns GateResult with passed=True. Tests:…, Empty command list returns GateResult with empty results list. Tests: results…, Empty command list records the requested mode in GateResult. Tests:…, TestEmptyCommandList

### Community 484 - "TestQualityGatesConstruction"
Cohesion: 0.25
Nodes (5): QualityGates construction and defaults., QualityGates constructs with empty pre_merge and post_merge lists by default.…, QualityGates.model_validate accepts 'pre-merge' kebab-case alias. Tests:…, QualityGates.model_validate accepts 'post-merge' kebab-case alias. Tests:…, TestQualityGatesConstruction

### Community 485 - "TestSemanticQueryCorpus"
Cohesion: 0.32
Nodes (5): 10-query semantic corpus achieves at least 80% success rate (8/10 matches)., Each corpus query returns at least one result (no empty result sets)., Corpus-based integration tests verifying the filter infrastructure supports…, Create all corpus items in the test backlog directory., TestSemanticQueryCorpus

### Community 486 - "test_tool_output_schemas.py"
Cohesion: 0.36
Nodes (7): Asserts every backlog_core MCP tool advertises a real output schema, not an…, No tool_responses.py model field name collides with an Output method.…, _schema_tokens(), test_all_typed_tools_advertise_a_real_output_schema(), test_no_response_model_field_shadows_an_output_method(), test_output_schemas_stay_within_token_budget(), _tool_schemas()

### Community 487 - "tn-verification-gate.md"
Cohesion: 0.29
Nodes (6): Step 1: Retrieve Both Inputs, Step 2: Re-Run Each Check Command, Step 3: Compute CriterionStatus, Step 4: Assemble TN Verification YAML, Step 5: Register Artifact via MCP, Step 6: Report Regressions (If verdict FAIL)

### Community 488 - "TestViewItemReturnsTenSectionsNotFortySix"
Cohesion: 0.33
Nodes (5): MockerFixture, Step 2 (design §3): drive the real summary-assembly path through ``view_item``.…, ``view_item(include_content=False)`` reports 10 sections for the real body. RED…, The rendered ``sections_index`` also excludes phantom entry-content headings., TestViewItemReturnsTenSectionsNotFortySix

### Community 489 - "test_a_plan_update_reports_a_dropped_connection_instead_of_raising"
Cohesion: 0.33
Nodes (7): usefixtures, Return the warnings an operation result carries. Returns: The ``warnings``…, ``_rename_item_title``'s mirror failure reaches the caller as a warning., ``_apply_plan_to_item``'s mirror failure reaches the caller as a warning., test_a_plan_update_reports_a_dropped_connection_instead_of_raising(), test_a_title_update_reports_a_dropped_connection_instead_of_raising(), _warnings()

### Community 490 - "Workflow Extraction Rules"
Cohesion: 0.29
Nodes (7): Agent roles, Coverage manifest, Existing layer data (collected 2026-06-08), Schema discipline, Source structure, Trust boundary — the core rule, Workflow Extraction Rules

### Community 491 - "_resolve_repo_with_timeout"
Cohesion: 0.29
Nodes (6): GitResolutionTimeoutError, Repo, RuntimeError, Raised when GitPython does not resolve a repository within the timeout., Construct a ``git.Repo`` bounded by a hang guard. GitPython's ``Repo()``…, _resolve_repo_with_timeout()

### Community 492 - ".list_plans"
Cohesion: 0.29
Nodes (5): BaseModel, Return all entries from ``bd memories --json``. ``bd memories --json`` returns…, Return plan summaries by scanning bd remember for plan index entries. Calls bd…, Single entry from ``bd memories --json`` output. Attributes: key: Remember…, _RememberEntry

### Community 493 - ".validate_parent_issue_number"
Cohesion: 0.29
Nodes (4): field_validator, r"""Validate that each item in a task ID list matches the task ID pattern.…, Coerce the ``issue`` field to a string. YAML parses bare integers (e.g.…, Accept None, int >= 0, or a beads nanoid string; reject everything else.…

### Community 494 - "resolve_task_id"
Cohesion: 0.29
Nodes (6): has_yaml_frontmatter(), Any, Task format detection and field resolution utilities. Provides helpers for…, r"""Return True if content begins with a valid YAML frontmatter block. A valid…, Resolve the task ID from a parsed YAML frontmatter dict. Supports both…, resolve_task_id()

### Community 495 - "Recursive Follow-up Handling: Steps 2–5"
Cohesion: 0.29
Nodes (7): Guard 1: Depth check, Guard 2: RT-ICA BLOCKED check, Recursive Follow-up Handling: Steps 2–5, Step 2: Search Backlog by Title Keywords, Step 3: Classify Follow-up Findings, Step 4: Link or Create Backlog Item, Step 5: Recursion Gate

### Community 496 - "Groomed items — staleness check"
Cohesion: 0.29
Nodes (7): Auto-Groom Check (Step 3.1), Extract Impact Radius files, Groomed items — staleness check, Phase 1 — Drift detection, Phase 2 actions by token, Phase 2 — Drift assessment, Ungroomed items

### Community 497 - "SAM (Stateless Agent Methodology) — Definition"
Cohesion: 0.29
Nodes (7): Canonical SAM (external repo), claude_skills implementation, Core Principles, How work-backlog-item embodies SAM, SAM (Stateless Agent Methodology) — Definition, Source, What SAM Is

### Community 498 - "plan_dir"
Cohesion: 0.29
Nodes (7): plan_dir(), plan_dir_with_p_files(), plan_dir_with_qg_files(), fixture, Return a temporary plan/ directory., Populate plan/ with P{NNN}-{slug}.yaml files and a legacy tasks-* file.…, Populate plan/ with a QG{NNN}-{slug}.yaml file alongside P-prefix files.…

### Community 500 - ".test_git_common_root_closes_repo_object"
Cohesion: 0.29
Nodes (5): MockerFixture, Tests that the GitPython Repo object constructed internally is closed., Clear module-level root cache before each test., _git_common_root closes the GitPython Repo it constructs. Tests: resource…, TestGitCommonRootResourceCleanup

### Community 501 - "t0-baseline-capture.md"
Cohesion: 0.33
Nodes (5): Step 1: Read the Plan, Step 2: Run Each Check Command, Step 3: Assemble T0 Baseline YAML, Step 4: Verify YAML Structure in Memory, Step 5: Register Artifact

### Community 502 - "TestPrewrappedContentSurvivesBodyRoundTrip"
Cohesion: 0.33
Nodes (4): A pre-wrapped submission must not lose content or emit a stray entry., Round-tripping a pre-wrapped submission yields one entry, not an orphan closing…, The agent's actual verdict text survives the round-trip. Why: The observed…, TestPrewrappedContentSurvivesBodyRoundTrip

### Community 503 - "TestFalsification"
Cohesion: 0.33
Nodes (4): Step 4 (design §3): falsification checks that must fail to fail. A test that…, The deleted ``_SECTION_BOUNDARY_RE`` pattern, run inline against the real body.…, The fix changes entry-block behaviour only, not plain-heading behaviour. This…, TestFalsification

### Community 504 - ".test_compact_valid_section_name_not_miss_and_metadata_filtered"
Cohesion: 0.33
Nodes (4): Finding #4: include_content=False with VALID names must not report a miss., backlog_view(summary=False, include_content=False, sections=['RT-ICA']).…, An INVALID name in compact mode still reports a miss (no false negative)., TestCompactValidNamesNotReportedAsMiss

### Community 505 - "ADR-3113-1: Dispatch roles name scope, not capability, and enforcement sits with the dispatcher"
Cohesion: 0.33
Nodes (5): ADR-3113-1: Dispatch roles name scope, not capability, and enforcement sits with the dispatcher, Consequences, Considered alternatives, Context, Decision

### Community 506 - "_emit_skill_handoff"
Cohesion: 0.33
Nodes (6): _emit_skill_handoff(), _ensure_skill_stub(), _normalize_skill_target(), Add a stub skill node to *stubs* when *skill_id* is absent from *known*.…, Strip a leading 'plugin:' qualifier from an L1 hands_off_to_skill target. L1…, Emit the edge for a ``hands_off_to_skill`` trace. Plugin-qualifier-normalized…

### Community 507 - "Beads and development-harness usage"
Cohesion: 0.33
Nodes (6): Beads and development-harness usage, Example, Handoff requirements, Related documentation, Rule of thumb, Side-by-side workflow

### Community 508 - "run_live_validation_skill.py"
Cohesion: 0.40
Nodes (5): _find_project_root(), main(), Run a single live validation query against a skill. Thin wrapper around…, Walk up from cwd looking for .claude/ to find the project root. Returns:…, Parse arguments, run query, exit with result code.

### Community 509 - "Backend Resolution"
Cohesion: 0.33
Nodes (5): Acting on the answer, Backend Resolution, Do not re-derive this, Identifier shapes, The chain

### Community 510 - "Read the Code Review Verdict"
Cohesion: 0.33
Nodes (5): Read the Code Review Verdict, Step A — Read by identifier, Step B — Step A found no such entry, Step C — No `code-review` entry for this quality-gate plan, Step D — Neither type yields a report

### Community 511 - "Output Event Types"
Cohesion: 0.33
Nodes (6): Assistant Events, Output Event Types, Rate Limit Events, Result Events, Streaming Events (with --include-partial-messages), System Events

### Community 512 - "Error Categories"
Cohesion: 0.33
Nodes (6): 1. Agent Failure, 2. Workflow Block, 3. System Error, Error Categories, Escalation, Groom: Error Handling

### Community 513 - "Workflow: Groom Drift Check"
Cohesion: 0.33
Nodes (6): Inputs, Mode A: Plan Drift, Mode B: Grooming Drift, Routing, Terminal State, Workflow: Groom Drift Check

### Community 514 - "test_backend_factory_import_order"
Cohesion: 0.33
Nodes (5): parametrize, unit, Regression coverage for acyclic backlog backend imports., Both import orders construct every backend and satisfy the contract., test_backend_factory_import_order()

### Community 515 - "sample_github_body.md"
Cohesion: 0.33
Nodes (5): Description, Fact-Check, Groomed (2026-01-15), Impact, Priority

### Community 516 - "TestSamClaimParser"
Cohesion: 0.33
Nodes (4): Test named-only parsing for ``plan claim``., A claim address must be supplied with ``--address``., Removed or misspelled options must fail in the parser., TestSamClaimParser

### Community 517 - "TestToolRegistration"
Cohesion: 0.33
Nodes (4): Tests for MCP tool registration on the agent_profile server. Tests: Both tools…, agent_profile server exposes 'load' and 'list' as registered tools. Tests: Tool…, agent_profile server exposes exactly two tools: load and list. Tests: No…, TestToolRegistration

### Community 518 - "test_backlog_list_passes_output_instance_to_operations"
Cohesion: 0.33
Nodes (5): backlog_add provides an Output instance as the 'output' keyword arg., backlog_list provides an Output instance as the 'output' keyword arg., test_backlog_add_passes_output_instance_to_operations(), _capture(), test_backlog_list_passes_output_instance_to_operations()

### Community 519 - "TestMergeIntegrationBranchValidation"
Cohesion: 0.33
Nodes (4): merge_integration_branch rejects head_branch == base_branch before API calls., Test head_branch == base_branch raises BacklogError without API call. Tests:…, Test distinct head and base branches are accepted and reach the API. Tests:…, TestMergeIntegrationBranchValidation

### Community 520 - "ADR-3072-1: Budget applies only at the Navigation stage"
Cohesion: 0.40
Nodes (4): ADR-3072-1: Budget applies only at the Navigation stage, Considered alternative, Context, Decision

### Community 521 - "session-end-kage-bunshin-child-notify.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 522 - "session-end-kage-bunshin-cleanup.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 523 - "stop-kage-bunshin-child-notify.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 524 - "stop-kage-bunshin-idle-check.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 525 - "task-completed-kage-bunshin-reminder.cjs"
Cohesion: 0.40
Nodes (4): { execFileSync }, fs, os, path

### Community 526 - "Planning Tools"
Cohesion: 0.40
Nodes (5): `/dh:clear-cove-task-design`, `/dh:generate-task`, `/dh:planner-rt-ica`, `/dh:validation-protocol`, Planning Tools

### Community 527 - "Quality Gate Plan Creation"
Cohesion: 0.40
Nodes (5): Quality Gate Plan Creation, Step 1: Check for existing QG plan, Step 2: Create QG plan (if not found), Step 2a: Put the QG plan in the ledger, Step 3: Reopen blocked tasks (on re-run)

### Community 528 - "Generate Task (Worker Task Prompt)"
Cohesion: 0.40
Nodes (4): Generate Task (Worker Task Prompt), Inputs, Lint Before Final Output, Output

### Community 529 - "TestParseTaskContentRawYaml"
Cohesion: 0.40
Nodes (4): MonkeyPatch, r"""Parses raw YAML frontmatter without emitting any WARNING. Tests:…, Tests for parse_task_content with bare YAML frontmatter (the live code path).…, TestParseTaskContentRawYaml

### Community 531 - "complete-implementation/SKILL.md"
Cohesion: 0.14
Nodes (7): Completion Verification Gate, Pre-Phase 1b: Process Accumulated Concerns, Concerns Check — Implementation Notes, Final Handoff Output, Migration Fidelity Sign-Off Gate, On-Block Output, QG dispatch step

### Community 532 - "Development Harness — Plugin Overview and Skill Router"
Cohesion: 0.29
Nodes (6): Development Harness — Plugin Overview and Skill Router, Lifecycle — Creation to Verified Closure, Quick Decision Reference, SAM Workflow Pipeline, Skill Router — "I want to do X", What This Plugin Provides

### Community 533 - "Experiment Log: Sequential Resume (2026-03-22)"
Cohesion: 0.40
Nodes (5): Call 1: Set Secret, Call 2: Recall Secret, Experiment Log: Sequential Resume (2026-03-22), Key Finding, Setup

### Community 534 - "Experiment Log: Stream-JSON Multi-Turn (2026-03-22)"
Cohesion: 0.40
Nodes (5): Experiment Log: Stream-JSON Multi-Turn (2026-03-22), Key Finding, Messages Sent, Results, Setup

### Community 535 - "DispatchStateManager"
Cohesion: 0.02
Nodes (92): DispatchStateManager, Path, Row, Close the underlying SQLite connection., Return the filesystem path to the SQLite database., Insert a wave row and all item rows. Args: milestone: GitHub milestone number.…, Retrieve a wave with all nested items. Args: milestone: GitHub milestone…, Retrieve all waves for a milestone in insertion order. Args: milestone: GitHub… (+84 more)

### Community 536 - "Team Health Check"
Cohesion: 0.40
Nodes (5): Output per member, Session file lookup, Team Health Check, Team name discovery, When to use

### Community 537 - "Monitoring spawned sessions"
Cohesion: 0.40
Nodes (5): CLI flags, JSON output statuses, Monitoring lifecycle, Monitoring spawned sessions, Spawning the monitor — choose based on what you need

### Community 538 - "test_cmd_list_shows_alive_and_dead_sessions"
Cohesion: 0.40
Nodes (3): test_cmd_list_shows_alive_and_dead_sessions(), fake_alive(), test_wait_for_session_exit_returns_true_after_a_few_polls()

### Community 539 - "test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case"
Cohesion: 0.40
Nodes (5): _CASE_SPELLINGS, A plan id spelled in another case routes to the ledger that holds the plan. The…, A ledger-only command finds the plan when its id is spelled in another case., test_a_ledger_only_command_accepts_a_plan_id_differing_only_in_case(), test_a_plan_address_differing_only_in_case_reads_the_ledger()

### Community 540 - "test_output_fields_always_present_on_error"
Cohesion: 0.40
Nodes (5): parametrize, Every tool response includes messages, warnings, and errors keys on success., Every tool response includes error key and output fields on BacklogError., test_output_fields_always_present_on_error(), test_output_fields_always_present_on_success()

### Community 541 - "test_default_test_paths_match_pyproject_testpaths"
Cohesion: 0.40
Nodes (4): skipif, Drift guard for run_pytest.py's standalone test-path duplication.…, This plugin's *existing* entries in root ``testpaths`` must equal…, test_default_test_paths_match_pyproject_testpaths()

### Community 542 - "AGENTS.md"
Cohesion: 0.06
Nodes (22): Development Harness, Dispatch Roles, Language, Adding a type, Artifact Type Registry, Ownership rule, Registration and discovery, Task plans (+14 more)

### Community 543 - ".__get_pydantic_json_schema__"
Cohesion: 0.50
Nodes (3): Generate the advertised schema from the response model. Returns: The response…, GetJsonSchemaHandler, JsonSchemaValue

### Community 544 - "_reset_config"
Cohesion: 0.50
Nodes (4): fixture, MonkeyPatch, Restore _config to None after each test to isolate state., _reset_config()

### Community 545 - "TestZeroIdSentinelIsDetectable"
Cohesion: 0.50
Nodes (3): Sanity check: the zero-ID prefix we assert against is the actual fallback. This…, The zero-timestamp ID produced by entry_blocks fallback starts with…, TestZeroIdSentinelIsDetectable

### Community 546 - "test_import_boundaries.py"
Cohesion: 0.50
Nodes (3): Import-order regressions for development-harness module boundaries., The operations-first import order completes in a fresh interpreter., test_operations_imports_before_server_without_cycle()

### Community 547 - "TestOperationsDoesNotImportFromGithubSync"
Cohesion: 0.50
Nodes (3): operations.py must not import rendering symbols from github_sync at module…, Verify via AST that operations.py has no github_sync rendering imports. After…, TestOperationsDoesNotImportFromGithubSync

### Community 548 - "TestPLRLintGate"
Cohesion: 0.50
Nodes (3): ruff PLR0915/PLR0914 gate on indexer.py. This class is deliberately RED before…, ruff --select PLR0915,PLR0914 must exit 0 on indexer.py after decomposition.…, TestPLRLintGate

### Community 549 - "test_init_docstring.py"
Cohesion: 0.50
Nodes (3): TDD test that every name in __all__ is documented in the module docstring.…, Every name in __all__ must appear as a substring in the module docstring.…, test_all_exports_appear_in_module_docstring()

### Community 550 - "Hook Subprocess Invocation"
Cohesion: 0.50
Nodes (3): Hook Subprocess Invocation, Never call `fastmcp call` from here, Use the plain CLI instead

### Community 551 - "SDLC Layer Separation Architecture"
Cohesion: 0.25
Nodes (7): Directory Structure, Evaluation, Experiments & Learnings, Layer Model, Principles, References, SDLC Layer Separation Architecture

### Community 552 - "DH Workflow Map — Coverage Manifest"
Cohesion: 0.17
Nodes (11): Collected layers, Collection methodology, DH Workflow Map — Coverage Manifest, Follow-up protocol, Key findings from collected layers (optimization-relevant), Remaining gaps, Source provenance, Tier 1 — Only the assembler output needs refreshing (layer data unchanged) (+3 more)

### Community 553 - "DH Plugin Known Entities"
Cohesion: 0.09
Nodes (21): Agent profile tools (mounted under backlog server namespace), Agents (30), Artifact tools, Backlog Item Sections (`backlog_groom(section=...)`), Backlog item tools, Body sections defined in item schema, DH Plugin Known Entities, Dispatch orchestration tools (+13 more)

### Community 555 - "pytest_runtest_protocol"
Cohesion: 0.50
Nodes (4): pytest_runtest_protocol(), Compute the per-test network policy from the e2e marker + env var. No public…, hookimpl, Item

### Community 556 - "Config"
Cohesion: 0.50
Nodes (4): pytest_unconfigure(), Restore the real socket functions at session teardown. Args: config: The pytest…, Config, One ``.dh/config.yaml`` key the ledger reads.

### Community 557 - "MCP Servers"
Cohesion: 0.50
Nodes (4): MCP Servers, `plugin:dh:backlog` — Structured Backlog Workflow, `plugin:dh:sam` — Stateless Agent Methodology (SAM), `plugin:dh:sequential_thinking` — Sequential Thinking

### Community 558 - "Recursive Follow-up Handling"
Cohesion: 0.50
Nodes (4): Constants, Recursive Follow-up Handling, Step 1: Detect Follow-up Plans, Steps 2–5: Route Follow-ups to Backlog

### Community 559 - "gen_run_stamp.py"
Cohesion: 0.50
Nodes (3): main(), Print "{UTC timestamp}-{16 hex chars}" to stdout., Print a collision-resistant run stamp for multi-perspective-review slugs. A UTC…

### Community 560 - "Groom finalize hardening provenance"
Cohesion: 0.50
Nodes (3): Carried from the retired `groom-backlog-item` skill, Groom finalize hardening provenance, Output Validation Gate retry — same model only

### Community 561 - "test_unknown_backend_name_refuses_as_a_backlog_error"
Cohesion: 0.50
Nodes (4): MonkeyPatch, unit, ``operations.try_get_github`` is the shortest MCP-reachable path through…, test_unknown_backend_name_refuses_as_a_backlog_error()

### Community 562 - "run_pytest.py"
Cohesion: 0.50
Nodes (3): main(), Run development-harness tests without a plugin-local project environment., Run the plugin test suites from the bundle root and forward arguments. A…

### Community 563 - "milestone_existing_and_leased"
Cohesion: 0.50
Nodes (4): milestone_existing_and_leased(), milestone_plan(), Build the plan one milestone item describes. Returns: The source, ready for…, Rebuild a milestone plan the ledger already holds, one of whose tasks holds an…

### Community 564 - "test_artifact_provider_fallback.py"
Cohesion: 0.67
Nodes (3): MonkeyPatch, test_get_artifact_provider_rejects_backend_without_content(), test_get_artifact_provider_returns_configured_content_provider()

### Community 565 - "test_guard_covers_testpath"
Cohesion: 0.50
Nodes (4): integration, parametrize, The root conftest guard applies to every configured testpath. Writes a probe…, test_guard_covers_testpath()

### Community 566 - "TestCreateBacklogItem"
Cohesion: 0.50
Nodes (3): Scenarios consumed by the /work-backlog-item create route., backlog_add creates a file, syncs a GitHub issue, and returns all expected…, TestCreateBacklogItem

### Community 569 - "_parse_args"
Cohesion: 0.67
Nodes (3): _parse_args(), Namespace, Parse server startup arguments. Returns: Parsed namespace; ``project_dir`` is…

### Community 572 - "_mock_get_encoding"
Cohesion: 0.67
Nodes (3): _mock_get_encoding(), Encoding, Return the byte-level mock encoder used when real BPE tables are unavailable.…

### Community 577 - "Apply status:verified Label"
Cohesion: 0.67
Nodes (3): Apply status:verified Label, Step 1: Locate the backlog item, Step 2: Apply the label

### Community 579 - "Milestone Dispatch Patterns"
Cohesion: 0.67
Nodes (3): Groom Dispatch, Milestone Dispatch Patterns, Work Dispatch

### Community 581 - "test_canonical_plan_id_leaves_a_non_uid_id_unchanged"
Cohesion: 0.67
Nodes (3): parametrize, An id that is not ``P`` plus exactly eight hex digits passes through unchanged.…, test_canonical_plan_id_leaves_a_non_uid_id_unchanged()

### Community 583 - "test_resolve_all_entry_ids_property_ids_are_always_pairwise_distinct"
Cohesion: 0.67
Nodes (3): given, Property: for any input list drawn from an alphabet designed to provoke…, test_resolve_all_entry_ids_property_ids_are_always_pairwise_distinct()

### Community 584 - "test_resolve_all_entry_ids_never_produces_duplicate_ids"
Cohesion: 0.67
Nodes (3): parametrize, For any input list of raw ids, every resolved id must be pairwise distinct --…, test_resolve_all_entry_ids_never_produces_duplicate_ids()

### Community 608 - "Add New Feature (SAM Workflow)"
Cohesion: 0.10
Nodes (20): Add New Feature (SAM Workflow), Artifact Discovery (Pre-Phase), Discovered During Implementation, Domain Signal Detection — Config-Driven (`.dh/skill_discovery.yaml`), Orchestrator Discipline, Phase 1: Discovery (@dh:feature-researcher), Phase 2: Codebase Analysis (@dh:codebase-analyzer), Phase 3: Architecture Spec (design-spec role) (+12 more)

### Community 609 - "Analyze Test Failures"
Cohesion: 0.12
Nodes (15): 1. Initial Analysis, 2. Investigate the Implementation, 3. Apply Critical Thinking, 4. Make a Determination, 5. Document Reasoning, Analysis Process, Analyze Test Failures, Context (+7 more)

### Community 610 - "Workflow"
Cohesion: 0.20
Nodes (9): API State, Constraints, Step 1 — Scope, Step 2 — Current API State, Step 3 — Changelog, Step 4 — Breaking Changes, Step 5 — Gotchas, Step 6 — Output (+1 more)

### Community 615 - "CLEAR + CoVe Task Design for Agent Swarms"
Cohesion: 0.09
Nodes (21): A: Adaptive, Apply CoVe When Any Are True, C: Concise, CLEAR + CoVe Task Design for Agent Swarms, CLEAR Guidelines for Task Prompts, CoVe Guidelines for Worker Tasks, E: Explicit, L: Logical (+13 more)

### Community 616 - "SOP (Architecture Audit)"
Cohesion: 0.10
Nodes (20): Architecture Audit — Module Dependency Graph, Color Legend, Output Format, Partitioned Report — Child Diagram, Partitioned Report — Parent Diagram (> 40 nodes), Single-Diagram Report (≤ 40 nodes — no partitioning), SOP (Architecture Audit), Step 0: Determine Scope (+12 more)

### Community 617 - "Claude Skills and Agent Code Review Patterns"
Cohesion: 0.17
Nodes (11): Agent Contracts, Anti-Patterns, Claude Skills and Agent Code Review Patterns, Code Fence Requirements, Description Quality, File Reference Standards, Frontmatter Validity, Non-Invocable Skills (+3 more)

### Community 618 - "CLI Application Code Review Patterns"
Cohesion: 0.18
Nodes (10): ANSI Color Codes, Anti-Patterns, Argument Validation, CLI Application Code Review Patterns, Dry Run for Destructive Operations, Exit Codes, Help and Version Flags, Non-Interactive Operation (+2 more)

### Community 619 - "LLM Integration Code Review Patterns"
Cohesion: 0.15
Nodes (12): Anti-Patterns, Context Management, Evaluation, LLM Integration Code Review Patterns, Model Selection, Prompt Hygiene, Retry Logic, Safety (+4 more)

### Community 620 - "Node.js Code Review Patterns"
Cohesion: 0.20
Nodes (9): Anti-Patterns, Dependency Hygiene, Environment Variables, Event Emitter Cleanup, Node.js Code Review Patterns, Process Exit, Security, Stream Backpressure (+1 more)

### Community 621 - "Python Code Review Patterns"
Cohesion: 0.20
Nodes (9): Anti-Patterns, Error Handling, Modern Python 3.11+ Idioms, pytest Patterns, Python Code Review Patterns, Ruff Compliance, ty Type Safety, Type Annotations (+1 more)

### Community 622 - "TypeScript Code Review Patterns"
Cohesion: 0.18
Nodes (10): Anti-Patterns, Async Patterns, Branded Types, Discriminated Unions Over Booleans, ESM, Runtime Safety, `satisfies` Operator, Strict Mode (+2 more)

### Community 623 - "Web Frontend Code Review Patterns"
Cohesion: 0.22
Nodes (8): Accessibility, Anti-Patterns, CSS, Event Listener Cleanup, Forms, Performance, Web Frontend Code Review Patterns, XSS Prevention

### Community 624 - "Codebase Auditor"
Cohesion: 0.17
Nodes (11): Agent Data Flow Mapping, Behavioral Contract Derivation, Codebase Auditor, Coding Convention Extraction, Input, Operating Constraints, Output Format, Plugin Context Check (+3 more)

### Community 625 - "Codemod Runner"
Cohesion: 0.20
Nodes (9): Codemod Runner, Large-Scale Codemod Swarm Pattern, Phase 1 — Scope Assessment (run before any transformation), Phase 2 — Batch Execution, Phase 3 — Per-Batch Idempotency Check, Phase 4 — Verification Trend, Phase 5 — Commit, Tool Quick Reference (+1 more)

### Community 628 - "Workflow"
Cohesion: 0.18
Nodes (10): Arguments, Complete Milestone, Error Handling, Step 1: Resolve and Audit, Step 2: Show State, Step 3: Handle Open Issues, Step 4: Close Milestone, Step 5: Update Project V2 (+2 more)

### Community 629 - "Comprehensive Test Review"
Cohesion: 0.25
Nodes (7): Additional Examination Points, Analysis Process, Comprehensive Test Review, Output Format, Related Skills, Standard Checklist, Test Review Process

### Community 630 - "SAM Stage 3 — Context Integration"
Cohesion: 0.14
Nodes (13): Behavioral Rules, Input, Output, Process, Role, Role Resolution, SAM Stage 3 — Context Integration, Step 1 — Scope Analysis (+5 more)

### Community 631 - "Create Artifact"
Cohesion: 0.13
Nodes (14): architect, `artifact_id`, `artifact_type`, codebase-analysis (one call per focus area), `content`, Create Artifact, Examples by artifact type, feature-context (+6 more)

### Community 633 - "File-to-Stack Mappings"
Cohesion: 0.11
Nodes (18): Claude Code Project, File-to-Stack Mappings, General Description Files, Go, Infrastructure and Automation, Java / JVM, Multi-Stack Projects, Pass 1 — Specific markers (highest priority) (+10 more)

### Community 634 - "skill_discovery.yaml — Schema Reference"
Cohesion: 0.09
Nodes (21): `always_use_skills`, `always_use_skills` is never filtered by `avoid_skills`, `avoid_skills`, `avoid_skills` overrides `prefer_skills`, Complete Annotated Example, Examples, Field Interaction Rules, File Location (+13 more)

### Community 635 - "Skill Marketplace Search Reference"
Cohesion: 0.11
Nodes (18): CLI Commands, Error Handling, Global vs Plugin-Bundled Skills, Globally installed skills (`~/.claude/skills/`), Install a skill, List installed skills, Marketplace unreachable, No results found for query (+10 more)

### Community 636 - "Wizard Questions Reference"
Cohesion: 0.10
Nodes (20): Category 1: Testing Conventions, Category 2: Linting and Formatting, Category 3: Type Checking, Category 4: CI/CD Quality Gates, Category 5: Documentation, Category 6: Domain-Specific, Q10: Database Schema Migrations or Complex SQL, Q11: Frontend Component Library (+12 more)

### Community 638 - "Implement Feature (SAM Workflow Execution)"
Cohesion: 0.05
Nodes (37): Codes a command may print to you, Sequence, The runner contract, Your two facts, Each turn, Export, The judge, The work loop (+29 more)

### Community 639 - "SAM Stage 4 — Task Decomposition"
Cohesion: 0.11
Nodes (17): Choosing a plan-creation path, Human Touchpoint Gate, Incremental path (large plans — preferred when 16+ tasks), Input, Monolithic path (small plans), Output, Process, Role (+9 more)

### Community 640 - "Test Failure Analysis Mindset"
Cohesion: 0.15
Nodes (12): 1. Pause and Read, 2. Trace the Implementation, 3. Consider the Context, 4. Make a Reasoned Decision, 5. Learn from the Failure, Core Principle, Dual Hypothesis Approach, Good Practices (+4 more)

### Community 641 - "Fix Validation Protocol"
Cohesion: 0.12
Nodes (15): Anti-Pattern 1: Claiming Success Without Reproducing Failure, Anti-Pattern 2: Confusing "No Errors" with Success, Anti-Pattern 3: Skipping Verification, Anti-Pattern 4: Partial Verification, Common Anti-Patterns to Avoid, Core Principle, Fix Validation Protocol, Integration with Testing (+7 more)

### Community 643 - "impact-analyst.md"
Cohesion: 0.07
Nodes (27): Backend Compatibility, Backend detection, Core Principle, Critical Rules, Decision Criteria, Escalation rule, GitHub-only tools, High risk indicators (+19 more)

### Community 648 - "work/rt-ica-gate.md"
Cohesion: 0.15
Nodes (12): BLOCKED Output Contract, Feasibility Gate Reference, Gate Logic, PASS Output Contract, STALE_GROOM Output Contract, Step 3.1: Auto-Groom (if needed), Step 3.2: RT-ICA Gate, Step 3.3: RT-ICA Date Stamp (+4 more)

### Community 653 - "Data Pipeline Optimization - Task Plan"
Cohesion: 0.12
Nodes (15): Acceptance Criteria, Acceptance Criteria, Acceptance Criteria, Acceptance Criteria, Data Pipeline Optimization - Task Plan, Dependency Graph, File Ownership Map, Objective (+7 more)

### Community 654 - "Bold Fields Test Plan"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Acceptance Criteria, Acceptance Criteria, Bold Fields Test Plan, Context, Context, Context, T1: Setup database schema (+2 more)

### Community 659 - "Complete ty Skill Implementation"
Cohesion: 0.50
Nodes (3): Complete ty Skill Implementation, Notes, Tasks

### Community 661 - "Context Manifest"
Cohesion: 0.22
Nodes (8): Context, Context, Context, Context Manifest, Objective, Objective, Objective, Overview

### Community 662 - "yaml_frontmatter_single.md"
Cohesion: 0.40
Nodes (4): Acceptance Criteria, Context, Objective, Requirements

### Community 663 - "Tasks: Widget Overhaul Follow-up"
Cohesion: 0.40
Nodes (4): Description, Parent Task, Status, Tasks: Widget Overhaul Follow-up

## Knowledge Gaps
- **2186 isolated node(s):** `npx`, `@modelcontextprotocol/server-sequential-thinking`, `STYLE_GUIDE`, `{ execFileSync }`, `fs` (+2181 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 11865 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **102 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Output` connect `Output` to `backlog_core/models.py`, `Entry`, `gh_client.py`, `sam_plan.py`, `test_backlog_list_passes_output_instance_to_operations`, `GitHubBackend`, `PullRequestRef`, `ContentRef`, `test_github_tools_issues.py`, `BranchInfo`, `backlog_list`, `Section`, `FileCache`, `test_github_tools_prs.py`, `OrdinalPathMapper`, `BacklogItem`, `BacklogError`, `BeadsBackend`, `Any`, `InMemoryBackend`, `test_disclosure_handler.py`, `BacklogConfig`, `WorkItemBackend`, `test_batch_section_writes.py`, `_Repository`, `BacklogItemMetadata`, `backlog_core/operations.py`, `BacklogViewDisclosureHandler`, `ArtifactType`, `github_branches.py`, `ContentConflictError`, `TokenBoundedExtractor`, `test_ac_overlap_warning.py`, `test_github_branches.py`, `test_backlog_core_server.py`, `test_backlog_add_output_messages_included`, `_item`, `sam_task_create`, `backlog.py`, `delete_integration_branch`, `create_backend`, `_item`, `Task`, `test_github_tools_labels.py`, `test_tool_output_schemas.py`, `test_a_plan_update_reports_a_dropped_connection_instead_of_raising`, `tool_responses.py`, `merge_integration_branch`, `create_integration_branch`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `BacklogError` connect `BacklogError` to `backlog_core/models.py`, `_validate_milestone_number`, `gh_client.py`, `Output`, `sam_plan.py`, `GitHubBackend`, `ContentRef`, `PullRequestRef`, `_github_exception`, `GistTaskLayer`, `SyncState`, `TestMergeIntegrationBranchValidation`, `backlog_list`, `Section`, `FileCache`, `test_github_tools_prs.py`, `MockerFixture`, `BacklogItem`, `_manifest_reference`, `ArtifactManifest`, `BeadsArtifactProvider`, `test_output_fields_always_present_on_error`, `InMemoryBackend`, `Any`, `BacklogConfig`, `test_backlog_sync_backlog_error_returns_error_key`, `test_backlog_close_backlog_error_returns_error_key`, `test_github_gist_artifact_provider.py`, `_Repository`, `test_github_tools_issues.py`, `_call`, `test_since_filter_bad_entry_id.py`, `test_backlog_groom_backlog_error_returns_error_key`, `test_backlog_normalize_backlog_error_returns_error_key`, `ContentUnavailableError`, `test_backlog_pull_backlog_error_returns_error_key`, `test_backlog_pull_selector_error_returns_error_key`, `backlog_core/operations.py`, `test_backlog_add_backlog_error_returns_error_key`, `ArtifactType`, `github_branches.py`, `BranchConflictError`, `ContentDuplicateMatch`, `test_artifact_provider.py`, `test_unknown_backend_name_refuses_as_a_backlog_error`, `classify_sync_error`, `ContentConflictError`, `call_mcp_tool`, `_call`, `TestIsNotFoundError`, `artifact_provider.py`, `test_github_branches.py`, `test_backlog_core_server.py`, `LinearArtifactProvider`, `find_item`, `test_server_sam.py`, `test_file_cache.py`, `backlog.py`, `test_backlog_groom_sections.py`, `RepoDiscoveryError`, `dh_migrate.py`, `get_repo_root`, `test_github_tools_labels.py`, `_resolve_labels_graphql`, `test_single_item_status_refusal.py`, `entry_blocks.py`, `create_integration_branch`, `TestBacklogErrorIsBase`, `sync_issues_graphql`, `test_github_tools_milestones.py`, `Task`, `_item`, `merge_integration_branch`, `_validate_slug`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `ViewItemResult` connect `ViewItemResult` to `backlog_core/models.py`, `test_section_boundary_scanner_live_3152.py`, `_filter_sections_isolated`, `gh_client.py`, `Output`, `GitHubBackend`, `Section`, `FileCache`, `test_view_sections_metadata_sync.py`, `MockerFixture`, `OrdinalPathMapper`, `BacklogItem`, `BacklogError`, `BeadsBackend`, `InMemoryBackend`, `_build_sections_metadata`, `test_disclosure_handler.py`, `BacklogConfig`, `WorkItemBackend`, `BacklogItemMetadata`, `_extract_response_dict`, `backlog_core/operations.py`, `BacklogViewDisclosureHandler`, `_paginate_body_result`, `ContentConflictError`, `_patch_github_body`, `test_backlog_core_server.py`, `.view_enrich_from_github`, `_make_view_result`, `_drift_view_result`, `test_status_source_wire.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 188 inferred relationships involving `BacklogItem` (e.g. with `WorkItemBackend` and `BeadsBackend`) actually correct?**
  _`BacklogItem` has 188 INFERRED edges - model-reasoned connections that need verification._
- **Are the 121 inferred relationships involving `Output` (e.g. with `migrate_live_run()` and `_migrate_queue_manifest_only()`) actually correct?**
  _`Output` has 121 INFERRED edges - model-reasoned connections that need verification._
- **Are the 143 inferred relationships involving `BacklogError` (e.g. with `_get_migrate_artifact_provider()` and `migrate_live_run()`) actually correct?**
  _`BacklogError` has 143 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `InMemoryBackend` (e.g. with `AddedCommentNode` and `IssueCommentNode`) actually correct?**
  _`InMemoryBackend` has 81 INFERRED edges - model-reasoned connections that need verification._