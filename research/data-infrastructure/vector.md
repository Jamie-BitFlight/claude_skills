---
name: vector
title: Vector
subtitle: High-performance observability data pipeline for logs, metrics, and traces
research_date: 2026-10-02
source_url: https://github.com/vectordotdev/vector
github_repository: https://github.com/vectordotdev/vector
version_at_research: v0.58.0
license: MPL-2.0
freshness_tracking:
  last_verified: 2026-10-03
  version_at_verification: v0.58.0
  next_review: 2027-01-03
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: medium (doc + code-read) | Installation & Usage: medium | Limitations and Caveats: medium"
---

# Vector

## Overview

Vector is an observability data pipeline written in Rust. The README describes it as "a high-performance, end-to-end (agent & aggregator) observability data pipeline that puts you in control of your observability data," used to collect, transform, and route logs and metrics to any vendor. The README states that it is "open source and up to 10x faster than every alternative in the space" (a vendor claim; the README gives no benchmark method in that sentence). It is maintained by Datadog's Community Open Source Engineering team (Source: `README.md`, tag v0.58.0).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| High observability costs and vendor lock-in | The README states "Vector enables dramatic cost reduction, novel data enrichment, and data security where you need it, not where it is most convenient for your vendors" (vendor claim, no figure given). Its listed use cases include "Reduce total observability costs" and "Transition vendors without disrupting workflows" |
| Multiple monitoring tools and agent fatigue | One tool deployed as an agent or an aggregator; listed use case "Consolidate agents and eliminate agent fatigue". README: "Logs, metrics (beta), and traces (coming soon). One tool for all of your data." |
| Data quality and visibility gaps | Listed use case "Enhance data quality and improve insights"; transforms (filter, remap, route, enrichment) run inside the pipeline |
| Performance and reliability of existing pipelines | README principle: "Built in Rust, Vector's primary design goal is reliability." README states "Vector's largest user processes over 500TB daily" (vendor-reported, community section) |

---

## Key Features

### Core Capabilities

- **Reliable**: README: "Built in Rust, Vector's primary design goal is reliability." The README states the goal and names no mechanism in that sentence. Mechanisms documented elsewhere are the configurable buffers with backpressure (see Backpressure and buffering below) and end-to-end acknowledgements (see Delivery guarantees below)
- **End-to-end**: README: "Deploys as an agent or aggregator. Vector is a complete platform."
- **Unified data model**: Source type `Event` has three variants, `Log`, `Metric` and `Trace` (Source: `lib/vector-core/src/event/mod.rs:53` — enum Event). The README rates metrics "beta" and traces "coming soon".
- **Open source**: Mozilla Public License 2.0 (Source: `LICENSE`, `Cargo.toml` — `license = "MPL-2.0"`).

### Data Collection and Routing

- **Multiple sources**: `src/sources/` contains, among others, `file.rs`, `http_server.rs`, `kafka.rs`, `syslog.rs`, `journald.rs`, `postgresql_metrics.rs`, `amqp.rs`, `gcp_pubsub.rs`, `pulsar.rs` and `logstash.rs`
- **Transforms**: `src/transforms/` contains `filter.rs`, `remap.rs` (programmable transformation), `route.rs`, `log_to_metric.rs`, `metric_to_log.rs`, `trace_to_log.rs`, `aws_ec2_metadata.rs`, plus directories such as `reduce`, `sample`, `dedupe` and `throttle`
- **Sinks**: `src/sinks/` contains, among others, `aws_s3`, `aws_cloudwatch_logs`, `elasticsearch`, `clickhouse`, `postgres`, `kafka`, `loki`, `splunk_hec`, `http`, `mezmo.rs` and `papertrail.rs`. The `webhdfs` sink is the one that pulls in the OpenDAL crate (Source: `Cargo.toml` — `sinks-webhdfs = ["dep:opendal"]`)

### Performance and Reliability

