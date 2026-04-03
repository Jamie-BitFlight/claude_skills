---
title: aiomqtt — The idiomatic asyncio MQTT client
resource_name: aiomqtt
package_url: https://pypi.org/project/aiomqtt/
repository_url: https://github.com/sbtinstruments/asyncio-mqtt
documentation_url: https://aiomqtt.bo3hm.com
license: BSD-3-Clause
category: async-libraries
freshness_date: 2026-03-29
next_review: 2026-06-29
---

## Overview

`aiomqtt` (package name `aiomqtt`, distributed on PyPI as `aiomqtt`) is described as "The idiomatic asyncio MQTT client". It is a Python wrapper around the paho-mqtt library that provides an async/await native interface to MQTT protocol operations.

**Identity data extracted from sources**:

- **Version**: 2.5.1 (released 2026-03-05) — extracted from `pyproject.toml` `version = "2.5.1"` and `CHANGELOG.md` "[2.5.1] - 2026-03-05"
- **Python compatibility**: Requires Python 3.8 to <4.0 — extracted from `pyproject.toml` `requires-python = ">=3.8,<4.0"` with explicit classifiers for `Programming Language :: Python :: 3.8` through `3.13`
- **License**: BSD 3-Clause License — extracted from `README.md` section "License" and root file `SPDX-License-Identifier: BSD-3-Clause`
- **Primary dependency**: paho-mqtt — extracted from `pyproject.toml` `dependencies = ["paho-mqtt>=2.1.0,<3.0.0", ...]` and README "The only dependency is paho-mqtt"
- **Authors**: Frederik Aalund, Felix Böhm, Jonathan Plasse — extracted from `pyproject.toml` authors list

## Problem Addressed

The MQTT protocol traditionally requires callback-based programming when using the paho-mqtt library. aiomqtt solves this by providing an async/await native interface.

**Extracted problem statement from README**:

> No more callbacks! 👍
> No more return codes (welcome to the `MqttError`)
> Graceful disconnection (forget about `on_unsubscribe`, `on_disconnect`, etc.)

This means developers can write coroutine-based code instead of registering multiple callback handlers for MQTT lifecycle events.

## Key Statistics

- **Project maturity**: Development Status 4 - Beta — extracted from `pyproject.toml` classifier `"Development Status :: 4 - Beta"`
- **Operating system**: OS Independent — extracted from `pyproject.toml` classifier `"Operating System :: OS Independent"`
- **Supported MQTT versions**: 5.0, 3.1.1, and 3.1 — extracted from README "Supports MQTT versions 5.0, 3.1.1 and 3.1"

## Key Features

**1. Async context manager-based connection**

The library uses Python's async context manager protocol (`async with`) to manage MQTT connections. Extracted from `docs/connecting-to-the-broker.md`:

> "The connection to the broker is managed by the `Client` context manager. This context manager connects to the broker when we enter the `with` statement and disconnects when we exit it again."

**2. Callback-free message iteration**

Messages are received via an async generator (`client.messages`) rather than callbacks. Extracted from `docs/subscribing-to-a-topic.md`:

> "Incoming messages are queued internally. You can use the `Client.messages` generator to iterate over incoming messages."

Concrete usage example from `docs/subscribing-to-a-topic.md`:

```python
async with aiomqtt.Client("test.mosquitto.org") as client:
    await client.subscribe("temperature/#")
    async for message in client.messages:
        print(message.payload)
```

**3. Topic matching with wildcard support**

The `Topic.matches()` method allows filtering messages using MQTT wildcard patterns. Extracted from `docs/subscribing-to-a-topic.md`:

> "You can filter messages with `Topic.matches()`. Similar to `Client.subscribe()`, `Topic.matches()` also accepts wildcards (e.g. `temperature/#`):"

**4. Customizable message queuing**

The library supports custom asyncio queue types for message ordering. Extracted from `docs/subscribing-to-a-topic.md`:

> "The default queue is `asyncio.Queue` which returns messages on a FIFO ("first in first out") basis. You can pass [other types of asyncio queues](https://docs.python.org/3/library/asyncio-queue.html) as `queue_type` to the `Client` to modify the order in which messages are returned, e.g. `asyncio.LifoQueue`."

Example from `docs/subscribing-to-a-topic.md` shows subclassing `asyncio.PriorityQueue` to implement priority-based message filtering.

**5. Quality of Service (QoS) levels**

Three QoS levels are supported: 0 (At most once), 1 (At least once), and 2 (Exactly once). Extracted from `docs/publishing-a-message.md`:

> - QoS 0 (**"At most once"**): The message is sent once, with no guarantee of delivery. This is the fastest and least reliable option. This is the default of aiomqtt.
> - QoS 1 (**"At least once"**): The message is delivered at least once to the receiver, possibly multiple times.
> - QoS 2 (**"Exactly once"**): The message is delivered exactly once to the receiver.

