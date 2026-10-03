# Utilization Proposals: coop

**Research entry**: ./research/agent-infrastructure/coop.md
**Generated**: 2026-10-03
**Integration surfaces found**: 1 (CLI)
**Proposals written**: 1
**Skipped**: 3 — parallel-work (no spawn mechanism of its own), delegate harness-notes (Agent-tool sub-agents cannot run in a VM), development-harness live e2e scripts (no agent execution)

---

## Utilization 1: kage-bunshin spawn.py → coop CLI

**Research entry**: ./research/agent-infrastructure/coop.md
**Caller**: ./plugins/development-harness/skills/kage-bunshin/scripts/spawn.py (documented in ./plugins/development-harness/skills/kage-bunshin/SKILL.md)
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds an opt-in VM isolation tier. Today `_build_spawn_shell_cmd` (spawn.py lines 565-607) launches `claude --dangerously-skip-permissions --worktree {name} --tmux` directly on the host; the only containment is a git worktree. coop would run the bypass-mode agent inside a disposable VM, so the VM is the blast radius.
**Setup cost**: High (infra change required) — coop install, `coop setup` golden-image build, and on Linux KVM plus sudo. `/dev/kvm` does not exist in this session's container, so the Firecracker backend cannot be exercised here.
**Integration surface**: `coop up`, `coop claude`, `coop status [INSTANCE]`, `coop logs [INSTANCE]`, `coop stop [INSTANCE]`, `coop destroy [INSTANCE]`, `coop push|pull [INSTANCE]` (all from the "Installation & Usage" section of the research entry)

### Why this caller

spawn.py's module docstring and `_build_spawn_shell_cmd` show every kage-bunshin child is started with `--dangerously-skip-permissions`, and SKILL.md (lines 328 and 360) makes bypass mode the default basis for choosing the notification mechanism. The child is launched with the permission prompts skipped, and the only isolation mechanism the skill documents is `--worktree`, which SKILL.md line 93 describes as creating "a git worktree at `.claude/worktrees/{name}`". SKILL.md does not state whether that restricts network, credentials, or files outside the repo; that is Not mentioned in documentation, and no observation of it was made in this session. The research entry's "Problem Addressed" table describes exactly this risk and documents coop's remedy: the guest runs in bypass mode (`bypassPermissions` for Claude) inside a Firecracker/Lima VM, with secrets forwarded via SSH env or stdin and workspace copied in via rsync or virtiofs. Hypothesis: running the agent inside a coop VM would add a host-isolation boundary that a worktree alone is not documented to provide. Verification step: on a KVM-capable host, run `coop claude` against a scratch repo and check whether the guest can reach host files, credentials, and network resources outside the forwarded workspace, then compare with a `spawn.py` session on the host. Search performed to confirm no existing equivalent: `grep -rliE "microvm|firecracker|lima|sandbox|bypassPermissions|dangerously" plugins .claude` returned no VM-isolation mechanism in plugins/development-harness/skills (only kage-bunshin's own bypass flag), and `grep -rniE coop` over plugins, .claude, and rules returned no coop references.

### Integration sketch

Constraints from coop's docs/commands.md (read in the upstream clone at 0.6.0): `coop claude [NAME] [FLAGS] [ARGS...]` passes `ARGS...` through to `claude` (example at line 314: `coop claude my-project -- --model sonnet`), and `coop shell -- COMMAND...` runs a command non-interactively with no PTY (line 287). The research entry does not mention passthrough of `--worktree`, `--tmux`, `--model` or `--max-budget-usd`; in docs/commands.md and docs/claude-integration.md only `--model` appears (by example), and a search for `worktree`, `tmux` and `max-budget` in those two files returned no matches. A documented non-interactive prompt channel for `coop claude` is Not mentioned in documentation; `coop shell -- COMMAND...` is the documented non-interactive path. Open question, narrowed: whether kage-bunshin's tmux send-keys/capture-pane control loop works against `coop claude` (it needs a PTY, and `coop shell -- COMMAND...` allocates none) and whether `--worktree`/`--tmux` are meaningful inside the guest. Verify by running `coop claude` under tmux on a KVM-capable host. Also, child hooks that write notifications to the host (`KAGE_BUNSHIN_PARENT_SESSION_ID`) would run in the guest, so notification delivery would need a pull step (`coop pull`) or the polling option.

Candidate shape, using only commands documented in the entry:

```bash
# new spawn.py flag: --isolation vm (default: worktree)
cd <repo>
coop up                      # ensure instance exists and is running
tmux new-session -d -s kb-launcher-{name} coop claude   # coop claude runs the agent in the VM
# send prompts as today via tmux send-keys to the launcher session
coop pull                    # sync guest workspace back to host (rsync) on completion
coop destroy {INSTANCE}      # replaces `stop`/`kill` cleanup for VM-isolated sessions
```

Status: concept only. Defer implementation until the narrowed open question above (tmux control of `coop claude`; `--worktree`/`--tmux`/`--max-budget-usd` behaviour) is answered by running it.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| ./plugins/agent-orchestration/skills/parallel-work/SKILL.md | Describes fan-out shapes and isolation guidance (line 14) but spawns nothing itself; the only concrete mechanism is the harness-notes worktree convention. Search: `grep -nE "sandbox\|dangerously\|bypass\|worktree\|isolat"` returned only prose references to worktrees. |
| ./plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md | Isolation section (line 13) covers `isolation: worktree` on the Agent tool; Agent-tool sub-agents run inside the parent harness process and cannot be redirected into a coop VM. Incompatible with the documented coop surface. |
| ./plugins/development-harness/docs/live-e2e-validation.md and live-test scripts | Their sandbox is an isolated GitHub repo, not an agent execution environment; the research entry's "sandbox" integration opportunity conflates the two. No overlap with coop's CLI. |
