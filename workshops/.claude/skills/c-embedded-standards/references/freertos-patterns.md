# FreeRTOS Patterns for Embedded Systems

Task management, synchronization, and communication patterns for nRF52/STM32.

## Configuration

### Static vs Dynamic Allocation

```c
/* In FreeRTOSConfig.h - prefer static allocation */
#define configSUPPORT_STATIC_ALLOCATION     1
#define configSUPPORT_DYNAMIC_ALLOCATION    0  /* Disable for MISRA compliance */

/* Required: implement these if static allocation enabled */
void vApplicationGetIdleTaskMemory(StaticTask_t **ppxIdleTaskTCBBuffer,
                                    StackType_t **ppxIdleTaskStackBuffer,
                                    uint32_t *pulIdleTaskStackSize);

void vApplicationGetTimerTaskMemory(StaticTask_t **ppxTimerTaskTCBBuffer,
                                     StackType_t **ppxTimerTaskStackBuffer,
                                     uint32_t *pulTimerTaskStackSize);
```

### Stack Size Guidelines

| Task Type        | Minimum Stack | Recommended |
| ---------------- | ------------- | ----------- |
| Minimal task     | 128 words     | 256 words   |
| Standard task    | 256 words     | 512 words   |
| Task with printf | 512 words     | 1024 words  |
| Network stack    | 1024 words    | 2048 words  |

---

## Task Patterns

### Static Task Creation

```c
#define SENSOR_TASK_STACK_SIZE    (512)
#define SENSOR_TASK_PRIORITY      (tskIDLE_PRIORITY + 2)

static StaticTask_t sensor_task_tcb;
static StackType_t sensor_task_stack[SENSOR_TASK_STACK_SIZE];
static TaskHandle_t sensor_task_handle;

void sensor_task_init(void)
{
    sensor_task_handle = xTaskCreateStatic(
        sensor_task_function,
        "Sensor",
        SENSOR_TASK_STACK_SIZE,
        NULL,
        SENSOR_TASK_PRIORITY,
        sensor_task_stack,
        &sensor_task_tcb
    );

    configASSERT(sensor_task_handle != NULL);
}

static void sensor_task_function(void *pvParameters)
{
    (void)pvParameters;  /* Unused */

    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(100);

    for (;;) {
        /* Periodic execution */
        read_sensors();
        process_data();

        /* Wait for next period */
        vTaskDelayUntil(&last_wake, period);
    }
}
```

### Task Notification Pattern

```c
/* More efficient than binary semaphore for single-producer single-consumer */
static TaskHandle_t consumer_task;

/* Producer (ISR or another task) */
void notify_consumer_from_isr(void)
{
    BaseType_t higher_priority_woken = pdFALSE;

    vTaskNotifyGiveFromISR(consumer_task, &higher_priority_woken);
    portYIELD_FROM_ISR(higher_priority_woken);
}

/* Consumer */
static void consumer_task_function(void *pvParameters)
{
    for (;;) {
        /* Block until notified */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        /* Process notification */
        handle_event();
    }
}
```

---

## Queue Patterns

### Static Queue

```c
#define MSG_QUEUE_LENGTH    16
#define MSG_QUEUE_ITEM_SIZE sizeof(message_t)

typedef struct {
    uint8_t type;
    uint8_t data[32];
    uint16_t length;
} message_t;

static StaticQueue_t msg_queue_struct;
static uint8_t msg_queue_storage[MSG_QUEUE_LENGTH * MSG_QUEUE_ITEM_SIZE];
static QueueHandle_t msg_queue;

void queue_init(void)
{
    msg_queue = xQueueCreateStatic(
        MSG_QUEUE_LENGTH,
        MSG_QUEUE_ITEM_SIZE,
        msg_queue_storage,
        &msg_queue_struct
    );

    configASSERT(msg_queue != NULL);
}
```

### ISR-Safe Queue Send

```c
void uart_rx_isr(void)
{
    message_t msg;
    BaseType_t higher_priority_woken = pdFALSE;

    /* Fill message from hardware */
    msg.type = MSG_TYPE_UART_RX;
    msg.length = uart_read(msg.data, sizeof(msg.data));

    /* Send to queue - don't block in ISR */
    if (xQueueSendFromISR(msg_queue, &msg, &higher_priority_woken) != pdPASS) {
        /* Queue full - handle overflow */
        g_queue_overflow_count++;
    }

    portYIELD_FROM_ISR(higher_priority_woken);
}
```

### Queue Receive with Timeout

```c
static void message_handler_task(void *pvParameters)
{
    message_t msg;

    for (;;) {
        /* Block for message with timeout */
        if (xQueueReceive(msg_queue, &msg, pdMS_TO_TICKS(1000)) == pdPASS) {
            switch (msg.type) {
            case MSG_TYPE_UART_RX:
                handle_uart_message(&msg);
                break;
            case MSG_TYPE_SENSOR:
                handle_sensor_message(&msg);
                break;
            default:
                LOG_WRN("Unknown message type: %d", msg.type);
                break;
            }
        } else {
            /* Timeout - perform periodic maintenance */
            check_watchdog();
        }
    }
}
```

---

## Mutex Patterns

### Static Mutex

```c
static StaticSemaphore_t flash_mutex_struct;
static SemaphoreHandle_t flash_mutex;

void flash_mutex_init(void)
{
    flash_mutex = xSemaphoreCreateMutexStatic(&flash_mutex_struct);
    configASSERT(flash_mutex != NULL);
}

bool flash_write_protected(uint32_t addr, const uint8_t *data, size_t len)
{
    bool success = false;

    /* Take mutex with timeout */
    if (xSemaphoreTake(flash_mutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
        success = flash_write(addr, data, len);
        xSemaphoreGive(flash_mutex);
    } else {
        LOG_ERR("Flash mutex timeout");
    }

    return success;
}
```