**6. Retained message support**

Messages can be marked as retained for new subscribers. Extracted from `docs/publishing-a-message.md`:

> "Messages can be published with the `retain` parameter set to `True`. The broker relays these messages to all subscribers as usual but also stores the most recent message for the topic."

**7. Persistent sessions**

Session persistence can be controlled via the `clean_session` parameter. Extracted from `docs/connecting-to-the-broker.md`:

> "Persistent sessions are kept alive when the client goes offline. This means that the broker stores the client's subscriptions and queues any messages of [QoS 1 and 2](...) that the client misses or has not yet acknowledged."

**8. Type hints throughout**

Extracted from README: "Fully type-hinted"

**9. Concurrent message processing**

Multiple worker tasks can process messages concurrently to prevent single messages from blocking others. Extracted from `docs/subscribing-to-a-topic.md`:

> "Messages are queued internally and returned sequentially from `Client.messages`. If a message takes a long time to handle, it blocks the handling of other messages. You can handle messages concurrently by using multiple worker tasks..."

## Technical Architecture

The architecture centers on the `Client` class and related core components, extracted from `aiomqtt/__init__.py`:

**Core components exported by the library**:

- `Client` — async context manager wrapping paho-mqtt
- `MessagesIterator` — async generator for iterating messages
- `Message` — represents a single MQTT message with topic, payload, QoS, retain flag, and message ID
- `Topic` and `Wildcard` — topic matching with wildcard support
- `ProtocolVersion` — enum for MQTT versions (V31, V311, V5)
- `TLSParameters` — dataclass for TLS configuration
- `ProxySettings` — proxy configuration class

**Data flow** (extracted from `docs/connecting-to-the-broker.md` and `docs/subscribing-to-a-topic.md`):

1. User creates a `Client` instance pointing to broker hostname
2. `async with client:` triggers `__aenter__`, which connects to the broker
3. User calls `await client.subscribe(topic)` to register topic subscriptions
4. Incoming messages are queued in an internal asyncio queue (default: `asyncio.Queue`)
5. User iterates `async for message in client.messages:` to consume messages from the queue
6. Each message is a `Message` object with attributes: `topic`, `payload` (bytes), `qos`, `retain`, `mid`, and `properties` (MQTT v5.0 only)
7. `async with` exit triggers `__aexit__`, which disconnects gracefully

**Exception hierarchy** (extracted from `aiomqtt/exceptions.py`):

- `MqttError` — base exception for all MQTT-related errors
- `MqttCodeError(MqttError)` — wraps MQTT protocol return codes
- `MqttConnectError(MqttCodeError)` — connection failures with human-readable messages
- `MqttReentrantError(MqttError)` — raised when Client context is re-entered (not reentrant, but reusable)

**Connection reusability pattern** (extracted from `docs/reconnection.md`):

> "The `Client` context is designed to be [reusable (but not reentrant)](https://docs.python.org/3/library/contextlib.html#reusable-context-managers)."

The same Client instance can be used in multiple `async with` blocks for reconnection logic, enabling automatic reconnection with backoff.

## Installation & Usage

**Installation**:

Extracted from README:

```bash
pip install aiomqtt
```

Or directly from GitHub:

```bash
pip install git+https://github.com/empicano/aiomqtt
```

**Basic publish example** (extracted from `docs/connecting-to-the-broker.md`):

```python
import asyncio
import aiomqtt

async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.publish("temperature/outside", payload=28.4)

asyncio.run(main())
```

**Basic subscribe example** (extracted from `docs/subscribing-to-a-topic.md`):

```python
import asyncio
import aiomqtt

async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        async for message in client.messages:
            print(message.payload)

asyncio.run(main())
```

**Reconnection with backoff** (extracted from `docs/reconnection.md`):

```python
import asyncio
import aiomqtt

async def main():
    client = aiomqtt.Client("test.mosquitto.org")
    interval = 5  # Seconds
    while True:
        try:
            async with client:
                await client.subscribe("humidity/#")
                async for message in client.messages:
                    print(message.payload)
        except aiomqtt.MqttError:
            print(f"Connection lost; Reconnecting in {interval} seconds ...")
            await asyncio.sleep(interval)

asyncio.run(main())
```

**Integration with FastAPI** (extracted from `docs/alongside-fastapi-and-co.md`):

The library can be integrated with web frameworks using the lifespan context manager pattern (FastAPI 0.93+, Starlette):

```python
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
import aiomqtt

async def listen(client):
    async for message in client.messages:
        print(message.payload)

client = None

async def get_mqtt():
    yield client

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    async with aiomqtt.Client("test.mosquitto.org") as c:
        client = c
        await client.subscribe("humidity/#")
        loop = asyncio.get_event_loop()
        task = loop.create_task(listen(client))
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)
```

**Platform-specific note for Windows** (extracted from README):

