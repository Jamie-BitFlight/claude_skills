---
name: coop
title: coop
subtitle: Isolated VM environments for running Claude Code and Codex
research_date: 2026-10-06
source_url: https://github.com/trailofbits/coop
github_repository: https://github.com/trailofbits/coop
version_at_research: 0.6.0
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-10-06
  version_at_verification: 0.6.0
  next_review: 2027-01-06
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: medium (doc + code-read) | Installation & Usage: high | Limitations and Caveats: medium"
---

# coop

Source snapshot: every claim in this entry was read from the `trailofbits/coop` git tag `v0.6.0` (commit `63e4ff36c18133518445dd1b706c0391c0a0376a`, commit date 2026-09-09; shallow clone read 2026-10-06). `Cargo.toml` at that tag declares version `0.6.0`. Later versions on the default branch were not read.

## Overview

coop is a Rust CLI that manages disposable virtual machines where Claude Code and Codex have full tool access — Docker, git, compilers, package managers — all without risk to the host machine (README.md). Each VM is isolated and is created from a reusable golden image. The tool orchestrates the complete VM lifecycle: setup, start, shell, stop, destroy, status, and logs (docs/ARCHITECTURE.md).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running AI agents with full development access creates host security risk | Agents execute inside isolated VMs; docs/ARCHITECTURE.md invariant 1: "The VM is the isolation boundary" |
| Managing VM infrastructure across platforms is complex and inconsistent | docs/backends.md: "Both backends expose the same CLI commands and produce the same guest environment" — Firecracker microVMs on Linux, Lima on macOS |
| Agents need reproducible, pre-configured environments with specific tooling | Golden images are built once by `coop setup` and copied per instance; profiles, extra packages, and post-install scripts customize the image (docs/images-and-profiles.md) |

---

## Key Features

### Multi-Platform Architecture

- **Firecracker on Linux**: microVMs on KVM; the CLI's backend for non-macOS builds is `FirecrackerBackend`, which delegates to `setup`, `vm::FirecrackerVm`, and `network` (docs/ARCHITECTURE.md). x86_64 is the primary test target; arm64 builds are available but untested (docs/getting-started.md).
- **Lima on macOS**: VMs on Apple Virtualization.framework through `limactl`; the generated Lima template sets `vmType: "vz"` and enables Rosetta for x86_64 binary translation on Apple Silicon (docs/backends.md).
- **Single CLI, dual backends**: backend chosen at compile time by the `PlatformBackend` type alias resolved with `#[cfg]`, with no runtime override (docs/backends.md: "The binary determines the backend; there is no runtime override") (code-read). Source: src/backend.rs — `pub type PlatformBackend`

### Agent Integration

- **Pre-installed agents**: `coop setup` builds a golden image whose provision script installs Docker, GitHub CLI, Claude Code, Codex, and any profile packages (docs/backends.md); instances are created from that image.
- **Managed `~/.claude/settings.json`**: written inside the guest during VM startup by `bootstrap_claude`, which injects an allowlisted set of host config entries (`CLAUDE.md`, `rules/`, `commands/` from `config_dir`) plus the managed `settings.json` (docs/ARCHITECTURE.md data-flow step 5; docs/claude-integration.md). Source: src/backend.rs — `fn bootstrap_claude`, `pub fn bootstrap_agents`
- **Bypass mode in the guest**: the managed `settings.json` sets `defaultMode: bypassPermissions` and `skipDangerousModePermissionPrompt: true` for Claude Code; `coop codex` passes `--dangerously-bypass-approvals-and-sandbox` by default; `--ask` on either command restores prompts for that session (docs/commands.md).
- **Marketplace and plugin install on first boot**: `bootstrap_claude` / `bootstrap_codex` install the delta of marketplaces, plugins, and MCP servers not already baked into the golden image (docs/ARCHITECTURE.md). The `[claude]` config section carries `marketplaces`, `plugins`, and `[claude.mcp_servers.<name>]` entries (docs/claude-integration.md).
- **Codex ChatGPT account auth**: `[codex] auth = "chatgpt"` launches Codex through a guest keyring wrapper (docs/commands.md `codex`; CHANGELOG.md v0.6.0).

