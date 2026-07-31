---
title: 'Blinker: Fast Signal/Event Dispatching System'
library_name: blinker
pypi_package: blinker
category: event-system
python_compatibility: 3.8+
last_updated: '2025-11-02'
official_docs: https://blinker.readthedocs.io
official_repository: https://github.com/pallets-eco/blinker
maintenance_status: active
---

# Blinker: Fast Signal/Event Dispatching System

## Official Information

**Repository:** <https://github.com/pallets-eco/blinker> **PyPI Package:** blinker **Current Version:** 1.9.0 (Released 2024-11-08) **Official Documentation:** <https://blinker.readthedocs.io/> **License:** MIT License **Maintenance Status:** Active (Pallets Community Ecosystem)

@source <https://github.com/pallets-eco/blinker> @source <https://blinker.readthedocs.io/> @source <https://pypi.org/project/blinker/>

## Core Purpose

Blinker provides a fast dispatching system that allows any number of interested parties to subscribe to events or "signals". It implements the Observer pattern with a clean, Pythonic API.

### Problem Space

Without blinker, you would need to manually implement:

- Global event registries for decoupled components
- Weak reference management for automatic cleanup
- Thread-safe event dispatching
- Sender-specific event filtering
- Return value collection from multiple handlers

### When to Use Blinker

**Use blinker when:**

- Building plugin systems that need event hooks
- Implementing application lifecycle hooks (like Flask)
- Creating decoupled components that communicate via events
- Building event-driven architectures within a single process
- Need multiple independent handlers for the same event
- Want automatic cleanup via weak references

**What you would be "reinventing the wheel" without it:**

- Observer/subscriber pattern implementation
- Named signal registries for plugin communication
- Weak reference management for receivers
- Thread-safe signal dispatching
- Sender filtering and context passing

## Python Version Compatibility

**Minimum Python Version:** 3.9+ **Python 3.11:** Fully compatible **Python 3.12:** Fully compatible **Python 3.13:** Fully compatible **Python 3.14:** Expected to be compatible

@source <https://blinker.readthedocs.io/en/stable/>

### Thread Safety

Blinker signals are thread-safe. The library uses weak references for automatic cleanup and properly handles concurrent signal emission and subscription.

## Integration Patterns

### Flask Ecosystem Integration

Flask uses blinker as its signal system foundation. Flask provides built-in signals like:

- `request_started` - Before request processing begins
- `request_finished` - After response is constructed
- `template_rendered` - When template is rendered
- `request_tearing_down` - During request teardown

@source <https://flask.palletsprojects.com/en/latest/signals/>

**Example Flask Signal Usage:**

```python
from flask import template_rendered


def log_template_renders(sender, template, context, **extra):
    sender.logger.info(f"Rendered {template.name} with context {context}")


template_rendered.connect(log_template_renders, app)
```

### Event-Driven Architecture

Blinker excels at creating loosely coupled components:

```python
from blinker import Namespace

# Create isolated namespace for your application
app_signals = Namespace()

# Define signals
user_logged_in = app_signals.signal("user-logged-in")
data_updated = app_signals.signal("data-updated")


# Multiple handlers can subscribe
@user_logged_in.connect
def update_last_login(sender, **kwargs):
    user_id = kwargs.get("user_id")
    # Update database


@user_logged_in.connect
def send_login_notification(sender, **kwargs):
    # Send email notification
    pass


# Emit signal
user_logged_in.send(app, user_id=123, ip_address="192.168.1.1")
```

### Plugin Systems

```python
from blinker import signal

# Core application defines hook points
plugin_loaded = signal("plugin-loaded")
before_process = signal("before-process")
after_process = signal("after-process")


# Plugins subscribe to hooks
@before_process.connect
def plugin_preprocess(sender, data):
    # Plugin modifies data before processing
    return data


# Application emits signals at hook points
results = before_process.send(self, data=input_data)
for receiver, result in results:
    if result is not None:
        input_data = result
```

## Real-World Examples

### Example 1: Flask Request Monitoring

@source <https://github.com/instana/python-sensor> (Flask instrumentation with blinker)

```python
from flask import request_started, request_finished
import time

request_times = {}


def track_request_start(sender, **extra):
    request_times[id(extra)] = time.time()


def track_request_end(sender, response, **extra):
    duration = time.time() - request_times.pop(id(extra), time.time())
    sender.logger.info(f"Request took {duration:.2f}s")


request_started.connect(track_request_start)
request_finished.connect(track_request_end)
```

### Example 2: Model Save Hooks

@source <https://blinker.readthedocs.io/>

```python
from blinker import Namespace

model_signals = Namespace()
model_saved = model_signals.signal("model-saved")


class Model:
    def save(self):
        # Save to database
        self._persist()
        # Emit signal for observers
        model_saved.send(self, model_type=self.__class__.__name__)


# Cache invalidation handler
@model_saved.connect
def invalidate_cache(sender, **kwargs):
    cache.delete(f"model:{kwargs['model_type']}")


# Audit logging handler
@model_saved.connect
def log_change(sender, **kwargs):
    audit_log.write(f"Model saved: {kwargs['model_type']}")
```

