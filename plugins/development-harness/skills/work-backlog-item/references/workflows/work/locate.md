# Work: Locate (Phase 1)

Find the backlog item and extract its fields. Entry path depends on <mode/>.

## Step 1.1: Interactive Browser (no arguments only)

**Trigger:** <mode/> is empty (no arguments passed).

Load [interactive-browser.md](./interactive-browser.md) for MCP error handling, display format, and response handling.

## Step 1.2: Issue-First Path (`#N`, bare number, or GitHub URL)

**Trigger:** <mode/> matches `#[0-9]+`, is a bare number, or is a GitHub issue URL (`https://github.com/.../issues/N`).

Load [issue-first.md](./issue-first.md) for field mapping, completed-issue discovery, and behavior when <mode/> is `auto`.

## Step 1.3: Find the Backlog Item

**Bypass:** If <mode/> is `#N`, a bare number, or a GitHub issue URL — skip this step entirely and go to Step 1.2. Issue-number and URL inputs resolve via `backlog_view` directly; no matching strategy is needed.

Title = <item_ref/>+ joined (args after the mode flag <mode/>). In interactive mode, title = full `<invocation_args/>`.

**When <mode/> is `auto` with no title (<item_ref/> is empty):** apply the "No title given" substitution from the `--auto mode rules` table — scan P0 then P1 sections for the first open item, log and use its title. Skip items with `status: done` or `status: resolved`.

Before executing Step 1.3: Load [find-item.md](./find-item.md).

Record the priority section (P0, P1, P2, Ideas) the item belongs to.

## Step 1.4: Extract Item Fields

From the matched item's entry in the `mcp__plugin_dh_backlog__backlog_list` returned dict, extract `title`, `plan`, `section` (priority), `issue`, and `groomed`. For detailed fields not in the list response (`description`, `source`, `added`, `research_first`, `suggested_location`), call `mcp__plugin_dh_backlog__backlog_view(selector="{title}", summary=false)` to fetch the full item from the backend.

- `title` — the `title` field from list JSON (required)
- `plan` — the `plan` field from list JSON (optional)
- `description` — from `backlog_view` response `description` field (required)
- `source` — from `backlog_view` response `source` field (optional)
- `added` — from `backlog_view` response `added` field (optional)
- `research_first` — from `backlog_view` response body, `**Research first**:` line (optional)
- `suggested_location` — from `backlog_view` response body, `**Suggested location**:` line (optional)

If the item already has a `**Plan**:` field, extract the plan address from the YAML filename (e.g., `plan/Pf3a4b5c6-machine-readable-inter-item-dependencies.yaml` → `Pf3a4b5c6`). Invoke immediately:

```text
Skill(skill: "dh:implement-feature", args: "P{id}")
```

After extracting fields, proceed to `validate.md` (Step 2.1) before continuing.
