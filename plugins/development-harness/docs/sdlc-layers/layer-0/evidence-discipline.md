# Evidence Discipline

Primary-source verification. Training data recall is explicitly rejected as evidence.

---

## fact-check

- **Evidence rules**: WebFetch, WebSearch, CLI output, repo source, MCP tools = valid. Training data recall = invalid.
- **Verdicts**: VERIFIED / REFUTED / INCONCLUSIVE
- **Integration**: REFUTED → RT-ICA treats as MISSING

---

## find-cause and root-cause-tracing-process

Evidence-chain protocol for investigations:

- **Valid**: Command output, file content, direct observation
- **Invalid**: Docs intent, training recall, inference from absence

Steps: Disambiguate (`/dh:find-cause`, with the user) → Reproduce, or falsify H0/Ha by experiment when the failure does not reproduce → Read source → Build evidence chain → Present findings. Every step after Disambiguate lives in `dh:root-cause-tracing-process`.

---

## scientific-thinking

Hypothesis-driven reasoning:

- Observation (factual only) → Hypothesis (H₀, Hₐ) → Prediction → Experiment Plan → Execute → Conclusion

Use for: bugs, architecture, refactor, strange behavior. Not for trivial tasks.

---

## Sources

- [fact-check SKILL.md](../../../skills/fact-check/SKILL.md)
- [find-cause SKILL.md](../../../skills/find-cause/SKILL.md)
- [root-cause-tracing-process SKILL.md](../../../skills/root-cause-tracing-process/SKILL.md)
- [scientific-thinking SKILL.md](../../../../plugins/scientific-method/skills/scientific-thinking/SKILL.md)
