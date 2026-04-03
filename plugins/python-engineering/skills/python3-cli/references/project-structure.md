# Python CLI Project Structure

## Directory Layout

```text
.
├── pyproject.toml
├── packages/
│   └── {package_name}/
│       ├── __init__.py
│       ├── cli.py
│       └── ...
├── tests/
│   └── test_*.py
├── scripts/
└── README.md
```

- Package code lives in `packages/{package_name}/` — never `src/`
- `{package_name}` derived from project name: hyphens → underscores
- Example: project `my-cli-tool` → `packages/my_cli_tool/`

## Hatchling Configuration (required in pyproject.toml)

```toml
[tool.hatchling.build.targets.wheel]
packages = ["packages/{package_name}"]
```

Example for project `mcp-config-tools`:

```toml
[tool.hatchling.build.targets.wheel]
packages = ["packages/mcp_config_tools"]
```
