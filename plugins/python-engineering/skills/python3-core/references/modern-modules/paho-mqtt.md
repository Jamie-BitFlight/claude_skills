---
title: 'paho-mqtt: Eclipse Paho MQTT Python Client'
library_name: paho-mqtt
pypi_package: paho-mqtt
category: networking
python_compatibility: 3.7+
last_updated: '2025-11-02'
official_docs: https://eclipse.dev/paho/files/paho.mqtt.python/html
official_repository: https://github.com/eclipse-paho/paho.mqtt.python
maintenance_status: active
---

# paho-mqtt: Eclipse Paho MQTT Python Client

## Core Purpose

The model must state that paho-mqtt is the official Eclipse Foundation implementation of the MQTT protocol client for Python.

MQTT (Message Queuing Telemetry Transport) is a lightweight publish-subscribe messaging protocol designed for machine-to-machine (M2M) and Internet of Things (IoT) communication. The model must explain that paho-mqtt solves the problem of reliable, lightweight messaging in bandwidth-constrained or unreliable network environments.

### What Problem Does It Solve?

The model must identify these key use cases:

1. **IoT Device Communication**: Enables lightweight messaging between sensors, actuators, and control systems
2. **Publish-Subscribe Patterns**: Provides decoupled communication where publishers and subscribers do not need to know about each other
3. **Bandwidth-Constrained Networks**: Minimizes network overhead compared to HTTP/REST
4. **Unreliable Network Handling**: Built-in Quality of Service (QoS) levels ensure message delivery guarantees
5. **Bi-directional Communication**: Supports both sending commands to devices and receiving telemetry data

### Reinventing the Wheel Without It

The model must verify that without paho-mqtt, developers would need to:

- Implement the complex MQTT protocol specification from scratch @ <https://mqtt.org/mqtt-specification/>
- Handle connection management, keep-alive pings, and automatic reconnection logic
- Implement three QoS levels (0, 1, 2) with appropriate acknowledgment mechanisms
- Manage topic subscriptions and wildcard matching
- Handle TLS/SSL encryption and WebSocket transport layers

## Official Information

The model must cite these verified sources:

- **Official Repository**: <https://github.com/eclipse-paho/paho.mqtt.python> @ verified 2025-10-21
- **PyPI Package**: `paho-mqtt` @ <https://pypi.org/project/paho-mqtt/>
- **Official Documentation**: <https://eclipse.dev/paho/files/paho.mqtt.python/html/>
- **License**: EPL-2.0 OR BSD-3-Clause (Eclipse Distribution License v1.0 and Eclipse Public License 2.0)
- **Maintainer**: Eclipse Foundation @ <https://www.eclipse.org/paho/>
- **Latest Version**: 2.1.0 (as of 2025-10-21)
- **Status**: Active development, production-ready (Beta classification indicates mature but evolving API)

## Python Version Compatibility

The model must verify from pyproject.toml @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/pyproject.toml>:

- **Minimum Python Version**: 3.7
- **Tested Versions**: 3.7, 3.8, 3.9, 3.10
- **Python 3.11-3.14 Status**: The model must state that Python 3.11+ compatibility is likely based on package maturity, but official classifiers only list up to 3.10. Users should test thoroughly.
- **Python 2.x**: NOT supported (users must stay on paho-mqtt 1.x for Python 2)

### Breaking Changes

The model must warn that version 2.0 introduced breaking changes:

- Callback API signatures changed (VERSION1 vs VERSION2)
- `CallbackAPIVersion` must now be explicitly specified
- Migration guide available @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html>

## Core Features

### 1. Quality of Service (QoS) Levels

The model must explain that MQTT provides three QoS levels @ <https://mqtt.org/mqtt-specification/>:

- **QoS 0 (At most once)**: Fire-and-forget, no acknowledgment, possible message loss
- **QoS 1 (At least once)**: Guaranteed delivery, possible duplicates, uses PUBACK
- **QoS 2 (Exactly once)**: Guaranteed single delivery, uses PUBREC/PUBREL/PUBCOMP handshake

