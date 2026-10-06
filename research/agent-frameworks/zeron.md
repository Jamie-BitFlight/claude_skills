---
name: zeron
title: Zeron
subtitle: Local-first multi-agent controller with optional device sync
research_date: 2026-10-02
source_url: https://github.com/zeronsh/zeron
github_repository: https://github.com/zeronsh/zeron
version_at_research: v0.2.102
license: MIT
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: v0.2.102
  next_review: 2027-01-02
  confidence_map: "Overview: medium, Problem Addressed: medium, Key Features: medium, Technical Architecture: medium (doc + code-read), Installation & Usage: high, Limitations and Caveats: low"
---

# Zeron

## Overview

Zeron is a native Rust application that provides local-first control of multiple coding agents with optional multi-device synchronization. The README (line 3) names Claude Code, Codex, Cursor, Devin, Grok, Hermes, Pi and Antigravity as the controlled agents; only the Claude Code and Codex harnesses are verified in this entry, and ARCHITECTURE.md lists the Cursor harness as deferred (see Limitations and Caveats, Deferred Product Work item 4), so the README list is the project's claim, not a verified per-agent support matrix. Every device runs a small engine that stores sessions locally, with installations starting in local-only mode without requiring an account or network connection. The application is available as a single binary that can run in headed (desktop UI) or headless (daemon) modes, with optional multi-device workspace sync via Cloudflare Durable Objects and CRDTs when enabled.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Fragmented agent control across multiple platforms | Unified local controller; the README names Claude Code, Codex, Cursor, Devin, Grok, Hermes, Pi and Antigravity, but only the Claude Code and Codex harnesses are verified here (Cursor is listed as deferred in ARCHITECTURE.md) |
| Privacy and autonomy concerns with cloud-first agent management | Local-first design by default—sessions remain on device until user explicitly enables sync |
| Disconnected sessions across devices | Optional Loro CRDT-based synchronization allowing session continuation across trusted devices and remote control |
| Loss of agent access when primary device is offline | VPS-capable headless mode enables always-on agent execution while controlling from laptop |
| Limited visibility into agent execution state | Native diff pane, terminal emulation, and git integration for real-time session inspection |

---

## Key Features

### Multi-Agent Harness Support

Zeron abstracts the control interface across multiple coding agents through a pluggable harness system. Each harness is a trait implementation that handles agent-specific communication protocols—Claude Code via stream-json subprocess protocol, Codex via app-server JSON-RPC, with a mock harness. The README names Cursor, Devin, Grok, Hermes, Pi and Antigravity as controlled agents (README.md line 3), but the per-harness implementation status for those is not verified beyond directory names: `crates/harness/src/` at v0.2.102 contains `claude/`, `codex/`, `cursor/`, `acp/`, `opencode/`, `pi/` and `mock.rs`, and their contents were not read.

### Local-First Session Persistence

Sessions persist to the device's local store by default. The session document schema—a Loro CRDT structure porting the original zeron implementation—includes a transcript with messages stored as LoroText values (measuring 1.03× oplog overhead), a durable command queue for send/steer/interrupt operations, and metadata. Each session remains under `{data_dir}/profiles/local/` when running in local-only mode. When a user signs in to enable sync, the profile switches to `{data_dir}/orgs/{org_id}/{user_id}/`, preserving the same session doc structure but enabling CloudFlare Durable Object synchronization.

### Optional Multi-Device Synchronization

Authentication and workspace management are deliberately decoupled: signing in via `zeron login` only changes the profile selected at the next daemon restart—existing local sessions are not uploaded or imported. Devices authenticated to the same account become trusted peers, enabling one device to list, read, and write files on another via relay-forwarded workspace requests. The workspace registry document (a Loro CRDT) syncs across devices, storing space definitions (device, folder pairs), chat indexes, devices, and session-status rows. A VPS can keep agents working after a laptop closes by running `zeron headless` on the VPS while a laptop UI connects and drives sessions remotely.

### Native UI with gpui

The interface is built in gpui (a pinned Zed revision with custom extensions for blur, edge fades, and GPU memory bounds). The UI organizes around a searchable spaces sidebar with session tabs as a device-local viewport (opening/closing tabs is local-only; archiving is explicit). Key UI components include:

