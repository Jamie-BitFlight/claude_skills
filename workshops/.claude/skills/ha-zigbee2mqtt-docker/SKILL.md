---
description: 'Home Assistant with Zigbee2MQTT Docker setup: container configuration, coordinator setup, device pairing, and automation. Use when deploying Home Assistant, configuring Zigbee2MQTT, pairing Zigbee devices, or creating automations.'
user-invocable: true
allowed-tools: Bash, Read, Write
---

# Home Assistant with Zigbee2MQTT Docker Setup

Deploy Home Assistant and Zigbee2MQTT in Docker containers for Zigbee device integration and testing.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Host                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Home Assistant │◀──▶│  Zigbee2MQTT    │                 │
│  │  :8123          │    │  :8080 (UI)     │                 │
│  │                 │    │                 │                 │
│  │  MQTT Client    │    │  MQTT Broker    │                 │
│  └────────┬────────┘    └────────┬────────┘                 │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                      │
│              ┌───────────────┐                              │
│              │   Mosquitto   │                              │
│              │   MQTT Broker │                              │
│              │   :1883       │                              │
│              └───────────────┘                              │
│                      │                                      │
└──────────────────────┼──────────────────────────────────────┘
                       │ USB
                       ▼
              ┌───────────────┐
              │  Zigbee       │
              │  Coordinator  │
              │  (CC2652/nRF) │
              └───────────────┘
```

---

## Directory Structure

```bash
# Create project directory
mkdir -p ~/homeassistant-zigbee
cd ~/homeassistant-zigbee

# Create directory structure
mkdir -p homeassistant
mkdir -p zigbee2mqtt/data
mkdir -p mosquitto/config
mkdir -p mosquitto/data
mkdir -p mosquitto/log
```

---

## Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - homeassistant

  zigbee2mqtt:
    image: koenkk/zigbee2mqtt:latest
    container_name: zigbee2mqtt
    restart: unless-stopped
    depends_on:
      - mosquitto
    ports:
      - "8080:8080"
    volumes:
      - ./zigbee2mqtt/data:/app/data
      - /run/udev:/run/udev:ro
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0  # Adjust for your coordinator
    environment:
      - TZ=America/New_York
    networks:
      - homeassistant

  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    depends_on:
      - mosquitto
      - zigbee2mqtt
    ports:
      - "8123:8123"
    volumes:
      - ./homeassistant:/config
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=America/New_York
    networks:
      - homeassistant

networks:
  homeassistant:
    driver: bridge
```

---

## Mosquitto Configuration

```conf
# mosquitto/config/mosquitto.conf
listener 1883
allow_anonymous false
password_file /mosquitto/config/password.txt

listener 9001
protocol websockets

persistence true
persistence_location /mosquitto/data/

log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
```

### Create MQTT User

```bash
# Create password file
docker run --rm -v $(pwd)/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2 \
  mosquitto_passwd -c /mosquitto/config/password.txt mqtt_user

# Enter password when prompted
```

---

## Zigbee2MQTT Configuration

```yaml
# zigbee2mqtt/data/configuration.yaml
homeassistant: true
permit_join: false

mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://mosquitto:1883
  user: mqtt_user
  password: your_mqtt_password

serial:
  port: /dev/ttyUSB0
  # For network coordinators (like SLZB-06):
  # port: tcp://192.168.1.100:6638

frontend:
  port: 8080
  host: 0.0.0.0

advanced:
  log_level: info
  log_output:
    - console
  network_key: GENERATE  # Will auto-generate on first start
  pan_id: GENERATE
  ext_pan_id: GENERATE
  channel: 15

# Device-specific settings (optional)
devices:
  '0x00158d0001234567':
    friendly_name: front_door_lock
    retain: true

# Group definitions (optional)
groups:
  '1':
    friendly_name: living_room_lights
```

### Supported Coordinators

| Coordinator      | Port Example    | Notes                  |
| ---------------- | --------------- | ---------------------- |
| CC2652P (Sonoff) | `/dev/ttyUSB0`  | Most common, USB       |
| CC2652RB         | `/dev/ttyACM0`  | USB CDC                |
| SLZB-06          | `tcp://IP:6638` | Network coordinator    |
| ConBee II        | `/dev/ttyACM0`  | USB                    |
| nRF52840 Dongle  | `/dev/ttyACM0`  | Nordic, needs firmware |

### Find Coordinator Port

```bash
# List USB devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# Check USB device info
dmesg | grep -i "tty\|usb"

# Find by ID (more reliable)
ls -la /dev/serial/by-id/
# Use this path in configuration for stability
```

---

## Home Assistant Configuration

```yaml
# homeassistant/configuration.yaml

# Minimal configuration - most done via UI
homeassistant:
  name: Home
  unit_system: metric
  time_zone: America/New_York

# Enable default integrations
default_config:

# MQTT integration (can also configure via UI)
mqtt:
  broker: mosquitto
  port: 1883
  username: mqtt_user
  password: your_mqtt_password
  discovery: true
  discovery_prefix: homeassistant

# Logger for debugging
logger:
  default: info
  logs:
    homeassistant.components.mqtt: debug
```

