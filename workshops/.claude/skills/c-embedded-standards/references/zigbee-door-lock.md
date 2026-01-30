# Zigbee Door Lock Cluster (0x0101) Reference

Complete implementation reference for the Door Lock cluster on nRF52/STM32 with ZBOSS stack.

## Cluster Specification

**Cluster ID:** `0x0101`
**ZCL Revision:** 8
**Specification:** Zigbee Cluster Library (ZCL 8)

---

## Server Attributes

### Mandatory Attributes

| Attribute       | ID     | Type  | Access      | Range           | Default        |
| --------------- | ------ | ----- | ----------- | --------------- | -------------- |
| LockState       | 0x0000 | enum8 | Read/Report | 0x00-0x02, 0xFF | 0x00           |
| LockType        | 0x0001 | enum8 | Read        | 0x00-0x0B       | Implementation |
| ActuatorEnabled | 0x0002 | bool  | Read        | true/false      | true           |

### Optional Attributes

| Attribute                   | ID     | Type   | Access      | Description                |
| --------------------------- | ------ | ------ | ----------- | -------------------------- |
| DoorState                   | 0x0003 | enum8  | Read/Report | Physical door state        |
| DoorOpenEvents              | 0x0004 | uint32 | Read        | Door open counter          |
| DoorClosedEvents            | 0x0005 | uint32 | Read        | Door close counter         |
| OpenPeriod                  | 0x0006 | uint16 | Read/Write  | Minutes door can stay open |
| NumberOfLogRecordsSupported | 0x0010 | uint16 | Read        | Event log capacity         |
| NumberOfTotalUsersSupported | 0x0011 | uint16 | Read        | Max PIN/RFID users         |
| NumberOfPINUsersSupported   | 0x0012 | uint16 | Read        | Max PIN users              |
| NumberOfRFIDUsersSupported  | 0x0013 | uint16 | Read        | Max RFID users             |

---

## Lock State Values

```c
typedef enum {
    ZB_ZCL_DOOR_LOCK_LOCK_STATE_NOT_FULLY_LOCKED = 0x00,
    ZB_ZCL_DOOR_LOCK_LOCK_STATE_LOCKED           = 0x01,
    ZB_ZCL_DOOR_LOCK_LOCK_STATE_UNLOCKED         = 0x02,
    ZB_ZCL_DOOR_LOCK_LOCK_STATE_UNDEFINED        = 0xFF
} zb_zcl_door_lock_lock_state_t;
```

## Lock Type Values

```c
typedef enum {
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_DEAD_BOLT          = 0x00,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_MAGNETIC           = 0x01,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_OTHER              = 0x02,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_MORTISE            = 0x03,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_RIM                = 0x04,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_LATCH_BOLT         = 0x05,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_CYLINDRICAL_LOCK   = 0x06,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_TUBULAR_LOCK       = 0x07,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_INTERCONNECTED     = 0x08,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_DEAD_LATCH         = 0x09,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_DOOR_FURNITURE     = 0x0A,
    ZB_ZCL_DOOR_LOCK_LOCK_TYPE_EUROCYLINDER       = 0x0B
} zb_zcl_door_lock_lock_type_t;
```

---

## Commands

### Client-to-Server Commands

| Command           | ID   | Payload                   | Response                  |
| ----------------- | ---- | ------------------------- | ------------------------- |
| LockDoor          | 0x00 | PINCode (optional)        | LockDoorResponse          |
| UnlockDoor        | 0x01 | PINCode (optional)        | UnlockDoorResponse        |
| Toggle            | 0x02 | PINCode (optional)        | ToggleResponse            |
| UnlockWithTimeout | 0x03 | Timeout, PINCode          | UnlockWithTimeoutResponse |
| GetLogRecord      | 0x04 | LogIndex                  | GetLogRecordResponse      |
| SetPINCode        | 0x05 | UserID, Status, Type, PIN | SetPINCodeResponse        |
| GetPINCode        | 0x06 | UserID                    | GetPINCodeResponse        |
| ClearPINCode      | 0x07 | UserID                    | ClearPINCodeResponse      |
| ClearAllPINCodes  | 0x08 | -                         | ClearAllPINCodesResponse  |

### Server-to-Client Responses