### Example 3: Sender-Specific Subscriptions

@source <https://github.com/pallets-eco/blinker> README

```python
from blinker import signal

round_started = signal("round-started")


# General subscriber - receives from all senders
@round_started.connect
def each_round(sender):
    print(f"Round {sender}")


# Sender-specific subscriber - only for sender=2
@round_started.connect_via(2)
def special_round(sender):
    print("This is round two!")


for round_num in range(1, 4):
    round_started.send(round_num)
# Output:
# Round 1
# Round 2
# This is round two!
# Round 3
```

### Example 4: Async Signal Handlers

@source <https://blinker.readthedocs.io/en/stable/>

```python
import asyncio
from blinker import Signal

async_signal = Signal()


# Async receiver
async def async_receiver(sender, **kwargs):
    await asyncio.sleep(1)
    print("Async handler completed")


async_signal.connect(async_receiver)

# Send to async receivers
await async_signal.send_async()


# Mix sync and async receivers
def sync_receiver(sender, **kwargs):
    print("Sync handler")


async_signal.connect(sync_receiver)


# Provide wrapper for sync handlers in async context
async def sync_wrapper(func):
    async def inner(*args, **kwargs):
        func(*args, **kwargs)

    return inner


await async_signal.send_async(_sync_wrapper=sync_wrapper)
```

## Usage Examples

### Basic Signal Definition and Connection

```python
from blinker import signal

# Named signals (shared across modules)
initialized = signal("initialized")

# Anonymous signals (class attributes)
from blinker import Signal


class Processor:
    on_ready = Signal()
    on_complete = Signal()

    def process(self):
        self.on_ready.send(self)
        # Do work
        self.on_complete.send(self, status="success")


# Connect receivers
@initialized.connect
def on_init(sender, **kwargs):
    print(f"Initialized by {sender}")


processor = Processor()


@processor.on_complete.connect
def handle_completion(sender, **kwargs):
    print(f"Status: {kwargs['status']}")
```

### Named Signals for Decoupling

```python
from blinker import signal


# Module A defines and sends
def user_service():
    user_created = signal("user-created")
    # Create user
    user_created.send("user_service", user_id=123, username="john")


# Module B subscribes (no import of Module A needed!)
def notification_service():
    user_created = signal("user-created")  # Same signal instance

    @user_created.connect
    def send_welcome_email(sender, **kwargs):
        print(f"Sending email to {kwargs['username']}")
```

### Checking for Receivers Before Expensive Operations

```python
from blinker import signal

data_changed = signal("data-changed")


def update_data(new_data):
    # Only compute expensive stats if someone is listening
    if data_changed.receivers:
        stats = compute_expensive_stats(new_data)
        data_changed.send(self, data=new_data, stats=stats)
    else:
        # Skip expensive computation
        data_changed.send(self, data=new_data)
```

### Temporarily Muting Signals (Testing)

```python
from blinker import signal

send_email = signal("send-email")


@send_email.connect
def actually_send(sender, **kwargs):
    # Send real email
    pass


def test_user_registration():
    # Don't send emails during tests
    with send_email.muted():
        register_user("test@example.com")
        # send_email signal is ignored in this context
```

### Collecting Return Values

```python
from blinker import signal

validate_data = signal("validate-data")


@validate_data.connect
def check_email(sender, **kwargs):
    email = kwargs["email"]
    if "@" not in email:
        return False, "Invalid email"
    return True, None


@validate_data.connect
def check_username(sender, **kwargs):
    username = kwargs["username"]
    if len(username) < 3:
        return False, "Username too short"
    return True, None


# Collect all validation results
results = validate_data.send(None, email="invalid", username="ab")

for receiver, (valid, error) in results:
    if not valid:
        print(f"Validation failed: {error}")
```

## When NOT to Use Blinker

### Scenario 1: Simple Callbacks Sufficient

**Don't use blinker when:**

- Single callback function is enough
- No need for dynamic subscription/unsubscription
- Callbacks are tightly coupled to caller

```python
# Overkill - use simple callback
from blinker import signal

sig = signal("done")
sig.connect(on_done)
sig.send(self)


# Better - direct callback
def process(callback):
    # do work
    callback()


process(on_done)
```

### Scenario 2: Async Event Systems

**Don't use blinker when:**

- Building async-first distributed event system
- Need message queuing and persistence
- Cross-process or cross-network communication

```python
# Wrong tool - blinker is in-process only
from blinker import signal

distributed_event = signal("cross-service-event")

# Better - use async message queue
import asyncio
from aio_pika import connect, Message


async def publish_event():
    connection = await connect("amqp://guest:guest@localhost/")
    channel = await connection.channel()
    await channel.default_exchange.publish(Message(b"event data"), routing_key="events")
```

### Scenario 3: Complex State Machines

**Don't use blinker when:**

