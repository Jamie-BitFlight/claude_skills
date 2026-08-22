# Common Failure Patterns and Verification Prevention

This document catalogs real-world examples of verification failures and demonstrates how the verification gate checkpoints prevent them.

## Pattern 1: The PEP 723 Misalignment

### Failure Sequence

**Observation:** `ModuleNotFoundError: No module named 'pydantic'`

**What Happened:**

1. Claude correctly identified: "PEP 723 dependencies aren't installed"
2. Claude then executed: `uv sync` (operates on pyproject.toml)
3. Verification gate NOT activated
4. Action targeted different system than hypothesis

### Root Cause

**Hypothesis system:** PEP 723 inline `# /// script` metadata **Action system:** pyproject.toml via `uv sync` **Misalignment:** Different dependency management systems

### How Verification Gate Prevents This

**Checkpoint 3 would have blocked:**

```text
┌─────────────────────────────────────────────────────────┐
│ HYPOTHESIS SYSTEM: PEP 723 inline script metadata      │
│                    (# /// script dependencies block)    │
├─────────────────────────────────────────────────────────┤
│ ACTION SYSTEM:     pyproject.toml dependencies          │
│                    (uv sync operates on this file)      │
├─────────────────────────────────────────────────────────┤
│ ALIGNMENT CHECK:   ✗ BLOCKED - Different systems       │
└─────────────────────────────────────────────────────────┘

EXECUTION BLOCKED
Failed checkpoint: 3 (Hypothesis-Action Alignment)
Reason: PEP 723 uses inline # /// script block, not pyproject.toml
Required before proceeding: Read script file to verify # /// block
```

**Correct action sequence:**

1. Read script file: `Read(file_path="packages/reset_all_tokens/cli.py", limit=50)`
2. Locate `# /// script` block in file
3. Verify pydantic in dependencies list
4. If missing: add pydantic to `# /// script` block
5. If present: investigate why `uv run` not installing it

### Lesson Learned

Pattern-matching ("ModuleNotFoundError" → `uv sync`) overrode explicit reasoning ("PEP 723" → inline metadata). Checkpoint 3 would have caught the system misalignment.

## Pattern 2: Configuration File Confusion

### Failure Scenario

**Observation:** Application ignores new timeout configuration in config.yaml

**Common mistake:**

1. Hypothesis: "Application not reading config.yaml"
2. Action: Modify config.yaml with different syntax/location
3. Actual problem: Application reads environment variable first, config.yaml is fallback

### Root Cause

Didn't verify configuration loading order. Pattern-matched "config not working" → "fix config file" without checking if config file is even being read.

### How Verification Gate Prevents This

**Checkpoint 2 requires evidence:**

```text
BLOCKED - Hypothesis not verified
REQUIRED: Gather evidence before proceeding
NEXT STEPS:
1. Grep for configuration loading code
2. Identify what sources are checked and in what order
3. Document findings with file paths and line numbers
4. Revise hypothesis if evidence contradicts it
```

**Correct sequence:**

1. Grep: `Grep(pattern="config.*yaml|load.*config", path="src/")`
2. Read: Configuration loader function
3. Observe: `config = os.getenv('TIMEOUT') or load_yaml('config.yaml')`
4. Revised hypothesis: "Environment variable overrides config.yaml"
5. Correct action: Set environment variable, not modify config.yaml

**Checkpoint 3 alignment:**

- Hypothesis system: Environment variable configuration
- Action system: Environment variable (export/set command)
- ✓ ALIGNED

### Lesson Learned

Must verify configuration precedence before modifying configuration files. Many applications have layered configs (env vars → CLI flags → config files → defaults).

## Pattern 3: Docker Network Layer Confusion

### Failure Scenario

**Observation:** Container can't reach external API

**Common mistake:**

1. Hypothesis: "Network connectivity issue"
2. Action: Modify host network settings
3. Actual problem: Container using bridge network, needs DNS configuration

### Root Cause

Didn't verify which network layer the problem affects. Pattern-matched "network problem" → "fix network" without identifying container vs host vs routing layer.

### How Verification Gate Prevents This

**Checkpoint 1 requires specific system:**

```text
BLOCKED - Hypothesis not stated
REQUIRED: State hypothesis explicitly before proceeding
EXAMPLE: "Hypothesis: The issue affects [specific system/component]"

❌ Too vague: "Network connectivity issue"
✓ Specific: "Container bridge network lacks DNS resolver for external domains"
```

**Checkpoint 3 catches layer misalignment:**

