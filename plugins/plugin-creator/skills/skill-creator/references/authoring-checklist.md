# Skill Authoring Pre-Publish Checklist

Run through every item before sharing or publishing a skill. Each unchecked item is a known failure mode.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Core Quality

- [ ] Description is specific and includes key terms — both what the skill does and when to use it
- [ ] SKILL.md body is under 500 lines
- [ ] Additional detail lives in separate reference files under `references/` — not inline in SKILL.md
- [ ] Content is written for Claude, not humans — instructions over explanations
- [ ] Every instruction justifies its token cost — no padding, no restating what Claude already knows
- [ ] No time-sensitive information (specific version numbers, "as of [date]" statements) — or isolated in an explicit "Legacy / Old Patterns" section
- [ ] Consistent terminology throughout — same term for the same concept, every time
- [ ] Examples are concrete, not abstract
- [ ] File references are one level deep — ``references/file.md`` not ``references/subdir/file.md``
- [ ] Progressive disclosure used appropriately — overview in SKILL.md, detail in references
- [ ] Workflows have clear, numbered steps

---

## Structure

- [ ] Frontmatter `name` field: max 64 characters, lowercase letters/numbers/hyphens only, no XML tags, no reserved words
- [ ] Frontmatter `description` field: max 1024 characters, non-empty, no XML tags
- [ ] Frontmatter is valid YAML — no unquoted colons in description values
- [ ] Reference files sit one level deep under `references/` — not in subdirectories
- [ ] Long reference files (100+ lines) have a Table of Contents at the top
- [ ] All file references use markdown link syntax with `./` prefix: ``references/file.md``
- [ ] All code fences have a language specifier

---

## Code and Scripts

- [ ] Scripts solve problems rather than instruct Claude to figure it out
- [ ] Error handling is explicit — scripts fail with a clear message, not silently
- [ ] No "voodoo constants" — every value (timeouts, limits, thresholds) has a comment explaining why that value was chosen
- [ ] Required packages listed in instructions and verified as available before use
- [ ] Scripts have clear inline documentation
- [ ] No Windows-style paths — all forward slashes
- [ ] Validation and verification steps present for critical operations
- [ ] Feedback loops included for quality-critical tasks

---

## Testing

- [ ] At least three evaluations created with realistic prompts
- [ ] Tested with Haiku, Sonnet, and Opus — instructions specific enough to work on Haiku, not only Opus
- [ ] Tested with real usage scenarios, not synthetic ones
- [ ] Team feedback incorporated (if applicable)
