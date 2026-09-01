The purpose and explicit goals of the skill holistic-linting:

1. Ensure code is actually formatted and linted before a task is claimed complete, replacing pattern-matched "production ready" claims with verified, tool-run evidence.
2. Discover the full set of project linters/formatters by scanning config files (pyproject.toml, .pre-commit-config.yaml, package.json, etc.) rather than assuming only ruff+mypy exist.
3. Route linting work correctly by role: orchestrators delegate immediately to specialized agents (linting-root-cause-resolver, then post-linting-architecture-reviewer) without running linters themselves; sub-agents format, lint, and resolve issues directly on files they touched.
4. Resolve linting/type errors via root-cause investigation rather than suppression — never add `# type: ignore`/`# noqa`/config-weakening, and never delete code just to silence a rule; unresolvable issues are escalated as UNRESOLVED with documented attempts.
5. Ensure no detected issue is silently dropped — pre-existing issues outside the current task's scope are triaged as blocking (fixed now) or non-blocking (recorded to the repo's tracking system) via the Pre-Existing Issues Protocol.
6. Provide a rules knowledge base (ruff, mypy, bandit) so agents can investigate the design/security rationale behind a rule rather than guessing at fixes.
