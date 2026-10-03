---
name: coop
title: coop
subtitle: Isolated VM environments for running Claude Code, Codex, and Grok Build
research_date: 2026-10-02
source_url: https://github.com/trailofbits/coop
github_repository: https://github.com/trailofbits/coop
version_at_research: 0.6.0
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 0.6.0
  next_review: 2027-01-02
  confidence_map: "Identity/Metadata: high | Features: high | Architecture: high | Usage Examples: high | Limitations: medium"
---

# coop

## Overview

coop is a Rust CLI that manages disposable virtual machines where Claude Code, Codex, and Grok Build have full tool access — Docker, git, compilers, package managers — all without risk to the host machine. Each VM is isolated, reproducible, and inexpensive to create and destroy. The tool orchestrates the complete VM lifecycle: setup, start, shell, stop, destroy, status, and logs.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running AI agents with full development access creates host security risk | Agents execute inside isolated VMs; only the VM is the blast radius |
| Managing VM infrastructure across platforms is complex and inconsistent | coop abstracts platform differences (Firecracker on Linux, Lima on macOS) behind a unified CLI and configuration model |
| Agents need reproducible, pre-configured environments with specific tooling | Golden images baked with Docker, GitHub CLI, Claude Code, Codex, and Grok Build; instances clone and customize from the template |
| Cross-platform agent infrastructure lacks unified tooling and config | Single CLI, same commands, same guest environment on both platforms |

---

## Key Features

### Multi-Platform Architecture

- **Firecracker on Linux**: Lightweight microVMs backed by KVM hardware virtualization (`x86_64` primary target, `arm64` available).
- **Lima on macOS**: VMs on Apple Virtualization.framework; supports Apple Silicon natively and x86_64 via Rosetta 2.
- **Single CLI, dual backends**: Backend selected at compile time via `#[cfg]` pragmas; no runtime dispatch overhead. Both backends expose identical CLI commands and produce the same guest environment.

### Agent Integration

- Pre-installed support for Claude Code, Codex, and Grok Build
- Managed `~/.claude/settings.json` injection with agent-specific configuration
- Guest runs in bypass mode (`bypassPermissions` for Claude, `--dangerously-bypass-approvals-and-sandbox` for Codex, `--always-approve` for Grok Build) to grant agents full autonomy within the VM
- Bootstrap logic injects agent config and marketplaces on first boot

### Workspace and Environment Management