### Workspace and Environment Management

- **Workspace sync**: `coop up` in copy mode (the default) tar-pipes the project into `/workspace` over SSH, with both sides hashing the tar stream with SHA-256 and aborting on divergence (docs/workspaces.md). `coop up --mount` is live virtiofs on Lima and a one-time rsync on Firecracker (docs/backends.md; docs/workspaces.md). `coop push` / `coop pull` use rsync when the guest has it and tar-pipe otherwise (docs/workspaces.md). See Limitations for how the sources word this.
- **Secret forwarding**: `ANTHROPIC_API_KEY` (and `OPENAI_API_KEY` for Codex) are forwarded when set, and `env_forward` lists additional variable names; forwarding rides SSH `SendEnv`, never argv (docs/configuration.md; docs/trust-model.md). For `GITHUB_TOKEN`, docs/configuration.md states it is "forwarded automatically when set", while docs/claude-integration.md and docs/trust-model.md state forwarding is off unless `github = auto|env|pat` is set (default `off`).
- **Port forwarding**: `--forward-port GUEST[:HOST]` spawns `ssh -L` tunnels; a host-port collision fails before the VM is created, and the error names the port and suggests a `GUEST:HOST` override (docs/configuration.md; docs/ARCHITECTURE.md step 2). Source: src/port_forward.rs — `pub fn check_host_port_collisions`
- **Multi-instance**: instance name resolution is three rules — zero instances fails, one instance makes the name optional, several make it required (docs/commands.md).

### Configuration and Customization

- **Type-safe config model**: `config::CoopConfig` is the type-safe core; value bounds are enforced by newtype constructors — `VmMemory` has a 128-MiB floor, `InstanceIndex` is `0..=252`, `SubnetMask` is `0..=32` — so `validate()` checks only environmental facts such as paths and binaries (docs/ARCHITECTURE.md "Config model"). Source: src/config.rs — `pub struct VmMemory`, `pub struct InstanceIndex` (`MAX: u16 = 252`, doc comment: the bound exists because the guest IP is `172.16.0.<idx + 2>`)
- **Secret indirection**: a config value of the form `cmd:<command>` is run on the host and resolved at VM start by `resolve_cmd_value` (docs/ARCHITECTURE.md; docs/trust-model.md notes these `cmd:` values run `sh -c` on the host).
- **Per-instance JSON sidecars**: `instance.json`, `vm_config.json`, `workspace.json`, `forwards.json`, `guest_env.json`, `model.json`, `proxy.json`, `devcontainer_state.json`, plus the Firecracker `.pid`/`.socket`/`.log`/vsock files, written atomically (docs/ARCHITECTURE.md).
- **Profiles**: built-in profiles `python`, `node`, `c`, `fuzz`, `rust`, `go` layer apt packages and scripts onto the template; custom profiles are declared under `[profiles.<name>]` with `apt_packages`, `pre_install`, `post_install`, `marketplaces`, `plugins` (docs/images-and-profiles.md).
- **devcontainer.json translation**: `postStartCommand`, `containerEnv`, `forwardPorts`, `hostRequirements`, `mounts`, and `features` are mapped to coop equivalents; public `ghcr.io/devcontainers/features/*` entries are fetched from GHCR and baked into the image at setup (docs/devcontainer.md).

### Lifecycle Automation

- **`coop up [DIR]`**: canonicalizes `DIR` as the project identity; reports success when a matching instance is running, restarts it when stopped, creates one when none exists (docs/commands.md).
- **`coop setup`**: builds the golden image and the backend runtime — on Linux downloads Firecracker and a kernel and builds a rootfs in a chroot; on macOS builds a Lima disk through a temporary builder VM (docs/backends.md).
- **`coop claude` / `coop codex`**: launches the agent CLI inside the VM over SSH; trailing `ARGS...` are passed through to the agent (docs/commands.md; docs/claude-integration.md).
- **`coop shell`**: opens an interactive shell at `/workspace`, or with `-- COMMAND...` runs one command non-interactively with no PTY and returns its exit code (docs/commands.md).
- **`coop resize`, `coop commit`, `coop restore`**: `resize` changes a stopped instance's disk size, memory, or vCPU count and writes memory and vCPU changes to the backend config (Firecracker per-instance JSON or Lima `lima.yaml`); `commit --image <name>` saves a stopped instance's filesystem as a reusable image listed by `coop images`; `restore --image <name>` replaces the disk of the same instance with an image (docs/commands.md).
- **`coop update`**: self-update with a mandatory SHA-256 check against `SHA256SUMS` and a best-effort Sigstore attestation check through `gh` (docs/ARCHITECTURE.md; docs/commands.md).

