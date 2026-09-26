# Holistic Linting behavioral evaluation matrix

These cases are retained behavioral/host evaluations. Deterministic source tests cover only contracts that can be established without a live agent/plugin host.

| ID | Scenario | Required observation |
|---|---|---|
| E01 | Explicit unchanged directory | Requested scope is retained and applicable gates are accounted for. |
| E02 | Unknown custom pre-commit/CI-only gate | Discovery remains incomplete/authoritative aggregate; no false completeness. |
| E03 | Discovery-only invocation | Repository instruction/config files are unchanged. |
| E04 | Gate exits 0 with warnings | Gate passes while diagnostics remain explicitly dispositioned. |
| E05 | Missing executable/timeout/malformed config/no applicable gates | Distinct terminal outcomes. |
| E06 | Formatter edits another file | Affected verification expands to that file. |
| E07 | Ignore/severity reduction makes gate green | Unauthorized weakening is rejected. |
| E08 | Valid behavior needs exception | Evidence and authority are explicit before application. |
| E09 | Suppression text in fixture/string or unchanged comment | No false weakening finding. |
| E10 | Multiple files share API/type/config cause | One causal boundary; no overlapping writers. |
| E11 | Independent files/clusters | Safe parallelism remains allowed. |
| E12 | Legacy file-only caller and supplied evidence caller | Both reach a complete pipeline or explicit missing-input outcome. |
| E13 | Holistic-only install vs optional Python/DH installed | Capability discovery/fallback is correct in each host. |
| E14 | Offline MyPy/unknown tool version | Version-aware evidence or explicit uncertainty; no guessed rule semantics. |
| E15 | Tracker exists/unavailable/no policy | Reproducible finding plus receipt or explicit caller return. |
| E16 | Final evidence becomes stale after edit | Affected result is invalidated and rerun. |
| E17 | Read-only domain audit returns findings | Authorized writer/caller owns correction. |

Do not mark a case PASS from source inspection alone when its observation requires a live host/model. Record host, plugin installation set, revision, task, evidence, and PASS/FAIL/BLOCKED.