### Recursive Mutex (when nesting required)

```c
static StaticSemaphore_t config_mutex_struct;
static SemaphoreHandle_t config_mutex;

void config_init(void)
{
    config_mutex = xSemaphoreCreateRecursiveMutexStatic(&config_mutex_struct);
}

void config_update(const config_t *new_config)
{
    xSemaphoreTakeRecursive(config_mutex, portMAX_DELAY);

    /* Can call other config functions that also take mutex */
    validate_config(new_config);
    apply_config(new_config);
    save_config(new_config);

    xSemaphoreGiveRecursive(config_mutex);
}
```

---

## Event Group Patterns

### Multi-Event Synchronization

```c
#define EVENT_SENSOR_READY    (1 << 0)
#define EVENT_NETWORK_READY   (1 << 1)
#define EVENT_CONFIG_LOADED   (1 << 2)
#define EVENT_ALL_READY       (EVENT_SENSOR_READY | EVENT_NETWORK_READY | EVENT_CONFIG_LOADED)

static StaticEventGroup_t startup_events_struct;
static EventGroupHandle_t startup_events;

void events_init(void)
{
    startup_events = xEventGroupCreateStatic(&startup_events_struct);
}

/* Called by each subsystem when ready */
void signal_sensor_ready(void)
{
    xEventGroupSetBits(startup_events, EVENT_SENSOR_READY);
}

/* Main task waits for all systems */
void wait_for_startup(void)
{
    EventBits_t bits = xEventGroupWaitBits(
        startup_events,
        EVENT_ALL_READY,
        pdFALSE,            /* Don't clear on exit */
        pdTRUE,             /* Wait for ALL bits */
        pdMS_TO_TICKS(10000)
    );

    if ((bits & EVENT_ALL_READY) == EVENT_ALL_READY) {
        LOG_INF("All systems ready");
    } else {
        LOG_ERR("Startup timeout, bits=0x%lx", bits);
    }
}
```

---

## Timer Patterns

### Software Timer

```c
static StaticTimer_t watchdog_timer_struct;
static TimerHandle_t watchdog_timer;

static void watchdog_timer_callback(TimerHandle_t timer)
{
    (void)timer;

    /* Feed hardware watchdog */
    wdt_feed();
}

void watchdog_timer_init(void)
{
    watchdog_timer = xTimerCreateStatic(
        "Watchdog",
        pdMS_TO_TICKS(500),     /* Period */
        pdTRUE,                  /* Auto-reload */
        NULL,                    /* Timer ID */
        watchdog_timer_callback,
        &watchdog_timer_struct
    );

    xTimerStart(watchdog_timer, 0);
}
```

---

## Critical Section Patterns

### Task-Level Critical Section

```c
void safe_update_global(uint32_t value)
{
    taskENTER_CRITICAL();
    g_shared_value = value;
    g_update_count++;
    taskEXIT_CRITICAL();
}
```

### ISR-Level Critical Section

```c
void ISR_handler(void)
{
    UBaseType_t saved_interrupt_status;

    saved_interrupt_status = taskENTER_CRITICAL_FROM_ISR();

    /* Critical section - interrupts disabled */
    update_shared_data();

    taskEXIT_CRITICAL_FROM_ISR(saved_interrupt_status);
}
```

---

## Stack Monitoring

```c
/* Enable in FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW    2
#define configUSE_TRACE_FACILITY          1

/* Stack overflow hook */
void vApplicationStackOverflowHook(TaskHandle_t task, char *task_name)
{
    LOG_ERR("Stack overflow in task: %s", task_name);

    /* Reset or enter safe state */
    NVIC_SystemReset();
}

/* Monitor stack high water mark */
void print_stack_usage(void)
{
    TaskStatus_t task_status;
    TaskHandle_t tasks[] = {sensor_task_handle, network_task_handle};

    for (int i = 0; i < ARRAY_SIZE(tasks); i++) {
        vTaskGetInfo(tasks[i], &task_status, pdTRUE, eInvalid);
        LOG_INF("Task %s: stack high water mark = %lu words",
                task_status.pcTaskName,
                task_status.usStackHighWaterMark);
    }
}
```

---

## Anti-Patterns to Avoid

### Don't Block in ISR

```c
/* WRONG - blocks in ISR */
void bad_isr(void)
{
    xQueueSend(queue, &data, portMAX_DELAY);  /* NEVER DO THIS */
}

/* CORRECT - non-blocking */
void good_isr(void)
{
    BaseType_t woken = pdFALSE;
    xQueueSendFromISR(queue, &data, &woken);
    portYIELD_FROM_ISR(woken);
}
```

### Don't Use Dynamic Allocation

```c
/* WRONG - dynamic allocation */
QueueHandle_t queue = xQueueCreate(10, sizeof(msg_t));

/* CORRECT - static allocation */
static StaticQueue_t queue_struct;
static uint8_t storage[10 * sizeof(msg_t)];
QueueHandle_t queue = xQueueCreateStatic(10, sizeof(msg_t), storage, &queue_struct);
```

### Don't Spin Without Yield

```c
/* WRONG - CPU hog */
while (!flag) {
    /* Busy wait - blocks other tasks */
}

/* CORRECT - yield to other tasks */
while (!flag) {
    vTaskDelay(pdMS_TO_TICKS(1));
}

/* BETTER - use event/notification */
ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
```

---

## References

- FreeRTOS Kernel Developer Docs: <https://www.freertos.org/Documentation/>
- FreeRTOS API Reference: <https://www.freertos.org/a00106.html>
- nRF Connect SDK FreeRTOS Integration
- STM32Cube FreeRTOS CMSIS-RTOS2 Wrapper