- **Delivery guarantees**: listed as a supported property in the README comparison table (row "Delivery guarantees"). Guarantee: "The **at-least-once** delivery guarantee ensures that an [event] received by a Vector component is ultimately delivered at least once" (Source: `website/content/en/docs/architecture/guarantees.md:53-54`). Mechanism: end-to-end acknowledgements, in which a source creates a batch notifier for events, one half stays with the source and the other is attached to the events, and "Vector captures the status of the response from the downstream service and uses it to update the batch notifier" (Source: `website/content/en/docs/architecture/end-to-end-acknowledgements.md:12-17`). A source connected to a sink with `acknowledgements` enabled waits for all connected sinks to mark the event delivered "or to persist the events to a disk buffer, if configured on the sink, before acknowledging receipt" (Source: `website/content/en/docs/architecture/guarantees.md:24-28`). A sink without acknowledgement support marks events delivered "when they are handed off to the sink component, before any deliveries are attempted" (Source: `website/content/en/docs/architecture/guarantees.md:39-41`)
- **Backpressure and buffering**: "Buffers are a configurable mechanism for dealing with backpressure ... choosing between memory and disk for where to store the buffered events, setting a maximum size, and deciding what should happen when the buffer is full (backpressure or load shedding)" (Source: `docs/ARCHITECTURE.md`)
- **Static binary**: "Vector compiles to a single static binary" (Source: `website/content/en/docs/setup/installation/_index.md`); "On *nix systems Vector's only dependency is libc" for the default builds, and musl builds are fully static (see Limitations and Caveats)

---

## Technical Architecture

Per the architecture document, "Vector runs a configuration consisting of a directed, acyclic graph of sources, transforms, and sinks" (Source: `docs/ARCHITECTURE.md`). Sources, transforms and sinks are each configured through a `SourceConfig`, `TransformConfig` or `SinkConfig` trait with a `build` method; "This building occurs largely in the `src/topology/builder.rs` file".

**Component counts at v0.58.0**: entries in `src/sources/` 46, `src/sinks/` 54, `src/transforms/` 19, counted with `ls | wc -l` (files and directories, including `mod.rs`/helper modules, so not a count of component types). The documentation sources reviewed state no component count: Not mentioned in documentation.

**Topology**: `src/topology/mod.rs` opens with "Topology contains all topology based types ... the ability to start, stop and reload a config." `TopologyPieces` (Source: `src/topology/builder.rs:1111`) holds built components; `RunningTopology` (Source: `src/topology/running.rs:56`) runs them and exposes `reload_config_and_respawn` (Source: `src/topology/running.rs:295`). Config reloads compute a `ConfigDiff` (Source: `src/config/diff.rs:9` — struct ConfigDiff, fields `sources`, `transforms`, `sinks`, `enrichment_tables`, `components_to_reload`), used in `src/topology/running.rs:315`.

**Events and buffers**: events move through buffers typed on `EventArray` — `type BuiltBuffer = (BufferSender<EventArray>, Arc<Mutex<Option<BufferReceiverStream<EventArray>>>>)` (Source: `src/topology/mod.rs:45-48`). `EventArray` is defined at `lib/vector-core/src/event/array.rs:137`, `BufferSender` at `lib/vector-buffers/src/topology/channel/sender.rs:220`, `BufferReceiverStream` at `lib/vector-buffers/src/topology/channel/receiver.rs:167`.

**Task model**: `type TaskHandle = tokio::task::JoinHandle<TaskResult>;` (Source: `src/topology/mod.rs:43`). The architecture document says "the final step is the spawn the actual tasks for each component", and `src/topology/running.rs` has `spawn_source` (line 1303), `spawn_transform` (line 1262) and `spawn_sink` (line 1221). For a source, "the result is mainly two tasks: the 'server' task of the source itself, and a 'pump' task that forwards its output on to the rest of the system" (Source: `docs/ARCHITECTURE.md`).

---

## Installation & Usage

### Installation

```bash
# Installation script (detects platform; documented in the quickstart)
curl --proto '=https' --tlsv1.2 -sSfL https://sh.vector.dev | bash

# From source (rust-toolchain.toml pins channel 1.95; Cargo.toml has rust-version = "1.95")
git clone https://github.com/vectordotdev/vector.git
cd vector
cargo build --release
```

The installation script command is quoted from `website/content/en/docs/setup/quickstart.md`. The source-build prerequisites list in `docs/DEVELOPING.md` is longer than a Rust toolchain: "Have working Rustup, Protobuf tools, C++/C build tools (LLVM, GCC, or MSVC), Python, and Perl, `make` ... `cmake`, `GNU coreutils`, and `autotools`." Kubernetes installation steps: Not mentioned in the sources reviewed for this entry.

### Basic Configuration Example