| Response                  | ID   | Payload             |
| ------------------------- | ---- | ------------------- |
| LockDoorResponse          | 0x00 | Status (ZCL status) |
| UnlockDoorResponse        | 0x01 | Status              |
| ToggleResponse            | 0x02 | Status              |
| UnlockWithTimeoutResponse | 0x03 | Status              |

---

## nRF Connect SDK Implementation

### Cluster Declaration

```c
#include <zboss_api.h>
#include <zcl/zb_zcl_door_lock.h>

/* Endpoint ID for door lock */
#define DOOR_LOCK_ENDPOINT    10

/* Cluster attributes */
static zb_uint8_t attr_lock_state = ZB_ZCL_DOOR_LOCK_LOCK_STATE_UNLOCKED;
static zb_uint8_t attr_lock_type = ZB_ZCL_DOOR_LOCK_LOCK_TYPE_DEAD_BOLT;
static zb_bool_t attr_actuator_enabled = ZB_TRUE;
static zb_uint8_t attr_door_state = ZB_ZCL_DOOR_LOCK_DOOR_STATE_DOOR_CLOSED;

/* Declare attribute list */
ZB_ZCL_DECLARE_DOOR_LOCK_ATTRIB_LIST(
    door_lock_attr_list,
    &attr_lock_state,
    &attr_lock_type,
    &attr_actuator_enabled
);

/* Declare cluster list */
ZB_ZCL_DECLARE_DOOR_LOCK_CLUSTER_LIST(
    door_lock_clusters,
    door_lock_attr_list
);

/* Declare endpoint */
ZB_AF_DECLARE_ENDPOINT_DESC(
    door_lock_ep,
    DOOR_LOCK_ENDPOINT,
    ZB_AF_HA_PROFILE_ID,
    0,  /* No device version */
    NULL,
    ZB_ZCL_ARRAY_SIZE(door_lock_clusters, zb_zcl_cluster_desc_t),
    door_lock_clusters,
    (zb_af_simple_desc_1_1_t *)&simple_desc_door_lock
);
```

### Command Handler

```c
static zb_uint8_t door_lock_cmd_handler(zb_bufid_t bufid)
{
    zb_zcl_parsed_hdr_t *cmd_info = ZB_BUF_GET_PARAM(bufid, zb_zcl_parsed_hdr_t);
    zb_uint8_t status = ZB_ZCL_STATUS_SUCCESS;

    LOG_INF("Door lock command: 0x%02x", cmd_info->cmd_id);

    switch (cmd_info->cmd_id) {
    case ZB_ZCL_CMD_DOOR_LOCK_LOCK_DOOR:
        status = handle_lock_door(bufid);
        break;

    case ZB_ZCL_CMD_DOOR_LOCK_UNLOCK_DOOR:
        status = handle_unlock_door(bufid);
        break;

    case ZB_ZCL_CMD_DOOR_LOCK_TOGGLE:
        status = handle_toggle(bufid);
        break;

    default:
        status = ZB_ZCL_STATUS_UNSUP_CMD;
        break;
    }

    /* Send response */
    send_door_lock_response(bufid, cmd_info->cmd_id, status);

    return ZB_ZCL_STATUS_SUCCESS;
}

static zb_uint8_t handle_lock_door(zb_bufid_t bufid)
{
    /* Validate PIN if required */
    if (pin_required && !validate_pin(bufid)) {
        return ZB_ZCL_STATUS_FAILURE;
    }

    /* Actuate lock */
    if (!actuate_lock(LOCK_ACTION_LOCK)) {
        return ZB_ZCL_STATUS_FAILURE;
    }

    /* Update attribute */
    attr_lock_state = ZB_ZCL_DOOR_LOCK_LOCK_STATE_LOCKED;

    /* Report attribute change */
    ZB_ZCL_SET_ATTRIBUTE(
        DOOR_LOCK_ENDPOINT,
        ZB_ZCL_CLUSTER_ID_DOOR_LOCK,
        ZB_ZCL_CLUSTER_SERVER_ROLE,
        ZB_ZCL_ATTR_DOOR_LOCK_LOCK_STATE_ID,
        (zb_uint8_t *)&attr_lock_state,
        ZB_FALSE
    );

    return ZB_ZCL_STATUS_SUCCESS;
}
```

