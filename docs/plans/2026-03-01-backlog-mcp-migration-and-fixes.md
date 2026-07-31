# Backlog MCP Migration + Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three open bugs/features in the backlog MCP server (#340, #322, #330), verify two already-implemented items (#311, #312), then complete the full CLI→MCP migration of all skill files (#329).

**Architecture:** All changes are in `.claude/skills/backlog/backlog_core/` (server.py + operations.py + parsing.py) and skill/agent markdown files. The MCP server is already registered in `.mcp.json`. GitHub Actions stays CLI. Skills call MCP tools; MCP tools delegate to operations.py.

**Tech Stack:** Python 3.11+, FastMCP, pytest, uv. Markdown skill files for skill/agent docs.

---

## Group 1: Fix #340 — regex crash in `append_or_replace_section`

**Root cause:** `re.sub(pattern, replacement_string, body)` crashes when `replacement_string` contains `\1`, `\g<name>`, or other regex backreference syntax. The fix is to pass a `lambda` instead of a string.

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/parsing.py` — 3 `re.sub` calls in `append_or_replace_section`

### Task 1: Write failing test for regex crash

**File:** `.claude/skills/backlog/tests/test_parsing.py`

**Step 1: Write failing test**

```python
def test_append_or_replace_section_with_backslash_in_content():
    """Content containing regex backreference syntax must not crash re.sub."""
    body = "## Fact-Check\n\nOld content\n"
    # \1 in replacement string triggers sre_constants.error if passed as string to re.sub
    content_with_backslash = r"Score: \1 — verified"
    result = append_or_replace_section(body, "Fact-Check", content_with_backslash)
    assert r"\1" in result


def test_append_or_replace_section_subsection_with_backslash():
    body = "## Groomed (2026-01-01)\n\n### Priority\n\nOld\n"
    content = r"High \g<name> priority"
    result = append_or_replace_section(body, "Priority", content)
    assert r"\g<name>" in result
```

**Step 2: Run to verify failure**

```bash
cd /home/user/repos/claude_skills
uv run python -m pytest .claude/skills/backlog/tests/test_parsing.py -k "backslash" -v 2>&1 | tail -20
```

Expected: `error: bad escape` or `sre_constants.error`

### Task 2: Fix the regex crash

**File:** `.claude/skills/backlog/backlog_core/parsing.py`

In `append_or_replace_section`, replace every `re.sub(pattern, f"...", ...)` with a lambda:

**Old (line ~652):**
```python
return section_re.sub(f"\n{new_block}", body)
```
**New:**
```python
return section_re.sub(lambda _: f"\n{new_block}", body)
```

**Old (line ~671):**
```python
new_groomed_body = sub_re.sub(f"\n{new_block}", groomed_body)
```
**New:**
```python
new_groomed_body = sub_re.sub(lambda _: f"\n{new_block}", groomed_body)
```

**Old (line ~674):**
```python
return groomed_re.sub(match.group(1) + new_groomed_body + "\n", body, count=1)
```
**New:**
```python
captured = match.group(1) + new_groomed_body + "\n"
return groomed_re.sub(lambda _: captured, body, count=1)
```

Also fix in `_write_groomed_to_item_file` (operations.py line ~214):
```python
# Old:
new_body = groomed_re.sub(f"\n{groomed_section}\n", body)
# New:
new_body = groomed_re.sub(lambda _: f"\n{groomed_section}\n", body)
```

**Step 3: Run tests**

```bash
uv run python -m pytest .claude/skills/backlog/tests/test_parsing.py -k "backslash" -v 2>&1 | tail -10
```

Expected: PASS

**Step 4: Full test suite**

```bash
uv run python -m pytest .claude/skills/backlog/tests/ -q 2>&1 | tail -5
```

Expected: 422+ passed

**Step 5: Commit and push**

```bash
git add .claude/skills/backlog/backlog_core/parsing.py .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/test_parsing.py
git commit -m "fix(backlog): use lambda in re.sub to prevent crash on backslash content (fixes #340)"
git push
```

---

## Group 2: Add #322 — title + description params to `backlog_update`

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/server.py` — `backlog_update` function
- Modify: `.claude/skills/backlog/backlog_core/operations.py` — `update_item` function
- Test: `.claude/skills/backlog/tests/test_operations.py` (or test_backlog_gh_first.py)