### Credential Management

- **GitHub PAT wizard** (`coop github setup-pat` / `rotate-pat` / `status` / `forget-pat`): opens the PAT-creation form, validates the token against `api.github.com`, stores it in a chosen secret manager, and writes a `[github.pat."owner/repo"]` entry holding a `cmd:` retrieval command (docs/commands.md; docs/configuration.md).
- **Pluggable secret storage**: macOS Keychain, Linux Secret Service, 1Password, or a `0600` file under `~/.coop/state/github-pat/` (docs/configuration.md).
- **Credential isolation**: secrets travel by SSH `SendEnv`, process env, or stdin; docs/trust-model.md lists the macOS `security` and 1Password `op` backends as documented exceptions that take the secret on argv at the store step.
- **Optional credential-injecting proxy**: with `[proxy]` enabled, a host-side `coop-proxy` process per (VM, provider) holds the real API credential, and the guest holds only a per-instance capability token, reached through an `ssh -R` reverse tunnel (docs/credential-proxy.md).

---

## Technical Architecture

### Core Design

Components by exact source name (docs/ARCHITECTURE.md "Layout", with identifiers confirmed in the v0.6.0 source for the items marked `Source:`):

1. **Central CLI dispatcher** (`lib.rs:run()`, per docs/ARCHITECTURE.md): emits dynamic completions, parses the clap `Cli`, initializes tracing to stderr, handles `Completions`, `Init`, `Update`, `Uninstall`, and `Devcontainer check` before loading config, then loads `config::CoopConfig`, constructs `backend::PlatformBackend::new()`, and dispatches each `Commands` variant to a `commands::cmd_*` handler. Lifecycle handlers call `cfg.validate_and_warn()?`; `list`/`status`/`logs` skip it (docs/ARCHITECTURE.md "Command dispatch").
2. **`VmBackend` trait** (`src/backend.rs`): every VM operation goes through it — `setup`, `create_and_start`, `start_existing`, `stop`, `destroy_instance`, `resize_disk`, `commit_disk`, `status`, `stream_logs`, `ssh_target`. Implementations: `FirecrackerBackend` (`#[cfg(not(target_os = "macos"))]`) and `LimaBackend` (`#[cfg(target_os = "macos")]`) (code-read). Source: src/backend.rs — `pub trait VmBackend`, `pub struct FirecrackerBackend`, `pub struct LimaBackend`
3. **Type-state machines**: `RunningInstance` / `StoppedInstance` in `backend.rs` are liveness proofs with private fields, minted only by the probes `as_running` / `as_stopped`; `FirecrackerVm<Configured>` / `FirecrackerVm<Running>` in `vm.rs` gate `start()`/`stop()` transitions at compile time (docs/ARCHITECTURE.md "Typestate invariants") (code-read). Source: src/backend.rs — `pub struct RunningInstance`, `pub struct StoppedInstance`
4. **`boot_preflight(cfg)`** (`backend.rs`): the single choke point every boot path calls first; it runs `cfg.validate()` (docs/ARCHITECTURE.md) (code-read). Source: src/backend.rs — `pub fn boot_preflight`
5. **Backend-shared operations**: the "shared guest operations" surface in `backend.rs` (env/secret forwarding, agent bootstrap, Claude/Codex config injection, git-repo cloning), plus `workspace.rs`, `ssh.rs`, `config.rs`, and the `commands/` handlers (docs/ARCHITECTURE.md). Source: src/backend.rs — `pub fn prepare_env_forwarding`, `pub fn bootstrap_agents`
6. **`coop-proxy`**: a separate binary crate in the same Cargo workspace for credential injection, policy, TLS, and jail; `cargo build --workspace` builds both crates (docs/ARCHITECTURE.md "Layout").