```text
┌─────────────────────────────────────────────────────────┐
│ HYPOTHESIS SYSTEM: Container bridge network             │
│                    (Docker networking layer)            │
├─────────────────────────────────────────────────────────┤
│ ACTION SYSTEM:     Host network settings                │
│                    (/etc/resolv.conf, firewall)         │
├─────────────────────────────────────────────────────────┤
│ ALIGNMENT CHECK:   ✗ BLOCKED - Different network layers│
└─────────────────────────────────────────────────────────┘
```

**Correct action:**

- Hypothesis system: Container network configuration
- Action system: Docker network settings (--dns flag, network creation)
- ✓ ALIGNED

### Lesson Learned

Network issues span multiple layers (application → container → host → external). Must identify specific layer before acting.

## Pattern 4: Python Virtual Environment Scope Confusion

### Failure Scenario

**Observation:** `pip install package` but Python script still can't import it

**Common mistake:**

1. Hypothesis: "Package not installed"
2. Action: `pip install package` (again, in different venv/global)
3. Actual problem: Script running in virtual environment, pip installed globally

### Root Cause

Didn't verify which Python/pip executable is being used. Multiple Python installations and virtual environments common.

### How Verification Gate Prevents This

**Checkpoint 2 requires evidence:**

```text
Evidence gathering required:
1. which python  # Which Python is active?
2. which pip     # Which pip is active?
3. python -c "import sys; print(sys.prefix)"  # Which environment?
4. pip show package  # Where is package installed?
```

**Checkpoint 4 catches pattern-matching:**

```text
⚠ PATTERN-MATCHING WARNING
I am using training data patterns without project verification.

DETECTED: "pip install" as reflexive response to ImportError
REQUIRED:
1. Verify which Python interpreter script uses
2. Verify which pip corresponds to that Python
3. Install to correct environment
```

**Correct sequence:**

1. Check script shebang or venv activation
2. Verify `which python` matches expected environment
3. Use environment-specific pip OR use `python -m pip install`
4. Verify with `python -c "import package"`

### Lesson Learned

"Package not found" has multiple causes (wrong environment, wrong version, wrong interpreter). Must verify environment before installing.

## Pattern 5: Git State vs File System State

### Failure Scenario

**Observation:** Code review comment says "function X is missing"

**Common mistake:**

1. Hypothesis: "Function X doesn't exist in codebase"
2. Action: Implement function X
3. Actual problem: Function X exists but in unstaged changes

### Root Cause

Didn't distinguish between git repository state (committed), working tree state (staged), and actual file state (unstaged). Reviewer saw committed state, developer working with file state.

### How Verification Gate Prevents This

**Checkpoint 2 demands evidence from correct context:**

```text
Evidence gathering:
1. git show HEAD:path/to/file.py  # What's in committed state?
2. git diff --staged path/to/file.py  # What's in staged state?
3. cat path/to/file.py  # What's in working file?

Hypothesis refinement:
❌ "Function X missing" (incomplete)
✓ "Function X exists in working tree but not in committed history"
```

**Correct action:**

- If function in working tree: Stage and commit
- If function not in working tree: Verify reviewer's context (which branch/commit?)

### Lesson Learned

"Missing" depends on context (git HEAD, staging, working directory, specific commit, specific branch). Must verify which context reviewer/user refers to.

## Pattern 6: Application Code vs Infrastructure Configuration

### Failure Scenario

**Observation:** Application returns 500 error under load

**Common mistake:**

1. Hypothesis: "Application has performance bug"
2. Action: Optimize application code
3. Actual problem: Infrastructure timeout (nginx, load balancer) too low

### Root Cause

Didn't verify at which layer the failure occurs. Pattern-matched "performance problem" → "optimize code" without checking infrastructure.

### How Verification Gate Prevents This

**Checkpoint 1 requires specific layer:**

```text
❌ Too vague: "Performance problem"
✓ Specific options to investigate:
- "Application processing timeout (code layer)"
- "Infrastructure request timeout (nginx/LB layer)"
- "Database query timeout (data layer)"
- "Network timeout (connectivity layer)"

Evidence needed to choose:
- Application logs: Does handler complete?
- Nginx logs: Does nginx return 504 Gateway Timeout?
- Database logs: Does query complete?
```

**Checkpoint 3 catches layer misalignment:**

```text
If hypothesis = "Infrastructure timeout"
And action = "Optimize application code"
Then BLOCKED - different operational layers
```

**Correct diagnostic sequence:**