### Task 3: Write failing tests for title/description update

```python
def test_update_item_title(tmp_backlog):
    """backlog_update with title renames the item."""
    # assumes tmp_backlog fixture provides a test item "Old Title"
    result = operations.update_item(selector="Old Title", title="New Title")
    assert result["title"] == "New Title"


def test_update_item_description(tmp_backlog):
    result = operations.update_item(selector="Test Item", description="Updated description text")
    assert "description" in result
```

**Step 1: Run to verify failure**

```bash
uv run python -m pytest .claude/skills/backlog/tests/ -k "update_item_title or update_item_description" -v 2>&1 | tail -10
```

### Task 4: Add `title` and `description` to `update_item` in operations.py

In `update_item` function (line ~1107), add two new parameters after existing ones:

```python
def update_item(
    selector: str,
    plan: str | None = None,
    status: str | None = None,
    create_issue: bool = False,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    groomed: bool = False,
    title: str | None = None,          # NEW
    description: str | None = None,    # NEW
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str]]:
```

In the function body, before the `return` statement, add:

```python
if title:
    _rename_item(item, title, repo, output=out)
    result["renamed_to"] = title

if description is not None:
    _update_description(item, description, repo, output=out)
    result["description_updated"] = True
```

Add helpers (after existing helpers in operations.py):

```python
def _rename_item(item: BacklogItem, new_title: str, repo: str, output: Output) -> None:
    """Rename item: update frontmatter title and GitHub issue title."""
    if not item.file_path:
        raise BacklogError("Item has no file path")
    path = Path(item.file_path)
    text = path.read_text()
    # Update title in frontmatter
    text = re.sub(r"^(title:\s*).*$", f"\\1{new_title}", text, count=1, flags=re.MULTILINE)
    path.write_text(text)
    if item.issue:
        issue_num = int(item.issue.lstrip("#"))
        repository = Github(auth=Auth.Token(_get_token())).get_repo(repo)
        gh_issue = repository.get_issue(issue_num)
        gh_issue.edit(title=new_title)
    output.info(f"  Renamed: {item.title!r} → {new_title!r}")


def _update_description(item: BacklogItem, description: str, repo: str, output: Output) -> None:
    """Update description field in frontmatter."""
    if not item.file_path:
        raise BacklogError("Item has no file path")
    path = Path(item.file_path)
    text = path.read_text()
    # Replace description in frontmatter (may be multi-line)
    text = re.sub(
        r"^(description:\s*).*?(?=\n\w|\Z)",
        lambda m: f"{m.group(1)}{description}",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    path.write_text(text)
    output.info("  Description updated")
```

### Task 5: Add `title` and `description` to `backlog_update` in server.py

```python
def backlog_update(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    plan: Annotated[str | None, Field(description="Path to a plan file to attach to the item")] = None,
    status: Annotated[str | None, Field(description="Set item status (e.g. 'in-progress')")] = None,
    create_issue: Annotated[bool, Field(description="Create a GitHub issue for this item if it lacks one (P0/P1 items only)")] = False,
    groomed_content: Annotated[str | None, Field(description="Groomed content to write. Replaces entire groomed section.")] = None,
    section: Annotated[str | None, Field(description="Section name for incremental groomed content update")] = None,
    content: Annotated[str | None, Field(description="Content for the named section")] = None,
    title: Annotated[str | None, Field(description="New title for the item. Updates local file and GitHub issue title.")] = None,   # NEW
    description: Annotated[str | None, Field(description="New description for the item. Updates frontmatter description field.")] = None,  # NEW
) -> dict:
```