Example from official docs @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/README.rst>:

```python
import paho.mqtt.client as mqtt

# QoS 0: Fire and forget
client.publish("topic/sensor", "temperature:22", qos=0)

# QoS 1: At least once delivery
msg_info = client.publish("topic/critical", "alert", qos=1)
msg_info.wait_for_publish()  # Wait for PUBACK

# QoS 2: Exactly once delivery
client.publish("topic/transaction", "payment:100", qos=2)
```

### 2. Connection Management

The model must verify that paho-mqtt handles:

- **Keep-Alive Mechanism**: Automatic ping/pong to maintain connection
- **Automatic Reconnection**: Built-in retry logic with exponential backoff
- **Clean Session vs Persistent Session**: Control message persistence across disconnections
- **Last Will and Testament (LWT)**: Automatic message sent on unexpected disconnection

Example @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html>:

```python
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Failed to connect: {reason_code}")
    else:
        print("Connected successfully")
        # Subscribe in on_connect ensures subscriptions persist across reconnections
        client.subscribe("sensors/#")


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Unexpected disconnect: {reason_code}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

# Configure reconnection with exponential backoff
client.reconnect_delay_set(min_delay=1, max_delay=120)

client.connect("mqtt.eclipseprojects.io", 1883, keepalive=60)
client.loop_forever()  # Handles automatic reconnection
```

### 3. Topic Wildcards

The model must explain MQTT topic wildcards @ <http://www.steves-internet-guide.com/understanding-mqtt-topics/>:

- **`+` (single-level wildcard)**: Matches one topic level, e.g., `home/+/temperature` matches `home/bedroom/temperature`
- **`#` (multi-level wildcard)**: Matches multiple levels, e.g., `sensors/#` matches `sensors/temp`, `sensors/humidity/outside`

```python
# Subscribe to all system topics
client.subscribe("$SYS/#")

# Subscribe to all rooms' temperature
client.subscribe("home/+/temperature")

# Helper function to check topic matches
from paho.mqtt.client import topic_matches_sub

assert topic_matches_sub("foo/#", "foo/bar")
assert topic_matches_sub("+/bar", "foo/bar")
assert not topic_matches_sub("non/+/+", "non/matching")
```

## Real-World Examples

The model must cite these verified examples from GitHub search @ 2025-10-21:

### 1. Home Assistant Integration

**Repository**: <https://github.com/home-assistant/core> (82,088 stars) **Use Case**: Open-source home automation platform using MQTT for device integration **Pattern**: Bidirectional communication with IoT devices (lights, sensors, thermostats)

```python
# Pattern extracted from Home Assistant ecosystem
import paho.mqtt.client as mqtt


def on_message(client, userdata, message):
    topic = message.topic  # e.g., "homeassistant/switch/living_room/state"
    payload = message.payload.decode()  # e.g., "ON" or "OFF"
    # Process device state changes
    handle_device_update(topic, payload)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect("homeassistant.local", 1883)
client.subscribe("homeassistant/#")
client.loop_forever()
```

### 2. AWS IoT Integration

**Repository**: <https://github.com/mariocannistra/python-paho-mqtt-for-aws-iot> (82 stars) **Use Case**: Connect Python applications to AWS IoT Core using MQTT over TLS **Pattern**: Secure cloud IoT communication with certificate-based authentication

```python
# Pattern from AWS IoT example @ https://github.com/mariocannistra/python-paho-mqtt-for-aws-iot
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# AWS IoT requires TLS with client certificates
client.tls_set(
    ca_certs="root-CA.crt", certfile="device-cert.pem", keyfile="device-private.key", tls_version=ssl.PROTOCOL_TLSv1_2
)

# AWS IoT endpoint
client.connect("a1b2c3d4e5f6g7.iot.us-west-2.amazonaws.com", 8883)

# Publish sensor data
client.publish("device/telemetry", '{"temp": 22.5, "humidity": 65}', qos=1)
```

### 3. Async Wrapper Pattern

