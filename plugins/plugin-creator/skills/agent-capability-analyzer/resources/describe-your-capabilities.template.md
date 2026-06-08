Your name and current agent-id is: AGENT_ID_HERE

Describe your capabilities using the XML tags below. Fill in each section honestly based on your instructions and training. Do not leave any tag empty.

<modus-operandi>
How you approach tasks — your working style, decision-making process, and the stance you take when activated.
</modus-operandi>

<core-capabilities-with-constraint-boundaries>
What you can do and where the boundaries are. Name specific capabilities and pair each with its constraint (e.g., "I write X but only when Y", "I analyse Z but never modify it").
</core-capabilities-with-constraint-boundaries>

<fundamental-process-followed>
The step-by-step process you follow when executing your primary task. List the actual steps in order.
</fundamental-process-followed>

<task-scopes-you-excel-at>
The specific task types, inputs, or problem shapes where you perform best. Be concrete — name the kinds of requests you handle most effectively.
</task-scopes-you-excel-at>

<outputs-produced>
The specific artifacts, formats, or responses you produce. Name file types, structures, or output shapes where relevant.
</outputs-produced>

<what-people-might-think-you-do-but-you-dont>
Tasks that seem adjacent to your domain but fall outside your scope. Things a reasonable person might ask you to do that you will decline or redirect.
</what-people-might-think-you-do-but-you-dont>

<two-line-personal-summary>
Two sentences. First: what you are. Second: what makes you the right agent for your domain rather than a general-purpose agent.
</two-line-personal-summary>

After completing all sections, run this exact command (replace `CAPABILITIES_HERE` with your full response above — escape any single quotes as `'\''`):

```bash
node $CLAUDE_PLUGIN_ROOT/scripts/update-agent-map.mjs --name "AGENT_ID_HERE" --capabilities 'CAPABILITIES_HERE'
```

Confirm success by reporting: `Updated agent-map.sqlite`

If the Bash tool is unavailable, return only the tagged content so the orchestrator can write it.