Pass through to `operations.update_item`:

```python
result = operations.update_item(
    selector=selector,
    plan=plan,
    status=status,
    create_issue=create_issue,
    groomed_content=groomed_content,
    section=section,
    content=content,
    title=title,
    description=description,
    output=out,
)
```

**Step 6: Run full test suite**

```bash
uv run python -m pytest .claude/skills/backlog/tests/ -q 2>&1 | tail -5
```

**Step 7: Commit and push**

```bash
git add .claude/skills/backlog/backlog_core/server.py .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/
git commit -m "feat(backlog): add title and description params to backlog_update (fixes #322)"
git push
```

---

## Group 3: Add #330 — section/status filter params to `backlog_list`

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/server.py` — `backlog_list`
- Modify: `.claude/skills/backlog/backlog_core/operations.py` — `list_items`

### Task 6: Write failing tests

```python
def test_list_items_filter_by_section():
    result = operations.list_items(section="P0")
    assert all(item["section"] == "P0" for item in result["items"])


def test_list_items_filter_by_status():
    result = operations.list_items(status="needs-grooming")
    # All returned items should match the status label
    for item in result["items"]:
        assert item.get("status") == "needs-grooming"
```

**Step 1: Run to verify failure**

```bash
uv run python -m pytest .claude/skills/backlog/tests/ -k "filter_by_section or filter_by_status" -v 2>&1 | tail -10
```

### Task 7: Add filtering to `list_items` in operations.py

The `list_items` function currently returns all open items. Add `section` and `status` params:

```python
def list_items(
    with_status: bool = False,
    from_github: bool = False,
    label: str | None = None,
    section: str | None = None,    # NEW — filter by P0/P1/P2/Ideas
    status: str | None = None,     # NEW — filter by status label value
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, ...]:
```

After the existing label filtering, add:

```python
if section:
    section_upper = section.upper()
    open_items = [it for it in open_items if it.section and it.section.upper() == section_upper]

if status:
    # status is a label value like "needs-grooming", "in-progress"
    # items with GitHub issues: match against status:* label
    # items without issues: match "needs-grooming" only (default for unissued items)
    filtered = []
    for it in open_items:
        item_status = it.metadata.get("status", "needs-grooming") if hasattr(it, "metadata") else "needs-grooming"
        if item_status == status:
            filtered.append(it)
    open_items = filtered
```

### Task 8: Add to `backlog_list` in server.py

```python
def backlog_list(
    with_status: Annotated[bool, ...] = False,
    from_github: Annotated[bool, ...] = False,
    label: Annotated[str | None, ...] = None,
    section: Annotated[str | None, Field(description="Filter by priority section: P0, P1, P2, or Ideas")] = None,   # NEW
    status: Annotated[str | None, Field(description="Filter by status label value e.g. 'needs-grooming', 'in-progress'")] = None,  # NEW
) -> dict:
```

Pass `section=section, status=status` to `operations.list_items`.

**Step 9: Run full test suite**

```bash
uv run python -m pytest .claude/skills/backlog/tests/ -q 2>&1 | tail -5
```

**Step 10: Commit and push**

```bash
git add .claude/skills/backlog/backlog_core/server.py .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/
git commit -m "feat(backlog): add section and status filter params to backlog_list (fixes #330)"
git push
```

---

## Group 4: Close #311 and #312 (already implemented)

### Task 9: Verify and close

**Step 1: Verify fuzzy duplicate (#311)**

```bash
grep -n "find_fuzzy_duplicates\|_check_for_duplicates\|force" \
  /home/user/repos/claude_skills/.claude/skills/backlog/backlog_core/operations.py | head -10
```

Expected: `find_fuzzy_duplicates` called in `_check_for_duplicates`, `force` param in `add_item`.

**Step 2: Verify open PR check (#312)**

```bash
grep -n "check_open_prs_for_issue" \
  /home/user/repos/claude_skills/.claude/skills/backlog/backlog_core/operations.py | head -5