Known intentional divergences between the backends (docs/ARCHITECTURE.md): `guest_host_address` is the TAP gateway (`network.host_ip`) on Firecracker and `host.lima.internal` on Lima; `mounts_are_live` is `false` on Firecracker and `true` on Lima; `ssh_target` is built from `guest_ip` + `ssh_port` on Firecracker and queried from `limactl` on Lima.

### Data Flow: Host → Guest

First boot (`lifecycle.rs:start_instance`, `BootMode::FirstBoot`) runs roughly (docs/ARCHITECTURE.md "Data flow: host → guest"):

1. **Resolve** the target repo/workspace and optionally prompt for a GitHub PAT (`pat_prompt::maybe_prompt`).
2. **Ports** — merge forward-port specs and fail fast on host-port collisions.
3. **Boot** the VM (`be.create_and_start`), then `wait_until_ready` (SSH probe with backoff).
4. **Forwards + state** — spawn `ssh -L` forwards and persist `ForwardsState`, `GuestEnvState`, `DevcontainerState` as JSON sidecars.
5. **Bootstrap** (`backend.rs:bootstrap_agents`) — if a `GITHUB_TOKEN` is present, `gh auth setup-git`; then `bootstrap_claude` / `bootstrap_codex`.
6. **Workspace** — copy mode tar-pipes; `--git-repo` clones inside the guest; mounts are live on Lima and rsync'd on Firecracker. Persist `WorkspaceState`.
7. **`postStartCommand`** hook (warned, not fatal).

### Firecracker (Linux)

All from docs/backends.md unless noted:

- **Setup**: downloads the Firecracker binary (jailer extracted alongside) and a guest kernel from Firecracker's CI S3 bucket, then builds a template rootfs: an ext4 image with an install script run in a chroot. docs/backends.md states the rootfs starts from the Firecracker CI squashfs rootfs (Ubuntu-based); docs/images-and-profiles.md states "debootstrap on Firecracker" for the base system.
- **Instance creation**: `cp --reflink=auto` of the template rootfs, patch network config with the instance IP, write a Firecracker JSON config (kernel, rootfs drive, vCPU/memory, network interface, vsock), create and attach a TAP device to the bridge, start the Firecracker process with `sudo`, then wait for SSH.
- **Networking**: dedicated TAP device per instance (`tap0`, `tap1`, …) on the Linux bridge `br0` (default host IP `172.16.0.1/24`); iptables NAT masquerade routes guest traffic through the host's default interface; guest IPs are `172.16.0.{index + 2}`. Guests cannot reach each other by IP: the isolated bridge-port flag blocks L2 and a `FORWARD -i br0 -o br0 -j DROP` rule blocks L3, and a host that cannot apply the flag fails the VM start.
- **Typestate**: `FirecrackerVm<Configured>` before boot, `FirecrackerVm<Running>` after.
- **Stop**: `SendCtrlAltDel` over the Firecracker API socket, falling back to `SIGTERM`, then `SIGKILL`.

### Lima (macOS)

All from docs/backends.md:

- **Setup**: temporary builder VM from an Ubuntu 24.04 cloud image, packages installed by a cloud-init provision script, disk extracted as the golden image, builder VM deleted afterwards; a fast-start template referencing the golden image is generated.
- **Instance creation**: `limactl start` with the fast-start template; Lima allocates the SSH port and coop reads it from `limactl list --json`; instance names are prefixed `coop-`.
- **Mounts**: `mountType: "virtiofs"` with empty `mounts: []`; `coop up --mount` adds virtiofs entries, giving live mounts.
- **Resource ownership**: "No `sudo` is required for any Lima operation".

### Update Verification Chain

