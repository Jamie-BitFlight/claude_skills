# Silent Failure Prevention

## Write Operations Must Report What Changed

Functions that perform side effects (file writes, API calls, database updates) must return a value indicating what changed — `bool`, count, or diff. Callers must use that value in user-facing output.

**Wrong:**

```python
def sync_to_remote(data):
    try:
        remote.update(data)
    except RemoteError:
        return False
    # BUG: returns True even if update was a no-op
    return True
```

**Right:**

```python
def sync_to_remote(data) -> bool:
    old = remote.read()
    new = merge(old, data)
    if new == old:
        return False
    remote.update(new)
    return True
```

Callers distinguish outcomes:

```python
if sync_to_remote(data):
    print("Synced")
else:
    print("No changes to sync")
```

## Branching on Input Values Requires an Explicit Fallback

Every `if`/`elif` chain or match on an input value must have a final branch that either acts or errors. Falling through to `return unchanged` without logging is a silent data loss bug.

**Wrong:**

```python
if name in KNOWN_SECTIONS:
    return replace_section(body, name, content)
# BUG: unknown name silently returns body unchanged
return body
```

**Right:**

```python
if name in SPECIAL_SECTIONS:
    return replace_special(body, name, content)
# Fallback: treat as generic section
return replace_generic(body, name, content)
```

If no fallback action is possible, raise or warn:

```python
raise ValueError(f"Unrecognized section: {name}")
```
