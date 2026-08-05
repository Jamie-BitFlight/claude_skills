---
paths:
- '**/SKILL.md'
- '**/agents/**/*.md'
- '**/commands/**/*.md'
- .claude/rules/**/*.md
- '**/CLAUDE.md'
---

# Citation Requirements

Every factual claim in skill documentation requires a cited source. **Reason**: Without citations, guidance cannot be verified, updated, or trusted — and false claims persist across sessions.

**Citation methods** (choose one per claim):

- **Inline**: `SOURCE: [Title](URL) (accessed YYYY-MM-DD)` within the section making the claim
- **Footer**: numbered `## References` section; cite as `[1]`, `[2]` in text
- **Separate file**: `./references/references.md` — link from SKILL.md

**By source type:**

- Official docs: URL + access date
- Skill derivations: link to source skill repo + note adaptations
- User preferences: date of conversation + validation evidence if tested
- Experimental results: method, sample size, results, dataset path
- Forums/community: cite every source URL + access date

**Verification checklist:**

- [ ] Every factual claim has cited source
- [ ] URLs include access dates (YYYY-MM-DD)
- [ ] Citations distinguish official docs, community practices, opinions
- [ ] Skill derivations link to source skill repository
- [ ] User preferences note conversation date and validation evidence
- [ ] Experimental claims reference datasets or methodology