> "Since Python 3.8, the default asyncio event loop is the `ProactorEventLoop`. Said loop [doesn't support the `add_reader` method](https://docs.python.org/3/library/asyncio-platforms.html#windows) that is required by aiomqtt. Please switch to an event loop that supports the `add_reader` method such as the built-in `SelectorEventLoop`:"

The README provides explicit code to set the event loop policy on Windows.

## Limitations and Caveats

**1. Message payload types**

Only certain payload types are natively supported. Extracted from `docs/publishing-a-message.md`:

> "aiomqtt accepts payloads of types `int`, `float`, `str`, `bytes`, `bytearray`, and `None`. `int` and `float` payloads are automatically converted to `str` (which is then converted to `bytes`)."

Complex types (dict, list) require manual serialization (e.g., via `json.dumps()`).

**2. Windows event loop limitation**

As documented in README: ProactorEventLoop on Windows does not support `add_reader()`, requiring explicit event loop policy switch.

**3. Reentrancy constraint**

Extracted from `docs/reconnection.md`: Client context is "reusable (but not reentrant)" — the same Client instance cannot be simultaneously entered in multiple `async with` blocks.

**4. Persistent session memory constraints**

Extracted from `docs/connecting-to-the-broker.md`:

> "The amount of messages that can be queued is limited by the broker's memory. If a client with a persistent session does not come back online for a long time, the broker will eventually run out of memory and start discarding messages."

**5. Blocking on single message handling**

Extracted from `docs/subscribing-to-a-topic.md`:

> "Messages are queued internally and returned sequentially from `Client.messages`. If a message takes a long time to handle, it blocks the handling of other messages."

Concurrent message processing requires explicit use of asyncio TaskGroup or similar constructs.

**6. Fire-and-forget task management**

When using background tasks without awaiting them, exceptions are not propagated until program exit. Extracted from `docs/subscribing-to-a-topic.md`:

> "You need to handle all possible exceptions _inside_ the fire-and-forget task. Unhandled exceptions will be silently ignored until the program exits."

## Relevance to Claude Code Development

The library is relevant for:

1. **IoT and real-time event systems**: Any Claude Code skill or tool that needs to integrate with MQTT brokers for sensor data, home automation, or industrial IoT applications.

2. **Long-running async services**: The reconnection pattern (reusable context manager) is directly applicable to building resilient background tasks that must survive network failures.

3. **Concurrent message processing workflows**: Multiple worker tasks processing incoming MQTT messages can be coordinated with asyncio TaskGroup, similar to how Claude Code agents might coordinate parallel tasks.

4. **FastAPI/Starlette integration**: Web-based Claude Code tools can use the lifespan context manager pattern to manage MQTT connections alongside HTTP request handling.

5. **Type-safe async code**: The library's full type hints support Claude Code development workflows that rely on static analysis and IDE support.

## References

- Repository: <https://github.com/sbtinstruments/asyncio-mqtt> (accessed 2026-03-29)
- Documentation: <https://aiomqtt.bo3hm.com> (accessed 2026-03-29)
- PyPI package: <https://pypi.org/project/aiomqtt/> (accessed 2026-03-29)
- paho-mqtt dependency: <https://github.com/eclipse/paho.mqtt.python> (accessed 2026-03-29)

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---|---|
| Identity/Metadata | high | 2026-03-29 | Version, license, authors extracted from pyproject.toml and CHANGELOG |
| Features | high | 2026-03-29 | All features verified in official documentation and source code |
| Architecture | high | 2026-03-29 | Component names and data flow extracted from source exports and docs |
| Installation & Usage | high | 2026-03-29 | Examples copied verbatim from official documentation |
| Limitations | high | 2026-03-29 | Constraints documented in README and guides |
| Relevance | medium | 2026-03-29 | Assessment based on library capabilities and Claude Code use cases |

**Next review**: 2026-06-29 (3 months from initial creation)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [AnyIO](./anyio.md) | async-libraries | Backend-agnostic async/await foundation; aiomqtt uses asyncio, AnyIO provides unified API across asyncio and Trio |
| [Trio](./trio.md) | async-libraries | Alternative structured concurrency model; aiomqtt event loop patterns share Trio's nursery-like cancellation semantics |
| [AsyncSSH](./asyncssh.md) | async-libraries | Complementary async transport layer; both provide async context manager patterns for persistent connections |
| [FastAPI](../api-frameworks/fastapi.md) | api-frameworks | Integration pattern: FastAPI lifespan context manager handles MQTT client lifecycle alongside HTTP requests |
| [Tornado](../api-frameworks/tornado.md) | api-frameworks | Comparable async architecture: both manage long-lived persistent connections via non-blocking event loops |

---

**Entry metadata**:

- **Created**: 2026-03-29
- **Resource**: aiomqtt v2.5.1
- **Category**: async-libraries
- **Extraction method**: Primary source reads (README.md, pyproject.toml, docs/*.md, source files)
