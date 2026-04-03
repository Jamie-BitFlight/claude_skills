# Skill Marketplace Search Reference

Reference for wizard Step 3: searching the skill marketplace for relevant candidates
based on inferred technology stack.

---

## CLI Commands

### List installed skills

```bash
npx skills list -g
```

Returns all globally installed skills with their names and source repositories. Use this
before searching to avoid suggesting skills already installed.

### Search marketplace

```bash
npx skills search <query>
```

Returns matching skills with name, description, and source repository. If the CLI does not
support `search` as a subcommand, fall back to browsing known community repositories and
filtering by keyword in the skill `description` field.

### Install a skill

```bash
npx skills add <repo-url> --skill '<skill-name>' -g -y
```

The `-g` flag installs globally (available in all projects). The `-y` flag suppresses
confirmation prompts for unattended installation.

---

## Search Query Strategies by Technology Stack

The wizard infers stack from repo signals (see `repo-inference-patterns.md`) and translates
each signal into one or more search queries.

| Inferred Stack | Search Queries | Example Skills to Look For |
|---|---|---|
| **Python** | `python testing`, `python linting`, `python typing`, `pytest` | `python-engineering`, `holistic-linting`, `python3-development` |
| **JavaScript / TypeScript / Node** | `typescript`, `react`, `node testing`, `eslint`, `jest` | `react-expert`, `react-patterns`, `shadcn`, `frontend-design` |
| **Infrastructure / DevOps** | `terraform`, `docker`, `kubernetes`, `vagrant`, `packer`, `ci cd` | `vagrant-reference`, `packer-prerequisites`, `vm-flightsimulator` |
| **Database / SQL** | `sqlite`, `sql optimization`, `database migration`, `postgres` | `sqlite-database-expert`, `sql-optimization`, `sql-code-review` |
| **Documentation / Writing** | `documentation`, `readme`, `markdown`, `api docs` | `documentation-writer`, `rwr`, `technical-writer` |
| **Security** | `security`, `audit`, `owasp`, `vulnerability` | `harden`, `audit` |
| **Embedded / Hardware** | `embedded`, `arduino`, `micropython`, `firmware`, `iot` | `embedded-dev-specialist` |
| **General Workflow** | `git`, `commit`, `code review`, `refactor` | `gsd`, `holistic-linting`, `code-refactorer` |

Run multiple queries when multiple stacks are detected. De-duplicate results by skill name.

---

## Result Evaluation Criteria

For each search result, apply these checks before recommending installation:

1. **Already installed?** — Run `npx skills list -g` and compare. Skip if already present.
2. **Relevant to inferred stack?** — The skill description must reference technologies
   found in the repo signal inventory. Reject skills with no stack overlap.
3. **Compatible with project conventions?** — Prefer skills that mention the same tools
   already configured in the project (e.g., if `pyproject.toml` uses `ruff`, prefer skills
   that mention `ruff` over ones that mention `flake8`).
4. **Source trustworthy?** — Prefer skills from the same repositories already listed in
   the project's `CLAUDE.md` or from the anthropics/skills catalog.

---

## Error Handling

### Marketplace unreachable

**Symptom**: `npx skills search` fails with a network error or times out.

**Wizard behavior**:
- Log: `Marketplace search unavailable. Proceeding with known skill catalog.`
- Fall back to a curated offline list of common skills derived from the inferred stack.
- Mark all offline suggestions with `(offline suggestion — verify availability)` in the
  generated config.
- Continue the wizard; do not abort.

### No results found for query

**Symptom**: Search returns zero results for a specific query.

**Wizard behavior**:
- Try a broader query (e.g., if `pytest fixtures` returns nothing, retry with `pytest`).
- If the broader query also returns nothing, skip that stack and note:
  `No marketplace skills found for <stack>. You can add skills manually later.`
- Do not treat absence of results as a fatal error.

### Skill install fails

**Symptom**: `npx skills add` exits non-zero.

**Wizard behavior**:
- Log the exact error output.
- Do not retry automatically.
- Add the skill to the `prefer_skills` list in the generated config as a comment with
  the error message so the user can install it manually.
- Continue generating the rest of the config.

### `npx` not available

**Symptom**: `npx: command not found`.

**Wizard behavior**:
- Notify the user: `npx is required for skill management. Install Node.js to enable
  marketplace search.`
- Skip Steps 3 and 4 (install).
- Generate the config with `skill_discovery: suggest` and empty `always_use_skills`.
- Recommend the user run `npx skills add ...` after installing Node.js.

---

## Global vs Plugin-Bundled Skills

Understanding the distinction prevents incorrect recommendations.

### Globally installed skills (`~/.claude/skills/`)

- Installed via `npx skills add ... -g`
- Available in **all** projects on this machine
- Not checked into the project repository
- Listed by `npx skills list -g`
- Appropriate for: general workflow tools, language-specific helpers, personal preferences

### Plugin-bundled skills

- Shipped as part of a Claude Code plugin (`plugin.json` references them)
- Activated when the plugin is installed: `claude plugin marketplace add <repo>`
- Available only when the plugin is active
- Listed in the plugin's `plugin.json` under `skills`
- Appropriate for: domain-specific tooling tied to a product (e.g., `vm-flightsimulator`
  skills are only useful when working with that plugin)

### Project-local skills (`.claude/skills/`)

- Checked into the project repository
- Available only in that project
- Not installed via `npx skills` — created or copied manually
- Appropriate for: project-specific conventions, one-off workflows

### Recommendation rule for the wizard

When writing to `skill_discovery.yaml`:
- `always_use_skills` and `prefer_skills` → reference **globally installed** skill names only
- Do not reference plugin-bundled skills (they activate automatically with their plugin)
- Do not reference project-local skills (they activate automatically in project scope)

---

## Offline Fallback Catalog

When marketplace is unreachable, use this minimal curated mapping:

| Stack Signal | Fallback Skill Candidates |
|---|---|
| `pyproject.toml` / Python | `python-engineering:python3-core`, `holistic-linting:lint` |
| `package.json` / Node | `plugin-creator:claude-skills-overview-2026` |
| `Vagrantfile` | `vagrant-reference` |
| SQL files | `sqlite-database-expert`, `sql-optimization` |
| React / JSX | `react-expert`, `shadcn` |

All offline candidates should be verified by the user before use.
