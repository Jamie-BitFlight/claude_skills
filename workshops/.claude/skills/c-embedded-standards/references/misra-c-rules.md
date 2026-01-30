# MISRA-C 2012 Rules Reference

Subset of MISRA-C 2012 rules most relevant to embedded firmware development.

## Directive Categories

| Category      | Meaning                                                |
| ------------- | ------------------------------------------------------ |
| **Required**  | Must be followed; deviations need formal documentation |
| **Advisory**  | Should be followed; deviations need rationale          |
| **Mandatory** | Must always be followed; no deviations permitted       |

---

## Memory and Pointers (Rules 11.x, 18.x)

### Rule 11.3 (Required)

**A cast shall not be performed between a pointer to object type and a pointer to a different object type**

```c
// VIOLATION
uint8_t buffer[4];
uint32_t *ptr = (uint32_t *)buffer;  // Alignment issues possible

// COMPLIANT - use memcpy
uint32_t value;
memcpy(&value, buffer, sizeof(value));
```

### Rule 11.4 (Required)

**A conversion shall not be performed between a pointer to object and an integer type**

```c
// VIOLATION
volatile uint32_t *reg = (uint32_t *)0x40000000;

// COMPLIANT - use platform abstraction
#define PERIPH_BASE ((volatile uint32_t *)0x40000000)
volatile uint32_t *reg = PERIPH_BASE;
```

### Rule 18.1 (Required)

**A pointer resulting from arithmetic on a pointer operand shall address an element of the same array**

```c
// VIOLATION - potential out-of-bounds
int arr[10];
int *ptr = arr + 15;  // Beyond array bounds

// COMPLIANT - bounds checking
if (index < ARRAY_SIZE(arr)) {
    int *ptr = arr + index;
}
```

---

## Control Flow (Rules 14.x, 15.x, 16.x)

### Rule 14.3 (Required)

**Controlling expressions shall not be invariant**

```c
// VIOLATION - always true
if (1) {
    do_something();
}

// COMPLIANT
if (config_enabled) {
    do_something();
}
```

### Rule 15.1 (Advisory)

**The goto statement should not be used**

```c
// AVOID
if (error) goto cleanup;

// PREFER - structured cleanup
bool success = false;
do {
    if (!step1()) break;
    if (!step2()) break;
    success = true;
} while (0);

cleanup_resources();
return success;
```

### Rule 16.2 (Required)

**A switch label shall only be used when the most closely-enclosing compound statement is the body of a switch statement**

```c
// VIOLATION - case inside if
switch (x) {
case 1:
    if (y) {
case 2:  // VIOLATION
        do_something();
    }
    break;
}
```

---

## Functions (Rules 17.x)

### Rule 17.2 (Required)

**Functions shall not call themselves, either directly or indirectly**

```c
// VIOLATION - direct recursion
uint32_t factorial(uint32_t n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);  // VIOLATION
}

// COMPLIANT - iterative
uint32_t factorial(uint32_t n) {
    uint32_t result = 1;
    for (uint32_t i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}
```

### Rule 17.7 (Required)

**The value returned by a function having non-void return type shall be used**

```c
// VIOLATION - ignoring return value
fclose(file);  // fclose returns int

// COMPLIANT - check return value
if (fclose(file) != 0) {
    LOG_ERR("Failed to close file");
}

// COMPLIANT - explicit discard (if truly intentional)
(void)fclose(file);  // Document why this is acceptable
```

---

## Standard Library (Rules 21.x)

### Rule 21.3 (Required)

**The memory allocation and deallocation functions of <stdlib.h> shall not be used**

```c
// VIOLATION
char *buffer = malloc(256);

// COMPLIANT - static allocation
static char buffer[256];

// COMPLIANT - pool allocation
char *buffer = memory_pool_alloc(&pool, 256);
```

### Rule 21.6 (Required)

**The Standard Library input/output functions shall not be used**

For production firmware, avoid `printf`, `scanf`, `fopen`, etc. Use platform-specific logging and I/O.

### Rule 21.7 (Required)

**The Standard Library functions atof, atoi, atol and atoll shall not be used**

```c
// VIOLATION - no error detection
int value = atoi(str);

// COMPLIANT - error detection
char *endptr;
errno = 0;
long value = strtol(str, &endptr, 10);
if (errno != 0 || endptr == str) {
    // Handle error
}
```

---

## Type Safety (Rules 10.x)

### Rule 10.1 (Required)

**Operands shall not be of an inappropriate essential type**

```c
// VIOLATION - mixing signed/unsigned
int32_t signed_val = -1;
uint32_t unsigned_val = 5;
if (signed_val < unsigned_val) {  // May not behave as expected
}

// COMPLIANT - explicit conversion
if (signed_val < 0 || (uint32_t)signed_val < unsigned_val) {
}
```

### Rule 10.3 (Required)

**The value of an expression shall not be assigned to an object with a narrower essential type**

```c
// VIOLATION
uint32_t large = 0x12345678;
uint8_t small = large;  // Truncation

// COMPLIANT - explicit handling
uint8_t small = (uint8_t)(large & 0xFF);
```

---

## Declaration and Definition (Rules 8.x)

### Rule 8.4 (Required)

**A compatible declaration shall be visible when an object or function with external linkage is defined**

```c
// VIOLATION - no declaration visible
void my_function(void) {  // No prototype in header
    // ...
}

// COMPLIANT
// In header: void my_function(void);
// In source:
void my_function(void) {
    // ...
}
```

### Rule 8.13 (Advisory)

**A pointer should point to a const-qualified type whenever possible**

```c
// IMPROVE
void process_data(uint8_t *data, size_t len);

// BETTER - indicates no modification
void process_data(const uint8_t *data, size_t len);
```

---

## References

- MISRA C:2012 Guidelines for the use of the C language in critical systems
- MISRA C:2012 Amendment 1 (additional security guidelines)
- [MISRA Compliance](https://www.misra.org.uk/)
