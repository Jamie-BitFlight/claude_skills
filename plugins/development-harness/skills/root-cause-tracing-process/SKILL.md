---
name: root-cause-tracing-process
description: Root-cause tracing with an evidence chain — reproduce the failure, read the source, and cite every claim from symptom to root cause; when the failure does not reproduce, falsify H0/Ha hypotheses by experiment until one survives. Use when an agent must establish why a bug, test failure, or unexpected behavior happens before fixing it.
argument-hint: <QUESTION and SUCCESS CRITERIA>
---

<tracing_input>$ARGUMENTS</tracing_input>

# Root-Cause Tracing Process

## Inputs

`<tracing_input/>` holds the caller's QUESTION and SUCCESS CRITERIA in this format, a raw request, or nothing:

```text
QUESTION: [confirmed interpretation]
SUCCESS CRITERIA:
- Reproduced the behavior with observed evidence
- Traced the mechanism from symptom to cause with file:line citations
- Can state root cause as: "[observable condition X] causes [observable behavior Y] because [mechanism Z]"
- All claims in the evidence chain are VERIFIED: yes
```

When `<tracing_input/>` holds a raw request, write the QUESTION and SUCCESS CRITERIA from it in this format before Step 0. When it is empty, take them from the conversation that loaded this skill, and write them from the request there when the conversation has none.

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

If you cannot reproduce the operation, state that. When a user is in the conversation, ask for their reproduction steps and retry Step 2 with them. Otherwise, or if their steps also fail, continue at Step 2B.

Do NOT skip this step by relying on a transcript or description of the failure. Run it yourself.

### Step 2B — Non-reproducible failure: falsify a hypothesis

Work the failure as an experiment.

1. Record every observation you hold — the report, logs, timings, and the conditions of each failing and passing run — as evidence entries.
2. State a falsifiable pair about one condition X that you can set:
   - **H0**: X has no effect on the failure.
   - **Ha**: X causes the failure.
3. Write the prediction: "If Ha holds, running the operation with X set produces observable Z. If H0 holds, it does not produce Z."
4. Design the experiment that could falsify Ha: vary X, hold the other conditions fixed, and list each confound that could produce Z without X.
5. Run the experiment as many times as the failure's observed frequency needs for Z to appear, and record each output verbatim as evidence entries.
6. Decide from the evidence:
   - Z absent in every run: Ha is falsified. Record it, form the next Ha from what the runs showed, and return to item 2.
   - Z present with a confound uncontrolled: control that confound and return to item 5.
   - Z present with the confounds controlled: Ha survives. Setting X is now the reproduction. Continue at Step 3 with it.

Step 2B is complete when Ha survives and gives a reproduction, or when you stop and list every falsified Ha, with its evidence and the next experiment to run, under UNVERIFIED ITEMS in Step 5.

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
QUESTION: [the QUESTION from Inputs]

SUCCESS CRITERIA MET: [yes/partial/no — against the SUCCESS CRITERIA from Inputs]

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
