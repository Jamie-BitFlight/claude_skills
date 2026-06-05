---
name: find-cause
description: Wraps investigation requests with evidence-chain discipline. Use when asked to find out why something happens, research a root cause, debug an issue, or investigate unexpected behavior. Transforms vague investigation requests into reproducible-proof investigations with a 5-step protocol — disambiguate, reproduce, read source, build evidence chain, present findings. Invoke with /find-cause followed by a description of what to investigate.
argument-hint: <what to investigate>
---

<investigation_request>$ARGUMENTS</investigation_request>

# Find Cause

Rewrite the user's investigation request using the evidence-chain protocol below, then execute it. The user's original request is in `<investigation_request/>`.

## Evidence-Chain Protocol

<evidence_chain_rules>

Every claim in the investigation output MUST have a corresponding evidence entry. Evidence is one of:

1. **Command output** — a command was executed and the output was captured
2. **File content** — a file was read and a specific line range is cited
3. **Direct observation** — a reproducible state was observed (directory listing, process output, HTTP response)

These are NOT evidence:

- Documentation that describes intended behavior (docs describe intent, not reality)
- Training data recall or pattern matching
- Inference from absence ("the docs don't mention it, so it must not exist")
- Reasoning from analogy ("X works this way, so Y does too")

</evidence_chain_rules>

## Investigation Procedure

### Step 0 — Discover investigation capabilities

Before investigating, discover what tools, servers, and agents are available. Execute these in parallel:

1. **System diagnostic tools** — `command -v rg docker podman strace ltrace jq yq curl` and any domain-relevant tools
2. **MCP servers** — List connected MCP servers and their tools (use `ListMcpResourcesTool` or equivalent)
3. **Available agents** — Check `~/.claude/agents/` and `.claude/agents/` for specialized agents that could assist
4. **Active skills** — Review loaded skills for relevant investigation protocols
5. **Containerization** — Check for Docker/Podman if sandboxing may be needed: `command -v docker podman`

Record the results as an investigation capability matrix:

```text
AVAILABLE CAPABILITIES:
- System tools: [list]
- MCP servers: [server -> relevant tools]
- Agents: [agent -> specialization]
- Skills: [skill -> investigation protocols]
- Sandbox options: [docker/podman/temp dir/none]
```

This matrix informs which verification paths are fastest in Step 1.5 and which advanced tools to leverage in Steps 2-3.

### Step 1 — Disambiguate the question and define success criteria

Read the user's request in `<investigation_request/>`. Perform two tasks:

#### A. Formulate distinct interpretations

Formulate 2 or more distinct interpretations of what they are asking. Present these interpretations to the user using the `AskUserQuestion` tool so the user can select the correct one or provide their own clarification.

Each interpretation MUST be a concrete, falsifiable question — not a vague restatement. Frame each as "Are you asking X?" where X is specific enough to investigate.

Example for the request "find out why the tests fail":

- **Interpretation A**: "Why do tests fail when run locally but pass in CI?"
- **Interpretation B**: "Why does a specific test case produce an unexpected assertion error?"
- **Interpretation C**: "Why did tests start failing after a recent change?"

Do NOT proceed until the user has confirmed which interpretation is correct or provided their own.

If the user selects "Other" and provides additional context, reformulate the interpretations and ask again. Only proceed when you have a single, unambiguous question to investigate.

#### B. Define success criteria

For the confirmed interpretation, state what a conclusive answer looks like:

```text
QUESTION: [confirmed interpretation]
SUCCESS CRITERIA:
- Reproduced the behavior with observed evidence
- Traced the mechanism from symptom to cause with file:line citations
- Can state root cause as: "[observable condition X] causes [observable behavior Y] because [mechanism Z]"
- All claims in the evidence chain are VERIFIED: yes
```

Present the success criteria to the user for confirmation. Adjust if the user's definition of "done" differs.

Do NOT proceed to Step 1.5 until both interpretation and success criteria are confirmed.

