---
title: unslop
subtitle: AI output humanization removing AI-isms with byte-exact preservation of code, tables, and URLs
category: ai-writing-tools
resource_url: https://github.com/MohamedAbdallah-14/unslop
github_url: https://github.com/MohamedAbdallah-14/unslop
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# unslop — AI Output Humanization with Byte-Exact Preservation

## Overview

unslop is a humanization system that removes AI-characteristic patterns (AI-ism) from language model output while preserving technical accuracy, code blocks, tables, URLs, and user intent. It operates as both a command-line Python package and a multi-platform plugin distributed to Claude Code, Cursor, Windsurf, Cline, Gemini CLI, and Codex. The system combines deterministic regex-based rewriting with optional LLM-assisted refinement and includes a detector feedback loop that recommends fallback strategies when humanization saturation is reached.

**Current version**: 0.6.2 (released 2026-05-05)
**License**: MIT
**Repository**: <https://github.com/MohamedAbdallah-14/unslop>

## Problem Addressed

Modern AI assistants produce prose with characteristic markers: hedging stacks ("I would suggest perhaps..."), sycophancy, stock vocabulary patterns, and tricolon structures. These patterns are detectable by AI-text detectors (TMR detector: 99.28% AUROC) and reduce reader credibility even when the underlying technical content is sound.

Existing competing solutions (Anthropic Custom Styles, Undetectable.ai, StealthGPT) either:

1. Add warmth/personality (shown to increase error rates by 11 percentage points per Ibrahim/Hafner/Rocher 2025)
2. Corrupt code or modify structural elements
3. Operate only as web services without IDE integration
4. Lack transparent exit conditions when detector evasion becomes infeasible

unslop addresses this by inverting the typical approach: subtract AI-characteristic patterns rather than add personality, preserve code/structure byte-for-byte, and provide honest feedback when the task reaches saturation.

## Key Statistics

**Measured results** (from README.md):

- 21/21 blind humanness preference (comparative study)
- 92.1% AI-ism reduction (tested against baseline)
- 333 tests across unit, benchmark, and perception harness categories
- 38 verified research citations backing implementation decisions
- Multi-platform availability: 6 AI assistants (Claude Code, Cursor, Windsurf, Cline, Gemini CLI, Codex)

**Code composition** (from repository):

- Python modules: 13 core modules in `unslop/scripts/`
- Hook files: 4 JavaScript/Shell hooks for SessionStart, UserPromptSubmit, status line tracking
- Test coverage: 333 tests in `tests/unslop/`
- Latest commit: 2026-05-05 03:19:50 +0300 (5af59d9)

## Key Features

### Five Rewriting Modes

unslop ships with five configurable rewriting strategies, each with different aggressiveness and LLM involvement:

1. **Subtle** — Deterministic regex removal of hedging stacks and stock phrases only
2. **Balanced** — Subtle + LLM refinement for word choice and sentence flow
3. **Full** — Aggressive deterministic patterns + LLM-assisted rewriting across all detected AI markers
4. **Voice-match** — Applies a user's personal stylometry profile (stored as numeric vector, not free text) to normalize output to their typical voice
5. **Anti-detector** — Full rewriting + feedback from TMR AI-text detector; uses detector output to iteratively eliminate remaining AI-characteristic patterns

**Mode persistence**: Selected mode is persisted to a flag file (default: `~/.unslop-mode`) with security hardening (O_NOFOLLOW, atomic writes, 0600 permissions, symlink refusal).

### Byte-Exact Preservation of Technical Content

Core principle: "Subtract, don't add." The system preserves:

- Code blocks (fenced and indented), with all formatting intact
- URLs and links (exact preservation, no text substitution)
- Tables (Markdown/HTML, untouched)
- YAML frontmatter in documents
- Headings and hierarchy structure
- Lists and nested structures

Mechanism: Placeholder protection and restoration. Content in protected regions (code blocks, URLs, YAML) is replaced with unique placeholders during rewriting, then restored byte-for-byte after humanization completes. This prevents accidental modification of technical content during LLM refinement passes.

### AI-ism Pattern Detection and Removal

unslop identifies AI-characteristic patterns through structural analysis:

1. **Hedging stacks** — "I would suggest perhaps that it might be beneficial to..." (deterministic reduction)
2. **Sycophancy** — "Your excellent question", "As you aptly noted" (phrase replacement)
3. **Stock vocabulary** — "Harness the power of", "State-of-the-art", "Paradigm shift" (vocabulary substitution)
4. **Tricolon structures** — Repeated three-part patterns (restructured to two or four parts)
5. **Reasoning-trace sanitization** — Strips `<internal_reasoning>` and similar agent scaffolding tags from output

**Confidence mechanism**: Each pattern removal is tagged with confidence level. Low-confidence changes are held for review in voice-match mode.

### Voice-Match Stylometry

Preserves user's personal writing style across multiple interactions:

- Maintains numeric style profile (10+ features: sentence length variance, passive/active ratio, conjunction frequency, punctuation patterns)
- Profile is stored as a numeric vector (no free-text encoding)
- Applied across five rewriting modes to ensure output "sounds like" the user even after humanization
- Per-turn reinforcement at turns 8, 16, 24, 32 to combat persona drift

### Detector Feedback Loop

TMR AI-text detector (AUROC: 99.28%) is integrated as a secondary validation step:

- After humanization completes, run detector feedback pass
- If detector confidence remains high on suspected AI patterns, surface those patterns
- Recommend cross-model paraphrase (user supplies alternative LLM) as fallback when threshold saturation is reached
- Honest exit condition: stops attempting evasion when diminishing returns indicate further changes would corrupt meaning

### DivEye Surprisal-Variance Signal

Implements DivEye metric (Basani/Chen et al., TMLR 2026) as a "humanness meter":

- Computes 10-feature surprisal vector across model ensemble
- Indicates where text differs from typical model distribution (high variance = more human-like)
- User-facing confidence bands: 0-3 (high AI characteristics), 4-6 (neutral), 7-10 (humanness signal strong)
- Used to guide mode selection and confidence thresholds

### Integrated Sub-Skills

Accessible via Claude Code activation command structure:

- **unslop-commit** — Humanize Git commit messages and PR descriptions
- **unslop-review** — Humanize code review comments while preserving technical feedback
- **unslop-file** — Humanize entire documentation files with structural preservation
- **unslop-reasoning** — Strip and clean reasoning traces from agent outputs
- **unslop-help** — Humanize help text and documentation without changing command syntax

## Technical Architecture

### Multi-Platform Source of Truth (SSOT) Pattern

unslop maintains a single source of truth with automated mirroring to six platforms:

**Primary source** (`SOURCE_DIR`):
- `skills/unslop/SKILL.md` (Claude Code skill definition)
- `rules/unslop-activate.md` (activation rules)

**Mirrored locations** (auto-synced via CI):
- Claude Code: `skills/unslop/SKILL.md`, `skills/unslop/references/`
- Cursor: `cursor-skills/unslop/SKILL.md`
- Windsurf: `windsurf-skills/unslop/SKILL.md`
- Cline: `cline-skills/unslop/SKILL.md`
- Gemini CLI: `gemini-skills/unslop/SKILL.md`
- Codex: `codex-skills/unslop/SKILL.md`

CI synchronization runs on every commit to root `SKILL.md`, updating all mirrors and rebuilding platform-specific distributions.

### Hook Architecture

**SessionStart hook** (`unslop-activate.js`):
- Runs at session initialization
- Checks flag file for selected mode
- Loads mode configuration and voice-match profile if applicable
- Initializes per-session state

**UserPromptSubmit hook** (`unslop-mode-tracker.js`):
- Runs on every prompt submission
- Updates mode persistence across turns
- Increments turn counter for per-turn reinforcement (turns 8, 16, 24, 32)
- Applies stylometry correction if voice-match is active

**Status line hooks** (`unslop-statusline.sh`, `unslop-statusline.ps1`):
- Cross-platform shell prompt integration
- Displays current mode and humanness confidence
- Non-blocking updates

**Shared configuration module** (`unslop-config.js`):
- Centralized flag file operations with security hardening:
  - Symlink refusal (rejects symlinked flag files)
  - O_NOFOLLOW flag on open() calls
  - Atomic writes (temp file + rename pattern)
  - 0600 file permissions (user-only read/write)
- Functions: `getDefaultMode()`, `safeWriteFlag()`, `readFlag()`, `getFlagPath()`
- Installation scripts for both POSIX (`hooks/install.sh`) and PowerShell (`hooks/install.ps1`)

### Python Package Structure

**Entry point**: `unslop = "scripts.cli:main"` (PEP 440)

**Core modules** (in `unslop/scripts/`):

