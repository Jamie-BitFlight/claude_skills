---
description: 'Reference knowledge for embedded C development: MISRA-C 2012 rules, Zigbee 3.0 door_lock cluster implementation, FreeRTOS task patterns, and C stdlib usage on nRF52/STM32. Use when writing firmware, reviewing embedded code, implementing Zigbee clusters, or working with FreeRTOS APIs.'
user-invocable: false
---

# Embedded C Development Standards

Domain knowledge for embedded C development targeting nRF52 and STM32 platforms with Zigbee and FreeRTOS.

## C Programming Standards

### MISRA-C 2012 Critical Rules

| Rule | Category  | Requirement                                     |
| ---- | --------- | ----------------------------------------------- |
| 11.3 | Pointers  | No cast between pointer and integer types       |
| 11.4 | Pointers  | No cast to pointer of different object type     |
| 14.3 | Control   | Controlling expressions shall have boolean type |
| 17.2 | Functions | Recursion shall not be used                     |
| 17.7 | Functions | Return value of non-void function shall be used |
| 21.3 | Stdlib    | Memory allocation functions shall not be used   |

See [MISRA-C Reference](./references/misra-c-rules.md) for complete rules.

### Memory Safety Patterns

```c
// CORRECT: Volatile for ISR-shared variables
static volatile uint32_t g_tick_count;

// CORRECT: Critical section protection
void safe_increment(void) {
    taskENTER_CRITICAL();
    g_shared_counter++;
    taskEXIT_CRITICAL();
}

// CORRECT: Bounds checking before array access
if (index < ARRAY_SIZE(buffer)) {
    buffer[index] = value;
}
```

### Interrupt Safety Checklist

- [ ] All ISR-shared variables marked `volatile`
- [ ] Critical sections protect shared data
- [ ] ISRs kept short (defer work to tasks)
- [ ] No blocking calls in ISRs
- [ ] Reentrant functions only in ISR context

---

## Zigbee Door Lock Cluster (0x0101)

### Cluster Overview

The Door Lock cluster provides an interface to door lock functionality.

**Cluster ID:** `0x0101`
**Role:** Server (lock device) or Client (controller)

### Required Attributes (Server)

| Attribute       | ID     | Type  | Access | Default        |
| --------------- | ------ | ----- | ------ | -------------- |
| LockState       | 0x0000 | enum8 | R      | NotFullyLocked |
| LockType        | 0x0001 | enum8 | R      | DeadBolt       |
| ActuatorEnabled | 0x0002 | bool  | R      | true           |

### Lock State Values

```c
typedef enum {
    DOOR_LOCK_STATE_NOT_FULLY_LOCKED = 0x00,
    DOOR_LOCK_STATE_LOCKED           = 0x01,
    DOOR_LOCK_STATE_UNLOCKED         = 0x02,
    DOOR_LOCK_STATE_UNDEFINED        = 0xFF
} door_lock_state_t;
```

### Required Commands

| Command            | ID   | Direction     | Fields             |
| ------------------ | ---- | ------------- | ------------------ |
| LockDoor           | 0x00 | Client→Server | PINCode (optional) |
| UnlockDoor         | 0x01 | Client→Server | PINCode (optional) |
| LockDoorResponse   | 0x00 | Server→Client | Status             |
| UnlockDoorResponse | 0x01 | Server→Client | Status             |

### nRF Connect SDK Implementation Pattern

```c
#include <zephyr/kernel.h>
#include <zboss_api.h>
#include <zigbee/zigbee_app_utils.h>
#include <zcl/zb_zcl_door_lock.h>

/* Door lock cluster attributes */
static zb_uint8_t attr_lock_state = ZB_ZCL_DOOR_LOCK_LOCK_STATE_UNLOCKED;
static zb_uint8_t attr_lock_type = ZB_ZCL_DOOR_LOCK_LOCK_TYPE_DEAD_BOLT;
static zb_bool_t attr_actuator_enabled = ZB_TRUE;

/* Attribute list declaration */
ZB_ZCL_DECLARE_DOOR_LOCK_ATTRIB_LIST(
    door_lock_attr_list,
    &attr_lock_state,
    &attr_lock_type,
    &attr_actuator_enabled
);

/* Command handler */
static zb_uint8_t door_lock_cmd_handler(zb_uint8_t param)
{
    zb_zcl_parsed_hdr_t *cmd_info = ZB_BUF_GET_PARAM(param, zb_zcl_parsed_hdr_t);

    switch (cmd_info->cmd_id) {
    case ZB_ZCL_CMD_DOOR_LOCK_LOCK_DOOR:
        return handle_lock_door(param);
    case ZB_ZCL_CMD_DOOR_LOCK_UNLOCK_DOOR:
        return handle_unlock_door(param);
    default:
        return ZB_ZCL_STATUS_UNSUP_CMD;
    }
}
```