### Step 1.5 — Prerequisite check and reproduction safety

Before investigating, assess two things: what you need to know, and whether reproduction is safe.

#### A. List unknowns and fastest verification paths

For each unknown in the investigation:

1. **State the unknown** — What do you need to know?
2. **Identify the fastest verification** — Can you observe it directly by running the system, or must you read source/docs? Consult the capability matrix from Step 0 to select the fastest available tool.
3. **Prefer direct observation** — If the system under investigation is available to run, running it produces observed facts. Reading source files and documentation to theorize about behavior is slower and less reliable.

If any unknown can be resolved by running the system, that verification MUST happen in Step 2 (reproduction), not through source reading or documentation research.

#### B. Classify reproduction constraints

<reproduction_safety>

Determine whether the problem has **bound** or **unbound** constraints:

**Bound constraints** — You can see the full system and evaluate the risks yourself:

- You can read the relevant files, understand what the operation does, and assess its effects
- All inputs, variables, and side effects are visible and evaluable
- You can determine whether reproduction is safe, destructive, or requires precautions
- Examples: a skill you can read and activate, a script whose behavior you can trace, a config you can parse

**Action**: Evaluate the risk. If safe, proceed to Step 2. If destructive or risky, establish precautions (temp directory, dry-run flag, backup) before reproducing. Do not ask the user further questions until you encounter something you cannot evaluate yourself.

**Unbound constraints** — You cannot see or evaluate the full system:

The operation involves systems you cannot inspect, infrastructure you do not have access to, credentials you do not possess, inputs/variables you cannot observe, or side effects you cannot predict.

**Action**: Before reproducing, batch ALL questions into a single `AskUserQuestion` interaction:

```text
INVESTIGATION SAFETY CHECK — answering all questions lets me proceed autonomously.

1. DESTRUCTIVE OPERATIONS: Does this operation delete data, send messages, modify shared state, deploy code, or have irreversible side effects? If yes, what precautions exist (backups, dry-run, test env)?

2. SANDBOX: Which sandbox should I use? (Docker container / temp directory / CI pipeline / remote host / local VM / local execution is safe)

3. MISSING INPUTS: I have [list known inputs]. I need [list missing inputs with specific questions].

4. OVERSIGHT LEVEL:
   - Before each step (high oversight)
   - Only on unexpected findings (autonomous with exceptions)
   - After investigation complete (fully autonomous)

5. BLIND SPOTS: What aspects of this system might I not see or misunderstand?
```

</reproduction_safety>

#### C. Determine execution mode

Based on the constraint classification:

**Autonomous mode** (bound constraints, or user selected autonomous oversight): Execute Steps 2-4 completely. Present findings in Step 5. Only interrupt if an unforeseen unbound constraint is encountered.

**Check-in mode** (unbound constraints, or user selected high oversight): Complete what you can with bound constraints. Document findings and gaps. Ask user before crossing any unbound boundary.

**Mid-investigation constraint discovery**: If you encounter an unbound constraint after starting autonomous execution — STOP. Document what you have verified so far. Use `AskUserQuestion` to batch: what access is needed, whether partial findings are acceptable, and whether an alternative verification path exists.

Do NOT proceed to Step 2 until: (bound) you have confirmed reproduction is safe, or (unbound) the user has provided the missing inputs and sandbox strategy.

### Step 2 — Reproduce and observe the problem

Execute the **same operation the user performed**, end-to-end, while observing its complete behavior. Not adjacent diagnostic commands — the actual operation. Not reading about what should happen — watching what does happen.

Reproduction IS observation. You must see the failure mechanism, not just confirm the failure occurred.

- If the user activated a skill, activate that skill
- If the user ran a command, run that command
- If the user triggered a workflow, trigger that workflow
- If the operation is destructive, execute it in the sandbox established in Step 1.5

Capture:

