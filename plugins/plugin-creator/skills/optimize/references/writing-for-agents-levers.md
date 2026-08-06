# Writing-for-Agents — 5 Levers Distilled

SOURCE: Matt Pocock's writing-for-agents framework (external framework, not authored by this repo) — `SKILL.md` and `SKILL-MECHANICS.md` (accessed 2026-08-06)

Five levers for auditing an AI-facing document (skill, agent file, CLAUDE.md, or any doc reached by a pointer). Each entry gives the definition and the one-line test that decides whether the lever applies to a given passage.

## The Two Loads

Context load is the cost of always-loaded material — a description, an AGENTS.md line, anything sitting in context every turn whether or not it fires. Cognitive load is the cost on the human, who is the index and must remember which documents exist and when to reach for each; it is not a cost to minimize, it is the price of human agency, and is spent where human judgement matters.

Test: does this material need to be always-loaded (context load), or can it live behind a pointer that only the human reaches for (cognitive load)?

## Model-Invoked vs. User-Invoked

A model-invoked skill keeps a `description`, so the agent — or another skill — can fire it autonomously; that description is permanent context load bought in exchange for discoverability. A user-invoked skill (`disable-model-invocation: true`) strips the description from the agent's reach — only the human typing its name can invoke it, at zero context load but full cognitive load.

Test: does the agent, or another skill, need to reach this skill on its own — or does it only ever fire by hand?

## Positive Framing Over Prohibition

Steering by prohibition drags the forbidden behavior into context and makes it more available, not less — negation is a weak modifier that the strongly-activated concept overruns. State the target behavior instead. A prohibition earns its place only as a hard guardrail that cannot be phrased positively, and even then it should be paired with the positive target.

Test: does this prohibition have a positive pairing stating the target behavior?

## The No-Op Test

An instruction the model already obeys by default pays load to say nothing. The test is model-relative, not reader-relative — two readers who disagree about a no-op are disagreeing about the model's default, and settle it by running the document, not by debate. When a sentence fails, delete the whole sentence rather than trim words from it.

Test: does this line change behavior versus the model's default?

## Leading Words

A leading word is a compact concept already living in the model's pretraining (_lesson_, _tracer bullets_, _fog of war_) that the agent thinks with while running the document. Repeated as a token, it recruits priors the model already holds and anchors a region of behavior in the fewest tokens. A phrase restated at multiple sites, or a triad spelled out in full ("fast, deterministic, low-overhead"), is a candidate for collapsing into one such word.

Test: could this restated phrase collapse into a single pretrained word the model already holds priors for?