---

## Deployment

### Start Services

```bash
cd ~/homeassistant-zigbee

# Pull latest images
docker-compose pull

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f zigbee2mqtt
```

### Initial Setup

1. **Access Zigbee2MQTT**: <http://localhost:8080>
2. **Access Home Assistant**: <http://localhost:8123>
3. **Complete HA onboarding wizard**
4. **Configure MQTT integration** (if not using YAML)

---

## Pairing Zigbee Devices

### Enable Pairing Mode

```bash
# Via Zigbee2MQTT Frontend (recommended)
# Settings > Permit Join > Enable

# Or via MQTT
docker exec mosquitto mosquitto_pub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/bridge/request/permit_join' \
  -m '{"value": true, "time": 120}'
```

### Pair Device

1. Enable permit_join in Zigbee2MQTT
2. Put device in pairing mode (usually hold button)
3. Watch Zigbee2MQTT logs for device discovery
4. Device appears in Zigbee2MQTT frontend
5. Device auto-discovered in Home Assistant

### Verify Pairing

```bash
# Check Zigbee2MQTT logs
docker-compose logs zigbee2mqtt | grep -i "interview"

# List devices via MQTT
docker exec mosquitto mosquitto_sub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/bridge/devices' -C 1

# Check Home Assistant entities
# Settings > Devices & Services > MQTT > Devices
```

---

## Testing Your Door Lock Device

### Device Configuration

```yaml
# Add to zigbee2mqtt/data/configuration.yaml
devices:
  '0x00158d0001234567':  # Your device IEEE address
    friendly_name: test_door_lock
    retain: true

# Optionally expose all attributes
device_options:
  '0x00158d0001234567':
    homeassistant:
      lock:
        value_template: "{{ value_json.state }}"
        command_topic: "zigbee2mqtt/test_door_lock/set"
```

### Test Commands

```bash
# Lock the door
docker exec mosquitto mosquitto_pub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/test_door_lock/set' \
  -m '{"state": "LOCK"}'

# Unlock the door
docker exec mosquitto mosquitto_pub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/test_door_lock/set' \
  -m '{"state": "UNLOCK"}'

# Get state
docker exec mosquitto mosquitto_sub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/test_door_lock' -C 1
```

### Home Assistant Automation Example

```yaml
# homeassistant/automations.yaml
- id: 'lock_door_at_night'
  alias: Lock Door at Night
  trigger:
    - platform: time
      at: '22:00:00'
  action:
    - service: lock.lock
      target:
        entity_id: lock.test_door_lock

- id: 'notify_on_unlock'
  alias: Notify on Door Unlock
  trigger:
    - platform: state
      entity_id: lock.test_door_lock
      to: 'unlocked'
  action:
    - service: notify.mobile_app
      data:
        message: "Front door was unlocked"
```

---

## Troubleshooting

### Coordinator Not Found

```bash
# Check device exists
ls -la /dev/ttyUSB0

# Check permissions
sudo chmod 666 /dev/ttyUSB0

# Or add user to dialout group
sudo usermod -a -G dialout $USER

# Check container can see device
docker-compose exec zigbee2mqtt ls -la /dev/ttyUSB0
```

### MQTT Connection Failed

```bash
# Test MQTT connectivity
docker exec mosquitto mosquitto_pub \
  -u mqtt_user -P your_password \
  -t 'test' -m 'hello'

docker exec mosquitto mosquitto_sub \
  -u mqtt_user -P your_password \
  -t 'test' -C 1

# Check mosquitto logs
docker-compose logs mosquitto
```

### Device Not Pairing

```bash
# Check permit_join is enabled
docker exec mosquitto mosquitto_sub \
  -u mqtt_user -P your_password \
  -t 'zigbee2mqtt/bridge/info' -C 1

# Factory reset device and retry
# Check device is Zigbee 3.0 compatible
# Try different channel (15, 20, 25)
```

### Home Assistant Not Discovering Devices

```bash
# Check MQTT discovery is enabled
# Verify discovery topic matches
docker exec mosquitto mosquitto_sub \
  -u mqtt_user -P your_password \
  -t 'homeassistant/#' -v

# Restart Home Assistant
docker-compose restart homeassistant

# Check HA logs
docker-compose logs homeassistant | grep -i mqtt
```

---

## Useful Commands Reference

```bash
# Restart all services
docker-compose restart

# Rebuild after config changes
docker-compose down && docker-compose up -d

# Backup data
tar -czvf backup.tar.gz homeassistant zigbee2mqtt mosquitto

# Update images
docker-compose pull && docker-compose up -d

# Enter container shell
docker-compose exec zigbee2mqtt sh
docker-compose exec homeassistant bash

# View resource usage
docker stats
```

---

## References

- [Zigbee2MQTT Documentation](https://www.zigbee2mqtt.io/)
- [Home Assistant Docker Installation](https://www.home-assistant.io/installation/linux#docker-compose)
- [Mosquitto Documentation](https://mosquitto.org/documentation/)
- [Zigbee2MQTT Supported Devices](https://www.zigbee2mqtt.io/supported-devices/)