1. `cli.py` — Command-line interface for all five modes
2. `humanize.py` — Deterministic regex-based pattern removal
3. `detect.py` — AI-ism pattern detection engine
4. `validate.py` — Ensures byte-exact preservation constraints
5. `benchmark.py` — Performance regression testing
6. `reasoning.py` — Reasoning-trace sanitization
7. `surprisal.py` — DivEye surprisal-variance computation
8. `stylometry.py` — Voice-match profile extraction and application
9. `style_memory.py` — Persistent user style storage
10. `structural.py` — Markdown/code structure preservation
11. `soul.py` — Overall coordination and orchestration
12. `detector.py` — TMR detector integration
13. `fetch_detectors.py` — Detector model management

**Configuration** (from `unslop/pyproject.toml`):

- Package name: `unslop`
- Version: dynamically read from `scripts.__version__` (current: 0.6.2)
- Python requirement: >=3.10
- Optional dependencies:
  - `llm`: `anthropic>=0.34` (for LLM-assisted modes)
  - `surprisal`: `torch`, `transformers`, `scipy` (for DivEye computation)
  - `dev`: `pytest`, `ruff`, `mypy` (development only)
- No mandatory dependencies (all dependencies are optional)

### Research Foundations

unslop's design is grounded in 38 peer-reviewed papers across six research areas:

1. **AI-text detection robustness** — TMR detector (AUROC 99.28%), Binoculars, DAMAGE
2. **Adversarial paraphrasing** — TempParaphraser, Adversarial Paraphrasing for Semantic Equivalence (APSE)
3. **Surprisal and perplexity** — DivEye (TMLR 2026), Basani/Chen et al.
4. **Hedging and linguistic markers** — ESL detection false positives (Liang et al.), hedging stack analysis
5. **Stylometry and voice matching** — Stylometric analysis, profile extraction
6. **AI policy and regulation** — EU AI Act Article 50 (transparency requirements), FTC guidance

**Key finding informing shipping code**: Ibrahim/Hafner/Rocher (2025) showed that adding warmth/personality to AI output increases error rate by 11 percentage points. This directly motivated unslop's "subtract, don't add" principle.

## Installation & Usage

### As a Claude Code Plugin

unslop activates automatically on SessionStart. Select a mode via:

```text
/unslop:activate --mode balanced
```

Available modes: `subtle`, `balanced`, `full`, `voice-match`, `anti-detector`

Humanize the current prompt or recent output:

```text
/unslop:humanize
```

View current mode and humanness metrics:

```text
/unslop:status
```

### As a Python Package (CLI)

Install from PyPI:

```bash
pip install unslop
```

Or via uv:

```bash
uv add unslop
```

Humanize text from stdin:

```bash
echo "I would suggest that it might be beneficial to consider..." | unslop --mode balanced
```

Humanize a file:

```bash
unslop --mode full --input document.md --output humanized.md
```

Apply voice-match to preserve user style:

```bash
unslop --mode voice-match --style-profile user-profile.json input.txt
```

Run detector feedback loop:

```bash
unslop --mode anti-detector --detector-rounds 3 input.txt
```

**Installation requirement**: Python 3.10 or later. Optional dependencies (anthropic, torch, transformers, scipy) are installed on-demand when using LLM-assisted or surprisal-based modes.

## Limitations and Caveats

### Documented Limitations

1. **Detector evasion durability** — unslop humanizes against current detectors (TMR, Binoculars). New detector architectures may identify unslop's output through unknown markers. The system includes honest exit conditions: when detector feedback reaches saturation, it recommends cross-model paraphrase rather than continuing to modify text.

2. **False positives in hedging detection** — Some legitimate hedging (epistemic modality for accuracy, uncertainty quantification in technical writing) may be incorrectly flagged. Voice-match mode mitigates this by learning user baseline.

3. **Style transfer imprecision** — Voice-match stylometry uses a 10-feature numeric profile. Rare stylistic features outside this feature set may not transfer correctly.

4. **Structural edge cases** — Nested markdown structures (code blocks inside lists, tables with embedded code) may occasionally fail byte-exact preservation if malformed. Validation pass catches these and reports them.

5. **Code block language detection** — Fenced code blocks without language specifiers are treated as plain text. Humanization may alter comments inside these blocks if they contain stock vocabulary.

6. **Cross-model paraphrase availability** — Anti-detector mode's fallback recommendation (use alternative LLM) assumes access to multiple models. Single-model environments cannot fully execute the fallback strategy.