### Attribute Reporting

```c
/* Configure attribute reporting */
static void configure_reporting(void)
{
    zb_zcl_reporting_info_t rep_info = {
        .direction = ZB_ZCL_CONFIGURE_REPORTING_SEND_REPORT,
        .ep = DOOR_LOCK_ENDPOINT,
        .cluster_id = ZB_ZCL_CLUSTER_ID_DOOR_LOCK,
        .cluster_role = ZB_ZCL_CLUSTER_SERVER_ROLE,
        .attr_id = ZB_ZCL_ATTR_DOOR_LOCK_LOCK_STATE_ID,
        .dst.profile_id = ZB_AF_HA_PROFILE_ID,
        .u.send_info.min_interval = 1,      /* 1 second min */
        .u.send_info.max_interval = 300,    /* 5 minutes max */
        .u.send_info.reported_value = &attr_lock_state,
        .u.send_info.def_min_interval = 1,
        .u.send_info.def_max_interval = 300
    };

    zb_zcl_put_reporting_info(&rep_info, ZB_TRUE);
}
```

---

## Hardware Abstraction

```c
/* Lock actuator interface */
typedef enum {
    LOCK_ACTION_LOCK,
    LOCK_ACTION_UNLOCK
} lock_action_t;

typedef void (*lock_complete_cb_t)(bool success);

/* Platform-specific implementation required */
bool actuate_lock(lock_action_t action);
bool actuate_lock_async(lock_action_t action, lock_complete_cb_t callback);
bool get_lock_position(void);  /* Returns true if locked */

/* Example GPIO-based implementation */
static bool actuate_lock(lock_action_t action)
{
    const struct gpio_dt_spec lock_gpio = GPIO_DT_SPEC_GET(DT_ALIAS(lock_motor), gpios);

    int ret = gpio_pin_set_dt(&lock_gpio, (action == LOCK_ACTION_LOCK) ? 1 : 0);
    if (ret < 0) {
        LOG_ERR("Failed to actuate lock: %d", ret);
        return false;
    }

    /* Wait for actuation to complete */
    k_sleep(K_MSEC(CONFIG_LOCK_ACTUATION_TIME_MS));

    /* Verify position */
    return (get_lock_position() == (action == LOCK_ACTION_LOCK));
}
```

---

## Security Considerations

### PIN Code Storage

```c
/* Never store PINs in plaintext */
#define MAX_PIN_USERS    10
#define PIN_HASH_SIZE    32

typedef struct {
    uint16_t user_id;
    uint8_t status;
    uint8_t type;
    uint8_t pin_hash[PIN_HASH_SIZE];  /* SHA-256 hash */
} pin_user_t;

static pin_user_t pin_users[MAX_PIN_USERS];

/* Hash PIN before comparison */
static bool validate_pin(const uint8_t *pin, size_t pin_len, uint16_t user_id)
{
    uint8_t computed_hash[PIN_HASH_SIZE];

    /* Compute hash of provided PIN */
    compute_sha256(pin, pin_len, computed_hash);

    /* Find user and compare */
    for (int i = 0; i < MAX_PIN_USERS; i++) {
        if (pin_users[i].user_id == user_id) {
            return memcmp(computed_hash, pin_users[i].pin_hash, PIN_HASH_SIZE) == 0;
        }
    }

    return false;
}
```

### Event Logging

```c
/* Log all lock/unlock events for audit */
typedef struct {
    uint32_t timestamp;
    uint8_t event_type;
    uint8_t source;      /* Local, Zigbee, PIN, RFID */
    uint16_t user_id;
    uint8_t status;
} door_lock_event_t;

void log_lock_event(uint8_t event_type, uint8_t source, uint16_t user_id, uint8_t status)
{
    door_lock_event_t event = {
        .timestamp = get_unix_timestamp(),
        .event_type = event_type,
        .source = source,
        .user_id = user_id,
        .status = status
    };

    event_log_write(&event);
}
```

---

## References

- Zigbee Cluster Library Specification (ZCL 8) - Section 5.2 Door Lock Cluster
- nRF Connect SDK: ZBOSS API Reference
- Nordic DevZone: Zigbee Door Lock Sample
