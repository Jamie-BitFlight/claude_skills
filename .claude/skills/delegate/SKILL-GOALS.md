The purpose and explicit goals of the skill delegate:

1. Produce sub-agent delegation prompts that carry exactly the WHERE (context/location/scope), WHAT (definition of success/acceptance criteria), and WHY (task identification) the agent needs — nothing more, nothing less.
2. Prevent orchestrator-side scope creep into agent territory: forbids prescribing HOW to implement, forbids pre-gathering context or file paths the agent can discover itself, and forbids restating repo conventions the agent will already load from AGENTS.md/CLAUDE.md.
3. Guarantee results actually reach the dispatcher by requiring every prompt to state an explicit DELIVERY channel (return path or artifact-file fallback) rather than assuming output surfaces automatically.
4. Enforce completeness on ambiguous fixes: when a code smell or issue is found, the agent must be told to audit the entire pattern, not patch a single instance.
5. Keep delegation grounded in current session facts only — an ECOSYSTEM CONTEXT slot for session-specific state (parallel agents on the same files, unmerged branches) that can't be discovered by reading the repo, kept separate from durable conventions.
6. Provide a pre-send verification gate (the Delegation Rules table and Quick Checklist) so an orchestrator can self-check a drafted prompt against the Observations+Success−Assumptions−Micromanagement formula before dispatching.