**Repository**: <https://github.com/mossblaser/aiomqtt> (53 stars) **Use Case**: AsyncIO wrapper around paho-mqtt for non-blocking event loops **Pattern**: Integration with modern Python async/await patterns

Note: The model must verify that paho-mqtt itself does NOT have native async support. Third-party wrappers exist:

- `aiomqtt` @ <https://github.com/empicano/aiomqtt> (recommended, actively maintained)
- `asyncio-mqtt` @ <https://github.com/sbtinstruments/asyncio-mqtt> (deprecated)

## Integration Patterns

### 1. MQTT Broker Compatibility

The model must verify that paho-mqtt works with these brokers @ <https://mqtt.org/software/>:

- **Eclipse Mosquitto**: Open-source, lightweight broker @ <https://mosquitto.org/>
- **HiveMQ**: Enterprise MQTT platform @ <https://www.hivemq.com/>
- **EMQX**: Scalable, distributed broker @ <https://www.emqx.io/>
- **AWS IoT Core**: Cloud-based managed service
- **Azure IoT Hub**: Microsoft cloud IoT platform
- **Google Cloud IoT Core**: Google cloud service

Example with Mosquitto @ <http://www.steves-internet-guide.com/into-mqtt-python-client/>:

```python
import paho.mqtt.client as mqtt


def on_message(client, userdata, message):
    print(f"Received: {message.payload.decode()} on {message.topic}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="python_client")
client.on_message = on_message

# Local Mosquitto broker
client.connect("localhost", 1883, 60)
client.subscribe("test/topic")
client.loop_forever()
```

### 2. WebSocket Transport

The model must verify WebSocket support @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/ChangeLog.txt>:

```python
import paho.mqtt.client as mqtt

# Connect via WebSocket (useful for browser-based or proxy environments)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")

# Configure WebSocket path and headers
client.ws_set_options(path="/mqtt", headers={"User-Agent": "Paho-Python"})

# Connect to broker's WebSocket port
client.connect("mqtt.example.com", 8080, 60)
```

### 3. TLS/SSL Encryption

The model must verify TLS support @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html>:

```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Server certificate validation
client.tls_set(ca_certs="ca.crt", certfile="client.crt", keyfile="client.key", tls_version=ssl.PROTOCOL_TLSv1_2)

# For testing only: disable certificate verification (insecure!)
# client.tls_insecure_set(True)

client.connect("secure.mqtt.broker", 8883)
```

## Usage Examples

### Basic Publish

Example from official docs @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/README.rst>:

```python
import paho.mqtt.publish as publish

# One-shot publish (connect, publish, disconnect)
publish.single("home/temperature", payload="22.5", hostname="mqtt.eclipseprojects.io", port=1883)

# Multiple messages at once
msgs = [
    {"topic": "sensor/temp", "payload": "22.5"},
    {"topic": "sensor/humidity", "payload": "65"},
    ("sensor/pressure", "1013", 0, False),  # Alternative tuple format
]
publish.multiple(msgs, hostname="mqtt.eclipseprojects.io")
```

### Basic Subscribe

Example from official docs @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/README.rst>:

```python
import paho.mqtt.subscribe as subscribe

# Simple blocking subscribe (receives one message)
msg = subscribe.simple("home/temperature", hostname="mqtt.eclipseprojects.io")
print(f"{msg.topic}: {msg.payload.decode()}")


# Callback-based subscription
def on_message_handler(client, userdata, message):
    print(f"{message.topic}: {message.payload.decode()}")
    userdata["count"] += 1
    if userdata["count"] >= 10:
        client.disconnect()  # Stop after 10 messages


subscribe.callback(on_message_handler, "sensors/#", hostname="mqtt.eclipseprojects.io", userdata={"count": 0})
```

### Production-Grade Client

Example combining best practices @ <https://cedalo.com/blog/configuring-paho-mqtt-python-client-with-examples/>:

