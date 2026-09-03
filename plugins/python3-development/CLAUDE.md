# python3-development Plugin — AI-Facing Documentation

Python-specialist plugin providing Python-specific implementation agents (architect, test
designer, code reviewer) and quality gates for modern Python 3.11+ development.

---

## Key References

- Language manifest (library registry, modern patterns): `./manifests/python3/language-manifest.yaml`

---

## Agents in This Plugin (Python-specific)

- `@python3-development:python-cli-architect` — implements Python CLI features (Typer/Rich)
- `@python3-development:python-cli-design-spec` — produces architecture specs for Python CLIs
- `@python3-development:python-pytest-architect` — writes pytest test suites
- `@python3-development:code-reviewer` — general code review with Python awareness, quality, and idioms
- `@python3-development:semantic-code-search` — semantic search over Python codebases
