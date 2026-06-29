---
title: "Tessera: Just-in-Time Terminal Access with Human Approval"
category: "security-tools"
source: "https://github.com/emmayusufu/tessera"
date_created: 2026-06-18
date_reviewed: 2026-06-18
next_review: 2026-09-18
confidence:
  overview: "high"
  architecture: "high"
  api_design: "high"
  limitations: "medium"
  deployment: "high"
---

## Overview

Tessera is a minimal, single-purpose terminal access broker for time-limited, just-in-time (JIT), human-approved access to remote hosts. It implements a three-party architecture: a **coordinator** (broker on public host), an **agent** (long-lived service on the target host), and a **client** (guest-side CLI requesting access). The system requires explicit human approval at the terminal for every session request before establishing connectivity.

**Primary distinction from competitors**: "The one thing Tessera gives you that Teleport gates behind its paid Enterprise tier is the request and human-approve, just-in-time access flow. Tessera also runs with no cluster or SSO to operate, and is MIT-licensed rather than AGPL." ([README: How it compares](https://github.com/emmayusufu/tessera#how-it-compares))

**Implementation**: Go 1.26, zero external dependencies (stdlib-only core logic), minimal external dependencies limited to `creack/pty` (terminal multiplexing) and `golang.org/x` standard library forks.

**Current status**: Active development on `main` branch (commit: 36678fda4a537ee101dedbb5a8a023b27b31069d), with production-grade deployment patterns documented but version tags not yet published in this clone.

---

## Problem Domain

Tessera addresses the access control pattern known as "zero standing privilege": grant temporary, scoped access on-demand rather than maintaining persistent credentials or roles.

**Use cases** ([README: When you might use it](https://github.com/emmayusufu/tessera#when-you-might-use-it)):
- On-call engineers requiring emergency access to production systems
- Contractors needing temporary SSH to a customer's machines
- Privileged operations that require human oversight (e.g., database migrations)
- Incident response with approval trails

**Key constraint**: "Tessera only makes sense as a consent-based tool: the host always approves, access is scoped to a session, and everything is audited. It is not a backdoor." ([README: Security note](https://github.com/emmayusufu/tessera#security-note))

---

## Architecture Overview

### Three-Component System

Tessera's design separates **approval logic** (human), **access brokering** (coordinator), and **local enforcement** (agent) into three autonomous processes:

1. **Coordinator** (`internal/coordinator/`): Central broker running on publicly routable host
   - Accepts mTLS connections from agents (long-lived, authenticated)
   - Exposes HTTP bootstrap endpoints for guest redeem/peek operations
   - Pairs approved guest connections with agent target streams
   - Logs all access events to append-only audit trail
   - **Key entry point**: `cmd/coordinator/main.go`
   - **Package documentation**: "Package coordinator is tessera's broker: it pairs an approved guest stream with its agent." ([coordinator.go](https://github.com/emmayusufu/tessera/blob/main/internal/coordinator/coordinator.go))

2. **Agent** (`internal/agent/`, `cmd/agent/main.go`): Long-running service on target host
   - Dials outbound to coordinator (agent initiates, never accepts inbound)
   - Hosts approved sessions forwarded from coordinator
   - Routes traffic to allowed local targets (TCP ports) or PTY shell
   - **Key types**: `Agent` struct with fields `ShareID`, `Dial` (netutil.Dialer), `Allowed` (target list), `Inner` (*tls.Config for end-to-end encryption), `Logger`, `ShellMode` (PTY-backed shell flag), `RecordPath` (session transcript directory)
   - **Documentation**: "Package agent runs on the host's side and serves approved streams to allowed local targets." ([agent.go](https://github.com/emmayusufu/tessera/blob/main/internal/agent/agent.go))
   - **Resilience**: `RunWithBackoff()` method implements exponential backoff (1s–30s capped) with jitter to recover from Wi-Fi flaps and coordinator hiccups

3. **Client/CLI** (`cmd/tessera/`, `internal/client/`): Guest-side command-line tool
   - Generates TLS certificates (command: `tessera ca`)
   - Requests access via coordinator HTTP bootstrap endpoints (command: `tessera join`)
   - Forwards approved session to local port or shares via `tessera share` (host-side command)
   - Operates in interactive mode when invoked without arguments
   - **Package documentation**: "Package client is the guest side: request access, then forward a local port through the coordinator." ([client.go](https://github.com/emmayusufu/tessera/blob/main/internal/client/client.go))

### Data Flow: Session Lifecycle

**Access request sequence** ([client.Request() function](https://github.com/emmayusufu/tessera/blob/main/internal/client/client.go)):

```
Guest → Coordinator (Request message):
  Kind: "request"
  ShareID: identifier for the shared resource
  Target: destination host:port
  Reason: human-provided justification
  Who: guest identity

Coordinator → Host terminal (prompt):
  "Incoming request from {who} to {target}: {reason}"
  [Host types y/n]

Host ↔ Coordinator (Decision message):
  Kind: "decision"
  Approved: bool
  Detail: reason if denied

Coordinator → Guest (Decision):
  If approved: SessionID, control connection remains open
  If denied: "access denied: {detail}"
```

**Session flow** ([client.Forward() function](https://github.com/emmayusufu/tessera/blob/main/internal/client/client.go)):

```
Guest binds local listener → accepts connections
For each local connection:
  1. Sends DataHello message to coordinator (Role: "guest", SessionID)
  2. Establishes inner TLS (guest is client, endpoint is server)
  3. Pipes local ↔ encrypted tunnel to agent

Agent receives DataHello → validates SessionID, routes to Target
Agent pipes Target ↔ encrypted tunnel back to guest
```

### Protocol Definition

All control messages use length-prefixed JSON framing ([internal/proto/](https://github.com/emmayusufu/tessera/blob/main/internal/proto/proto.go)):

**Message kinds** (Kind enum):
- `"register"` — agent registration with coordinator
- `"request"` — guest requests access (ShareID, Target, Reason, Who)
- `"decision"` — approval/denial (Approved, Detail)
- `"open_data"` — data stream initialization
- `"data_hello"` — announce stream (SessionID, ConnID, Role)
- `"approval_subscribe"` — host subscribes to approval prompts
- `"approval_prompt"` — new request pending approval
- `"approval_decision"` — host responds with y/n
- `"share_upload"` — coordinator → guest with share info
- `"share_response"` — guest acknowledges share
- `"session_ended"` — session termination

**Wire format** ([WriteMsg/ReadMsg](https://github.com/emmayusufu/tessera/blob/main/internal/proto/proto.go)):
- 4-byte big-endian frame length prefix
- JSON body (max 64 KB per frame)
- No outer encryption; relies on mTLS for agent ↔ coordinator, separate inner TLS for guest ↔ target

### Audit Mechanism

Every access event is logged to an append-only JSON lines file ([internal/audit/](https://github.com/emmayusufu/tessera/blob/main/internal/audit/audit.go)):

**Event record structure**:

```go
type Event struct {
  Time      time.Time  // server time
  Kind      string     // event type
  RequestID string     // request identifier
  SessionID string     // session identifier
  ShareID   string     // shared resource identifier
  Who       string     // guest identity
  Target    string     // destination
  Reason    string     // stated justification
  Detail    string     // approval reason (if denied)
  Token     string     // bootstrap code (hashed, never raw)
}
```

**Key property**: "Bootstrap events ('bootstrap_minted', 'bootstrap_redeemed', 'bootstrap_expired') store hex(sha256(canonical-code)) in the Token field; never the raw code." ([audit.go](https://github.com/emmayusufu/tessera/blob/main/internal/audit/audit.go))

**Field safety**: User-controllable fields (Who, Target, Reason, Detail) are capped at 256 characters to prevent audit log bloat attacks.

**Persistence**: Synchronous writes with `fsync()` after every event; mutex-protected to ensure thread-safe concurrent appends.

---

## Core Components

### 1. Coordinator (`internal/coordinator/`)

**Responsibility**: Brokering connections, enforcing timeouts, pair guest→agent streams.

**Key types**:
- `agentConn`: Outbound mTLS connection from agent (wrapper with send-side mutex)
- `approverConn`: mTLS connection from host for approval (receive approval decisions)
- `request`: Pending access request with decision channel (goroutine-based flow)
- `session`: Active approved session tracking streams and idle timeout

**Timeouts**:
- `defaultIdleTimeout = 30 * time.Minute` — session dies after 30 min inactivity
- `pairTimeout = 15 * time.Second` — max wait for guest to complete handshake after approval

**HTTP endpoints** ([coordinator/http.go](https://github.com/emmayusufu/tessera/blob/main/internal/coordinator/http.go)):
- `POST /bootstrap/redeem` — guest redeems bootstrap code → mTLS cert + coordinator address
- `GET /bootstrap/peek` — guest queries active share status
- `GET /healthz` — health check, returns "ok {version}"

**Rate limiting** ([coordinator/ratelimit.go](https://github.com/emmayusufu/tessera/blob/main/internal/coordinator/ratelimit.go)): Per-IP request throttling on bootstrap endpoints.

### 2. Agent (`internal/agent/`)

**Responsibility**: Hosting approved streams, routing to local targets, managing PTY shells.

**Agent struct fields**:
- `ShareID string` — session identifier
- `Dial netutil.Dialer` — function to establish coordinator connection
- `Allowed []string` — list of allowed targets (host:port)
- `Inner *tls.Config` — end-to-end TLS config (client-side)
- `Logger *slog.Logger` — structured logger
- `ShellMode bool` — if true, serve PTY shells instead of TCP forwarding
- `RecordPath string` — directory for shell session transcripts (mode requires pre-existing dir)

**Resilience pattern**: `RunWithBackoff()` exponential backoff retry logic — starts at 1s, doubles up to 30s cap, plus jitter.

**PTY handling** ([imports: `github.com/creack/pty`](https://github.com/emmayusufu/tessera/blob/main/internal/agent/agent.go)): Allocates pseudo-terminal when ShellMode is enabled, spawns shell subprocess, relays I/O.

### 3. Client (`internal/client/`, `cmd/tessera/`)

**Responsibility**: Certificate generation, access request, port forwarding.

**Functions**:
- `Request()` — sends access request, waits for decision
  - Returns (sessionID, control conn, error)
  - Fails fast if coordinator denies
- `Forward()` — forwards local listener through approved session
  - Accepts connections on local listener
  - Dials coordinator data stream per connection
  - Performs inner TLS handshake
  - Pipes local ↔ encrypted tunnel

**CLI commands**:
- `tessera ca` — generate CA certificate
- `tessera join {coordinator-url}` — interactive mode, obtain guest cert
- `tessera share` — run agent-side approval handler (host terminal receives prompts)

### 4. Certificate Management (`internal/certs/`)

Uses Go standard library TLS APIs to:
- Generate self-signed CA
- Issue agent and guest certificates
- Validate mTLS certificate chains
- Persist to disk (`~/.config/tessera/` for guest, systemd env/file for agent)

---

## Technology Stack

**Language**: Go 1.26 ([go.mod](https://github.com/emmayusufu/tessera/blob/main/go.mod))

**Direct dependencies**:
- `github.com/creack/pty v1.1.24` — PTY handling (shell session multiplexing)
- `golang.org/x/term v0.43.0` — terminal I/O (ANSI escape, raw mode)
- `golang.org/x/sys v0.44.0` — system calls (TTY control)

**Stdlib core**:
- `crypto/tls` — mTLS (agent ↔ coordinator, guest endpoint ↔ agent)
- `crypto/rand`, `crypto/sha256` — randomness, hashing
- `encoding/json`, `encoding/binary` — message serialization
- `net`, `net/http` — TCP, HTTP APIs
- `io`, `os/exec`, `syscall` — subprocess, I/O piping
- `log/slog` — structured logging
- `context` — cancellation, timeouts

**Build system**: GNU Make ([Makefile](https://github.com/emmayusufu/tessera/blob/main/Makefile))
- Targets: `build`, `test`, `race`, `vet`, `fmt`, `staticcheck`, `lint`, `clean`
- Version baking via `-ldflags "-X github.com/emmayusufu/tessera/internal/version.Version=$(VERSION)"`

**CI/CD**: GitHub Actions ([.github/workflows/release.yml](https://github.com/emmayusufu/tessera/blob/main/.github/workflows/release.yml))
- Multi-platform release: linux/{amd64,arm64}, darwin/{amd64,arm64}
- Publishes binaries + container image to GHCR
- Triggered on tag push (v*)

---

## Security Model

### Consent-Based Access

"The host always approves, access is scoped to a session, and everything is audited." ([README](https://github.com/emmayusufu/tessera#security-note))

**Approval flow requirements**:
1. Every request is delivered synchronously to the host's terminal
2. Host must explicitly type 'y' or 'n' (binary decision)
3. No timeout — request waits indefinitely if host doesn't respond
4. No approval token or magic link — decision happens where the admin is sitting

### Session Scoping

- Each session is bound to a single guest, single target, single time window
- Session dies on:
  - Either party disconnecting
  - 30-minute idle timeout
  - Coordinator shutdown
  - Explicit host revocation (if operator-token is configured)

### Encryption

**Two-layer TLS**:
1. **Outer TLS** (agent ↔ coordinator): mTLS with certificate-based auth
   - Agent cert issued by coordinator during registration
   - Coordinator validates agent cert on every connection
2. **Inner TLS** (guest local ↔ agent target): End-to-end encryption
   - Coordinator relays ciphertext opaque (does not decrypt)
   - Guest generates ephemeral inner TLS cert
   - Target endpoint (SSH, DB, etc.) handles inner cert

**Mandatory outer HTTPS**: "Serve the redeem/peek endpoints over HTTPS (`-http-cert`/`-http-key`) in production so the guest's bundle (which contains a private key) is not sniffable in transit." ([README](https://github.com/emmayusufu/tessera#security-note))

### Audit Trail

Every event (request, approval, denial, session open, session close, session ended) is logged with:
- Exact timestamp (server time)
- All parties (Who, Target, Reason)
- Decision (Approved, Detail)
- Bootstrap code (hashed, not plaintext)

Append-only file prevents tampering (one-way writes, fsync per record).

### Known Limitations

**Not covered**:
- No RBAC or policy engine (all/nothing approval per request)
- No revocation without operator-token (if token not configured, no revoke capability)
- No session recording in TCP mode (only shell mode supports RecordPath)
- Coordinator is single point of failure (no HA/cluster mode)
- No persistent state recovery (in-memory session map, lost on restart)

---

## Deployment

### Coordinator Deployment

**Host requirements**:
- Public IP or DNS FQDN
- TLS certificate (can use self-signed for bootstrap, Let's Encrypt recommended for production)
- Port 8443 (mTLS, agent/approver) and 8080 (HTTP, guest bootstrap) or custom via flags

**Two production paths** ([deploy/DEPLOYING.md](https://github.com/emmayusufu/tessera/blob/main/deploy/DEPLOYING.md)):

1. **Native binary + systemd** (recommended):

   ```bash
   curl https://github.com/emmayusufu/tessera/releases/download/v0.3.0/coordinator-linux-amd64 \
     > /usr/local/bin/coordinator
   chmod 0755 /usr/local/bin/coordinator
   cp tessera-coordinator.service /etc/systemd/system/
   sudo systemctl enable --now tessera-coordinator
   ```

   - Verify: `curl http://localhost:8080/healthz` → "ok v0.3.0"

2. **Docker container** (18 MB distroless image):

   ```bash
   docker build -t tessera .
   docker compose up -d
   ```

   - Image contains all three binaries (coordinator, agent, tessera)
   - Entrypoint defaults to coordinator; override with `--entrypoint` for agent/client

**Configuration** (flags and env vars):
- `-listen :8443` / `TESSERA_LISTEN` — mTLS listen address
- `-http :8080` / `TESSERA_HTTP` — HTTP bootstrap listen address
- `-http-cert cert.pem -http-key key.pem` — HTTPS cert/key (optional, recommended)
- `-operator-token {hex}` / `TESSERA_OPERATOR_TOKEN` — token for revoke operations (optional)
- `-audit /var/log/tessera/audit.log` — audit log path

**Operator Token**:
- Generate once: `tessera token`
- Install on host: `tessera token {token-hex}` → stores in `~/.config/tessera/operator-token`
- Enables revoke: `curl -X POST -H "Authorization: Bearer $(cat ~/.config/tessera/operator-token)" https://coordinator/s/{sessionID}/revoke`

### Agent Deployment

**Host requirements**:
- Outbound connectivity to coordinator (mTLS port, 8443 default)
- Operator token (if revoke is needed)

**Run agent**:

```bash
agent -coordinator coordinator.example.org:8443 \
  -share-id {some-id} \
  -allow localhost:22,localhost:5432
```

**Shell mode**:

```bash
agent -coordinator ... -shell-mode -record-path /var/lib/tessera/sessions
```

- Records PTY activity to `{session-id}.log` in record directory
- RecordPath directory must exist (agent doesn't create it)

### Guest Workflow

1. Generate cert bundle:

   ```bash
   tessera join https://coordinator.example.org
   ```

   Saves to `~/.config/tessera/{cert,key,ca}.pem`

2. Request and forward in one command:

   ```bash
   tessera -coordinator coordinator.example.org:8443 \
     -share-id host-share \
     -target {target-host:port} \
     -reason "emergency debug" \
     -local-listen 127.0.0.1:9999
   ```

   - Waits for approval at host terminal
   - On approval, forwards localhost:9999 → target through coordinator

---

## Limitations & Gaps

### Documented Limitations

From README ([What's not covered](https://github.com/emmayusufu/tessera#whats-not-covered)):
- No support for SSH agent forwarding
- No support for X11 forwarding
- No support for dynamic port forwarding (SOCKS proxy)
- Assumes target endpoint handles its own authentication (e.g., SSH key, DB password)

### Architectural Constraints

1. **Coordinator is stateful, non-distributed**
   - In-memory session tracking, no persistence layer
   - Single-machine deployment only
   - Restart loses all active sessions
   - No failover or load balancing

2. **No granular RBAC**
   - Approval is binary (yes/no) per request
   - No role-based access control, no attribute-based policies
   - No time-window or resource-quota enforcement

3. **Session recording limited to shell mode**
   - TCP forwarding mode does not record traffic
   - Shell mode requires pre-existing RecordPath directory
   - No playback mechanism for recorded sessions

4. **Certificate management manual**
   - Cert rotation requires coordinator restart
   - No automatic issuance or expiry handling
   - Guest must manually refresh cert when it expires

### Missing Capabilities (vs. Teleport)

Per README ([How it compares](https://github.com/emmayusufu/tessera#how-it-compares)):
- No SSH support (Tessera tunnels TCP; target must implement auth)
- No Kubernetes API proxy
- No database proxy
- No RDP
- No SSO integration
- No session recording in TCP mode
- No RBAC or policy engine
- No cluster/HA mode

---

## Extension Points

Tessera is designed for minimal customization. Primary integration surfaces:

1. **Protocol extension** ([internal/proto/](https://github.com/emmayusufu/tessera/blob/main/internal/proto/proto.go)):
   - Add new `Kind` enum values for new message types
   - Msg struct can accept new JSON fields (backward-compatible)

2. **Approval handler** ([cmd/tessera/ commands](https://github.com/emmayusufu/tessera/blob/main/cmd/tessera/)):
   - `tessera share` is the reference approval handler (terminal-based)
   - Custom handler can subscribe via `approval_subscribe` message and respond with `approval_decision`

3. **Target forwarding** ([internal/agent/](https://github.com/emmayusufu/tessera/blob/main/internal/agent/)):
   - Agent's `Allowed` list pins targets at startup
   - Modify Agent struct to support dynamic allowlists (currently hardcoded per agent invocation)

4. **Shell mode recording** ([internal/agent/](https://github.com/emmayusufu/tessera/blob/main/internal/agent/)):
   - `RecordPath` writes transcripts as plaintext logs
   - Can extend to structured formats (JSON, HAR-like) or compression

5. **Audit log format** ([internal/audit/](https://github.com/emmayusufu/tessera/blob/main/internal/audit/)):
   - Currently append-only JSON lines to filesystem
   - Can fork to send to centralized log (syslog, CloudWatch, ELK) by modifying Log type

---

## Current Status & Testing

**Development stage**: Active — main branch, no released versions yet in repo.

**Test coverage** ([files counted](https://github.com/emmayusufu/tessera)):
- 33 Go source files total (cmd, internal packages)
- 7 test files (*_test.go)
  - `internal/coordinator/bootstrap_test.go`
  - `internal/coordinator/http_test.go`
  - `internal/coordinator/http_bootstrap_test.go`
  - `internal/coordinator/integration_test.go` — full end-to-end flow
  - `internal/proto/proto_test.go`
  - `internal/certs/certs_test.go`

**Build & quality gates** ([Makefile](https://github.com/emmayusufu/tessera/blob/main/Makefile)):
- `make test` — go test ./...
- `make race` — go test -race ./... (detect data races)
- `make vet` — go vet ./...
- `make fmt` — gofmt + goimports
- `make staticcheck` — staticcheck ./... (lint)
- `make lint` — golangci-lint run

**Pre-commit hooks** ([README](https://github.com/emmayusufu/tessera#pre-commit-hooks)):
- gofmt, go vet, go test
- Custom: no em-dashes in files/messages, no AI/Claude attribution, no work-email leakage

---

## Comparison & Alternatives

### vs. Teleport

**Tessera advantages**:
- "The one thing Tessera gives you that Teleport gates behind its paid Enterprise tier is the request and human-approve, just-in-time access flow." ([README](https://github.com/emmayusufu/tessera#how-it-compares))
- No cluster or SSO required
- MIT license (vs. AGPL for Community Edition)
- Minimal binary footprint (static 18 MB container)

**Teleport advantages** (Community Edition):
- SSH, Kubernetes, database, RDP, web, SSO
- Session recording (comprehensive)
- RBAC / policy engine
- HA / multi-node cluster
- Auditing, compliance features
- Production-audited

**Recommendation**: Use Teleport if available in your environment; Tessera if you need the approval-first flow, have no cluster infrastructure, or prefer minimal operational footprint.

### vs. SSH with Sudo/Bastion

Tessera advantages:
- Audit trail (every request logged with reason, who, target)
- Time-limited sessions (30-min idle timeout, hard session end)
- Approval required (not permission-based, consent-based)
- No standing credentials (ephemeral certs)

Traditional SSH disadvantages:
- Credentials persist
- No approval flow (SSH key = instant access)
- Audit trail depends on syslog/shell history (fragile)

---

## Quick Start

### Deploy coordinator (Docker)

```bash
docker build -t tessera .
docker compose up -d
curl http://localhost:8080/healthz
```

### Deploy agent (systemd)

```bash
sudo curl -o /usr/local/bin/agent https://github.com/emmayusufu/tessera/releases/download/v0.3.0/agent-linux-amd64
sudo chmod 0755 /usr/local/bin/agent
sudo /usr/local/bin/agent -coordinator coordinator.example.org:8443 -share-id my-host -allow localhost:22
```

### Request access (guest)

```bash
tessera -coordinator coordinator.example.org:8443 \
  -share-id my-host \
  -target localhost:22 \
  -reason "emergency debug" \
  -local-listen 127.0.0.1:2222

# [at host terminal: approve]
# Guest can now: ssh -p 2222 user@127.0.0.1
```

---

## Integration Opportunities

1. **Centralized audit aggregation**: Extend audit.Log to ship events to CloudWatch, Datadog, or Splunk
2. **Policy engine**: Replace binary approval with policy check (e.g., "grant if time < 17:00 and reason contains 'incident'")
3. **Cert management**: Integrate with cert-manager or Vault for automated mTLS renewal
4. **Session playback**: Record TCP sessions in shell mode format (asciinema) for forensics
5. **CLI integrations**: Git hook to require reason before sensitive operations
6. **OpenTelemetry**: Instrument coordinator with OTEL for metrics/traces

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Trigger.dev](../agent-infrastructure/trigger-dev.md) | agent-infrastructure | durable checkpoint-resume execution and human-in-the-loop waitpoints for approval workflows |
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent workspace manager using tmux transport for parallel agent coordination via broker pattern |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent workflows with state machine transitions and routing logic for approval decisions |
| [Fly.io](../agent-infrastructure/fly-io.md) | agent-infrastructure | cloud platform with Firecracker VM isolation and programmatic orchestration for agent infrastructure |
| [OpenBao](../llm-infrastructure/openbao.md) | llm-infrastructure | identity-based secrets engine and auth methods applicable to mTLS certificate and approval flow architecture |
| [Beads](../task-management/beads.md) | task-management | Dolt-powered version-controlled issue tracker with append-only audit logging for compliance |
| [Shpool](../developer-tools/shpool.md) | developer-tools | shell session pool daemon with raw PTY passthrough and reattach replay (analogous to Tessera's PTY shell mode) |

---

## Source Materials

- **Repository**: <https://github.com/emmayusufu/tessera>
  - README.md (all sections cited)
  - Source: internal/coordinator/, internal/agent/, internal/client/, internal/proto/, internal/audit/, internal/certs/
  - Build: Makefile, go.mod, .github/workflows/release.yml
  - Deployment: deploy/DEPLOYING.md, deploy/tessera-coordinator.service

**Verification date**: 2026-06-18
**Access method**: Git shallow clone (`--depth 1`, commit 36678fda4a537ee101dedbb5a8a023b27b31069d)