`coop update` fetches release metadata from the pinned `trailofbits/coop` repo, downloads the platform tarball + `SHA256SUMS` + `attestations.jsonl`, verifies the checksum (mandatory), verifies the Sigstore attestation via `gh` against that bundle (falling back to the attestations API when the release has no usable bundle; best-effort), extracts with path-escape-safe `tar` flags, and atomically renames the new `coop-proxy` beside the CLI before replacing `coop`; each replacement is atomic and the pair is not a single transaction. A background notifier checks for new versions on a 24-hour interval (disabled in dev/CI/non-TTY) (docs/ARCHITECTURE.md "`coop update`").

### Design Rationale (as documented)

- Backend selection is compile-time: docs/ARCHITECTURE.md states "There is no runtime backend enum and no dispatch cost" and invariant 2, "Don't add a runtime backend enum".
- Lifecycles are encoded in types: docs/ARCHITECTURE.md calls this "a load-bearing design choice"; docs/code-style.md says illegal transitions "become compile errors" and recommends type-state "when the lifecycle is the *primary* abstraction a type exposes".
- Value invariants live in constructors: docs/ARCHITECTURE.md invariant 4, "Parse into a newtype at the boundary; don't re-validate primitives downstream".
- docs/ARCHITECTURE.md invariants 5-7: secrets never touch argv or logs; remote commands are built with `RemoteCommand::arg` and host commands with `Cmd::arg`; state is transparent JSON sidecars written atomically.
- The Firecracker guest runs a minimal CI kernel missing several netfilter modules; workarounds (iptables-legacy, static `resolv.conf`, `DOCKER_INSECURE_NO_IPTABLES_RAW=1`) are applied in `guest-config.sh` (docs/ARCHITECTURE.md "Guest image").

### Extension and Integration Points

- Image customization: `--profile`, custom `[profiles.<name>]`, `--extra-packages`, and `--post-install <path>` (a script run in the template chroot with root access) (docs/images-and-profiles.md).
- Named images and `coop commit` / `coop up --image <name>` for checkpointed images (docs/commands.md).
- `devcontainer.json` discovery and translation, including GHCR OCI Features (docs/devcontainer.md).
- `[claude]` config section: `marketplaces`, `plugins`, `mcp_servers`, `config_dir`, `env_forward`; a `[codex]` section with `auth` and `env_forward` fields also exists (docs/claude-integration.md; docs/configuration.md).
- Per-start hooks: `--post-start <cmd>` and `postStartCommand` (docs/commands.md; docs/ARCHITECTURE.md).
- Credential proxy: `[proxy]` section and the `coop-proxy` binary (docs/credential-proxy.md).
- A plug-in interface for third-party backends: Not mentioned in documentation (docs/backends.md and docs/ARCHITECTURE.md describe exactly two backends chosen at compile time).

---

## Limitations and Caveats

- **Platform support**: README.md states coop is tested on macOS arm64 (Apple Silicon) and Linux x86_64, and that Linux arm64 builds are available but untested. docs/getting-started.md lists the macOS prerequisite as Apple Silicon (arm64) with Rosetta 2 for x86_64 guests.
- **Lima requirement on macOS**: `coop setup` fails without `limactl` on `PATH` (docs/getting-started.md; README.md).
- **Firecracker privileges**: Source A (docs/getting-started.md) states "`/dev/kvm` must exist and be writable by your user" and "`sudo` privileges (Firecracker uses jailer and TAP networking)". Source B (docs/backends.md) states "Starts the Firecracker process with `sudo`. Firecracker requires root for KVM and TAP access", lists `sudo` operations including TAP and bridge creation, iptables, rootfs chroot/mount, and instance-directory removal, and says setup checks `/dev/kvm` and offers to fix permissions via `setfacl` or the `kvm` group.
- **Workspace sync transports**: docs/ARCHITECTURE.md Layout labels `workspace.rs` "workspace sync (rsync/tar)" and its data-flow step 6 says copy mode uses tar-pipe while mounts are "rsync'd on Firecracker". docs/workspaces.md states `coop up` copy mode tar-pipes, `--mount` on Firecracker is a one-time rsync, and `push`/`pull` use rsync when the guest has it and tar-pipe otherwise. On Firecracker `--mount` is not live: docs/backends.md says "Use `coop push` and `coop pull` to re-sync".
- **Linux guests share one bridge**: CHANGELOG.md v0.6.0 states "Restart all running Linux VMs after upgrading to apply guest-to-guest network isolation. Every VM on the shared bridge needs the restart; a pre-upgrade VM leaves peers reachable."
- **Docker inside agent VMs**: docs/getting-started.md states "Each VM gets its own filesystem, network stack, and Docker daemon." docs/backends.md's parity table lists Docker in the guest as "Works (with iptables-legacy workaround)" on Firecracker. Behaviour when Docker fails inside the VM: Not mentioned in documentation.
- **Nested virtualization**: Not mentioned in documentation (no match for `nested` in README.md or docs/ at the v0.6.0 tag).
- **Disk shrink**: docs/backends.md states "Shrinking is not supported" for both backends' disk resize.
- **Upgrading from v0.5.4**: docs/getting-started.md states the published v0.5.4 Linux ARM64 binary reports `coop 0.5.4-dev (8e24729+dirty)` and "refuses `coop update` because it identifies itself as a development build"; rerunning the installer bypasses the old updater.
- **`restore --reprovision`**: CHANGELOG.md v0.6.0 states it "replaces the guest disk, including any guest keyring and cached account login".

