---
name: code-review-llm
description: Reviews LLM integration, prompt templates, model selection, token/cost budgets, evaluation harnesses, structured outputs, retries, and streaming. Checks trust boundaries and task evidence against the selected provider/model contract rather than prescribing universal model tiers or sampling settings.
user-invocable: false
---

# LLM Integration Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when prompt files, model selection logic, or evaluation harness code are detected.

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria. Verify model identifiers, request
parameters, and error semantics against the provider and SDK version the target actually uses.

## Prompt Hygiene

- Keep instruction authority distinguishable from user/retrieved content. Trace where untrusted text can influence instructions, tool arguments, or consequential actions.
- Check that user-controlled content is treated as data at its intended boundary. String interpolation, escaping, role separation, or templating alone does not establish resistance to prompt injection.
- Review prompt composition for accidental instruction mixing, missing delimiters, or lost context using concrete inputs; do not report every f-string as an injection defect.
- Recommend dedicated prompt resources when versioning, reuse, or review clarity benefits; do not impose a line-count rule on inline strings.

## Model Selection

- Evaluate the selected model against the task's quality, cost, latency, and reproducibility requirements using relevant evidence. Do not infer a cost or quality regression solely from a tier name or task label.
- Check the selection rationale and configuration ownership, including fallback behavior when the chosen model is unavailable.
- Verify that model identifiers are valid for the provider API or harness field being used. Choose pinned identifiers or aliases according to the target's reproducibility/update contract; do not substitute harness tier names into an unrelated API.

```python
# The configured identifier must match the selected provider and release policy.
model = config.model_identifier
```

## Context Management

- Trace context growth against the selected model's input/output budgets and the application's supported workload; report overflow or loss of required context with the affected scenario.
- Check that any truncation, summarization, or retention strategy preserves the task's important instructions, evidence, and state. Turn count alone does not determine context size.
- Token count must be tracked and logged — silent context truncation is harder to debug than explicit overflow handling

## Token Economics

- Token count must be estimated before sending requests in batch or high-volume operations — surprise cost overruns from unexpectedly large inputs are preventable
- Fail fast on oversize inputs rather than truncating silently — silent truncation corrupts the task without surfacing an error
- For programmatic consumers, evaluate supported structured-output modes against the required schema, failure behavior, and measured cost; do not equate JSON syntax with valid content.

## Structured Output Validation

- Establish the schema and semantic constraints required before a model response is consumed; `json.loads(response)` alone does not establish those constraints.
- Validation failures must remain observable with useful diagnostics. Preserve evidence without disclosing secrets or sensitive response content beyond the project's logging/privacy contract.
- Separate partial stream framing from final validation. Do not act on incomplete structured output unless the consumer has an explicit partial-output contract and its required checks have passed.

## Temperature and Sampling

- Check which sampling parameters the selected model supports and whether the application sends valid values.
- Require evidence for the task's repeatability or variation needs; a temperature value alone does not prove either requirement. Review regression evaluations against permitted outcomes rather than prescribing one setting for every classification or creative task.

```python
# Send only parameters supported by the selected model; validate outcomes separately.
response = client.messages.create(model=config.model_identifier, messages=[...], **config.sampling_parameters)
```

## Evaluation

- Verify material prompt changes against the approved behavior and preserved invariants using representative regression evidence. Do not treat incidental previous wording as the oracle.
- Evaluation datasets must be versioned alongside the prompts that were evaluated against them
- Apply the target's required evaluation/release gate; report missing coverage or automation with the consequential failure it can allow. Source review and authored eval cases are not executed results.

## Safety

- Trace who controls instruction-bearing content and the permissions of downstream tools; prevent untrusted content from acquiring authority reserved for the application or user.
- Check sensitive-data disclosure, retention, and diagnostics against the application's actual authorization/privacy contract; identify the external flow and missing protection rather than inventing a universal consent workflow.
- Prompt injection vectors — places where user content could override or escape the intended prompt structure — must be identified and bounded

## Retry Logic

- Classify retryable failures from the provider's documented semantics and retry guidance. Check backoff, jitter, or other coordination against rate limits and retry amplification.
- Verify that retries cannot duplicate consequential downstream effects or silently exhaust the budget.
- Do not blindly retry malformed or oversized requests; determine whether the request must change before another attempt can succeed.
- Maximum retry count must be bounded — infinite retry loops are a blocking finding

## Streaming

- Check partial responses, cancellation, completion markers, and the final assembled result against the consumer's streaming contract; buffering is acceptable when incremental delivery is not required.
- Connection drops must be handled explicitly — unhandled streaming errors that silently return empty results are a blocking finding
- Verify the timeout/cancellation policy bounds the supported wait for initial output and completion; identify unbounded or prematurely terminated paths.

## Anti-Patterns

```python
# WRONG: user input in system prompt
system = f"You are a helpful assistant. The user's name is {user_name}."

# RIGHT: user data in user turn only
system = "You are a helpful assistant."
messages = [{"role": "user", "content": f"My name is {user_name}. ..."}]

# WRONG: retry on context limit
for attempt in range(3):
    try:
        return client.messages.create(...)
    except APIError:  # catches 400 context limit AND 429 rate limit
        time.sleep(2**attempt)

# RIGHT: only retry transient errors
for attempt in range(3):
    try:
        return client.messages.create(...)
    except RateLimitError:
        time.sleep(2**attempt + random.random())
    except APIError:
        raise  # non-retryable — propagate immediately
else:
    raise RuntimeError("Retry budget exhausted")
```