```python
import paho.mqtt.client as mqtt
import time


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Connection failed: {reason_code}")
        return

    print(f"Connected with result code {reason_code}")
    # Subscribe in on_connect ensures subscriptions persist after reconnection
    client.subscribe("sensors/#", qos=1)


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Unexpected disconnect. Reconnecting... (code: {reason_code})")


def on_message(client, userdata, message):
    print(f"Topic: {message.topic}")
    print(f"Payload: {message.payload.decode()}")
    print(f"QoS: {message.qos}")
    print(f"Retain: {message.retain}")


def on_publish(client, userdata, mid, reason_code, properties):
    print(f"Message {mid} published")


# Create client with VERSION2 callbacks (recommended)
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="sensor_monitor",
    clean_session=False,  # Persistent session
)

# Set callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_publish = on_publish

# Authentication
client.username_pw_set("username", "password")

# TLS (if required)
# client.tls_set(ca_certs="ca.crt")

# Reconnection settings
client.reconnect_delay_set(min_delay=1, max_delay=120)

# Connect
client.connect("mqtt.example.com", 1883, keepalive=60)

# Start network loop in background thread
client.loop_start()

# Application logic
try:
    while True:
        # Publish sensor data
        result = client.publish("sensors/temperature", "22.5", qos=1)
        result.wait_for_publish()  # Block until published
        time.sleep(5)
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    client.loop_stop()
    client.disconnect()
```

### Loop Management Patterns

The model must explain three loop options @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html>:

```python
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("mqtt.eclipseprojects.io", 1883)

# OPTION 1: Blocking loop (simplest)
# Runs forever, handles reconnection automatically
client.loop_forever()

# OPTION 2: Threaded loop (recommended for most cases)
# Runs in background thread, main thread free for other work
client.loop_start()
# ... do other work ...
client.loop_stop()

# OPTION 3: Manual loop (advanced, full control)
# Must be called regularly, manual reconnection handling
while True:
    rc = client.loop(timeout=1.0)
    if rc != 0:
        # Handle connection error
        break
```

## When NOT to Use paho-mqtt

The model must provide clear decision guidance based on verified constraints:

### Use HTTP/REST Instead When

1. **Request-Response Pattern**: Simple one-off queries without persistent connection

   - Example: Weather API calls, database queries
   - Reason: HTTP is simpler for synchronous request-response

2. **Large Payload Transfer**: Transferring files, images, or large datasets

   - Example: Uploading videos, downloading reports
   - Reason: HTTP has better tooling for chunked transfer, range requests

3. **Browser-Based Only**: Pure web applications without IoT integration

   - Example: Standard web app, SPA without real-time requirements
   - Reason: REST APIs are natively supported by browsers

4. **Strong Consistency Required**: Immediate consistency across all clients
   - Example: Financial transactions, inventory management
   - Reason: MQTT is eventually consistent, REST can enforce immediate consistency

### Use WebSockets Instead When

1. **Full-Duplex, Low-Latency Communication**: Real-time chat, gaming, collaborative editing

   - Example: Slack-like messaging, Google Docs collaboration
   - Reason: WebSockets provide bidirectional streams without MQTT protocol overhead

2. **Custom Protocol**: Need full control over message format and semantics
   - Example: Proprietary binary protocols, custom RPC
   - Reason: WebSockets are a transport layer, MQTT adds specific semantics

### Use Message Queues (RabbitMQ, Kafka) Instead When

1. **Complex Routing Logic**: Advanced routing rules, message transformation

   - Example: Enterprise service bus, workflow orchestration
   - Reason: RabbitMQ exchanges provide richer routing than MQTT topics

2. **High-Throughput Log Streaming**: Million+ messages per second, log aggregation

   - Example: Centralized logging, event sourcing at scale
   - Reason: Kafka optimized for high-throughput sequential writes

3. **Message Persistence and Replay**: Need to replay message history
   - Example: Event sourcing, audit trails
   - Reason: Kafka provides durable log storage, MQTT has limited persistence

## Decision Matrix: MQTT vs Alternatives

The model must provide this decision matrix based on verified use cases:

| **Use Case**             | **MQTT (paho-mqtt)**        | **HTTP/REST**             | **WebSocket** | **Message Queue**   |
| ------------------------ | --------------------------- | ------------------------- | ------------- | ------------------- |
| **IoT Sensor Data**      | ✅ Optimal                  | ❌ Too heavy              | ⚠️ Possible   | ❌ Overkill         |
| **Home Automation**      | ✅ Optimal                  | ❌ Polling inefficient    | ⚠️ Possible   | ❌ Too complex      |
| **Mobile Notifications** | ✅ Good (battery efficient) | ⚠️ Polling wastes battery | ✅ Good       | ❌ Overkill         |
| **Real-time Chat**       | ⚠️ Possible                 | ❌ No real-time           | ✅ Optimal    | ⚠️ Possible         |
| **File Transfer**        | ❌ Not designed for this    | ✅ Better tools           | ⚠️ Possible   | ❌ Wrong tool       |
| **Microservices RPC**    | ⚠️ Possible                 | ✅ Standard approach      | ❌ Overkill   | ✅ Enterprise scale |
| **Telemetry Collection** | ✅ Optimal                  | ❌ Too chatty             | ❌ Overkill   | ✅ At massive scale |

### Use MQTT When

The model must verify these conditions favor MQTT:

1. ✅ **Bandwidth is constrained** (cellular, satellite links)
2. ✅ **Network is unreliable** (intermittent connectivity)
3. ✅ **Many-to-many communication** (pub-sub pattern)
4. ✅ **Low latency required** (< 100ms message delivery)
5. ✅ **Battery-powered devices** (minimal protocol overhead)
6. ✅ **IoT/M2M communication** (devices, sensors, actuators)
7. ✅ **Topic-based routing** (hierarchical topic namespaces)

### Use HTTP/REST When

The model must verify these conditions favor HTTP:

1. ✅ **Request-response pattern** (client initiates, server responds)
2. ✅ **Stateless interactions** (no persistent connection needed)
3. ✅ **Large payloads** (files, documents, media)
4. ✅ **Caching required** (HTTP caching semantics)
5. ✅ **Browser-based clients** (native browser support)
6. ✅ **Standard CRUD operations** (REST conventions)

### Use WebSocket When

The model must verify these conditions favor WebSocket:

1. ✅ **Full-duplex communication** (simultaneous send/receive)
2. ✅ **Custom protocol** (need full control over wire format)
3. ✅ **Browser-based real-time** (chat, collaboration, gaming)
4. ✅ **Lower latency than MQTT** (no protocol overhead)
5. ✅ **Simple point-to-point** (no pub-sub routing needed)

## Known Limitations

The model must cite these verified limitations @ <https://github.com/eclipse-paho/paho.mqtt.python/blob/master/README.rst>:

### Session Persistence

1. **Memory-Only Sessions**: When `clean_session=False`, session state is NOT persisted to disk
   - Impact: Session lost if Python process restarts
   - Lost data: QoS 2 messages in-flight, pending QoS 1/2 publishes
   - Mitigation: Use `wait_for_publish()` to ensure message delivery before shutdown

```python
# Session is only in memory!
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clean_session=False)

# Ensure message is fully acknowledged before shutdown
msg_info = client.publish("critical/data", "important", qos=2)
msg_info.wait_for_publish()  # Blocks until PUBCOMP received
```

2. **QoS 2 Duplicate Risk**: With `clean_session=True`, QoS > 0 messages are republished after reconnection
   - Impact: QoS 2 messages may be received twice (non-compliant with MQTT spec)
   - Standard requires: Discard unacknowledged messages on reconnection
   - Recommendation: Use `clean_session=False` for exactly-once guarantees

### Native Async Support

The model must verify that paho-mqtt does NOT have native asyncio support:

- **Workaround**: Use third-party wrappers like `aiomqtt` @ <https://github.com/empicano/aiomqtt>
- **Alternative**: Use threaded loops (`loop_start()`) or external event loop support