```

Expected: called in `close_item` and `resolve_item`.

**Step 3: Close both issues**

```bash
gh issue close 311 -R Jamie-BitFlight/claude_skills --comment "Already implemented: fuzzy duplicate detection via find_fuzzy_duplicates() in operations.py and force param in backlog_add MCP tool."
gh issue close 312 -R Jamie-BitFlight/claude_skills --comment "Already implemented: check_open_prs_for_issue() called in close_item() and resolve_item() in operations.py."
```

---

## Group 5: Complete #329 — CLI→MCP migration of skill files

This is the largest group. Update all Tier 1–3 files from the migration map.

**Pattern for skill files:** Replace every `uv run .claude/skills/backlog/scripts/backlog.py <cmd> [flags]` bash block with the equivalent MCP tool call notation:

```
mcp__plugin_dh_backlog__backlog_<cmd>(param=value, ...)
```

### Task 10: Update CLAUDE.md Backlog Operations section

**File:** `.claude/CLAUDE.md`

Find the "Backlog Operations" section (currently around line 214-220). Replace the policy:

**Old:**
```markdown
**Single interface**: Use `.claude/skills/backlog/scripts/backlog.py` for all backlog and GitHub issue CRUD...

\`\`\`bash
uv run .claude/skills/backlog/scripts/backlog.py add|list|sync|close|resolve|update ...
\`\`\`
```

**New:**
```markdown
**Single interface**: Use the `backlog` MCP server for all backlog and GitHub issue CRUD. The MCP server exposes 10 tools: `backlog_add`, `backlog_list`, `backlog_view`, `backlog_sync`, `backlog_close`, `backlog_resolve`, `backlog_update`, `backlog_groom`, `backlog_normalize`, `backlog_pull`.

**Fallback (CI/GitHub Actions only)**: The CLI (`uv run .claude/skills/backlog/scripts/backlog.py`) is retained for shell environments without an MCP client. GitHub Actions `backlog-sync.yml` stays CLI — no change required there.

**Capability gap fallback**: If an MCP tool lacks a needed operation, invoke `/backlog-tools-administrator` to extend both the CLI and MCP server simultaneously.
```

### Task 11: Update session hooks

**File:** `.claude/hooks/session-start-backlog.cjs`

Update any references to CLI commands in `additionalContext` to reference MCP tool names. Look for text like `backlog.py add` and replace with `mcp__plugin_dh_backlog__backlog_add`.

**File:** `.claude/hooks/stop-backlog-reminder.cjs`

Same pattern — update CLI references to MCP tool names.

**Step: Run hooks to verify no crash**

```bash
node .claude/hooks/session-start-backlog.cjs 2>&1 | head -5
node .claude/hooks/stop-backlog-reminder.cjs 2>&1 | head -5
```

Expected: no parse errors (hooks may print nothing or need stdin — just check exit code 0).

### Task 12: Update `work-backlog-item/SKILL.md` (19 invocations)

**File:** `.claude/skills/work-backlog-item/SKILL.md`

For every bash block containing `uv run .claude/skills/backlog/scripts/backlog.py`, replace with the MCP tool call. Use the mapping from `CLI_TO_MCP_MIGRATION.md` Tier 2, item 10.

Key replacements (apply to ALL 19 occurrences):