---

## Installation & Usage

### Install

Latest release (README.md; docs/getting-started.md):

```bash
curl -fsSL https://raw.githubusercontent.com/trailofbits/coop/main/install.sh | bash
```

`install.sh` verifies the tarball's SHA-256 against the release's `SHA256SUMS` and, when `gh` is installed, its Sigstore build-provenance attestation (docs/getting-started.md).

Build from source (requires Rust and CMake; README.md):

```bash
cargo build --workspace --release
cp target/release/coop target/release/coop-proxy /usr/local/bin/
```

### Prerequisites (docs/getting-started.md)

**macOS (Lima backend)**

- Lima installed with `limactl` on `PATH` (`brew install lima`)
- Apple Silicon (arm64)
- Rosetta 2 for x86_64 guests on Apple Silicon: `softwareupdate --install-rosetta`

**Linux (Firecracker backend)**

- KVM access (`/dev/kvm` must exist and be writable by your user)
- x86_64 or arm64 architecture
- `sudo` privileges (Firecracker uses jailer and TAP networking)
- `curl`, `tar`, `e2fsprogs` (for `mkfs.ext4`, `resize2fs`)

### Setup

```bash
coop setup
```

On Linux, `coop setup` installs Firecracker and fetches a guest kernel; on macOS it builds the Lima golden image (README.md; docs/backends.md). Keep coop updated with `coop update`.

### Usage

Examples from docs/commands.md and docs/claude-integration.md:

```bash
coop up .                                      # create or reuse the project's instance
coop claude                                    # launch Claude Code in the VM
coop claude my-project --ask                   # prompt for permissions instead of bypassing them
coop claude my-project -- --model sonnet       # extra args passed through to claude
coop codex                                     # launch Codex in the VM
coop shell my-project -- cat /etc/os-release   # non-interactive command, no PTY; returns its exit code
```

Instance management (docs/commands.md):

```bash
coop list
coop status [NAME]
coop logs my-project -f
coop stop my-project
coop destroy [NAME]
```

Resize, checkpoint, and restore (docs/commands.md):

```bash
coop resize my-project --mem 8192 --vcpus 4
coop resize my-project --size 150G
coop stop my-project
coop commit my-project --image my-project-baseline
coop restore my-project --image safe-point
```

GitHub PAT management (docs/commands.md):

```bash
coop github setup-pat --repo trailofbits/coop
coop github status
coop github rotate-pat --repo trailofbits/coop
coop github forget-pat --repo trailofbits/coop
```

Workspace sync (docs/commands.md; docs/workspaces.md):

```bash
coop up ~/code/my-project --mount     # live on Lima, one-time sync on Firecracker
coop push                             # host workspace to guest /workspace
coop pull                             # guest /workspace to host
```

---

## References

All sources were read from the `trailofbits/coop` tag `v0.6.0` (commit `63e4ff36c18133518445dd1b706c0391c0a0376a`) by shallow clone.

