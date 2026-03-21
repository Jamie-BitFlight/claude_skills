# Zeroboot

**Research Date**: 2026-03-21
**Last Verified**: 2026-03-21
**Category**: agent-infrastructure
**Source**: <https://github.com/zeroboot-dev/zeroboot>
**Next Review**: 2026-06-21

## Overview

Zeroboot is a sub-millisecond VM sandbox engine for AI agents using copy-on-write (CoW) forking via Firecracker and KVM. It achieves 0.79ms median spawn latency with only ~265KB memory per fork, compared to competitors' 27–300ms latencies and 50–128MB memory overhead. Each sandbox is a real KVM virtual machine with hardware-enforced memory isolation, not containers or namespaces.

**Primary use case**: Enabling AI agents (Claude Code, LLM-based systems) to execute untrusted code (Python, Node.js) in isolated, fast-forking environments.

**Status**: Working prototype. The fork primitive and benchmarks are real; API and SDKs functional but not yet production-hardened (as of 2026-03-21).

## Problem Addressed

Executing untrusted code from AI agents requires:
- **Isolation**: Memory and system state must be separate per execution
- **Speed**: Agent workflows need sub-second latency for code execution
- **Efficiency**: Managing many concurrent agent runs without consuming 50–128MB per instance

Traditional approaches (containers, language VMs) trade off isolation for speed or isolation for efficiency. Zeroboot uses hardware-enforced VM isolation with copy-on-write memory mapping to achieve both sub-millisecond fork latency and minimal memory overhead (~265KB).

## Key Statistics

- **Repository**: <https://github.com/zerobootdev/zeroboot>
- **Language**: Rust (2021 edition)
- **Version**: 0.1.0 (as of 2026-03-19)
- **License**: Apache-2.0
- **GitHub Stars**: 1,394 (as of 2026-03-21)
- **GitHub Forks**: 61
- **Created**: 2026-03-15
- **Last Updated**: 2026-03-21
- **Latest Release**: None published (development branch only)

## Key Features

### Benchmark Performance

Zeroboot's fork latency and memory efficiency substantially outperform competing sandbox solutions:

| Metric | Zeroboot | E2B | microsandbox | Daytona |
|---|---|---|---|---|
| **Spawn latency p50** | 0.79ms | ~150ms | ~200ms | ~27ms |
| **Spawn latency p99** | 1.74ms | ~300ms | ~400ms | ~90ms |
| **Memory per sandbox** | ~265KB | ~128MB | ~50MB | ~50MB |
| **Fork + exec (Python)** | ~8ms | — | — | — |
| **1000 concurrent forks** | 815ms | — | — | — |

SOURCE: README.md, Benchmarks section (accessed 2026-03-21)

### API Surface

**Four REST endpoints** (via axum/tokio):

1. **POST /v1/exec** — Execute code in a freshly forked VM
   - Parameters: `code` (required), `language` (optional: python/node/javascript, default python), `timeout_seconds` (optional, default 30)
   - Response: `id`, `stdout`, `stderr`, `exit_code`, `fork_time_ms`, `exec_time_ms`, `total_time_ms`

2. **POST /v1/exec/batch** — Execute multiple code snippets in parallel, each in its own fork
   - Parameters: array of `executions` (each with code and language)
   - Response: array of results matching single-exec response shape

3. **GET /v1/health** — Template readiness and status
   - Response: template availability per language (python, node) with memory allocation

4. **GET /v1/metrics** — Prometheus-format metrics (fork time histograms, exec time histograms, request counts, error rates)

**Authentication**: Bearer token via `Authorization` header. Keys stored in `api_keys.json`. Rate limit: **100 req/s per key** (HTTP 429 when exceeded). Invalid/missing keys return HTTP 401.

SOURCE: API.md (accessed 2026-03-21)

### Language Support

- **Python** — with pre-loaded modules (numpy, pandas supported)
- **Node.js / JavaScript** — via Node.js runtime
- Extension mechanism: Template-based runtime pre-loading via Firecracker snapshots

SOURCE: README.md SDK section, API.md language field (accessed 2026-03-21)

### SDKs

**Python SDK** (zero external dependencies — stdlib urllib only):

```python
from zeroboot import Sandbox

sb = Sandbox("zb_live_your_api_key")
result = sb.run("import numpy; print(numpy.random.rand(3))")
print(result.stdout)  # [0.123 0.456 0.789]
print(result.fork_time_ms)  # ~0.75
```

**TypeScript SDK** (zero external dependencies — uses fetch):

