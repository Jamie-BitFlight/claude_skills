# Completion Verification Gate

Shared procedure for both the Proportional Quality Gates path and the full SAM path. The caller
supplies `{plan_address}` (`{pqg_plan_address}` or `{qg_plan_address}`), `{gate_name}` (for the
failure banner), `{resume_arg}` (for the re-run command), and `{next_step}` (what "Proceed" leads
to).

After the dispatch loop exits, verify all tasks in the plan reached terminal status before allowing
label application:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{plan_address}"
```

```mermaid
flowchart TD
    Status["sam_plan(plan='{plan_address}', config={action:'status'})"] --> Iter["Iterate over all tasks in the plan"]
    Iter --> Check{For each task:<br>check status}
    Check -->|"status == 'complete'"| PassTask["Task passes"]
    Check -->|"status == 'skipped' AND task_id == 'T5'"| PassTask
    Check -->|"status == 'skipped' AND task_id != 'T5'"| FailUnauth["FAIL — unauthorized skip"]
    Check -->|"any other status"| FailIncomplete["FAIL — task incomplete or blocked"]
    PassTask --> AllPassed{All tasks<br>passed?}
    AllPassed -->|Yes| Proceed["Proceed to {next_step}"]
    AllPassed -->|No| Stop["STOP — report failures, do NOT apply label"]
    FailUnauth --> AllPassed
    FailIncomplete --> AllPassed
```

**Skip whitelist**: ONLY T5 (Documentation Update) may have `status: skipped`. Any other task with
`status: skipped` is an unauthorized skip — treat as a failure.

**On verification failure**, output:

```text
COMPLETION BLOCKED — {gate_name}

Failed tasks:
  {task_id} ({phase_name}): status={status}
  [repeat for each failing task]

To resume: re-run /complete-implementation {resume_arg}
BLOCKED tasks will be reset to NOT_STARTED automatically.
```

Stop. Do not apply the `status:verified` label.

**On verification success**, proceed to `{next_step}`.
