# Skill Goals

1. Resolve DH CLI and script paths from the installed `dh-cli-usage` skill location rather than from the authoring repository or caller working directory.
2. Apply DH operations to the caller's active workspace and configured backend unless the caller explicitly selects another target; never inject an authoring-repository target.
3. When no trustworthy runtime skill location is available, stop or use an equivalent MCP operation rather than guessing a checkout path.