See [Door Lock Cluster Reference](./references/zigbee-door-lock.md) for complete implementation.

---

## FreeRTOS Patterns

### Task Creation

```c
#define TASK_STACK_SIZE    (1024)
#define TASK_PRIORITY      (tskIDLE_PRIORITY + 2)

static StaticTask_t task_tcb;
static StackType_t task_stack[TASK_STACK_SIZE];

TaskHandle_t task_handle = xTaskCreateStatic(
    task_function,          /* Task function */
    "TaskName",             /* Task name (debug) */
    TASK_STACK_SIZE,        /* Stack size (words) */
    NULL,                   /* Parameters */
    TASK_PRIORITY,          /* Priority */
    task_stack,             /* Stack buffer */
    &task_tcb               /* TCB buffer */
);
```

### Queue Communication

```c
#define QUEUE_LENGTH    (10)
#define QUEUE_ITEM_SIZE sizeof(message_t)

static StaticQueue_t queue_buffer;
static uint8_t queue_storage[QUEUE_LENGTH * QUEUE_ITEM_SIZE];

QueueHandle_t msg_queue = xQueueCreateStatic(
    QUEUE_LENGTH,
    QUEUE_ITEM_SIZE,
    queue_storage,
    &queue_buffer
);

/* Send from ISR */
void UART_IRQHandler(void) {
    BaseType_t higher_priority_woken = pdFALSE;
    message_t msg = {.type = MSG_RX_COMPLETE};

    xQueueSendFromISR(msg_queue, &msg, &higher_priority_woken);
    portYIELD_FROM_ISR(higher_priority_woken);
}

/* Receive in task */
void task_function(void *param) {
    message_t msg;
    for (;;) {
        if (xQueueReceive(msg_queue, &msg, portMAX_DELAY) == pdTRUE) {
            process_message(&msg);
        }
    }
}
```

### Mutex Protection

```c
static StaticSemaphore_t mutex_buffer;
SemaphoreHandle_t resource_mutex = xSemaphoreCreateMutexStatic(&mutex_buffer);

void access_shared_resource(void) {
    if (xSemaphoreTake(resource_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        /* Access protected resource */
        modify_shared_data();
        xSemaphoreGive(resource_mutex);
    } else {
        /* Handle timeout */
        LOG_ERR("Mutex timeout");
    }
}
```

See [FreeRTOS Reference](./references/freertos-patterns.md) for complete patterns.

---

## C Standard Library on Embedded

### Safe Alternatives

| Avoid         | Use Instead            | Reason                     |
| ------------- | ---------------------- | -------------------------- |
| `malloc/free` | Static allocation      | Fragmentation, determinism |
| `sprintf`     | `snprintf`             | Buffer overflow protection |
| `strcpy`      | `strncpy` or `strlcpy` | Bounds checking            |
| `strcat`      | `strncat`              | Bounds checking            |
| `atoi`        | `strtol`               | Error detection            |
| `gets`        | `fgets`                | Buffer overflow            |

### Safe String Operations

```c
#include <string.h>
#include <stdint.h>

/* Safe string copy with null termination guarantee */
static inline size_t safe_strcpy(char *dst, const char *src, size_t dst_size) {
    if (dst_size == 0) return 0;

    size_t src_len = strlen(src);
    size_t copy_len = (src_len < dst_size - 1) ? src_len : (dst_size - 1);

    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';

    return copy_len;
}

/* Safe integer parsing with error checking */
static inline bool safe_parse_int(const char *str, int32_t *result) {
    char *endptr;
    errno = 0;

    long value = strtol(str, &endptr, 10);

    if (errno != 0 || endptr == str || *endptr != '\0') {
        return false;
    }

    if (value < INT32_MIN || value > INT32_MAX) {
        return false;
    }

    *result = (int32_t)value;
    return true;
}
```

---

## Platform-Specific Notes

### nRF52 (Nordic)

- Use nRF Connect SDK (Zephyr-based) for new projects
- ZBOSS stack for Zigbee implementation
- `CONFIG_HEAP_MEM_POOL_SIZE` for dynamic allocation (if required)
- Hardware crypto via CryptoCell for secure operations

### STM32

- STM32CubeIDE or CMake-based builds
- HAL or LL drivers depending on performance needs
- FreeRTOS via CMSIS-RTOS2 wrapper or direct API
- Static allocation recommended (`configSUPPORT_STATIC_ALLOCATION=1`)

---

## References

- [MISRA-C 2012 Rules](./references/misra-c-rules.md)
- [Zigbee Door Lock Cluster](./references/zigbee-door-lock.md)
- [FreeRTOS Patterns](./references/freertos-patterns.md)
- [Zigbee Cluster Library Specification](https://csa-iot.org/developer-resource/specifications-download-request/) (CSA members)