- **Transcript**: Virtualized list with spring-based stick-to-bottom tracking (interrupted by user input, re-engages within 70px per ARCHITECTURE.md line 179), block-granular rows with incremental streaming markdown re-parse, and scroll-anchor absorption.
- **Composer**: Hand-rolled text input with auto-grow (76–260px), IME support, question panel (1-9 keys, 220ms auto-advance per ARCHITECTURE.md line 198; `AUTO_ADVANCE_MS: u64 = 220` in `crates/ui/src/composer.rs`) for multi-choice scenarios, and attachment/image drag-drop.
- **Terminal**: Alacritty VTE terminal emulation with portable-pty backend, tab drag-reorder, 150ms sliding animations, 12ms input coalescing, and 1MB replay (ARCHITECTURE.md line 203).
- **Diff Pane**: Unified-patch virtualized viewer with per-file collapse animation (180ms), time-sliced syntax highlighting, and 200ms width transitions.
- **Theme System**: Device-local independent light/dark variants with optional VS Code file/package import and custom family support, accent overrides for interaction roles only.

### Headless and Headed Modes

One binary, two modes: headed mode launches a gpui window and optionally hosts a local engine over IPC if no daemon is running; `zeron headless` runs the engine as a daemon only. In-process mode uses an in-memory RPC transport (same protocol as external daemons, no serialization shortcuts), keeping the boundary honest. Headless mode serves the local profile over localhost IPC and, when authenticated and synced, also hosts its DeviceRoom for remote peers.

### Cargo Workspace Architecture

In the main-branch clone read on 2026-10-05 (commit 3d4bfd1), the root `Cargo.toml` lists 18 workspace members: 17 crates under `crates/` plus the `apps/zeron` application. The list below covers the crates under `crates/`:

- **zeron-proto**: Wire types (AgentEvent, ToolCall, RunRequest, Model), serde+ndjson framing, and pure derivations both frontends share (sort orders, staleness gating, grouping).
- **zeron-doc**: Session doc + workspace registry schemas, Loro mirror layer with incremental diff application, parts folding, command ledger, continuation splitting at 256KB.
- **zeron-sync**: Loro room client (join/version-vector backfill/fragments/backoff), ephemeral presence, DocsStore with SQLite snapshots.
- **zeron-harness**: Harness trait + implementations (Claude Code stream-json subprocess, Codex app-server JSON-RPC, mock), steering mailbox, requestInput catalog. Its `src/` also holds `cursor/`, `acp/`, `opencode/` and `pi/` directories (names only; contents not read).
- **zeron-engine**: Sessions engine (pub/sub broadcast, run journal with resumable seq replay), doc host + command executor, repos/worktrees, checkout-diff sync, terminals, uploads, agent credential swap, WorkOS auth, device-room host/peers, identity.
- **zeron-rpc**: Typed request/response/stream RPC over WS (tokio-tungstenite) + in-memory transport, device-room virtual sockets (s/k/to/from frames).
- **zeron-ui**: gpui app shell, sidebar, conversation, composer, terminal, diff, settings, animation kit.
- **zeron-preview**: "Project-scoped HTTP discovery, stable local routing, and authenticated peers" (`crates/preview/src/lib.rs` line 1).
- **zeron-update**: "release checking and self-update, shared by the engine (the background checker + `ApplyUpdate`), the CLI (`zeron update`), and the UI" (`crates/update/src/lib.rs` lines 1-3).
- **zeron-theme**, **zeron-voice**, **zeron-markdown**, **zeron-syntax**, **zeron-text**, **zeron-mcp**, **zeron-mobile**, **zeron-client**: Specialized support crates.

Async runtime: tokio throughout; in-process UI bridges via `gpui_tokio` (futures surfaced as gpui Tasks).

### Edge Infrastructure (TypeScript)

The backend for multi-device sync runs as CloudFlare Workers + Durable Objects, absorbing responsibilities from the original zeron server:

