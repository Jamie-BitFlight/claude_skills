# Ray

| Field         | Value                                                              |
| ------------- | ------------------------------------------------------------------ |
| Research Date | 2026-02-05                                                         |
| Primary URL   | <https://docs.ray.io/en/latest/>                                   |
| GitHub        | <https://github.com/ray-project/ray>                               |
| PyPI          | <https://pypi.org/project/ray/>                                    |
| Version       | ray-2.53.0 (released 2025-12-20)                                   |
| License       | Apache-2.0                                                         |
| Discord/Slack | <https://www.ray.io/join-slack>                                    |
| Forum         | <https://discuss.ray.io/>                                          |
| Managed       | <https://www.anyscale.com/> (Anyscale - commercial Ray platform)   |

---

## Overview

Ray is an AI compute engine for scaling Python and AI applications from a laptop to a cluster. The framework consists of a core distributed runtime and a set of AI libraries (Ray Data, Ray Train, Ray Tune, Ray Serve, RLlib) for accelerating ML workloads. Ray provides unified infrastructure for data preprocessing, distributed training, hyperparameter tuning, model serving, and reinforcement learning, with native support for LLM inference and MCP server deployment.

---

## Problem Addressed

| Problem                                              | Solution                                                                      |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- |
| Single-node environments cannot scale ML workloads   | Seamlessly scale Python code from laptop to cluster with minimal changes      |
| Different tools for training, serving, tuning        | Unified framework: Train, Serve, Tune, Data libraries share common runtime    |
| LLM serving requires specialized infrastructure      | Ray Serve LLM with vLLM integration for high-throughput inference             |
| ML data pipelines are complex to parallelize         | Ray Data provides streaming, distributed data processing with PyTorch/NumPy   |
| Hyperparameter tuning is compute-intensive           | Ray Tune scales experiments across cluster with state-of-the-art algorithms   |
| MCP servers need scalable HTTP deployment            | Native MCP server deployment with Ray Serve (Streamable HTTP, STDIO modes)    |
| Distributed computing requires complex orchestration | Ray Core provides Tasks (stateless), Actors (stateful), Objects abstractions  |
| GPU resource management across jobs                  | Built-in GPU scheduling, placement groups, and autoscaling                    |
| Fault tolerance in distributed systems               | Automatic task/actor fault tolerance with lineage-based reconstruction        |

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 41,140                    | 2026-02-05    |
| GitHub Forks      | 7,184                     | 2026-02-05    |
| Open Issues       | 3,351                     | 2026-02-05    |
| Contributors      | 408+                      | 2026-02-05    |
| PyPI Monthly DL   | 43,801,701                | 2026-02-05    |
| PyPI Weekly DL    | 7,585,297                 | 2026-02-05    |
| Primary Language  | Python, C++               | 2026-02-05    |
| Repository Age    | Since October 2016        | 2026-02-05    |

---

## Key Features

### Ray Core (Distributed Runtime)

- **Tasks**: Stateless functions executed remotely in the cluster
- **Actors**: Stateful worker processes with persistent state across calls
- **Objects**: Immutable values accessible across the cluster via ObjectRefs
- **Placement Groups**: Co-locate tasks and actors for performance optimization
- **Runtime Environments**: Package dependencies with tasks/actors (pip, conda, containers)
- **Ray Compiled Graph (beta)**: Optimize DAGs for low-latency multi-GPU workloads

### Ray Data (Scalable Data Processing)

- **Streaming Execution**: Process larger-than-memory datasets
- **Native ML Integration**: First-class support for PyTorch, TensorFlow, NumPy tensors
- **LLM Support**: Built-in APIs for working with LLMs and text data
- **Batch Inference**: Scale offline inference across cluster
- **Data Sources**: Parquet, JSON, CSV, images, cloud storage (S3, GCS, Azure)

### Ray Train (Distributed Training)

- **Framework Support**: PyTorch, PyTorch Lightning, Hugging Face Transformers, XGBoost, JAX, TensorFlow
- **DeepSpeed Integration**: For large model training
- **Checkpointing**: Automatic checkpoint saving and loading
- **Fault Tolerance**: Resume from checkpoint on node failures
- **Mixed Precision**: Native support for FP16/BF16 training

### Ray Tune (Hyperparameter Tuning)

- **Search Algorithms**: Grid, random, Bayesian (Optuna, HyperOpt), evolutionary
- **Schedulers**: ASHA, Population Based Training (PBT), HyperBand
- **Early Stopping**: Terminate unpromising trials automatically
- **Experiment Tracking**: Integration with MLflow, Weights & Biases, TensorBoard
- **Distributed Trials**: Run thousands of trials in parallel

### Ray Serve (Model Serving)

- **LLM Serving**: High-throughput inference with vLLM backend integration
- **MCP Server Deployment**: Native Model Context Protocol support
  - Streamable HTTP mode for real-time interactions
  - STDIO to HTTP conversion for existing MCP servers
  - MCP Gateway for aggregating multiple services
  - Multi-service deployment patterns