- **Workspace sync**: Copies host project directories into the VM (rsync on Firecracker, live virtiofs mounts on Lima)
- **Secret forwarding**: GitHub PAT, API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`), and arbitrary `env_forward` entries cross the host→guest boundary securely via SSH env channel or stdin
- **Port forwarding**: SSH `-L` local port forwards with collision detection
- **Multi-instance**: Multiple independent VMs per configuration; automatic instance name resolution

### Configuration and Customization

- Type-safe TOML config model with newtype constructors enforcing bounds (e.g., `VmMemory` has 128-MiB minimum, `InstanceIndex` is `0..=252`)
- Secret indirection via `cmd:` retrieval commands evaluated at VM start
- devcontainer.json support: parse, merge, and apply per-project environment specs
- Per-instance JSON sidecars track runtime state (config, workspace, forwards, guest env, model routing, proxy state, devcontainer state)

### Lifecycle Automation

- **`coop up`**: Ensure instance exists and is running
- **`coop setup`**: Build golden images and prepare Firecracker/Lima infrastructure
- **`coop claude|codex|grok`**: Launch agent CLI inside the VM
- **`coop shell`**: Interactive shell access
- **`coop resize`, `coop commit`, `coop restore`**: Disk and instance management
- **`coop update`**: Self-update with SHA-256 and Sigstore attestation verification

### Credential Management

- **GitHub PAT wizard** (`coop github setup`/`rotate`/`status`/`forget`): Interactive PAT lifecycle management
- **Pluggable secret backends**: macOS Keychain, 1Password (`op`), systemd secret-tool, or file-based storage
- **Per-VM PAT assignment**: Persistent selection of which stored PAT entry to use for a specific instance
- **Credential isolation**: Secrets never travel on `argv`; SSH `SendEnv`, process env, or stdin only

---

## Technical Architecture

### Core Design

coop's core architecture consists of:

1. **Central CLI dispatcher** (`lib.rs`): Parses arguments, loads config, initializes tracing (stderr), handles commands that don't require a loaded config first (completions, init, update, uninstall), then dispatches to command handlers in `commands/`.

2. **VmBackend trait** (`backend.rs`): Unified abstraction for VM operations (setup, create_and_start, start_existing, stop, destroy_instance, resize_disk, commit_disk, status, stream_logs, ssh_target). Two implementations:
   - `FirecrackerBackend` on Linux — delegates to `vm.rs`, `setup.rs`, `network.rs`
   - `LimaBackend` on macOS — delegates to `lima.rs`

3. **Type-state machines**: Compile-time enforcement of valid state transitions:
   - `RunningInstance` / `StoppedInstance` (`backend.rs`) — point-in-time observations with private fields, minted by `as_running` / `as_stopped`
   - `FirecrackerVm<Configured>` / `FirecrackerVm<Running>` (`vm.rs`) — gate lifecycle transitions at compile time

4. **Backend-shared operations**: Configuration, secrets, workspace, SSH, agent bootstrap, devcontainer handling — all implementations live above the trait and must hold for both backends.

5. **Per-instance state**: JSON sidecars in instance directory track `instance.json`, `vm_config.json`, `workspace.json`, `forwards.json`, `guest_env.json`, `model.json`, `proxy.json`, `devcontainer_state.json`, plus Firecracker `.pid`/`.socket`/`.log` files.

### Data Flow: Host → Guest

1. **Resolve** target repo/workspace; optionally prompt for GitHub PAT
2. **Ports** — merge forward-port specs, fail fast on collisions
3. **Boot** the VM (`create_and_start`), wait for SSH readiness
4. **Forwards + state** — spawn `ssh -L` forwards, persist JSON sidecars
5. **Bootstrap** — if `GITHUB_TOKEN` present, run `gh auth setup-git`; then `bootstrap_claude` / `bootstrap_codex` inject config and marketplaces
6. **Workspace** — copy via tar-pipe (Firecracker) or live mount (Lima); persist `WorkspaceState`
7. **postStartCommand** hook (warned, not fatal)

### Firecracker (Linux)

- **Setup**: Downloads Firecracker binary, guest kernel, builds template rootfs by chroot-installing packages into an ext4 image
- **Instance creation**: Copy template rootfs with CoW when possible, patch network config with instance IP, mount, create Firecracker JSON config, attach TAP device to bridge, start process with `sudo`
- **Networking**: Dedicated TAP device per instance (`tap0`, `tap1`, …) attached to Linux bridge (`br0`); iptables NAT masquerade routes guest traffic through host's default interface; SSH reaches guest via `guest_ip:ssh_port`
- **Typestate**: `FirecrackerVm<Configured>` before boot, `FirecrackerVm<Running>` after; `start()`/`stop()` transitions enforced at compile time
- **Lifecycle management**: Instance operation lock held from stopped-state probe through disk mutations; file is sibling of instance directory so removal doesn't orphan the lock

### Lima (macOS)

- **Setup**: Creates temporary builder VM from Ubuntu 24.04 cloud image, provisions packages via cloud-init, extracts disk as golden image, deletes builder
- **Instance creation**: `limactl start` with fast-start template referencing golden image; Lima allocates SSH port automatically
- **Networking**: Host reaches guest via assigned SSH port; no manual port configuration needed
- **Mounts**: virtiofs live mounts; host/guest path changes visible immediately on both sides
- **Resource ownership**: No `sudo` required; Lima runs as current user

### Typestate Invariants

- **`boot_preflight(cfg)`** is the single choke point every boot path calls; runs `cfg.validate()` so no VM starts on invalid config
- **Instance operation lock** held from stopped-state probe through resize, commit, or restore; same lock acquired by start/stop/destroy; file sibling of instance directory survives directory removal
- **Allocation** refuses occupied instance paths; if any directory has unreadable metadata, allocation stops (network index cannot be trusted)

### Update Verification Chain

`coop update` fetches release metadata, downloads tarball + `SHA256SUMS` + `attestations.jsonl`, verifies checksum (mandatory), verifies Sigstore attestation via `gh` against bundle or falls back to GitHub API (best-effort), extracts with path-escape-safe `tar` flags, atomically renames new binaries in place.

---

## Installation & Usage

### Install

Latest release:

```bash
curl -fsSL https://raw.githubusercontent.com/trailofbits/coop/main/install.sh | bash
```

The installer verifies SHA-256 against `SHA256SUMS` and optionally verifies Sigstore attestation with `gh` (if installed).

Build from source (requires Rust and CMake):

```bash
cargo build --workspace --release
cp target/release/coop target/release/coop-proxy /usr/local/bin/
```

Nix:

```bash
nix build
./result/bin/coop --version
```

### Prerequisites

**macOS (Lima backend)**

- Lima installed (`brew install lima`)
- Apple Silicon (arm64) or Intel x86_64 (via Rosetta 2)

**Linux (Firecracker backend)**

- KVM access: `/dev/kvm` must exist and be writable by your user
- x86_64 or arm64 architecture
- `sudo` privileges for Firecracker and TAP networking
- `curl`, `tar`, `e2fsprogs`, `setfacl`, `unsquashfs`, `ssh`, `rsync`

### Setup

Build VM template images and infrastructure:

```bash
coop setup
```

On macOS, this creates Lima golden image. On Linux, downloads Firecracker binary, guest kernel, builds template rootfs.

Keep coop updated:

```bash
coop update
```

### Usage

Start an instance and launch an agent:

```bash
cd ~/code/my-project
coop up              # Ensure instance exists and is running
coop claude          # Launch Claude Code agent
# or
coop codex           # Codex agent
# or
coop grok            # Grok Build agent
```

Interactive shell:

```bash
coop shell
coop shell my-project -- cat /etc/os-release   # non-interactive command, no PTY; returns its exit code
```

Claude Code passthrough (docs/commands.md, `claude`): `coop claude [NAME] [FLAGS] [ARGS...]`, where `ARGS...` are "Extra arguments passed through to `claude`" and `--ask` prompts for permissions instead of the guest default `bypassPermissions`:

```bash
coop claude my-project --ask
coop claude my-project -- --model sonnet
```

Manage instances:

```bash
coop list                    # List all instances
coop status [INSTANCE]       # Show instance status
coop logs [INSTANCE]         # Stream instance logs
coop stop [INSTANCE]         # Stop a running instance
coop destroy [INSTANCE]      # Destroy an instance
coop destroy --all           # Destroy all instances
```

Resize and customize:

```bash
coop resize [INSTANCE] --memory 8G --cpus 4 --disk 100G
coop commit [INSTANCE]       # Commit instance changes to image template
coop restore [INSTANCE]      # Restore instance to image template state
```

GitHub PAT management:

```bash
coop github setup            # Interactive PAT wizard
coop github status           # Show saved PATs
coop github rotate KEY       # Rotate a saved PAT
coop github forget KEY       # Delete a saved PAT entry
```

Workspace and file sync:

```bash
coop up --mount /host/path   # Mount host directory in guest (live on Lima, one-time copy on Firecracker)
coop push [INSTANCE]         # Sync local workspace to guest (rsync)
coop pull [INSTANCE]         # Sync guest workspace to local (rsync)
```

---

## Relevance to Claude Code Development

### Integration Opportunities

- **Isolated agent execution** → `rules/commit-cadence-and-worktrees.md`
  - Term: `worktree-isolated`
  - Today: "invisible to worktree-isolated agents (see below)."
  - Change: this rule file treats worktrees as the agent isolation unit; coop's documented VM boundary (docs/getting-started.md: "Each VM gets its own filesystem, network stack, and Docker daemon") is a different isolation tier that this file does not mention. Adding a note there would only be warranted if an orchestrator is written to launch agents through `coop claude`; no such launcher exists in the paths searched

- **Bypass-mode agent launch** → `plugins/development-harness/skills/kage-bunshin/SKILL.md`
  - Term: `dangerously-skip-permissions`
  - Today: "Use when all sessions were spawned with `--dangerously-skip-permissions` (bypass mode). In bypass mode, no permission prompts can occur, so passive notification on completion or timeout is sufficient. Zero LLM tokens."
  - Change: hypothesis to verify, not a finding: `plugins/development-harness/skills/kage-bunshin/scripts/spawn.py` launches `claude --dangerously-skip-permissions --worktree` on the host (line 604), and coop documents that its guest runs Claude Code in `bypassPermissions` mode with "the VM itself" as "the isolation boundary" (docs/commands.md, `claude`). Verification step: confirm whether tmux send-keys/capture-pane control works against `coop claude`, and how `--worktree`, `--tmux` and `--max-budget-usd` behave there; docs/commands.md documents only `ARGS...` "passed through to `claude`" (e.g. `coop claude my-project -- --model sonnet`), and does not mention those other flags

---

## Limitations and Caveats

- **Platform support**: Primary test targets are macOS arm64 and Linux x86_64; Linux arm64 builds are available but untested
- **Lima requirement on macOS**: Must be pre-installed before `coop setup` — fails without it
- **Firecracker requires sudo**: KVM and TAP networking require elevated privileges
- **One-time workspace sync on Firecracker**: Unlike Lima's live virtiofs mounts, Firecracker syncs are one-time (rsync or tar-pipe); use `coop push`/`coop pull` to re-sync
- **Docker inside agent VMs**: docs/getting-started.md:3 states "Each VM gets its own filesystem, network stack, and Docker daemon." Behaviour when Docker fails inside the VM: Not mentioned in documentation
- **Nested virtualization**: Not mentioned in documentation (the only `nested` match in docs/ and README.md is "nested skill references" in docs/claude-integration.md:115, about skill directory copying)
- **Nix builds identify as development**: Nix-installed coop reports as a development build and disables `coop update` and background release notifications; upgrade via `nix profile upgrade coop` instead

---

## References

- [coop GitHub Repository](https://github.com/trailofbits/coop) (accessed 2026-10-02)
- [README.md — Installation, setup, and basic usage](https://github.com/trailofbits/coop/blob/main/README.md) (accessed 2026-10-02)
- [docs/ARCHITECTURE.md — Module map, two-backend design, data flow, invariants](https://github.com/trailofbits/coop/blob/main/docs/ARCHITECTURE.md) (accessed 2026-10-02)
- [docs/getting-started.md — Prerequisites and installation details](https://github.com/trailofbits/coop/blob/main/docs/getting-started.md) (accessed 2026-10-02)
- [docs/backends.md — Firecracker and Lima backend specifics](https://github.com/trailofbits/coop/blob/main/docs/backends.md) (accessed 2026-10-02)
- [docs/commands.md — `claude` and `shell` flags, ARGS passthrough](https://github.com/trailofbits/coop/blob/main/docs/commands.md) (accessed 2026-10-03)
- [docs/trust-model.md — Security boundaries, taint sources, invariants](https://github.com/trailofbits/coop/blob/main/docs/trust-model.md) (accessed 2026-10-02)
- [Cargo.toml — Version 0.6.0, Apache-2.0 license, Rust dependencies](https://github.com/trailofbits/coop/blob/main/Cargo.toml) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [HolyClaude](./holyclaude.md) | agent-infrastructure | Competing approach: pre-built Docker container with Claude Code and agents; coop provides lightweight VMs with credential forwarding and multi-agent support |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | coop extends Claude Code's execution model by providing isolated VMs; harness abstracts how agents interface with Claude Code |
| [Oh-My-ClaudeCode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | coop provides low-level VM management for multi-agent orchestration; orchestration layer would coordinate launching agents into coop instances |