```typescript
import { Sandbox } from "@zeroboot/sdk";
const result = await new Sandbox("zb_live_your_key").run("console.log(1+1)");
```

Both SDKs support `run_batch()` for parallel execution.

SOURCE: README.md SDK sections, sdk/python/README.md, sdk/node/README.md (accessed 2026-03-21)

## Technical Architecture

### Fork Mechanism (0.79ms latency)

Zeroboot uses a three-phase model:

**Phase 1: Template Creation (one-time, ~15 seconds)**
- Firecracker boots a KVM VM with the target runtime pre-loaded (Python + numpy/pandas, Node.js, etc.)
- Guest init scripts pre-load modules and configure the runtime
- VM memory and CPU state are fully snapshotted to disk (vmstate + memory dump)
- Snapshot is immutable and reused for all subsequent forks

**Phase 2: Fork (~0.8ms)**
- Fork Engine (kvm.rs) creates a new KVM VM using `KVM_CREATE_VM` + `KVM_CREATE_IRQCHIP` + `KVM_CREATE_PIT2`
- Restores IOAPIC redirect table from snapshot (do NOT zero-init; read first, patch, write back)
- Memory snapshot file is mmap'd with `MAP_PRIVATE` flag, giving copy-on-write semantics:
  - Read operations hit the shared snapshot (no copy)
  - Write operations trigger page faults → kernel allocates a private page for that fork
  - Each fork's actual RSS is ~265KB (only modified pages), not the full snapshot
- CPU state restored in strict order: `sregs` → `XCRS` → `XSAVE` → `regs` → `LAPIC` → `MSRs` → `MP_STATE`
- Serial I/O enabled via 16550 UART emulation for guest communication

**Phase 3: Isolation**
- Each fork is a separate KVM VM with hardware-enforced memory isolation via Intel VT-x / AMD-V
- Writes trigger CoW page faults; forks cannot read each other's data
- Isolation is enforced by hardware, not containers or OS namespaces

### Component Modules (Rust)

| Module | Purpose |
|---|---|
| `vmm::kvm.rs` | Fork engine: KVM VM creation, CoW mmap setup, CPU state restoration |
| `vmm::vmstate.rs` | Firecracker vmstate binary parser; auto-detects field offsets (no hardcoding) |
| `vmm::firecracker.rs` | Template creation via Firecracker HTTP API |
| `vmm::serial.rs` | 16550 UART emulation for guest-to-host I/O |
| `api::handlers.rs` | HTTP API handlers: /exec, /exec/batch, /health, /metrics; auth, rate-limiting |
| `main.rs` | CLI: template creation, test-exec, bench, serve |

**Key dependencies**:
- `kvm-ioctls` 0.19 — KVM ioctl bindings
- `axum` 0.8, `tokio` 1.x — async HTTP server (full features)
- `serde`, `serde_json` — serialization
- `nix` 0.29 — OS syscalls (mmap, ioctl, fs)
- `libc` 0.2 — C FFI for low-level operations
- `uuid` 1.x (v7) — execution ID generation

SOURCE: Cargo.toml, ARCHITECTURE.md (accessed 2026-03-21)

### Key Implementation Details

**Vmstate Parsing**: Firecracker's binary vmstate format uses variable-length versionize sections with offsets that shift between Firecracker versions and rootfs variants. The parser auto-detects field locations by anchoring on the IOAPIC base address (`0xFEC00000`) instead of hardcoding offsets.

**Entropy Seeding**: `getrandom()` blocks in Firecracker VMs until the CRNG is initialized. Guest init scripts must seed entropy via the `RNDADDENTROPY` ioctl and pass `random.trust_cpu=on` as a kernel boot argument.

**SIMD Dispatch**: Firecracker's CPUID filtering confuses numpy's runtime CPU feature detection, causing SIGILL crashes. Templates set `NPY_DISABLE_CPU_FEATURES` before importing numpy.

**IOAPIC Restoration**: Must use `KVM_GET_IRQCHIP` first to read existing state, then patch redirect table entries from snapshot, then `KVM_SET_IRQCHIP`. Zero-initializing the irqchip struct corrupts other state and breaks interrupt routing.

SOURCE: ARCHITECTURE.md, Implementation Details section (accessed 2026-03-21)

## Installation & Usage

### Managed API (Easiest)

Use the hosted service at <https://api.zeroboot.dev>. Obtain an API key from the Zeroboot dashboard and set it as `ZEROBOOT_API_KEY` in your environment. Example request:

```bash
curl -X POST https://api.zeroboot.dev/v1/exec \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${ZEROBOOT_API_KEY}" \
  -d '{"code":"import numpy as np; print(np.random.rand(3))"}'
```