- **Composition**: Chain multiple models and business logic
- **Autoscaling**: Scale replicas based on request load
- **Batching**: Dynamic request batching for throughput
- **FastAPI Integration**: Native decorator-based API definition

### Ray RLlib (Reinforcement Learning)

- **Algorithm Library**: PPO, DQN, SAC, A3C, IMPALA, and more
- **Multi-Agent**: Support for multi-agent environments
- **Offline RL**: Train from logged data without environment
- **Custom Environments**: Gymnasium-compatible interface

### Infrastructure & Operations

- **Kubernetes Native**: KubeRay operator for K8s deployment
- **Cloud Support**: AWS, GCP, Azure with autoscaling
- **Ray Dashboard**: Web UI for monitoring jobs, actors, logs
- **Distributed Debugger**: Debug distributed applications
- **Metrics**: Prometheus/Grafana integration for observability

---

## Technical Architecture

### Stack Components

| Component       | Technology                                                 |
| --------------- | ---------------------------------------------------------- |
| Core Runtime    | C++ (plasma object store, GCS, raylet)                     |
| Python API      | Python 3.9+ with async support                             |
| Serialization   | Apache Arrow, cloudpickle                                  |
| Object Store    | Plasma (shared memory)                                     |
| Scheduler       | Distributed, two-level (global + local)                    |
| Networking      | gRPC between nodes                                         |
| Dashboard       | React-based web UI                                         |

### Architectural Layers

```text
Ray AI Libraries (Data, Train, Tune, Serve, RLlib)
           |
    Ray Core API (Tasks, Actors, Objects)
           |
    Ray Runtime (GCS, Raylet, Object Store)
           |
    Infrastructure (K8s, Cloud, Local)
```

### Key Abstractions

1. **Head Node**: Runs Global Control Store (GCS), driver processes
2. **Worker Nodes**: Run raylets (local scheduler) and worker processes
3. **Object Store**: Shared memory for zero-copy data transfer between tasks
4. **GCS**: Centralized metadata store for actor locations, job info
5. **Raylet**: Per-node resource manager and local scheduler

### MCP Server Architecture (Ray Serve)

```text
Client Request -> Ray Serve Ingress -> Deployment Replicas
                       |
              MCP Protocol Handler
                       |
            Tool Execution (Actors)
                       |
              Response Streaming
```

---

## Installation and Usage

### Installation

```bash
# Basic installation
pip install ray

# With specific components
pip install "ray[default]"     # Ray Core + Dashboard
pip install "ray[data]"        # + Ray Data
pip install "ray[train]"       # + Ray Train
pip install "ray[tune]"        # + Ray Tune
pip install "ray[serve]"       # + Ray Serve
pip install "ray[rllib]"       # + RLlib
pip install "ray[all]"         # All components

# Using uv
uv pip install "ray[serve]"
```

### Ray Core - Basic Task

```python
import ray

ray.init()

@ray.remote
def process_data(x):
    return x * 2

# Execute in parallel
futures = [process_data.remote(i) for i in range(10)]
results = ray.get(futures)
```

### Ray Core - Actor

```python
@ray.remote
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
        return self.value

counter = Counter.remote()
ray.get([counter.increment.remote() for _ in range(10)])
```

### Ray Serve - LLM Deployment

```python
from ray import serve
from ray.serve.llm import LLMConfig, build_openai_app

llm_config = LLMConfig(
    model_loading_config=dict(
        model_id="meta-llama/Llama-2-7b-chat-hf",
    ),
    deployment_config=dict(
        autoscaling_config=dict(
            min_replicas=1,
            max_replicas=4,
        )
    ),
)

app = build_openai_app(llm_config)
serve.run(app)
```

### Ray Serve - MCP Server Deployment

```python
from ray import serve

@serve.deployment
class MCPToolServer:
    async def handle_tool_call(self, tool_name: str, arguments: dict):
        # Tool implementation
        if tool_name == "search":
            return await self.search(arguments["query"])
        return {"error": "Unknown tool"}

# Deploy with autoscaling
serve.run(MCPToolServer.bind())
```

### Ray Data - Batch Processing

```python
import ray

ds = ray.data.read_parquet("s3://bucket/data/")

# Distributed transformations
ds = ds.map(lambda row: {"processed": row["text"].upper()})
ds = ds.filter(lambda row: len(row["processed"]) > 10)

# Write results
ds.write_parquet("s3://bucket/output/")
```

### Ray Train - Distributed Training