| Old bash block | New MCP notation |
|---|---|
| `uv run ... backlog.py list --format json --with-status -R ...` | `mcp__plugin_dh_backlog__backlog_list(with_status=true)` |
| `uv run ... backlog.py list --format json -R ...` | `mcp__plugin_dh_backlog__backlog_list()` |
| `uv run ... backlog.py list -R ...` | `mcp__plugin_dh_backlog__backlog_list()` |
| `uv run ... backlog.py view "{}" --format json -R ...` | `mcp__plugin_dh_backlog__backlog_view(selector="{}")` |
| `uv run ... backlog.py update "{title}" --plan "..." -R ...` | `mcp__plugin_dh_backlog__backlog_update(selector="{title}", plan="...")` |
| `uv run ... backlog.py update "{title}" --status in-progress -R ...` | `mcp__plugin_dh_backlog__backlog_update(selector="{title}", status="in-progress")` |
| `uv run ... backlog.py update "{title}" --create-issue -R ...` | `mcp__plugin_dh_backlog__backlog_update(selector="{title}", create_issue=true)` |
| `uv run ... backlog.py close "{title}" --reason "..." -R ...` | `mcp__plugin_dh_backlog__backlog_close(selector="{title}", reason="...")` |
| `uv run ... backlog.py close "{title}" --plan "..." --checklist-pass -R ...` | `mcp__plugin_dh_backlog__backlog_close(selector="{title}", plan="...", checklist_pass=true)` |
| `uv run ... backlog.py close "#{N}" --plan "..." --checklist-pass -R ...` | `mcp__plugin_dh_backlog__backlog_close(selector="#{N}", plan="...", checklist_pass=true)` |
| `uv run ... backlog.py resolve "{title or #N}" --reason "..." -R ...` | `mcp__plugin_dh_backlog__backlog_resolve(selector="...", reason="...")` |

Also update the reference files:
- `.claude/skills/work-backlog-item/references/step-procedures.md` (2 invocations)
- `.claude/skills/work-backlog-item/references/github-integration.md` (3 invocations)
- `.claude/skills/work-backlog-item/references/close-resolve-procedure.md` (3 invocations)

### Task 13: Update `create-backlog-item/SKILL.md`

**File:** `.claude/skills/create-backlog-item/SKILL.md`

Replace the single `backlog.py add` bash block with:

```
mcp__plugin_dh_backlog__backlog_add(
    title="{title}",
    priority="{priority}",
    description="{description}",
    source="{source}",
    type="{type}"
)
```

### Task 14: Update `groom-backlog-item/SKILL.md`

**File:** `.claude/skills/groom-backlog-item/SKILL.md`

Replace the 6 CLI invocations using the mapping from migration map Tier 2, item 15.

### Task 15: Update `group-items-to-milestone/SKILL.md`

**File:** `.claude/skills/group-items-to-milestone/SKILL.md`

Replace the single `backlog.py list --format json` with `mcp__plugin_dh_backlog__backlog_list()`.

### Task 16: Commit and push migration

```bash
git add \
  .claude/CLAUDE.md \
  .claude/hooks/session-start-backlog.cjs \
  .claude/hooks/stop-backlog-reminder.cjs \
  .claude/skills/work-backlog-item/SKILL.md \
  .claude/skills/work-backlog-item/references/ \
  .claude/skills/create-backlog-item/SKILL.md \
  .claude/skills/groom-backlog-item/SKILL.md \
  .claude/skills/group-items-to-milestone/SKILL.md
git commit -m "feat(backlog): migrate skill files from CLI to MCP server tools (fixes #329)"
git push
```

### Task 17: Close the MCP conversion idea item

```bash
gh issue list -R Jamie-BitFlight/claude_skills --search "Convert backlog.py into MCP server" --json number,title | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['number'] if d else 'not found')"
# Then:
gh issue close <NUMBER> -R Jamie-BitFlight/claude_skills --comment "Completed: backlog MCP server implemented (422 tests), registered in .mcp.json, all skill files migrated."
```

---

## Verification

After all groups complete:

```bash
# Full test suite still green
uv run python -m pytest .claude/skills/backlog/tests/ -q 2>&1 | tail -3

# MCP server starts cleanly
cd .claude/skills/backlog && timeout 3 uv run python -m backlog_core.server 2>&1 | head -5 || true
```

Expected: 422+ tests passing, server starts without import errors.
