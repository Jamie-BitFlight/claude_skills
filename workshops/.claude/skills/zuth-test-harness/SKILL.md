---
description: 'ZUTH (Zigbee Unified Test Harness) setup, configuration, and test execution for Zigbee certification testing. Use when setting up ZUTH environment, running certification tests, configuring test cases, or debugging Zigbee protocol compliance.'
user-invocable: true
allowed-tools: Bash, Read, Write
---

# ZUTH Zigbee Test Harness

Setup and usage guide for Zigbee Unified Test Harness (ZUTH) for certification testing.

## Overview

ZUTH is the official test harness for Zigbee certification, replacing the legacy ZTT (Zigbee Test Tool). It validates device compliance with Zigbee 3.0 specifications.

### Components

| Component   | Purpose                                      |
| ----------- | -------------------------------------------- |
| ZUTH Core   | Test execution engine                        |
| Golden Unit | Reference Zigbee device (coordinator/router) |
| DUT         | Device Under Test                            |
| Sniffer     | Packet capture for protocol analysis         |
| ZUTH GUI    | Test configuration and execution interface   |

---

## Installation

### System Requirements

- Windows 10/11 (64-bit) - Primary support
- Linux (Ubuntu 20.04+) - Limited support
- Python 3.8+ for scripting
- Java 11+ for GUI components

### Download and Install

```bash
# ZUTH is available from CSA (Connectivity Standards Alliance)
# Requires membership for download access
# https://csa-iot.org/developer-resource/zigbee-test-harness/

# Extract to installation directory
unzip ZUTH-x.x.x.zip -d /opt/zuth

# Set environment variables
export ZUTH_HOME=/opt/zuth
export PATH="$PATH:$ZUTH_HOME/bin"
```

### Hardware Setup

```
┌─────────────┐    USB    ┌─────────────┐
│   ZUTH PC   │──────────▶│ Golden Unit │
│             │           │ (nRF52840)  │
│             │    USB    └─────────────┘
│             │──────────▶┌─────────────┐
│             │           │   Sniffer   │
│             │           │ (nRF52840)  │
│             │           └─────────────┘
│             │
│             │    DUT connected via:
│             │    - Serial (for commands)
│             │    - Zigbee network (for testing)
└─────────────┘
```

### Golden Unit Setup

```bash
# Flash golden unit firmware (Nordic example)
nrfjprog --program golden_unit_nrf52840.hex --verify --reset

# Verify golden unit responds
# Check serial port for golden unit interface
ls /dev/ttyACM*

# Configure golden unit serial port in ZUTH config
```

---

## Configuration

### ZUTH Configuration File

```xml
<!-- zuth_config.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<ZUTHConfiguration>
    <TestHarness>
        <GoldenUnit>
            <Port>COM3</Port>  <!-- or /dev/ttyACM0 -->
            <BaudRate>115200</BaudRate>
        </GoldenUnit>
        <Sniffer>
            <Port>COM4</Port>
            <Channel>15</Channel>
        </Sniffer>
    </TestHarness>

    <Network>
        <PanId>0x1234</PanId>
        <ExtendedPanId>0x0123456789ABCDEF</ExtendedPanId>
        <Channel>15</Channel>
        <NetworkKey>01234567890123456789012345678901</NetworkKey>
    </Network>

    <DUT>
        <Name>MyDevice</Name>
        <Type>EndDevice</Type>  <!-- Coordinator, Router, EndDevice -->
        <ManufacturerCode>0x1234</ManufacturerCode>
    </DUT>
</ZUTHConfiguration>
```

### DUT Profile Configuration

```xml
<!-- dut_profile.xml -->
<DUTProfile>
    <DeviceInfo>
        <DeviceType>HA_DOOR_LOCK</DeviceType>
        <ProfileId>0x0104</ProfileId>  <!-- HA Profile -->
        <DeviceId>0x000A</DeviceId>    <!-- Door Lock -->
    </DeviceInfo>

    <Endpoints>
        <Endpoint id="1">
            <ProfileId>0x0104</ProfileId>
            <DeviceId>0x000A</DeviceId>
            <Clusters>
                <InputCluster>0x0000</InputCluster>  <!-- Basic -->
                <InputCluster>0x0101</InputCluster>  <!-- Door Lock -->
                <OutputCluster>0x0019</OutputCluster> <!-- OTA -->
            </Clusters>
        </Endpoint>
    </Endpoints>

    <Features>
        <Feature name="PIN_SUPPORT">true</Feature>
        <Feature name="RFID_SUPPORT">false</Feature>
        <Feature name="DOOR_POSITION_SENSOR">true</Feature>
    </Features>
</DUTProfile>
```

---

## Running Tests

### GUI Mode

```bash
# Start ZUTH GUI
$ZUTH_HOME/bin/zuth-gui

# In GUI:
# 1. File > Load Configuration > zuth_config.xml
# 2. File > Load DUT Profile > dut_profile.xml
# 3. Test > Select Test Suite > Base Device Behavior
# 4. Test > Run Selected Tests
```

### Command Line Mode

```bash
# List available test suites
zuth-cli --list-suites

# Run specific test suite
zuth-cli --config zuth_config.xml \
         --dut-profile dut_profile.xml \
         --suite "Base Device Behavior" \
         --output results/

# Run specific test case
zuth-cli --config zuth_config.xml \
         --dut-profile dut_profile.xml \
         --test "BDB-TC-01" \
         --output results/

# Run all applicable tests
zuth-cli --config zuth_config.xml \
         --dut-profile dut_profile.xml \
         --run-all \
         --output results/
```

### Test Output