```python
from ray.train.torch import TorchTrainer
from ray.train import ScalingConfig

def train_func():
    # Training loop with automatic DDP
    model = ...
    for epoch in range(10):
        train_epoch(model)

trainer = TorchTrainer(
    train_func,
    scaling_config=ScalingConfig(num_workers=4, use_gpu=True),
)
result = trainer.fit()
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **MCP Server Scaling**: Ray Serve provides production-grade infrastructure for deploying MCP servers at scale, with autoscaling, load balancing, and fault tolerance.

2. **Distributed Agent Execution**: Ray Core's Tasks and Actors provide patterns for implementing distributed agent orchestration - stateless tasks for parallel execution, stateful actors for maintaining agent context.

3. **LLM Serving Infrastructure**: Ray Serve LLM with vLLM backend enables self-hosted LLM inference for scenarios requiring local models or custom fine-tuned models.

4. **Batch Processing for RAG**: Ray Data enables scalable document processing pipelines for building RAG knowledge bases - embedding generation, chunking, indexing.

5. **Hyperparameter Optimization**: Ray Tune could optimize skill/prompt configurations through systematic search.

### Patterns Worth Adopting

1. **Task/Actor Separation**: Distinguishing stateless operations (Tasks) from stateful processes (Actors) provides clean abstraction for agent design.

2. **Object Store Pattern**: Ray's plasma object store enables zero-copy data sharing between workers - relevant for large context passing between agents.

3. **Autoscaling Patterns**: Ray Serve's replica autoscaling based on queue depth provides reference for scaling agent deployments.

4. **Fault Tolerance via Lineage**: Ray reconstructs failed objects by re-executing their lineage - applicable to agent checkpoint/recovery patterns.

5. **Composition Patterns**: Ray Serve's deployment composition (model pipelines, business logic chains) informs multi-step agent workflow design.

### Integration Opportunities

1. **MCP Gateway**: Deploy multiple MCP servers behind Ray Serve gateway for unified tool access.

2. **Batch Inference Skills**: Use Ray Data for batch processing in Claude Code skills requiring large-scale data operations.

3. **Distributed Skill Execution**: Ray Core could enable parallel execution of independent skill sub-tasks.

4. **Self-Hosted LLM Fallback**: Ray Serve LLM as fallback for local inference when cloud APIs are unavailable.

5. **Agent State Management**: Ray Actors could maintain persistent agent state across conversations.

### Comparison with Related Tools

| Aspect              | Ray                              | Dask                        | Apache Spark              |
| ------------------- | -------------------------------- | --------------------------- | ------------------------- |
| Primary Focus       | ML/AI workloads                  | General data science        | Big data analytics        |
| Stateful Processing | Native (Actors)                  | Limited                     | Limited                   |
| Model Serving       | Ray Serve (built-in)             | External required           | External required         |
| RL Support          | RLlib (comprehensive)            | None                        | None                      |
| MCP Integration     | Native Ray Serve support         | None                        | None                      |
| GPU Support         | First-class                      | Limited                     | Improving                 |
| Latency             | Low (designed for ML)            | Higher                      | Higher                    |

---

## References

| Source                      | URL                                                                | Accessed   |
| --------------------------- | ------------------------------------------------------------------ | ---------- |
| Official Documentation      | <https://docs.ray.io/en/latest/>                                   | 2026-02-05 |
| GitHub Repository           | <https://github.com/ray-project/ray>                               | 2026-02-05 |
| GitHub README               | <https://github.com/ray-project/ray/blob/master/README.rst>        | 2026-02-05 |
| PyPI Package                | <https://pypi.org/project/ray/>                                    | 2026-02-05 |
| PyPI Stats                  | <https://pypistats.org/packages/ray>                               | 2026-02-05 |
| Ray Architecture Whitepaper | <https://docs.google.com/document/d/1tBw9A4j62ruI5omIJbMxly-la5w4q_TjyJgJL_jN2fI/preview> | 2026-02-05 |
| Ray OSDI Paper              | <https://arxiv.org/abs/1712.05889>                                 | 2026-02-05 |
| Ownership Paper (NSDI'21)   | <https://www.usenix.org/system/files/nsdi21-wang.pdf>              | 2026-02-05 |
| Discussion Forum            | <https://discuss.ray.io/>                                          | 2026-02-05 |
| Anyscale (Managed Ray)      | <https://www.anyscale.com/>                                        | 2026-02-05 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, issues, contributors), PyPI statistics API, and official documentation. Statistics verified via direct API calls on 2026-02-05.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | ray-2.53.0                          |
| Release Date       | 2025-12-20                          |
| GitHub Stars       | 41,140 (as of 2026-02-05)           |
| Monthly Downloads  | 43,801,701 (as of 2026-02-05)       |
| Next Review Date   | 2026-05-05                          |

**Review Triggers**:

- Major version release (ray-3.x)
- Significant MCP integration updates
- New Ray Serve LLM capabilities
- GitHub stars milestone (45K, 50K)
- PyPI downloads milestone (50M monthly)
- Breaking changes to Ray Serve or Ray Core APIs
- New agent/agentic workflow features