- [coop GitHub Repository](https://github.com/trailofbits/coop), tag v0.6.0 (accessed 2026-10-06)
- [README.md — Installation, setup, platform test targets](https://github.com/trailofbits/coop/blob/v0.6.0/README.md), v0.6.0 (accessed 2026-10-06)
- [CHANGELOG.md — v0.6.0 upgrade notes and features](https://github.com/trailofbits/coop/blob/v0.6.0/CHANGELOG.md), v0.6.0 (accessed 2026-10-06)
- [docs/ARCHITECTURE.md — Layout, two-backend design, data flow, invariants](https://github.com/trailofbits/coop/blob/v0.6.0/docs/ARCHITECTURE.md), v0.6.0 (accessed 2026-10-06)
- [docs/getting-started.md — Prerequisites and installation](https://github.com/trailofbits/coop/blob/v0.6.0/docs/getting-started.md), v0.6.0 (accessed 2026-10-06)
- [docs/backends.md — Firecracker and Lima backend specifics](https://github.com/trailofbits/coop/blob/v0.6.0/docs/backends.md), v0.6.0 (accessed 2026-10-06)
- [docs/commands.md — Command reference](https://github.com/trailofbits/coop/blob/v0.6.0/docs/commands.md), v0.6.0 (accessed 2026-10-06)
- [docs/claude-integration.md — Claude Code bootstrap and configuration](https://github.com/trailofbits/coop/blob/v0.6.0/docs/claude-integration.md), v0.6.0 (accessed 2026-10-06)
- [docs/configuration.md — Config reference, env forwarding, GitHub PAT](https://github.com/trailofbits/coop/blob/v0.6.0/docs/configuration.md), v0.6.0 (accessed 2026-10-06)
- [docs/workspaces.md — Workspace sync transports](https://github.com/trailofbits/coop/blob/v0.6.0/docs/workspaces.md), v0.6.0 (accessed 2026-10-06)
- [docs/images-and-profiles.md — Golden images, profiles, extra packages, post-install](https://github.com/trailofbits/coop/blob/v0.6.0/docs/images-and-profiles.md), v0.6.0 (accessed 2026-10-06)
- [docs/devcontainer.md — devcontainer.json translation](https://github.com/trailofbits/coop/blob/v0.6.0/docs/devcontainer.md), v0.6.0 (accessed 2026-10-06)
- [docs/credential-proxy.md — Credential-injecting proxy](https://github.com/trailofbits/coop/blob/v0.6.0/docs/credential-proxy.md), v0.6.0 (accessed 2026-10-06)
- [docs/trust-model.md — Security boundaries and secret-handling invariants](https://github.com/trailofbits/coop/blob/v0.6.0/docs/trust-model.md), v0.6.0 (accessed 2026-10-06)
- [docs/code-style.md — Type-state for lifecycles](https://github.com/trailofbits/coop/blob/v0.6.0/docs/code-style.md), v0.6.0 (accessed 2026-10-06)
- [Cargo.toml — Version 0.6.0](https://github.com/trailofbits/coop/blob/v0.6.0/Cargo.toml), v0.6.0 (accessed 2026-10-06)
- [src/backend.rs — VmBackend, PlatformBackend, type-state structs, bootstrap functions](https://github.com/trailofbits/coop/blob/v0.6.0/src/backend.rs), v0.6.0 (accessed 2026-10-06)
- [src/config.rs — VmMemory, InstanceIndex newtypes](https://github.com/trailofbits/coop/blob/v0.6.0/src/config.rs), v0.6.0 (accessed 2026-10-06)
- [src/port_forward.rs — check_host_port_collisions](https://github.com/trailofbits/coop/blob/v0.6.0/src/port_forward.rs), v0.6.0 (accessed 2026-10-06)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [HolyClaude](./holyclaude.md) | agent-infrastructure | Competing approach: pre-built Docker container with Claude Code and agents; coop provides lightweight VMs with credential forwarding and multi-agent support |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | coop extends Claude Code's execution model by providing isolated VMs; harness abstracts how agents interface with Claude Code |
| [Oh-My-ClaudeCode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | coop provides low-level VM management for multi-agent orchestration; orchestration layer would coordinate launching agents into coop instances |
