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

* "run this command" -> **DOES**
* "capture its stdout as `run_stamp`" -> **DOES**
* resolvable script path -> **RESOLVES**
* shell-portability explanation -> **EXPLAINS**
* timestamp-resolution discussion -> **EXPLAINS**
* CSPRNG implementation discussion -> **EXPLAINS**

If the contract requires the agent to obtain a suitable run address through the supplied script, you would reduce it to:

````markdown
```text
Then stamp the run so this invocation gets its own address. Run this command and capture its
stdout as `run_stamp`:
```

```text
${CLAUDE_SKILL_DIR}/scripts/gen_run_stamp.py
```
````

The mechanism belongs to the script. The skill carries the instruction needed to use it.