Response:

```json
{
  "id": "019cf684-1fd5-73c0-9299-52253f9aa79c",
  "stdout": "[0.123 0.456 0.789]\n",
  "stderr": "",
  "exit_code": 0,
  "fork_time_ms": 0.75,
  "exec_time_ms": 7.2,
  "total_time_ms": 8.0
}
```

Managed service signup: <https://tally.so/r/aQGkpb> (early access, teams who don't want to self-host).

SOURCE: README.md, API.md (accessed 2026-03-21)

### Self-Hosting

**Requirements**: Linux host with KVM support (Intel VT-x or AMD-V).

**Deployment artifacts** in `deploy/`:
- systemd service file for process management
- fleet deployment script for multi-node setups

**API keys** configured via `api_keys.json` or `ZEROBOOT_API_KEYS_FILE` environment variable:

```json
["zb_live_key1", "zb_live_key2"]
```

**CLI commands** (from `src/main.rs`):
- `zeroboot template <runtime>` — Create a new snapshot
- `zeroboot test-exec <code>` — Test code execution
- `zeroboot bench` — Run benchmark suite
- `zeroboot serve --port 8080` — Start HTTP API server

SOURCE: README.md, ARCHITECTURE.md, docs/DEPLOYMENT.md (accessed 2026-03-21)

### Python SDK Example

```python
import sys
sys.path.insert(0, "sdk/python")

from zeroboot import Sandbox

sb = Sandbox("zb_live_your_api_key")

# Single execution
result = sb.run("import numpy; print(numpy.random.rand(3))")
print(result.stdout)        # [0.123 0.456 0.789]
print(result.fork_time_ms)  # ~0.75

# Batch execution (parallel)
results = sb.run_batch([
    "print(1 + 1)",
    "print(2 * 3)",
    "import math; print(math.pi)",
], language="python")

for r in results:
    print(r.stdout)
```

SOURCE: sdk/python/README.md (accessed 2026-03-21)

## Limitations and Caveats