### What is NOT in Scope

- Modifying code semantics or logic
- Changing technical accuracy
- Altering URLs or external references
- Modifying tables or data structures
- Removing or changing YAML frontmatter
- Changing document organization (heading hierarchy, list structure)

## Relevance to Claude Code Development

### Direct Integration Points

1. **Plugin activation system** — unslop demonstrates multi-platform plugin distribution via SSOT + CI mirroring. Applicable to any skill requiring synchronized deployment across Claude Code, Cursor, Windsurf, and other AI assistants.

2. **Hook architecture** — SessionStart and UserPromptSubmit hooks show persistent state management (flag files, atomic writes, security hardening) for cross-turn behavior. Relevant for skills requiring mode persistence or per-turn reinforcement.

3. **Deterministic + LLM hybrid approach** — Combining regex-based extraction with optional LLM refinement provides a template for skills requiring both speed (deterministic) and quality (LLM-assisted) paths.

4. **Byte-exact preservation pattern** — Placeholder protection/restoration technique is reusable for any skill modifying text while preserving code, URLs, or other structured elements.

5. **Stylometry and voice matching** — Numeric profile approach (avoiding free-text storage) is relevant for skills implementing user preference learning or style transfer.

### Use Cases for Claude Code Users

- Humanize documentation, blog posts, or technical writing without corrupting code examples
- Clean up reasoning traces from agent outputs before sharing
- Maintain consistent personal voice across multiple AI assistant interactions
- Verify AI-ism removal via detector feedback before finalizing sensitive content (applications, professional writing)

## References

**Official Documentation**:
- README.md: <https://github.com/MohamedAbdallah-14/unslop/blob/main/README.md> (accessed 2026-05-10)
- CLAUDE.md: <https://github.com/MohamedAbdallah-14/unslop/blob/main/CLAUDE.md> (accessed 2026-05-10)
- RESEARCH_AND_TECH.md: <https://github.com/MohamedAbdallah-14/unslop/blob/main/RESEARCH_AND_TECH.md> (accessed 2026-05-10)

**Research Foundations** (selected from 38 cited papers):
- Basani/Chen et al. (2026). DivEye: Surprisal-variance signal for humanness. *TMLR*
- Ibrahim/Hafner/Rocher (2025). Warmth paradox: Adding personality increases error rate. *Proceedings of ACL*
- Binoculars detector and DAMAGE framework (AI-text detection robustness)
- EU AI Act Article 50 (transparency in AI-generated content)

**Source Repository**:
- GitHub: <https://github.com/MohamedAbdallah-14/unslop> (accessed 2026-05-10, latest commit 2026-05-05 03:19:50 +0300)
- PyPI: <https://pypi.org/project/unslop/> (distribution)

**Package Manifest**:
- pyproject.toml: <https://github.com/MohamedAbdallah-14/unslop/blob/main/unslop/pyproject.toml> (accessed 2026-05-10)

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|------------|---------------|-------|
| Overview | high | 2026-05-10 | Repository README, git metadata, latest commit verified |
| Problem Addressed | high | 2026-05-10 | Extracted from README and RESEARCH_AND_TECH.md with citations |
| Key Statistics | high | 2026-05-10 | Measurement results from README (21/21 blind preference, 92.1% AI-ism reduction), test count from directory structure |
| Key Features | high | 2026-05-10 | Five modes documented in README, byte-exact preservation detailed in CLAUDE.md, detector loop described in RESEARCH_AND_TECH.md |
| Technical Architecture | high | 2026-05-10 | SSOT pattern, hook files, and Python modules verified from directory structure and source files |
| Research Foundations | high | 2026-05-10 | 38 citations listed in RESEARCH_AND_TECH.md with arXiv URLs and DOIs |
| Installation & Usage | high | 2026-05-10 | Installation commands and API extracted from README and CLI module |
| Limitations | medium | 2026-05-10 | Documented limitations from README "Limitations and Caveats" section; confidence medium because limitations reflect current state and may evolve with future versions |
| Relevance | medium | 2026-05-10 | Assessed based on feature set and integration points; specific use case value depends on user workflow |

**Next Review**: 2026-08-10 (three months)

**What to Check**:
- Version bump (current: 0.6.2)
- New platforms added to SSOT mirroring
- Detector robustness against new AI-text detection techniques
- Feature additions or mode changes
- Test coverage expansion
