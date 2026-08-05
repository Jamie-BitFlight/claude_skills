# Interactive Browser (Step 1.1)

**Trigger:** <mode/> is empty (no arguments passed).

For MCP tool errors encountered at any step, load [error-handling.md](./error-handling.md) for error
classification and handling instructions.

1. Call the CLI: `uv run plugins/development-harness/sam_schema/cli.py backlog list`.

   Note: the CLI's `backlog list` has no `--search` flag (unlike the MCP `backlog_list` tool) —
   full-text search across title/section/topic/type/description/body has no CLI path. Not needed
   here since this call passes no search term.

   Parse the returned JSON. Each entry in `items` has `section`, `title`, `issue`, `plan`, `status`, `milestone`, `file_path` (index format), `groomed` (true if item has groomed content).

2. **Groomed** = item has `groomed: true` in `backlog list` output. For full groomed content, call `uv run plugins/development-harness/sam_schema/cli.py backlog view --selector "{title or #N}"` (CLI has no `summary` parameter — its output is already the flatter, full-detail equivalent of MCP's `summary=false`) — the response `sections` dict contains groomed field values (e.g., `response["sections"]["Acceptance Criteria"]`). If groomed sections are present, use them.

3. Present a numbered list. Use these status indicators in user-visible output only:

   ```text
   Backlog Items:

   P0
     1. ✅ SAM: Error Recovery / Rollback Procedures       [#12  status:in-progress  v1.0]
     2. 🔍 SAM: Regex False Positive Suppression           [#14  status:needs-grooming  v1.0]

   P1
     3. 📋 SAM: Validate Task File Schema                  [no issue]
     4. 📋 SAM: Implement Feature Dry-Run Mode             [no issue]

   P2
     5. 🔍 SAM: Context Window Budget Tracking             [#18  status:needs-grooming  —]

   Ideas
     6. 📋 SAM: Multi-Repo Support                         [no issue]

   Status: ✅ = planned/in-progress  🔍 = groomed/needs-grooming  📋 = not yet groomed

   Options:
     [number]   — Select item to work on
     G [number] — Groom a specific item
     G all      — Groom all ungroomed items
     D [number] — Show full details for an item
   ```

4. Use `AskUserQuestion` to ask: "Which item would you like to work on next?"

5. Handle the response:
   - `[number]` — use that item's title as the working title and proceed to [find-item.md](./find-item.md)
   - `G [number]` — invoke `Skill(skill="groom-backlog-item", args="{item title}")` then re-display the list
   - `G all` — invoke `Skill(skill="groom-backlog-item", args="all")` then re-display the list
   - `D [number]` — display the full item description, research_first field, and groomed content (if present), then re-display the list
   - `C [number]` — proceed to close path with that item's title
   - `R [number]` — proceed to resolve path with that item's title
