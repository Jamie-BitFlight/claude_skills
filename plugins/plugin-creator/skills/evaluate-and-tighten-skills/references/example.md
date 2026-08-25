# Example

Given:

````markdown
```text
Then stamp the run so this invocation gets its own address. Run this command and capture its
stdout as `run_stamp` - a plain script invocation, not a shell pipeline, so it runs unchanged under
bash, PowerShell, or cmd.exe:
...

The UTC timestamp alone only has whole-second resolution...
gen_run_stamp.py draws 8 bytes (64 bits) from secrets.token_hex...
```
````

Classification:

* "run this command" -> DOES
* "capture its stdout as `run_stamp`" -> DOES
* resolvable script path -> RESOLVES
* shell-portability explanation -> EXPLAINS
* timestamp-resolution discussion -> EXPLAINS
* CSPRNG implementation discussion -> EXPLAINS

If the contract requires the agent to obtain a suitable run address through the supplied script, you would reduce it to:

````markdown
```text
Then stamp the run so this invocation gets its own address. Run this command and capture its
stdout as `run_stamp`:
```

```text
uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/gen_run_stamp.py"
```
````

The mechanism belongs to the script. The skill carries the instruction needed to use it.

## Maintenance placement

Given:

````markdown
```text
Run the stamp script. We originally used `date +%s%N` piped through `md5sum` for this, but
that produced collisions when two orchestrators launched runs in the same millisecond (see
#142), so we switched to the token_hex-based script.

The script must be invoked exactly once per run. Invoking it twice for the same run silently
produces two different stamps, and this same fixed-length hex format is also assumed by the
concurrency lock and the archival cleanup job.
```
````

Disposition:

* "Run the stamp script." -> DOES -> KEEP-RUNTIME.
* "We originally used `date +%s%N`... so we switched..." plus "(see #142)" -> EXPLAINS, a rejected approach with no present consequence -> DELETE. The issue link provided provenance for history that no longer matters, not for a current invariant, so it is deleted along with the narrative rather than kept.
* "The script must be invoked exactly once per run... silently produces two different stamps" -> non-obvious invariant scoped to this one script -> MOVE-LOCAL: add to `gen_run_stamp.py`'s own docstring — "Idempotency: call once per run; repeated calls return different values with no error."
* "...this same fixed-length hex format is also assumed by the concurrency lock and the archival cleanup job" -> non-obvious, cross-cutting, still constrains present changes -> MOVE-MAINTENANCE entry in `MAINTENANCE.md`:

  ```markdown
  ## Invariants

  - Run-stamp format is fixed-length hex.
    - Owned by: gen_run_stamp.py, concurrency lock, archival cleanup
    - Origin: #142
  ```

Reduced `SKILL.md`:

````markdown
```text
Run the stamp script. Invoke it exactly once per run.
```
````

The rejected `date`/`md5sum` approach and the collision history are gone entirely — git history and #142 still hold them if ever needed. What remains is placed where each maintainer will actually encounter it: the script's own docstring for its local behavior, `MAINTENANCE.md` for the cross-cutting constraint other components rely on. Nothing was copied wholesale — each entry states only the smallest durable fact.
