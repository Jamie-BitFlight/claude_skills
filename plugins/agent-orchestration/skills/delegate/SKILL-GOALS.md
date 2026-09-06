The purpose and explicit goals of the skill delegate:

1. Keep the orchestrator's context window reserved for judgment by routing all substantive work — reading, gathering facts, analysis, writing changes, validation, testing, reporting, review — to sub-agents instead of doing it inline.
2. Give the orchestrator a repeatable decomposition method: split a request into only the phases that produce work, pick the right agent for each (specialist, generic, or reviewer), and dispatch independent phases concurrently rather than serially.
3. Standardize what a dispatch prompt must contain — observations, definition of success, context, delivery instructions — so a sub-agent receives a complete, bounded, fact-only task with no inherited assumptions and no implementation steps handed to specialists.
4. Define a sub-agent contract (stay inside the assigned phase, don't fan out further, report STATUS: DONE/PARTIAL/BLOCKED with evidence) so returned work is verifiable and safely re-dispatchable rather than trusted on faith.
5. Give the orchestrator a disciplined way to adjudicate reports: verify evidence actually supports the claim, resolve conflicting reports via a falsifiable check, cap re-dispatch attempts on the same gap, and escalate to the user instead of looping.
6. Guarantee an independent review of every code change (never by the agent that wrote it), and recognize when a single reported issue is actually an instance of a wider pattern worth auditing before narrowly patching it.