- **ChatRoom DO**: Per-chat session document sync using Zeron's chat2 row protocol (loro updates as append-only rows + Range-resumable checkpoints).
- **DeviceRoom DO**: Per-device byte relay, nudges, and sidecar slots for diff/tail data.
- **WorkspaceRegistry**: Private per-user room (`reg1/{orgId}/{userId}`) with authenticated row sync and ephemeral presence.
- **Auth Routes**: `/auth/exchange` and `/auth/refresh` for WorkOS integration, orgs onboarding.
- **R2 Attachments**: Cloud storage with per-account cache under `{data_dir}/orgs/{org_id}/{user_id}/uploads/`.

---

## Technical Architecture

Zeron's topology connects gpui UI to an engine (local or remote) via typed RPC, with optional multi-device sync through CloudFlare Durable Objects:

```text
gpui UI ─ in-proc/localhost RPC ─ engine A ══ DeviceRoom DO relay ══ engine B ─ RPC ─ gpui UI
                    │       optional edge Worker: auth, rooms, R2        │
                    └── optional chat2 sync ──  ChatRoom DO (per chat) ──┘
                                          └─ Workspace registry room ────┘
```

### Data Model — Loro CRDT

Two persistent document kinds persist identically whether sync is enabled:

1. **Session doc** (per chat): Schema is a Rust port of the original zeron's `packages/session-doc`, carrying `meta` (map), `messages` (list of maps with LoroText bodies), and `commands` (list with append-only per-device entries, host-only outcomes, dedupe/TTL/supersede evaluation). Constants: `STREAM_COMMIT_MS=120`, `DO_FLUSH_MS=5s`, compaction at 8MB, 30-day retention, 64-message tail (ARCHITECTURE.md lines 104-105). Continuation splitting at 256KB, render-only tool parts (full inputs in host's local run journal).

2. **Workspace registry doc** (per profile): Stores spaces (id, deviceId, path, name, gitDetected, checkoutId), chat index (id, deviceId, title, archived, cwd, branch, checkoutId, spaceId, lastSeenAt, lastMessagePreview/At, config), devices, session-status rows, and checkout-diff summary pointers. Writer discipline: each device writes its own rows, creates/renames/archives are LWW sets, presence uses ephemeral room frames.

**Mirror layer** (`zeron-doc` crate): Rust equivalent of loro-mirror—typed structs for schema, incremental application of `doc.subscribe` diffs (no full re-hydration per change), and diff-reconcile write path. UI renders mirror state directly with per-entry change notifications.

### Command Plane

Send/steer/interrupt/respondInput are durable command entries in the session doc (`QueueCommand`), executed by the chat's host device. Offline sends queue in the doc; mark-processed before execute; steer with no live run dispatches as next turn. This is zeron's proven design, kept verbatim.

### Authentication and Workspace Scope

- **AuthState**: Live credential state (`SignedOut`, `NeedsOrganization`, or `SignedIn`).
- **WorkspaceScope**: Immutable storage boundary set at engine startup: `Local`, `Synced`, or explicit `Development`. ARCHITECTURE.md (line 51) states: "The engine never re-resolves an open store because `AuthState` changed. This prevents a sign-in, token refresh, or revocation from silently swapping databases or attaching online transports to a runtime that started local-only."

Startup behavior:

| Condition | WorkspaceScope | Online transports |
| --- | --- | --- |
| WorkOS enabled, no saved session | `Local` | Disabled |
| Saved WorkOS session with bearer | `Synced` | Enabled when bearer available |
| WorkOS disabled, no dev bearer | `Development` | Disabled |
| Explicit non-empty dev bearer | `Development` | Enabled |

---

## Installation & Usage

### Linux Installation

```bash
curl -fsSL https://zeron.sh/install.sh | sh
zeron status
```

The installer:
- Starts the daemon immediately and keeps it running across reboots
- Adds Zeron to the application launcher (`~/.local/share/zeron.desktop` and icon)
- Requires system ALSA runtime (`libasound.so.2`) even in headless mode (shared desktop executable)
- Verifies the binary starts and reports missing runtime libraries
- For desktop sidebar browser use, requires the Linux browser runtime

Day-to-day commands:

```bash
zeron status      # local/synced mode and engine status
zeron update      # update to the latest release
zeron daemon start|stop|restart|status
```