1. **CSPRNG State Sharing**: Forks share the CSPRNG state from the snapshot. Kernel entropy is reseeded via `RNDADDENTROPY`, but userspace PRNGs (numpy.random, OpenSSL) require explicit reseeding per fork to avoid repeating random sequences. Refer to [Firecracker's guidance](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/random-for-clones.md).

2. **Single vCPU**: Each fork has a single vCPU. Multi-vCPU support is architecturally feasible but not yet implemented.

3. **No Networking**: Network I/O is not available inside forks. Sandboxes communicate with the host and each other only via serial I/O (stdout/stderr).

4. **Template Updates**: Updating a template requires a full re-snapshot (~15 seconds). No incremental patching mechanism exists.

5. **Rate Limiting**: Managed API enforces 100 req/s per API key (returns HTTP 429 if exceeded).

6. **Production Readiness**: The fork primitive and benchmarks are validated; the API and SDKs are functional but not production-hardened (as stated in project status).

SOURCE: README.md Known limitations section, API.md rate-limit documentation (accessed 2026-03-21)

## Relevance to Claude Code Development

### Direct Applicability

Zeroboot directly addresses the execution sandbox requirement for Claude Code's agent system:

1. **Sub-millisecond Isolation**: Agent workflows execute untrusted code (user-written tools, scripts, dynamic LLM-generated code) in isolated VMs. Zeroboot's 0.79ms fork latency enables many serial code executions within a single agent task without noticeable delay (e.g., 100 forks = ~80ms overhead).

2. **Managed and Self-Hosted Options**: Claude Code can use the hosted API (<https://api.zeroboot.dev>) for rapid prototyping or self-host for private deployments with custom runtimes (custom Python packages, proprietary Node.js modules).

3. **Language Diversity**: Supports Python (with numpy/pandas) and Node.js, matching the polyglot nature of agent tasks.

4. **Zero-Dependency SDKs**: Python SDK uses only stdlib, reducing Claude Code's dependency footprint.

5. **Real Hardware Isolation**: Unlike containers, each fork is a KVM VM with hardware-enforced isolation, suitable for untrusted code from LLM outputs.

### Use Cases

- **Code Execution Backend**: Replace or augment E2B sandboxes for agent code execution
- **Tool Testing**: Agents can test tools in isolated VMs before deploying them
- **Prompt Evaluation**: Run LLM-generated code safely for grading or verification
- **Parallel Agent Tasks**: Run 1000+ concurrent forks efficiently (~815ms for 1000 parallel executions)

### Integration Considerations

- **Managed API**: Zero infrastructure overhead; suitable for cloud deployments
- **Self-Hosting**: Requires Linux with KVM; suitable for on-premises or private cloud
- **Template Customization**: Pre-load Claude-specific libraries (claude-sdk, anthropic, etc.) into templates for faster cold starts
- **Entropy Handling**: Agent code generators must be aware of CSPRNG reseeding requirements (e.g., add `numpy.random.seed()` to generated code)

## References

- **Repository**: <https://github.com/zerobootdev/zeroboot> (accessed 2026-03-21)
- **API Documentation**: <https://github.com/zerobootdev/zeroboot/blob/main/docs/API.md> (accessed 2026-03-21)
- **Architecture Documentation**: <https://github.com/zerobootdev/zeroboot/blob/main/docs/ARCHITECTURE.md> (accessed 2026-03-21)
- **Deployment Guide**: <https://github.com/zerobootdev/zeroboot/blob/main/docs/DEPLOYMENT.md> (accessed 2026-03-21)
- **Python SDK**: <https://github.com/zerobootdev/zeroboot/tree/main/sdk/python> (accessed 2026-03-21)
- **TypeScript SDK**: <https://github.com/zerobootdev/zeroboot/tree/main/sdk/node> (accessed 2026-03-21)
- **Managed API**: <https://api.zeroboot.dev/v1/health> (accessed 2026-03-21)
- **Early Access Signup**: <https://tally.so/r/aQGkpb> (accessed 2026-03-21)
- **Firecracker Random Guidance**: <https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/random-for-clones.md>

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Fly.io](./fly-io.md) | agent-infrastructure | Uses Firecracker microVMs like zeroboot; Sprites product provides persistent agent sandboxes with checkpoint/restore; both optimize for sub-second startup and hardware isolation |
| [Kernel (kernel-sh)](./kernel-sh.md) | agent-infrastructure | Browser-as-a-service with VM-per-instance isolation; complements zeroboot by handling web automation while zeroboot handles untrusted code execution |
| [TinyFish](./tinyfish.md) | agent-infrastructure | Serverless web agent platform; agent execution workload that could use zeroboot as backend for isolated code execution within web automation workflows |
| [PinchTab](./pinchtab.md) | agent-infrastructure | Browser control infrastructure for agents; shares agent infrastructure pattern with zeroboot for providing isolated execution to agent workflows |
| [OpenHands](../coding-agents/openhands.md) | coding-agents | Open-source agent platform with sandboxed execution environment; zeroboot provides alternative ultra-low-latency sandbox backend for agent code execution |
| [OpenAI Codex CLI](../coding-agents/openai-codex-cli.md) | coding-agents | Terminal coding agent with OS-enforced sandbox isolation; zeroboot provides similar untrusted code execution guarantees via KVM-based VMs |
| [OpenFang](../agent-frameworks/openfang.md) | agent-frameworks | Agent OS with WASM sandbox for tool execution; both zeroboot and OpenFang address agent security boundaries—zeroboot via hardware VMs, OpenFang via WASM metering |
| [Micro-Agent](../agent-frameworks/micro-agent.md) | agent-frameworks | ReAct agent framework with Docker container sandbox for shell execution; zeroboot offers lighter-weight alternative with 0.79ms fork latency vs. container startup |

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---|---|---|---|
| Identity/Metadata | high | 2026-03-21 | Repository metadata current as of commit date; version from Cargo.toml |
| Key Statistics | high | 2026-03-21 | GitHub API data current; star count and fork count reflect live counts |
| Benchmarks | high | 2026-03-21 | Extracted verbatim from README; benchmarks marked as real but validation timing unknown |
| Key Features | high | 2026-03-21 | API endpoints documented and verified against live health endpoint example |
| Technical Architecture | high | 2026-03-21 | Architecture documented in official ARCHITECTURE.md with implementation details; derived from source module names verified via Glob |
| Installation & Usage | high | 2026-03-21 | Examples extracted from official READMEs and API docs; managed API example uses demo key |
| Limitations | high | 2026-03-21 | Extracted directly from README Known limitations section |
| Relevance to Claude Code | medium | 2026-03-21 | Derived from feature analysis and stated problem domain; use cases inferred from architecture |
| Cross-References | high | 2026-03-21 | Matched against 162+ entries in research/README.md index; scored by category overlap, shared technology stack, and problem domain alignment |

**Next Review Date**: 2026-06-21 (3 months)

**Review Triggers**:
- Major version release (currently 0.1.0 prerelease)
- Production release announcement
- API breaking changes
- New SDK releases
- Significant performance changes in benchmarks
