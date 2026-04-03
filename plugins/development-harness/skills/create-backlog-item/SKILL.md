---
name: create-backlog-item
description: Use when capturing a new backlog item via the backlog MCP server. Three modes — guided intake (no args), quick entry (quick {title}), or fully autonomous (--auto {title}). Validates required fields, detects duplicates, and offers GitHub Issue creation for P0/P1 items.
argument-hint: '[quick {title} | --auto {title} | <empty for guided intake>]'
user-invocable: true
context: fork
---

<mode>$0</mode>
<item_title>$1</item_title>

# Create Backlog Item

Capture a new backlog item via `mcp__plugin_dh_backlog__backlog_add`. The MCP server handles persistence and GitHub Issue creation.
See [backlog lifecycle overview](../../docs/backlog-lifecycle.md) for the end-to-end flow.

## PROHIBITED: Backlog Items Describe Problems, Not Solutions

**NEVER include any of the following in a backlog item description:**

- "Required changes" sections
- "Potential approaches" or "Suggested fixes"
- Implementation instructions ("replace X with Y", "add function Z")
- Scope expansion beyond what the user described ("also update CLAUDE.md", "also fix the tests")
- File-level prescriptions ("modify file X at line Y")

**WHY:** Prescriptive fixes in backlog items bypass grooming, RT-ICA, and architecture review. They encode untested assumptions as requirements. This has caused hours of wasted work — a backlog item prescribed modifying project-level files that were out of scope, and agents followed those instructions.

**A backlog item contains:**

- What is broken or missing
- Where it was observed
- What the impact is

Solutions come from investigation during grooming and planning — not at creation time.

## Arguments

`<mode/>` selects the operating mode:

| `<mode/>` value | Mode | Remaining args |
|---|---|---|
| (empty) | Guided intake via `AskUserQuestion` | — |
| `quick` | Fast entry — skip title question | `<item_title/>`+ = title |
| `--auto` | Fully autonomous — no interactive prompts | `<item_title/>`+ = title |

```text
/create-backlog-item                                   # guided intake
/create-backlog-item quick GitHub milestone skill      # quick entry
/create-backlog-item --auto vercel skills npm package  # autonomous (agent use)
```

## Workflow

### Step 1: Collect Item Fields

**If `<mode/>` is `--auto`:**

Title = `<item_title/>` onward (all remaining words joined). Do not call `AskUserQuestion`. Instead:

1. Search `research/` recursively for any file whose name or content matches the title (case-insensitive). Read the best match.
2. Call `mcp__plugin_dh_backlog__backlog_list()` to search existing items for related titles and understand priority patterns.
3. Derive all fields from the research file, task description, and available context:
   - **Title**: from `<item_title/>` onward
   - **Priority**: infer from description urgency keywords (`critical`, `required`, `must` → P1; `nice to have`, `optional` → P2; default P2)
     P1 requires either a matched urgency keyword or explicit --priority=P1 flag.
     P0 is never assigned by auto-mode — P0 must be set manually.
   - **Description**: summarize problem space and desired outcome from research file — do NOT include implementation steps, architecture ideas, proposed solutions, required changes, or file-level prescriptions. If the research file contains fix instructions, strip them. Keep only: what is broken, where it was observed, what the impact is.
   - **Verbatim user report**: the `<item_title/>` argument string, reproduced exactly — character for character, no trimming, no reformatting.
   - **Source**: `"Agent task — auto-derived from research/{filename}"`
   - **Type**: infer from description (`install`, `integrate`, `add` → Feature; default Feature)
   - **How to reproduce**: omit unless the research file contains explicit reproduction steps stated as direct observations. Do NOT infer or construct steps.
4. Log every decision:

```text
[AUTO] Title: {title} — from <item_title/> onward
[AUTO] Priority: P2 — inferred from description (no urgency keywords found, defaulting P2)
[AUTO] Description: derived from research/skill-generation-tools/vercel-labs-skills.md
[AUTO] Source: Agent task — auto-derived from research/skill-generation-tools/vercel-labs-skills.md
[AUTO] Type: Feature — inferred from "integrate" keyword
```

Proceed to Step 2 (validate).

**If `<mode/>` is empty (guided intake):**

Use `AskUserQuestion` with two questions:

```text
Question 1: "What is the title of this backlog item?"
  header: "Title"
  options: (free text — no options; user will type)

Question 2: "What priority?"
  header: "Priority"
  options:
    - label: "P0 — Must have"
    - label: "P1 — Should have"
    - label: "P2 — Nice to have"
    - label: "Idea — Not yet sized"
```

Then ask:

```text
Question 3: "Describe the item. Cover: (1) what the problem is and where it lives, (2) what success looks like when it's done, (3) how you'll know it's working. Do not describe the fix or implementation approach — those come later in planning."
  header: "Description"
```

Capture the user's answer to Question 3 **verbatim** as the `verbatim_user_report` value before structuring it into a Description. The Description is your structured interpretation; the verbatim report is the user's exact words.

Then ask:

```text
Question 4: "What is the source or trigger for this item? (e.g., code review, user request, session observation — or press Enter to skip)"
  header: "Source"
  options:
    - label: "Code review"
    - label: "User request"
    - label: "Session observation"
    - label: "Research finding"
    - label: "Skip"
```

Then ask:

```text
Question 5: "What type of work is this?"
  header: "Type"
  options:
    - label: "Feature"
    - label: "Bug"
    - label: "Refactor"
    - label: "Docs"
    - label: "Chore"
```

Then ask:

```text
Question 6: "Can you provide concrete reproduction steps? (specific commands, files, and exact error messages you observed — or press Enter to skip)"
  header: "How to reproduce"
  options:
    - label: "Skip"
```