### Multi-Device Setup

To enable sync, stop the daemon, sign in, and restart:

```bash
zeron daemon stop
zeron login
zeron daemon start
```

The login changes the profile selected at next startup. Returning to local-only:

```bash
zeron daemon stop
zeron logout
zeron daemon start
```

### macOS and Windows

- **macOS**: Use the desktop release, or build from source and run `zeron daemon install` for launchd service.
- **Windows**: Run `zeron-<version>-windows-x86_64-setup.exe` installer (installs for user, no admin needed, adds Start menu entry). A portable ZIP is available; keep `zeron-update.json` beside `zeron.exe` for in-app updates.

### Updates

The desktop app checks for new releases on startup, every hour while running, and after machine sleep. Updates download in the background; the sidebar shows **Update ready — restart to apply**. Check manually via **Zeron → Check for Updates…** (macOS) or the account menu (Windows/Linux). Set `ZERON_AUTO_UPDATE=0` to disable background downloads. Linux installs from the release tarball use `~/.zeron/app` and update in place; daemon services restart on idle; `zeron update` updates headless installs on demand.

---

## Limitations and Caveats

### Excluded Features

Token-usage display (profile heatmap, lifetime stats, per-message token columns, `WatchUsage`) is excluded. ARCHITECTURE.md (line 10) lists the goal as "Feature parity with zeron **except token-usage display** (poor fit for CRDTs; excluded)." and line 257 repeats the exclusion.

### Privacy Boundary

Devices authenticated to the same synced account are **trusted peers** for remote workspace access—a remote peer can request workspace file contents and write changes. Ignored-file visibility is **not** an authorization boundary; when `includeIgnored` is enabled, remote peers can read and write files like `.env`. `.git` remains unavailable. ARCHITECTURE.md (line 84) states: "Zeron intentionally does not maintain a filename denylist because it would be incomplete and could imply a security guarantee it cannot provide." If authenticated devices must no longer trust one another, that policy must be enforced by the owning engine for remote requests; UI-only hiding is not a security control.

### Deferred Product Work

Items 1-4 are deferred product work; item 5 is recorded separately as a milestone gap:

1. Explicit session selection and copy between local and synced profiles, including attachment copying, provenance, and conflict behavior.
2. Browsing both scopes simultaneously or switching visible scope without engine restart.
3. Supported self-hosted backend contract (current endpoint and bearer overrides remain development seams).
4. Cursor harness implementation, per ARCHITECTURE.md (its M5 gaps line and Open question 3, "parity item, scheduled after Codex"). The file carries no date of its own; it is from the v0.2.102 clone, whose commit is dated 2026-10-02. This conflicts with the README listing Cursor as a controlled agent and with `crates/harness/src/cursor/` existing (`catalog.rs`, `mod.rs`, `shim.mjs`, `state.rs`), so the statement may be stale. Whether Cursor, ACP, OpenCode or Pi harnesses are functional is not verified beyond directory names.
5. Prefers-reduced-motion support and engine hardening (instance lock, watchdogs) are listed as gaps of the M6 Polish milestone in ARCHITECTURE.md (lines 288-290). The same file says at line 194 that `prefers-reduced-motion` is honored, so the source contradicts itself on this point; it is not described as intentionally deferred.

### Workspace File Trust

Remote workspace file requests are subject to workspace-relative path containment, symlink, and write-conflict checks. Ignored-file visibility setting does not restrict what remote peers may access.

---

## References

- [Zeron Repository](https://github.com/zeronsh/zeron) (accessed 2026-10-02)
- [Zeron ARCHITECTURE.md](https://github.com/zeronsh/zeron/blob/main/ARCHITECTURE.md) (accessed 2026-10-02)
- [Zeron README](https://github.com/zeronsh/zeron/blob/main/README.md) (accessed 2026-10-02)
- [Zeron CONTEXT.md](https://github.com/zeronsh/zeron/blob/main/CONTEXT.md) (accessed 2026-10-02)
- [Zeron Cargo.toml](https://github.com/zeronsh/zeron/blob/main/Cargo.toml) (accessed 2026-10-02)