```bash
# Results directory structure
results/
├── summary.html          # Human-readable summary
├── summary.xml           # Machine-readable results
├── captures/             # Packet captures per test
│   ├── BDB-TC-01.pcap
│   └── ...
└── logs/                 # Detailed test logs
    ├── BDB-TC-01.log
    └── ...
```

---

## Test Categories

### Base Device Behavior (BDB)

| Test ID   | Description                       | DUT Action Required        |
| --------- | --------------------------------- | -------------------------- |
| BDB-TC-01 | Commissioning - Touchlink         | Enable touchlink mode      |
| BDB-TC-02 | Commissioning - Network Steering  | Start network steering     |
| BDB-TC-03 | Commissioning - Network Formation | Form network (coordinator) |
| BDB-TC-04 | Finding and Binding               | Enable F&B target mode     |

### Cluster-Specific Tests

| Test ID  | Cluster   | Description             |
| -------- | --------- | ----------------------- |
| DL-TC-01 | Door Lock | Lock command handling   |
| DL-TC-02 | Door Lock | Unlock command handling |
| DL-TC-03 | Door Lock | PIN code management     |
| DL-TC-04 | Door Lock | Lock state reporting    |

### Security Tests

| Test ID   | Description            |
| --------- | ---------------------- |
| SEC-TC-01 | Network key update     |
| SEC-TC-02 | Link key establishment |
| SEC-TC-03 | Trust center operation |

---

## DUT Interface Commands

### ZUTH expects DUT to respond to these commands via serial

```text
# Command format: <CMD> [params]\r\n
# Response format: <STATUS> [data]\r\n

# Network commands
CMD: JOIN_NETWORK
RSP: OK JOINED <short_addr> <pan_id>

CMD: LEAVE_NETWORK
RSP: OK LEFT

CMD: GET_NETWORK_INFO
RSP: OK SHORT_ADDR=0x1234 PAN_ID=0x5678 CHANNEL=15

# Cluster commands
CMD: CLUSTER_CMD <endpoint> <cluster_id> <cmd_id> [payload_hex]
RSP: OK SENT

CMD: REPORT_ATTR <endpoint> <cluster_id> <attr_id>
RSP: OK REPORTED <value>

# Test mode commands
CMD: ENTER_TEST_MODE
RSP: OK TEST_MODE

CMD: EXIT_TEST_MODE
RSP: OK NORMAL_MODE

CMD: SET_ATTR <endpoint> <cluster_id> <attr_id> <value>
RSP: OK SET

# Commissioning commands
CMD: START_COMMISSIONING <method>
RSP: OK COMMISSIONING

CMD: FACTORY_RESET
RSP: OK RESET
```

### Implementing DUT Interface

```c
/* DUT serial command handler example */
static void handle_zuth_command(const char *cmd, char *response, size_t resp_size)
{
    if (strncmp(cmd, "JOIN_NETWORK", 12) == 0) {
        /* Trigger network steering */
        zb_bdb_start_top_level_commissioning(ZB_BDB_NETWORK_STEERING);
        snprintf(response, resp_size, "OK JOINING");

    } else if (strncmp(cmd, "LEAVE_NETWORK", 13) == 0) {
        zb_bdb_reset_via_local_action(0);
        snprintf(response, resp_size, "OK LEFT");

    } else if (strncmp(cmd, "GET_NETWORK_INFO", 16) == 0) {
        snprintf(response, resp_size, "OK SHORT_ADDR=0x%04X PAN_ID=0x%04X CHANNEL=%d",
                 zb_get_short_address(),
                 zb_get_pan_id(),
                 zb_get_current_channel());

    } else if (strncmp(cmd, "CLUSTER_CMD", 11) == 0) {
        /* Parse and send cluster command */
        handle_cluster_cmd(cmd + 12, response, resp_size);

    } else {
        snprintf(response, resp_size, "ERROR UNKNOWN_CMD");
    }
}
```

---

## Troubleshooting

### Golden Unit Not Responding

```bash
# Check serial port connection
screen /dev/ttyACM0 115200

# Verify golden unit firmware
# Re-flash if necessary
nrfjprog --program golden_unit.hex --verify --reset

# Check USB permissions
sudo usermod -a -G dialout $USER
```

### DUT Not Joining Network

```bash
# Verify channel alignment
# Check network key configuration
# Ensure DUT is in commissioning mode
# Check sniffer capture for join attempts
```

### Test Timeout

```bash
# Increase timeout in configuration
# Check DUT response time
# Verify serial communication working
# Review test log for last successful step
```

### Analyzing Failures

```bash
# Open packet capture in Wireshark
wireshark results/captures/BDB-TC-01.pcap

# Filter for Zigbee frames
# Look for:
# - Association request/response
# - Network key transport
# - Cluster commands and responses
```

---

## Best Practices

### Pre-Certification Checklist

- [ ] All applicable test cases pass
- [ ] No manual intervention required during tests
- [ ] DUT firmware is release candidate version
- [ ] All debug output disabled
- [ ] Power consumption within spec
- [ ] Security features properly implemented

### Test Environment

- Isolate test network from other Zigbee devices
- Use RF shielded enclosure if available
- Document firmware version and hardware revision
- Keep test logs for all certification attempts

---

## References

- [CSA Zigbee Certification Program](https://csa-iot.org/certification/zigbee/)
- [Zigbee Base Device Behavior Specification](https://csa-iot.org/developer-resource/specifications-download-request/)
- [ZUTH User Guide](https://csa-iot.org/developer-resource/zigbee-test-harness/) (CSA members)
- [Zigbee PRO Stack User Guide](https://csa-iot.org/developer-resource/specifications-download-request/)
