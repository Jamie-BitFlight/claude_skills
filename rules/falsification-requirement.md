# Falsification Requirement

Every hypothesis test must include a falsification check — a test that would DISPROVE the hypothesis if the result differs from prediction.

Before acting on a confirmed hypothesis, state:

- Confirmation test: [what you ran, what it showed]
- Falsification test: [what would disprove this]
- Falsification result: [what you observed]

If you cannot state the falsification test, you have not tested the hypothesis — you have illustrated it.

Example:

```text
Hypothesis: uv fails because PATH excludes /root/.local/bin
Confirmation: env -i PATH=/usr/local/bin uv → "not found" ✓
Falsification: check actual subprocess PATH for /root/.local/bin
Falsification result: PATH DOES include it → hypothesis REJECTED
```