If the user provides steps, include them verbatim. If they press Enter or choose Skip, omit the field from the item block.

**If `<mode/>` is `quick`:**

Title = `<item_title/>` onward. Ask only:

- Priority (Question 2 above)
- Description (Question 3 above)

`verbatim_user_report` = the full `<item_title/>` argument string, reproduced exactly. Source defaults to "Session observation". Type defaults to "Feature".

### Step 2: Validate Inputs

Required fields: `title`, `priority`, `description`.

- If any required field is missing or empty: report which field is missing and stop.
- `title` must be non-empty after trimming whitespace.
- `description` must be non-empty after trimming whitespace. If it contains implementation instructions (how to fix, what to change, which files to modify), remove them. Keep only: what is broken, where it was observed, what the impact is.

### Step 3: Duplicate Detection

**Search syntax note**: `backlog_list(search=...)` is a multi-keyword boolean substring search — NOT semantic and NOT fuzzy. Exact title strings miss semantically related items with different wording. Always search with OR-joined key concepts extracted from the title, not the full title string.

Extract 2–4 key concept words from the title and join with ` OR `:

```text
# Title: "Formalise IssueBackend Protocol and audit BacklogItem field portability"
# Key concepts: IssueBackend, backend protocol, backend abstraction, field portability
search = "IssueBackend OR backend protocol OR backend abstraction"
```

Call:

```text
mcp__plugin_dh_backlog__backlog_list(search="{concept1} OR {concept2} OR {concept3}")
```

Also supports `field:value` syntax (`title:auth`, `type:bug`) and regex (`/pattern/`) for narrower checks.

If a match is found with overlapping concepts, report:

```text
Possible duplicate: "{existing title}" already exists in {section}.
Proceed anyway? (y/n)
```

Use `AskUserQuestion` with Yes / No options. If No: stop.

**In `--auto` mode**: if a duplicate is found, log `[AUTO] STOP — duplicate detected: "{existing title}" in {section}` and stop without writing. Do not ask.

### Step 4: Compose Item Block

Format today's date as `YYYY-MM-DD` (use system date).

```text
### {title}

**Source**: {source, or "Not specified" if skipped}
**Added**: {YYYY-MM-DD}
**Priority**: {P0|P1|P2|Idea}
**Type**: {type}
**Description**: {description}
**Verbatim user report**: {exact words from the user — argument string, Question 3 answer, or source text. Never paraphrased, never summarized, never reformatted.}
**How to reproduce**: {reproduction steps, or omit entirely if not provided}
```

**"Verbatim user report" rules:**

- REQUIRED — always populated. This field is never omitted.
- Source by mode:
  - **Guided intake**: the user's exact answer to Question 3 (Description), captured before any structuring.
  - **Quick mode**: the full `<item_title/>` argument string, character for character.
  - **`--auto` mode**: the full `<item_title/>` argument string, character for character.
- NEVER edit, summarize, paraphrase, clean up, or reformat this field. It is a verbatim record of the user's original words.
- Purpose: future readers can understand the user's actual intent, not an AI's interpretation of it.

**"How to reproduce" rules:**

- OPTIONAL — only populate when the user provided concrete reproduction steps, or when steps are directly observable from the reported problem (e.g., a specific command the user ran and the exact error message they received).
- Do NOT invent reproduction steps. If the user did not provide steps and they cannot be derived from direct observation, leave this field empty or omit it entirely. Invented reproduction steps are harmful — they send investigators down wrong paths.
- When populated, steps must be concrete and verifiable: specific commands, specific files, specific error messages observed. Vague steps ("run the app and see the error") must not be included.

If research questions were embedded in the description (lines starting with `?` or `Research:`),
keep them in the `description` — the `backlog_add` MCP tool has no `research_first` parameter.
Prefix the questions with `Research first:` inside the description text so they remain visible.

### Step 5: Create per-item file via backlog MCP tool

Call the `mcp__plugin_dh_backlog__backlog_add` tool:

| Parameter | Value |
|-----------|-------|
| `gate_token` | `"problems-not-solutions"` |
| `title` | `"{title}"` |
| `priority` | `"{priority}"` |
| `description` | `"{description}"` |
| `source` | `"{source}"` |
| `type` | `"{type}"` |
| `how_to_reproduce` | `"{reproduction steps}"` if provided; omit parameter entirely if not |
| `verbatim_user_report` | `"{exact user words}"` — always provide; never omit |

Check the returned dict for `error` key.

**Note on `research_first`:** The `--research-first` CLI flag has no MCP equivalent. The `research_first` parameter does not exist on `backlog_add`. Embed research questions directly in the `description` parameter instead.

### Step 6: Confirm Write

The script outputs the confirmation. Report to user:

```text
Backlog item created.

  Title:    {title}
  Priority: {priority}
  Section:  {section heading}
  Added:    {date}

Next steps:
  Groom:  /dh:groom-backlog-item {title}
  Work:   /dh:work-backlog-item {title}
```

## Error Handling

- Missing required field: report field name, stop.
- Duplicate detected and user says No: stop without writing.
- backlog script fails: report error, stop.
- GITHUB_TOKEN not set (for P0/P1 issue creation): MCP tool reports warning; item still created in local cache.

## Completion Criteria

- `backlog_add` MCP tool invoked successfully (no `error` key in response)
- GitHub Issue created and linked (MCP tool handles)
- Next-step commands shown to user

## Handoff

```text
NEXT: skill="groom-backlog-item" args="{item title}" condition="item created successfully AND metadata.status=needs-grooming"
```