1. Check error code: 500 vs 502 vs 504 (each indicates different layer)
2. Check application logs: Did handler execute?
3. Check infrastructure logs: Where did request die?
4. Formulate layer-specific hypothesis
5. Take action on correct layer

### Lesson Learned

Performance issues span multiple layers. Error code and logs indicate layer. Must target correct layer with action.

## Pattern 7: Test Failure Pattern Matching

### Failure Scenario

**Observation:** Test fails with assertion error

**Common mistake:**

1. Hypothesis: "Test assertion is wrong"
2. Action: Change test assertion to pass
3. Actual problem: Code behavior changed, test correctly identifies regression

### Root Cause

Pattern-matched "test fails" → "fix test" without verifying if test expectation is correct.

### How Verification Gate Prevents This

**Checkpoint 2 requires evidence:**

```text
Evidence gathering:
1. Read test to understand WHAT it's testing
2. Read code to understand current BEHAVIOR
3. Read git history: Did behavior change recently?
4. Check if test expectation matches specification

Hypothesis paths:
Path A: "Test expectation incorrect" (fix test)
Path B: "Code behavior regressed" (fix code)
Path C: "Specification changed" (update both)
```

**Checkpoint 4 catches reflexive test-fixing:**

```text
⚠ PATTERN-MATCHING WARNING
DETECTED: Immediate test modification without verification
REQUIRED:
1. Verify what behavior test expects
2. Verify what behavior code implements
3. Verify which is correct per specification
4. Only then decide whether to fix test or code
```

### Lesson Learned

Test failures mean "code and test disagree" - must determine which is correct. Never reflexively change tests to match code.

## Meta-Pattern: Cognitive Dissonance Resolution

### Universal Failure Mode

**Structure:**

1. Observation triggers pattern recognition (System 1)
2. Explicit reasoning identifies correct system (System 2)
3. Pattern recognition overrides explicit reasoning
4. Action executes on pattern-matched system, not reasoned system

**Example:**

- System 2: "PEP 723 dependencies" (explicitly stated)
- System 1: "ModuleNotFoundError" → `uv sync` (pattern-matched)
- System 1 wins without verification gate

### Why This Happens

**Cognitive architecture:**

- Pattern recognition is fast (single forward pass)
- Verification requires sequential tool calls (Read/Grep/WebFetch)
- Without structural gate, fast path wins

**Solution:** Verification gates add latency to System 1 path, allowing System 2 reasoning to catch up. Mandatory checkpoints before action execution prevent pattern-matching override.

### Verification Gate as Cognitive Brake

**Without gate:**

```text
Observation → Pattern Recognition → Action
            ↓
        Explicit Reasoning (too slow, overridden)
```

**With gate:**

```text
Observation → Pattern Recognition --------┐
            ↓                              ↓
        Explicit Reasoning → Verification Gate → Action
                                   ↑
                           (BLOCKS if misaligned)
```

Gate forces System 1 and System 2 to synchronize before action.

## Summary: Failure Prevention by Checkpoint

### Checkpoint 1: Hypothesis Stated

**Prevents:**

- Vague problem statements
- Acting without diagnosis
- Skipping problem identification

**Catches:**

- "Network issue" (too vague → requires layer specification)
- "Not working" (too vague → requires system specification)

### Checkpoint 2: Hypothesis Verified

**Prevents:**

- Assumption-based actions
- Pattern-matching solutions
- Unverified diagnoses

**Catches:**

- Acting on "probably X" without checking
- Assuming configuration precedence without reading code
- Assuming environment state without verification

### Checkpoint 3: Hypothesis-Action Alignment

**Prevents:**

- System layer confusion
- Targeting wrong component
- Cognitive dissonance (correct diagnosis, wrong action)

**Catches:**

- PEP 723 hypothesis → pyproject.toml action
- Container network hypothesis → host network action
- Application code hypothesis → infrastructure config action

### Checkpoint 4: Pattern-Matching Detection

**Prevents:**

- Training data override
- Reflexive solutions
- Non-project-specific actions

**Catches:**

- "Standard practice" without project verification
- Immediate solution without investigation
- Generic approach without project context

## Usage in Practice

When reviewing past work for verification failures:

1. **Identify the misalignment:** What system did hypothesis identify vs what system did action target?
2. **Determine which checkpoint would have blocked it:** Usually Checkpoint 3 (alignment)
3. **Extract the lesson:** What evidence-gathering would have revealed the misalignment?
4. **Document the pattern:** Add to this reference for future prevention
