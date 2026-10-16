---
name: generate-hooks
description: Produce hook scripts from discovered anti-patterns — drafts by default, --install writes to settings
argument-hint: '[--install] [--from <analysis-file>]'
allowed-tools: Read,Write,Edit,Glob,Grep,Task
---

Generate Claude Code hook configurations from kaizen analysis findings. Translates discovered anti-patterns into automated prevention hooks.

## Arguments

- `--install` — Write hooks directly to project settings instead of draft files. Without this flag, hooks are written as proposals to `.planning/kaizen/hooks/`.
- `--from <analysis-file>` — Source analysis file to generate hooks from. Default: most recent analysis file in `.planning/kaizen/`.

## Execution Steps

1. **Find source analysis.** If `--from` is provided, use that file. Otherwise, glob for the most recent `.planning/kaizen/analysis-*.md`.

2. **Load proposal admission.** Read [Proposal Admission](../skills/kaizen-improvement/SKILL.md#proposal-admission) before selecting candidates. This is a document handoff, not a command invocation.

3. **Extract hook-eligible findings.** Read the analysis file and identify findings where the recommended improvement type is "hook". Filter candidates for:
   - Tool misuse patterns (PreToolUse deny/redirect)
   - Missing context injection (SubagentStart)
   - Quality gate violations (SubagentStop, Stop)
   - Repeated manual corrections (PreToolUse)

4. **Spawn @improvement-generator agent.** Delegate hook generation:

   ```text
   subagent_type: improvement-generator
   prompt: "Generate hook configurations from these admitted findings: {findings}. Follow the loaded Proposal Admission guidance and write proposals to .planning/kaizen/hooks/ or install qualified hooks to settings if --install flag is set."
   ```

   The agent uses the kaizen-improvement skill which contains hook patterns and templates.

5. **Output results.**

   **Draft mode (default):** Write each hook proposal as a separate file in `.planning/kaizen/hooks/`:

   ```text
   .planning/kaizen/hooks/
   ├── tool-misuse-prevention.md
   ├── edit-before-read-guard.md
   └── research-to-files-enforcement.md
   ```

   Each file contains the hook configuration, script (if command type), rationale, and testing instructions.

   **Install mode (--install):** Merge only hook candidates that meet the loaded Proposal Admission into the project's `hooks/hooks.json` or `.claude/settings.json`. The flag authorizes that write. Report what was installed.

6. **Display summary.** Show the user how many hooks were generated, what anti-patterns they address, and where the output was written.
