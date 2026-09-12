# Utilization Proposals: RTK (Rust Token Killer)

**Research entry**: ./research/developer-tools/rtk.md
**Generated**: 2026-09-12
**Integration surfaces found**: 3 (CLI tool | Package manager installation | PreToolUse hook)
**Proposals written**: 2
**Skipped**: 2 — (already covered by built-in tools, CLI-only with no persistent state)

---

## Utilization 1: Claude Code Session Hook → RTK Auto-Installation

**Research entry**: ./research/developer-tools/rtk.md
**Caller**: `.claude/hooks/session-start.js` (to be created) plus a new `SessionStart` entry in `.claude/settings.json` — creating the file alone does not register it; `.claude/settings.json` currently registers exactly three `SessionStart` commands (`context-loader.mjs --reset`, `session-init.sh`, `bd prime --hook-json`), none of which reference this file
**Integration mechanism**: PreToolUse hook via `rtk init -g`
**Replaces or adds**: Adds transparent command filtering for all Bash tool calls in Claude Code sessions
**Setup cost**: Low (single binary install + hook registration, no state management)
**Integration surface**: `rtk init -g` (default Claude Code hook installation command)

### Why this caller

Claude Code agents in this repository run intensive workflows involving Git operations (status, log, diff, commit, push, pull), testing (pytest, cargo test), and build commands (ruff, tsc, cargo build). These commands produce verbose output that consumes tokens without proportional information value (progress bars, boilerplate formatting, repetitive logging). A session-start hook can install RTK once per session and register its PreToolUse hook with Claude Code, transparently filtering all subsequent Bash command output.

The `.claude/hooks/session-start.js` hook file does not currently exist (discovered at path `/home/user/claude_skills/.claude/hooks/`), so this represents new capability addition. RTK's "Auto-Rewrite (default)" mode applies 100% of invocations without context overhead, making this a transparent token-saving mechanism for agents running multi-step workflows.

### Integration sketch

```javascript
// .claude/hooks/session-start.js
// Run on every Claude Code session start to install RTK and register hook

const { spawnSync } = require('child_process');
const path = require('path');

function installRTK() {
  // Check if rtk is already installed
  const checkResult = spawnSync('which', ['rtk'], { stdio: 'pipe' });

  if (checkResult.status !== 0) {
    // Install via homebrew (macOS/Linux) or cargo (fallback), each bounded so a stalled
    // registry/network call cannot block SessionStart indefinitely (see AGENTS.md's
    // scripts/run_bounded.py convention for external command invocations).
    console.log('Installing RTK...');

    const installResult = spawnSync(
      'uv',
      ['run', '--script', 'scripts/run_bounded.py', '--timeout-seconds', '60', '--', 'brew', 'install', 'rtk'],
      { stdio: 'inherit', shell: true }
    );

    if (installResult.status !== 0) {
      // Fallback to cargo, same bound
      spawnSync(
        'uv',
        ['run', '--script', 'scripts/run_bounded.py', '--timeout-seconds', '120', '--', 'cargo', 'install', '--git', 'https://github.com/rtk-ai/rtk'],
        { stdio: 'inherit' }
      );
    }
  }

  // Register Claude Code hook (default: rtk init -g)
  const hookResult = spawnSync('rtk', ['init', '-g'], {
    stdio: 'inherit'
  });

  if (hookResult.status === 0) {
    console.log('RTK installed and hook registered for Claude Code');
  }
}

installRTK();
```

**Note**: The exact hook API for Claude Code PreToolUse registration is documented in the RTK README (line 415-437). The session-start hook would invoke `rtk init -g` once per session to register the hook. Per the research entry (README.md lines 124-140), RTK requires restarting the AI tool after `rtk init -g` before the hook takes effect — so filtering begins with the *next* session after installation, not the current one. A session-start hook that only just ran the install cannot rewrite Bash calls made later in that same session.

---

## Utilization 2: Development Harness Execution Agents → RTK Command Filtering

**Research entry**: ./research/developer-tools/rtk.md
**Caller**: Development Harness agents (e.g., `@dh:execution`, `@dh:task-worker`) spawned by `/dh:dispatch` and `/dh:work-milestone`
**Integration mechanism**: Implicit via session-start hook (or explicit per-task opt-in via RTK configuration)
**Replaces or adds**: Adds transparent token reduction for git, test, and build command output captured by agents
**Setup cost**: Low (zero additional setup if session-start hook installed; medium if per-task configuration required)
**Integration surface**: PreToolUse hook (via session-start) + optional RTK configuration in `~/.config/rtk/config.toml`