1. **Complete command/action** with all arguments, flags, environment variables
2. **Complete output** — stdout and stderr, not just the final line
3. **Exit code or observable result**
4. **Side effects** — files changed, network calls made, processes spawned
5. **Timing** — immediate failure, delayed, intermittent

**Anti-pattern**: Running `ls`, `env`, `grep` to diagnose the environment before reproducing. Those are Step 3 activities (source reading). Step 2 is experiencing the failure firsthand.

Build evidence as you go:

```text
CLAIM: [What the system did when reproduced]
EVIDENCE: Bash — executed [command], captured [output], exit code [N]
VERIFIED: yes
DEPENDS ON: none (reproduction — primary observation)
```

If reproduction diverges from the user's report (succeeds when it should fail, or vice versa), document what you did differently and what environmental differences might explain the divergence.

If you cannot reproduce the operation, state that and ask the user for reproduction steps.

Do NOT skip this step by relying on a transcript or description of the failure. Run it yourself.

### Step 3 — Read the source

Read the files involved in the failure. Cite file paths and line numbers for every relevant code path. Do not summarize — quote the specific lines that matter.

Leverage capabilities discovered in Step 0: use MCP servers for documentation lookup, specialized agents for domain analysis, and system tools (strace, network inspection) for runtime behavior that source reading alone cannot reveal.

Build evidence entries as you read:

```text
CLAIM: [What the source code does at this point]
EVIDENCE: Read — [file:lines] show [quoted content]
VERIFIED: yes
DEPENDS ON: [claim numbers from Step 2 that led you to this code path]
```

### Step 4 — Build the evidence chain

Assemble claims from Steps 2-3 into a logical chain where each claim depends on prior claims and traces from observable symptom to root cause.

Chain structure follows this pattern:

```text
SYMPTOM (what the user observed)
  -> MECHANISM (what actually happened during reproduction)
    -> PROXIMATE CAUSE (what code path or condition triggered the mechanism)
      -> ROOT CAUSE (why that condition exists)
```

Entry format:

```text
CLAIM: [What you assert]
EVIDENCE: [Tool] — [file:line or command:output]
VERIFIED: [yes/no]
DEPENDS ON: [Prior claim numbers that must be true for this claim to hold]
```

If a claim depends on documentation describing intended behavior, training data recall, inference from absence, or reasoning by analogy — mark it `VERIFIED: no` and state what direct observation would make it verifiable.

If a claim cannot be verified with available tools, mark it `VERIFIED: no` and state what verification step is missing.

### Step 5 — Present findings

Structure the output as:

```text
QUESTION: [Restated from Step 1]

SUCCESS CRITERIA MET: [yes/partial/no — against criteria defined in Step 1B]

EVIDENCE CHAIN:
1. CLAIM: ...
   EVIDENCE: ...
   VERIFIED: yes
   DEPENDS ON: none (symptom)

2. CLAIM: ...
   EVIDENCE: ...
   VERIFIED: yes
   DEPENDS ON: 1

3. CLAIM: ...
   EVIDENCE: ...
   VERIFIED: yes
   DEPENDS ON: 1, 2

ROOT CAUSE: [Single statement supported by the chain above]
DEPENDS ON: [claim numbers]

UNVERIFIED ITEMS: [List any claims marked VERIFIED: no, with what would make them conclusive]
```

## Prohibited Behaviors

- Do NOT present inferences as conclusions
- Do NOT use words "probably", "likely", "seems", "I think", "I believe", "I assume"
- Do NOT assert causality without citing the observed evidence that supports it
- Do NOT skip reproduction by referencing a user-provided transcript — reproduce it yourself
- Do NOT fill gaps with theories — state "I don't have that information" and describe what tool or action would fill the gap
- Do NOT investigate components of a system before reproducing the system's behavior end-to-end — reproduction eliminates unknowns that component inspection cannot
- Do NOT ask the user multiple times when questions can be batched into a single interaction
- Do NOT proceed past an unverified DEPENDS ON claim — if claim N is unverified and claim M depends on N, claim M is automatically suspect