```python
# NOT native async - need wrapper
import asyncio
from aiomqtt import Client  # Third-party wrapper


async def main():
    async with Client("mqtt.eclipseprojects.io") as client:
        async with client.messages() as messages:
            await client.subscribe("sensors/#")
            async for message in messages:
                print(message.payload.decode())


asyncio.run(main())
```

## Installation

The model must verify installation from official sources @ <https://pypi.org/project/paho-mqtt/>:

```bash
# Standard installation
pip install paho-mqtt

# With SOCKS proxy support
pip install paho-mqtt[proxy]

# Development installation from source
git clone https://github.com/eclipse-paho/paho.mqtt.python
cd paho.mqtt.python
pip install -e .
```

## Common Patterns and Best Practices

### 1. Reconnection Handling

The model must recommend this pattern @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html>:

```python
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, reason_code, properties):
    # ALWAYS subscribe in on_connect callback
    # This ensures subscriptions are renewed after reconnection
    client.subscribe("sensors/#", qos=1)


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Unexpected disconnect: {reason_code}")
        # loop_forever() and loop_start() will automatically reconnect


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

# Configure reconnection delay
client.reconnect_delay_set(min_delay=1, max_delay=120)

client.connect("mqtt.example.com", 1883)
client.loop_forever()  # Handles reconnection automatically
```

### 2. Logging for Debugging

The model must recommend enabling logging @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html>:

```python
import logging
import paho.mqtt.client as mqtt

# Enable standard Python logging
logging.basicConfig(level=logging.DEBUG)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.enable_logger()  # Uses standard logging module


# Or use custom on_log callback
def on_log(client, userdata, level, buf):
    if level == mqtt.MQTT_LOG_ERR:
        print(f"ERROR: {buf}")


client.on_log = on_log
```

### 3. Graceful Shutdown

The model must recommend this pattern for clean disconnection:

```python
import paho.mqtt.client as mqtt
import signal
import sys

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    client.disconnect()  # Triggers clean disconnect
    client.loop_stop()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

client.connect("mqtt.example.com", 1883)
client.loop_start()

# Application runs...
signal.pause()  # Wait for SIGINT
```

## References and Sources

The model must cite these verified sources used in this research:

1. Official Eclipse Paho repository @ <https://github.com/eclipse-paho/paho.mqtt.python>
2. Official documentation @ <https://eclipse.dev/paho/files/paho.mqtt.python/html/>
3. MQTT specification @ <https://mqtt.org/mqtt-specification/>
4. Steve's Internet Guide (MQTT tutorials) @ <http://www.steves-internet-guide.com/>
5. HiveMQ MQTT client guide @ <https://www.hivemq.com/blog/mqtt-client-library-paho-python/>
6. Cedalo MQTT configuration guide @ <https://cedalo.com/blog/configuring-paho-mqtt-python-client-with-examples/>
7. EMQX Python MQTT guide @ <https://www.emqx.com/en/blog/how-to-use-mqtt-in-python>
8. Home Assistant core repository @ <https://github.com/home-assistant/core>
9. AWS IoT Python example @ <https://github.com/mariocannistra/python-paho-mqtt-for-aws-iot>
10. aiomqtt async wrapper @ <https://github.com/empicano/aiomqtt>

## Summary

The model must conclude that paho-mqtt is the recommended solution when:

1. Building IoT applications with resource-constrained devices
2. Implementing pub-sub messaging patterns with topic-based routing
3. Operating in unreliable or bandwidth-limited network environments
4. Requiring specific QoS guarantees for message delivery
5. Integrating with standard MQTT brokers (Mosquitto, HiveMQ, EMQX, AWS IoT)

The model must avoid paho-mqtt when:

1. Simple request-response patterns suffice (use HTTP/REST)
2. Real-time, low-latency browser communication needed (use WebSocket)
3. Complex message routing or high-throughput streaming required (use RabbitMQ/Kafka)
4. Large file transfers or binary data streaming needed (use HTTP)

The model must verify that paho-mqtt is production-ready, actively maintained by the Eclipse Foundation, and the de facto standard MQTT client library for Python.
