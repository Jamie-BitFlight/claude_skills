---
name: code-review-llm
description: Use when reviewing AI/ML code or LLM integration — activates on prompt templates, model selection logic, token budget concerns, or evaluation harness code. Enforces prompt hygiene, model tier matching, context window management, token economics, structured output validation, temperature settings, retry logic, streaming error handling, and PII/safety rules.
user-invocable: false
---

# LLM Integration Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when prompt files, model selection logic, or evaluation harness code are detected.

## Prompt Hygiene

- System prompt must be separated from user content — mixing them in a single string removes the security boundary
- System prompts must not include user-controlled content unless that content is explicitly sanitized and bounded
- Prompt templates must use structured variable substitution, not string concatenation — f-strings with raw user input are a blocking finding
- Long prompts should be stored in dedicated files, not inline strings — inline multi-line strings are acceptable only below 10 lines

## Model Selection

- Model tier must match task complexity — using Opus for tasks that Haiku can handle is a blocking finding (cost regression)
- Using Haiku for tasks requiring multi-step reasoning, architecture decisions, or complex judgment is a blocking finding (quality regression)
- Model selection must be documented with the rationale — `model = "haiku"  # retrieval only, no reasoning required`
- Model names must not be hardcoded as full version strings — use the tier alias (`sonnet`, `haiku`, `opus`) so upgrades require one change

```python
# WRONG: hardcoded version string
model = "claude-haiku-4-5"

# RIGHT: tier alias — version resolved by the client
model = "claude-haiku-latest"
# or better: configurable
model = config.model_tier  # "haiku" | "sonnet" | "opus"
```

## Context Management

- Unbounded context accumulation (appending all messages without a limit) is a blocking finding — long sessions will silently hit context limits and start dropping messages
- Sliding window or summarization strategy must be implemented for conversations expected to exceed ~50 turns
- Token count must be tracked and logged — silent context truncation is harder to debug than explicit overflow handling

## Token Economics

- Token count must be estimated before sending requests in batch or high-volume operations — surprise cost overruns from unexpectedly large inputs are preventable
- Fail fast on oversize inputs rather than truncating silently — silent truncation corrupts the task without surfacing an error
- Structured output requests (JSON mode) reduce token waste from freeform formatting — use when parsing responses programmatically

## Structured Output Validation

- Model responses used programmatically must be validated against a schema before use — `json.loads(response)` without validation is a blocking finding
- Schema validation must produce a specific error that includes the raw response for debugging — swallowing parse errors is a blocking finding
- Partial response handling: when streaming, the validation schema must tolerate incomplete JSON until the stream closes

## Temperature and Sampling

- Temperature setting must be documented with the rationale
- `temperature=0` is required for deterministic tasks (classification, extraction, code generation with tests) — any other value is a blocking finding
- `temperature>0` is required for creative tasks (variation generation, brainstorming) — using `0` eliminates variation intentionally

```python
# RIGHT: documented temperature
response = client.messages.create(
    model="claude-sonnet-latest",
    temperature=0,  # deterministic — this is a classification task
    messages=[...]
)
```

## Evaluation

- Prompt changes must be accompanied by regression tests that verify the old expected outputs still hold
- Evaluation datasets must be versioned alongside the prompts that were evaluated against them
- Evaluation harness must run in CI — manual evaluation without automation is a blocking finding for production prompts

## Safety

- User-controlled content must not be passed as the system prompt — only static, developer-controlled content belongs in the system prompt
- PII (names, email addresses, IP addresses, financial data) must not be passed to external model APIs without documented user consent and data retention agreements
- Prompt injection vectors — places where user content could override or escape the intended prompt structure — must be identified and bounded

## Retry Logic

- Retry logic must use exponential backoff with jitter — fixed-interval retries exacerbate rate limit pressure
- Retry on `429` (rate limited) with backoff is correct
- Retry on `400` (bad request, context length exceeded) is a blocking finding — these errors are not transient and retrying wastes budget
- Maximum retry count must be bounded — infinite retry loops are a blocking finding

## Streaming

- Streaming clients must handle partial responses — a streaming handler that only processes the final concatenated string is acceptable but wastes the streaming benefit
- Connection drops must be handled explicitly — unhandled streaming errors that silently return empty results are a blocking finding
- Timeout on first token is separate from timeout on stream completion — both must be configured

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
        time.sleep(2 ** attempt)

# RIGHT: only retry transient errors
for attempt in range(3):
    try:
        return client.messages.create(...)
    except RateLimitError:
        time.sleep(2 ** attempt + random.random())
    except APIError:
        raise  # non-retryable — propagate immediately
```