- Need state transitions with guards and actions
- Require hierarchical or concurrent states
- Complex workflow orchestration

```python
# Wrong tool - too complex for simple signals
from blinker import signal

# Better - use state machine library
from transitions import Machine


class Order:
    states = ["pending", "paid", "shipped", "delivered"]

    def __init__(self):
        self.machine = Machine(model=self, states=Order.states, initial="pending")
        self.machine.add_transition("pay", "pending", "paid")
        self.machine.add_transition("ship", "paid", "shipped")
```

### Scenario 4: Request/Response Patterns

**Don't use blinker when:**

- Need bidirectional request/response communication
- Require RPC-style method calls
- Need return values from specific handlers

```python
# Awkward with signals
result = some_signal.send(self, request="data")
# Hard to know which handler provided what


# Better - direct method call or dependency injection
class ServiceLocator:
    def get_service(self, name):
        return self._services[name]


service = locator.get_service("data_processor")
result = service.process(data)
```

## Decision Guidance Matrix

| Use Blinker When                     | Use Callbacks When             | Use AsyncIO When                  | Use Message Queue When             |
| ------------------------------------ | ------------------------------ | --------------------------------- | ---------------------------------- |
| Multiple independent handlers needed | Single handler sufficient      | Async/await throughout codebase   | Cross-process communication needed |
| Plugin system with dynamic handlers  | Tightly coupled components     | I/O-bound async operations        | Message persistence required       |
| Decoupled modules need communication | Callback logic is simple       | Event loop already present        | Distributed systems                |
| Framework-level hooks (like Flask)   | Direct function call works     | Concurrent async tasks            | Reliability and retry needed       |
| Observable events in OOP design      | Inline lambda sufficient       | Network I/O heavy                 | Message ordering matters           |
| Weak reference cleanup needed        | Manual lifecycle management OK | WebSockets/long-lived connections | Load balancing across workers      |

### Decision Tree

<eg>
Need event notifications?
├─ Single process only?
│  ├─ YES: Continue
│  └─ NO: Use message queue (RabbitMQ, Redis, Kafka)
│
├─ Multiple handlers per event?
│  ├─ YES: Continue
│  └─ NO: Use simple callback function
│
├─ Handlers need to be dynamic (plugins)?
│  ├─ YES: Use Blinker ✓
│  └─ NO: Direct method calls may suffice
│
├─ Async/await heavy codebase?
│  ├─ YES: Consider asyncio event system
│  │       (or use Blinker with send_async)
│  └─ NO: Use Blinker ✓
│
└─ Need weak reference cleanup?
   ├─ YES: Use Blinker ✓
   └─ NO: Simple callbacks OK
</eg>

## Installation

```bash
pip install blinker
```

Current version: 1.9.0 Minimum Python: 3.9+

@source <https://pypi.org/project/blinker/>

## Key Features

- **Global named signal registry:** `signal('name')` returns same instance everywhere
- **Anonymous signals:** Create isolated `Signal()` instances
- **Sender filtering:** `connect(handler, sender=obj)` for sender-specific subscriptions
- **Weak references:** Automatic cleanup when receivers are garbage collected
- **Thread safety:** Safe for concurrent use
- **Return value collection:** Gather results from all handlers
- **Async support:** `send_async()` for coroutine receivers
- **Temporary connections:** Context managers for scoped subscriptions
- **Signal muting:** Disable signals temporarily (useful for testing)

@source <https://blinker.readthedocs.io/en/stable/>

## Common Pitfalls

1. **Memory leaks with strong references:**

   ```python
   # Default uses weak references - OK
   signal.connect(handler)

   # Strong reference - prevents garbage collection
   signal.connect(handler, weak=False)  # Use sparingly!
   ```

2. **Expecting signals to modify behavior:**

   - Signals are for observation, not control flow
   - Don't rely on signal handlers to prevent actions
   - Use explicit validation/authorization instead

3. **Forgetting sender parameter:**

   ```python
   @my_signal.connect
   def handler(sender, **kwargs):  # sender is required!
       print(kwargs["data"])
   ```

4. **Cross-process communication:**

   - Blinker is in-process only
   - Use message queues for distributed systems

5. **Performance with many handlers:**
   - Check `signal.receivers` before expensive operations
   - Consider limiting number of subscribers for hot paths

## Related Libraries

- **Django Signals:** Built into Django, similar concept but Django-specific
- **PyPubSub:** More complex publish-subscribe system
- **asyncio events:** For async-first applications
- **RxPY:** Reactive extensions for Python (more powerful, more complex)
- **Celery:** For distributed task queues and async workers

## Summary

Blinker is the standard solution for in-process event dispatching in Python, particularly within the Pallets ecosystem (Flask). Use it when you need clean, decoupled event notifications between components in the same process. For distributed systems, async-heavy codebases, or simple single-callback scenarios, consider alternatives.

**TL;DR:** Blinker = Observer pattern done right, with weak references, thread safety, and a clean API. Essential for Flask signals and plugin systems.