Field names below were checked against the v0.58.0 config structs (`include` in `src/sources/file.rs:67`, tagged `mode` in `src/sources/syslog.rs:77`, `endpoints` in `src/sinks/elasticsearch/config.rs:102`, `bucket` and `key_prefix` in `src/sinks/aws_s3/config.rs`). The example has not been executed, and required options not shown (for example sink `encoding`, S3 `region`) were not checked. YAML, TOML and JSON config formats: Not mentioned in the sources reviewed for this entry.

```yaml
sources:
  syslog_input:
    type: syslog
    mode: tcp
    address: "0.0.0.0:514"

  file_input:
    type: file
    include:
      - "/var/log/app.log"

transforms:
  filter_errors:
    type: filter
    inputs:
      - syslog_input
      - file_input
    condition: |
      .severity == "error" || .level == "ERROR"

sinks:
  elasticsearch:
    type: elasticsearch
    inputs:
      - filter_errors
    endpoints:
      - "https://elasticsearch.example.com"
    mode: bulk

  s3_archive:
    type: aws_s3
    inputs:
      - syslog_input
    bucket: "log-archive"
    key_prefix: "logs/"
```

### Running Vector

`src/cli.rs` defines `Validate(validate::Opts)` and `Test(unit_test::Opts)` subcommands.

```bash
vector validate /etc/vector/vector.yaml
vector --config /etc/vector/vector.yaml
vector test /etc/vector/vector.yaml
```

---

## Limitations and Caveats

- **Traces are not released**: the README principle line reads "Logs, metrics (beta), and traces (coming soon)", and the README comparison table marks traces with a construction symbol for Vector (Source: `README.md`, tag v0.58.0).
- **musl builds perform worse**: "Please note that musl, as of this writing, has a significantly worse performance profile than glibc when Vector is running in multiple threads (Vector defaults to the number of available cores). We recommend that you use glibc when available unless you're running Vector on a single CPU." (Source: `website/content/en/docs/setup/installation/_index.md`)
- **Source builds need more than Rust**: see the prerequisites quoted under Installation (Source: `docs/DEVELOPING.md`).
- **Performance and cost figures are vendor claims**: the "up to 10x faster" and "dramatic cost reduction" statements are README text with no methodology in the quoted sentence; no independent benchmark was reviewed.
- **Other limitations** (resource usage, scaling limits, unsupported platforms): Not mentioned in documentation reviewed for this entry. Confidence: low for completeness.

---

## References

- [Vector GitHub Repository](https://github.com/vectordotdev/vector) (accessed 2026-10-03; README, docs and source read from tag v0.58.0)
- [Vector Documentation Home](https://vector.dev/docs/) (accessed 2026-10-02)
- [Vector Installation Guide](https://vector.dev/docs/setup/installation/) (accessed 2026-10-02)
- [Vector Architecture Documentation](https://vector.dev/docs/architecture/) (accessed 2026-10-02)
- Vector source code at tag v0.58.0: `src/topology/mod.rs`, `src/topology/running.rs`, `src/topology/builder.rs`, `src/config/diff.rs`, `src/sources/`, `src/sinks/`, `src/transforms/`, `docs/ARCHITECTURE.md` (accessed 2026-10-03)
- Vector Cargo.toml at tag v0.58.0: version 0.58.0, license MPL-2.0 (accessed 2026-10-03). The default branch `Cargo.toml` shows 0.59.0-dev, which is the next development version on master; this entry's `version_at_research` is the v0.58.0 release tag, so the two differ by design.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Chroma](./chroma.md) | data-infrastructure | Complementary vector database layer for storing and indexing observability data |
| [CocoIndex](./cocoindex.md) | data-infrastructure | Shares Rust-based real-time data transformation architecture and incremental processing patterns |
| [Honker](./honker.md) | data-infrastructure | Alternative SQLite-native event stream and pub/sub infrastructure for observability pipelines |
| [Tinybird](./tinybird.md) | data-infrastructure | Native ClickHouse analytics platform; Vector sinks directly to ClickHouse backends for real-time analytics |
| [MotherDuck](./motherduck.md) | data-infrastructure | Serverless analytics destination for vector-collected observability data via DuckDB |
| [Logfire](../ai-observability/logfire.md) | ai-observability | Complementary full-stack LLM observability platform for analyzing telemetry data collected by Vector |