### Why this caller

The development-harness plugin orchestrates multi-step workflows through its SAM 7-stage pipeline and dispatch system. Stages like S5 (Execution) and S6 (Forensic Review) spawn agents (`@dh:task-worker`, `@dh:code-reviewer`, `@dh:execution`) that run Bash commands to:
- Execute Git operations for branch management and changelog generation
- Run test suites (pytest, cargo test, jest) to validate implementations
- Run build/lint commands (ruff, tsc, cargo build, golangci-lint) to verify code quality

Each of these command types is explicitly supported by RTK (research entry lines 36-49: Git, test runners, build & linting). The development-harness agents currently receive full, unfiltered output, consuming context that could be preserved by RTK's intelligent filtering. The "Execution" agent in particular operates in long-running workflows where context accumulation over multiple tasks becomes expensive.

Referencing `./plugins/development-harness/AGENTS.md`: the harness "owns the process" and orchestrates specialists. RTK integration becomes a cross-cutting optimization that reduces output verbosity for all spawned agents without modifying their instruction sets.

### Integration sketch

**Scenario 1: Via session-start hook (minimal setup, next session onward)**

Once RTK is installed and the AI tool has been restarted after `rtk init -g` (see Utilization 1), the PreToolUse hook rewrites the agent's own Bash tool calls — not subprocess calls an agent's Python code makes internally. A Claude Code Bash tool invocation of `git status` is what gets rewritten; a `subprocess.run(["git", "status"])` executed from inside an already-running Python process is not intercepted, since PreToolUse only sees the outer tool call that started that process, not what it does afterward. An agent that wants RTK's filtering on a command it runs via Python must invoke `rtk git status` explicitly rather than the bare command.

**Scenario 2: Explicit RTK configuration (per-milestone control) — requires new implementation work**

RTK's actual configuration file is `~/.config/rtk/config.toml` (README.md lines 442-459), not `.dh/config.yaml`:

```toml
[hooks]
exclude_commands = ["curl", "playwright"]  # skip rewrite for these

[retriever]
mode = "sqlite"  # sqlite (default) | tee (legacy) | disabled
```

Nothing in this repo currently reads `.dh/config.yaml` or dispatch plan metadata to configure RTK — a repository-wide search finds no such integration. Per-milestone control would require new harness code to translate dispatch/milestone settings into this TOML file (or invoke `rtk` with equivalent flags) before spawning agents; this is unbuilt, not an existing capability.

When a command fails, RTK saves the unfiltered output for later recovery via `rtk recall {token-id}` (README.md line 193).

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| Claude Code built-in tools (Read, Grep, Glob) | RTK filters only Bash tool calls; built-in tools do not pass through hook and are not auto-rewritten. Alternative: use shell equivalents (`cat`, `rg`/`grep`, `find`) if RTK filtering is required. |
| Pre-commit hooks | Already covered by built-in `prek` (Rust-based pre-commit replacement) with its own output suppression flags (`-q` for quiet mode). RTK would be redundant for pre-commit hooks, which intentionally run in isolation before commit and have different output expectations (validation errors must be visible). |

---

## Implementation Considerations

**Cost estimation**:
- Session-start hook: 10–15 minutes to implement and test
- Development-harness integration: 20–30 minutes for configuration documentation + optional per-task RTK enablement
- Total: Low to medium cost, high payoff for agents running intensive Git/test/build workflows

**Risk assessment**:
- **Low**: RTK's "Fail-Safe" design (line 117–118) preserves original output if filtering fails, so no agent breakage on error
- **Medium**: Hook registration could conflict with other harnesses (Codex, Cursor, Gemini) — RTK documents per-harness `init` flags (lines 169–175) to handle this
- Mitigation: Session-start hook should detect harness type (Claude Code is default) and only register Claude Code hook

**Verification**:
- Token savings measurement: RTK provides `rtk gain` dashboard (research entry lines 81–88) for per-session token savings analytics
- Integration confirmation: Test that `rtk git status`, `rtk pytest`, and `rtk cargo test` run correctly within session
- Agent behavior: Confirm that development-harness agents receive filtered output in their Bash capture without changes to agent prompts
