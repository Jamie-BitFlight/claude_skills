# Skill Completeness Checklist

A checklist for evaluating whether a skill provides everything an AI agent needs to reliably produce its intended outcome. Derived from patterns observed in Anthropic's official skills repository (<https://github.com/anthropics/skills>).

---

## agentskills.io Best Practice Checks

Five checks derived from agentskills.io design principles. Each check applies to any skill, regardless of purpose type. Evaluate PASS / PARTIAL / FAIL with evidence from SKILL.md.

SOURCE: agentskills.io/skill-creation/best-practices (accessed 2026-05-23). Principle quotes are paraphrased from the source; verdict criteria (PASS/PARTIAL/FAIL) are operationalized from the principles and are not verbatim from agentskills.io.

---

### Check 1: Approach vs Output

**Principle:** "A skill should teach the agent *how to approach* a class of problems, not *what to produce* for a specific instance."

**Question:** Is the skill scoped to a class of problems, or is it a narrow one-shot recipe for a single specific output?

| Verdict | Criteria | Example evidence |
|---------|----------|-----------------|
| **PASS** | Skill defines an approach, process, or method applicable to a range of inputs | "Here is how to approach any code review" — the skill adapts to the specific code |
| **PARTIAL** | Skill covers a class but over-specifies output format or structure | Approach is sound but the expected output section locks to one template |
| **FAIL** | Skill is a recipe for one specific output type or instance | "Generate a Q3 2024 expense report in this exact format with these exact columns" |

**Generating an eval for FAIL:** Create a prompt that tests whether the skill handles a related-but-different variant. If the skill only works for the exact trained case, the eval will fail.

---

### Check 2: Lean Instructions

**Principle:** "Concise, stepwise guidance with a working example tends to outperform exhaustive documentation. When you find yourself covering every edge case, consider whether most are better handled by the agent's own judgment." (paraphrased from agentskills.io/skill-creation/best-practices, accessed 2026-05-23 — exact wording on site differs)

**Question:** Does the skill over-specify, adding rules that narrow behavior without improving outcomes?

**Scope:** This check applies to procedural instructions and rules only. Anti-pattern examples (wrong/right pairs, contrast demonstrations) are behavioral anchoring points — repetition in examples is intentional and correct. Do not apply this check to the Anti-Patterns category or to example blocks.

| Verdict | Criteria | Example evidence |
|---------|----------|-----------------|
| **PASS** | Each instruction has a clear purpose; removing any would reduce quality | Concise steps; each step maps to a failure mode it prevents |
| **PARTIAL** | Most instructions are purposeful; a rule section feels like padding or restates the same constraint in multiple places | Same prohibition stated in two separate rule blocks (not examples) |
| **FAIL** | Instructions are exhaustive to the point of constraining valid approaches | More than 10 "never do X" rules; multi-page procedural checklists for simple tasks |

**Generating an eval for FAIL:** Create a prompt that has a valid, high-quality solution the over-constraints would prohibit. Check whether the skill allows it.

---

### Check 3: Reasoning over Directives

**Principle:** "'Do X because Y tends to cause Z' works better than 'ALWAYS do X, NEVER do Y.'"

**Question:** Does the skill explain the *why* behind its rules, or does it rely on bare imperatives?

| Verdict | Criteria | Example evidence |
|---------|----------|-----------------|
| **PASS** | Rules include rationale — agent understands cause and effect | "Use openpyxl formulas, not Python-computed values, because Excel can't recalculate hardcoded numbers" |
| **PARTIAL** | Some rules have rationale; others are bare directives | Mix of explained and unexplained constraints |
| **FAIL** | Rules are stated as imperatives only — ALWAYS/NEVER with no explanation | "ALWAYS validate before writing. NEVER use inline styles." — no reason given |

**Generating an eval for FAIL:** Create a prompt where the directive would produce the wrong result in an edge case. An agent with understanding of the *why* will adapt; an agent following a bare directive will not.

---

### Check 4: Description Trigger Accuracy

**Principle:** "An under-specified description means the skill won't trigger when it should; an over-broad description means it triggers when it shouldn't."

**Question:** Does the description generate a clear should-trigger / should-not-trigger boundary?

| Verdict | Criteria | Example evidence |
|---------|----------|-----------------|
| **PASS** | Description includes specific trigger keywords and scope limits; a reader can generate at least 3 clear should-trigger and 3 clear should-not-trigger cases | "Use when auditing skill quality, checking marketplace readiness..." — specific and bounded |
| **PARTIAL** | Description covers the main use case but edge cases are ambiguous | "Use for code review" — does it apply to SQL? Infrastructure? Config files? |
| **FAIL** | Description is too generic (triggers on everything) or too narrow (misses valid uses) | "Use this skill." / "Use only for Python 3.11 async context manager review." |

**Generating an eval for FAIL:** Generate a should-trigger and a should-not-trigger case based on the description. If the boundary is unclear, the eval tests will be inconsistent.

---

### Check 5: Bundle Signal

**Principle:** "If every test run independently wrote a similar helper script, that's a signal to bundle it."

**Question:** Are there operations in this skill that an agent would re-implement from scratch on every invocation — and if so, are they bundled?

| Verdict | Criteria | Example evidence |
|---------|----------|-----------------|
| **PASS** | Repetitive operations are bundled as scripts, or the skill has no repetitive operations | Scripts provided for format manipulation; or skill is purely behavioral |
| **PARTIAL** | Some repetitive operations identified; partial bundling | Core operations scripted but peripheral helpers still generated ad-hoc |
| **FAIL (risk flag)** | Skill instructs the agent to write a helper each time, or involves operations that are clearly repetitive and deterministic | "Write a Python function to parse the XML" — will be written fresh each invocation |

**Note:** This check identifies a *risk to verify during evaluation*, not a confirmed finding. A FAIL here means: add a behavioral eval that checks whether the agent produces consistent implementations across runs.

**Generating an eval for FAIL:** Run the same prompt twice. Check whether the generated helper is structurally equivalent. Inconsistency confirms the bundle-signal risk.

---

### Mapping FAIL/PARTIAL to Eval Test Cases

For each Check rated FAIL or PARTIAL, suggest 1–2 eval scenarios in the audit report (natural language paragraphs — do not write a JSON file):

| Check | Suggested eval type | What to assert |
|-------|--------------------|-|
| 1 — Approach vs Output | Variant prompt (related but different case) | Agent applies the skill's approach rather than refusing or forcing original format |
| 2 — Lean Instructions | Valid-but-constrained prompt | Agent allows the high-quality solution the over-constraint would prohibit |
| 3 — Reasoning over Directives | Edge case prompt where directive would fail | Agent adapts based on understanding, not bare rule |
| 4 — Description accuracy | Should-trigger / should-not-trigger pair | Skill activates on should-trigger; does not interfere on should-not-trigger |
| 5 — Bundle signal | Repeat same prompt twice | Helper implementations are structurally equivalent across runs |

---

## How to Use This Checklist

**Apply categories selectively based on the skill's purpose.** Categories 1–3 and 5–6 are universal. Categories 4, 7, and 8 are conditional — apply them only when the skill's purpose warrants them.

### When is each conditional category warranted?

**Scripts (Category 4)** — warranted when the skill wraps operations that are:
- Fragile (format-specific XML manipulation, PDF field filling, coordinate transforms)
- Error-prone without deterministic code (binary file parsing, LibreOffice automation)
- Repeatedly rewritten from scratch each invocation (AI generates the same boilerplate every time)

Not warranted when: the skill enforces behavior through instructions Claude internalizes; the task is text-based reasoning; the skill is a reference document or behavioral standard.

**References (Category 7)** — warranted when the skill requires:
- API schemas, format specifications, or standards the AI cannot reliably reconstruct
- Domain conventions that are correct-by-convention rather than correct-by-logic (financial modeling color codes, legal citation formats, brand hex values)
- Documentation for a tool or library that changes over time

Not warranted when: the knowledge is stable and well-represented in training data; the skill is short enough that inline content is sufficient.

**Special case — reference/knowledge skills**: References ARE warranted by definition. The reference files are the product. Score this category against the 0–3 rubric (organization, discoverability, linkage from SKILL.md) rather than marking N/A.

**Assets (Category 8)** — warranted when the skill:
- Produces output that depends on bundled templates, fonts, or boilerplate (PPTX themes, HTML scaffolds, brand fonts)
- Benefits from reusable output resources the AI uses (not reads into context)

Not warranted when: the skill produces instructional or behavioral output with no associated output resources.

**If a category is not warranted: absence of scripts/references/assets is correct. It is not a gap. Do not recommend adding them.**

---

## 1. Preparation — Does the skill ensure prerequisites are met before work begins?

- [ ] Does the skill verify the environment has required tools/dependencies before starting?
- [ ] Does the skill inspect the input (file, data, state) to understand what it's working with before acting?
- [ ] Are there scripts that extract structured metadata from the input so the AI operates on verified data instead of assumptions?

**Observed examples from Anthropic skills:**

- The PPTX skill runs `inventory.py` to extract every shape with its coordinates, fonts, placeholder types, and default font sizes into structured JSON before any replacement happens. The AI knows exactly what exists in the document.
- The DOCX skill runs `unpack.py` to decompose the .docx ZIP archive into raw XML files, then uses `grep` on `word/document.xml` to verify how text is split across `<w:r>` elements before writing any modification script.
- The XLSX skill states "You can assume LibreOffice is installed" — making the dependency explicit rather than leaving the AI to discover it at runtime.
- The PDF skill provides `extract_form_field_info.py` and `check_fillable_fields.py` to analyze a PDF's form structure before attempting to fill it.

---

## 2. Progression — Does the skill define concrete steps with the right level of control?

- [ ] Does the skill provide a clear sequence of steps the AI follows to produce its output?
- [ ] Are fragile or error-prone operations handled by deterministic scripts rather than generated code?
- [ ] Does the skill show working code examples with imports and realistic data that can be copied directly?
- [ ] Does the skill provide ❌ WRONG / ✅ CORRECT contrast pairs for operations where the AI is known to make mistakes?
- [ ] Does the skill route the AI through a decision tree when multiple paths exist?

**Observed examples from Anthropic skills:**

- The PDF skill ships 8 Python scripts that perform form analysis, field filling, bounding box checking, image conversion, and validation. The AI calls `fill_fillable_fields.py` — it doesn't try to write PDF manipulation code from scratch each time. The output is deterministic.
- The DOCX skill shows "BAD: replaces entire sentence" vs "GOOD: only marks what changed" with exact XML, including the specific `w:rsidR` attribute preservation pattern. The AI has a concrete pattern to follow and a concrete mistake to avoid.
- The XLSX skill shows "WRONG: Hardcoding Calculated Values" (calculating in Python, writing static numbers) vs "CORRECT: Using Excel Formulas" (writing `=SUM(B2:B9)`). This targets a specific failure mode where the AI produces spreadsheets that can't recalculate.
- The DOCX skill provides a Workflow Decision Tree at the top: Creating? → Use docx-js. Editing your own doc? → Basic OOXML. Editing someone else's doc? → Redlining workflow. Legal/academic/business? → Redlining required.
- The PPTX skill defines two entirely separate workflows: "Creating without template" (HTML→PPTX pipeline) vs "Creating with template" (inventory→rearrange→replace pipeline), each with numbered steps.

---

## 3. Verification — Does the skill confirm the output is correct before declaring success?

- [ ] Does the skill include explicit verification steps that check the output for known error categories?
- [ ] Are there scripts that automate verification (not just manual inspection)?
- [ ] Does the skill define an error-correction loop (verify → fix → re-verify)?
- [ ] Does the skill specify what "correct" looks like with concrete acceptance criteria?

**Observed examples from Anthropic skills:**

- The XLSX skill mandates `recalc.py` after every formula write, then checks the JSON output for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` errors with specific locations. If `status` is `errors_found`, the workflow loops back: fix the identified errors and recalculate again.
- The PPTX skill requires visual validation after generation: "Create thumbnail grid → Read and carefully examine the thumbnail image for: text cutoff, text overlap, positioning issues, contrast issues → If issues found, adjust and regenerate → Repeat until all slides are visually correct."
- The DOCX redlining workflow requires final verification: convert to markdown with `pandoc --track-changes=all`, then `grep` for original phrases (must NOT find them) and replacement phrases (must find them).
- The PPTX `replace.py` script validates that all referenced shapes exist in the inventory before writing. If a non-existent shape is referenced, it reports the error with available shapes listed.
- The PPTX `validate.py` script runs after each XML edit: "CRITICAL: Validate immediately after each edit and fix any validation errors before proceeding."

---

## 4. Scripts — Does the skill ship executable automation for its core operations?

- [ ] Are repetitive operations (ones the AI would rewrite each time) captured in scripts?
- [ ] Do scripts accept `--help` and work as self-documenting black boxes?
- [ ] Do scripts handle edge cases, error reporting, and cleanup that generated code would miss?
- [ ] Are scripts tested and known to produce correct output?

**Observed examples from Anthropic skills:**

- The PDF skill: `extract_form_field_info.py`, `fill_fillable_fields.py`, `fill_pdf_form_with_annotations.py`, `check_fillable_fields.py`, `check_bounding_boxes.py`, `create_validation_image.py`, `convert_pdf_to_images.py`
- The PPTX skill: `html2pptx.js` (HTML→PPTX conversion), `inventory.py` (shape extraction), `rearrange.py` (slide duplication/reordering), `replace.py` (text replacement with validation), `thumbnail.py` (visual grid generation)
- The XLSX skill: `recalc.py` (formula recalculation via LibreOffice with error scanning), plus a full `office/` directory with `unpack.py`, `validate.py`, `soffice.py`, and validators for docx/pptx/redlining
- The DOCX skill: `document.py` (Document library for OOXML manipulation), `utilities.py`, plus `ooxml/scripts/` with `pack.py`, `unpack.py`, `validate.py`
- The webapp-testing skill explicitly instructs: "Always run scripts with `--help` first. DO NOT read the source until you try running the script first."
- The skill-creator skill: `init_skill.py` (scaffolding), `package_skill.py` (packaging with validation), `quick_validate.py` (frontmatter/structure validation)

---

## 5. Concrete Examples — Does the skill teach through demonstration rather than description?

- [ ] Does the skill include working code with real imports, realistic variable names, and complete function calls?
- [ ] Are examples showing exact input→output pairs rather than abstract descriptions?
- [ ] Do examples cover the common cases the AI will encounter?
- [ ] Are edge cases and error handling demonstrated in examples?

**Observed examples from Anthropic skills:**

- The XLSX skill provides complete openpyxl examples for creating, loading, formatting, and formula writing — each with imports and realistic cell references.
- The PDF skill provides complete examples for pypdf (merge, split, rotate, metadata, encrypt), pdfplumber (text, tables, advanced table extraction to DataFrame), and reportlab (basic creation, multi-page with Platypus).
- The slack-gif-creator provides the complete GIFBuilder workflow: create builder → generate frames with PIL drawing → save with optimization parameters.
- The MCP builder provides exact Zod/Pydantic schema patterns, tool registration syntax, and response formatting for both TypeScript and Python SDKs.

---

## 6. Anti-Patterns — Does the skill explicitly show what NOT to do?

- [ ] Are known failure modes documented with concrete "don't do this" examples?
- [ ] Do anti-pattern examples show the actual bad output (not just describe it)?
- [ ] Is the correction shown side-by-side with the mistake?

**Observed examples from Anthropic skills:**

- The XLSX skill: ❌ `sheet['B10'] = total` (hardcoded Python calculation) vs ✅ `sheet['B10'] = '=SUM(B2:B9)'` (Excel formula)
- The DOCX redlining: ❌ BAD XML replacing entire sentence vs ✅ GOOD XML marking only the changed word, preserving original `<w:r>` RSIDs
- The frontend-design skill: "NEVER use generic AI-generated aesthetics" with specific banned patterns (Inter font, purple gradients, centered layouts)
- The web-artifacts-builder: "avoid using excessive centered layouts, purple gradients, uniform rounded corners, and Inter font"
- The algorithmic-art skill: ❌ "Creating HTML from scratch" / ❌ "Inventing custom styling" vs ✅ "Copy the template's exact HTML structure" / ✅ "Keep Anthropic branding"

---

## 7. Reference Material — Does the skill provide domain knowledge the AI cannot generate from training data?

- [ ] Does the skill include reference documentation for APIs, schemas, formats, or standards the AI needs?
- [ ] Is reference material organized so only the relevant section gets loaded for a given task?
- [ ] Does the skill link to reference files from the workflow steps where they're needed?

**Observed examples from Anthropic skills:**

- The MCP builder provides 4 reference files: `mcp_best_practices.md`, `node_mcp_server.md`, `python_mcp_server.md`, `evaluation.md` — each loaded at the phase where it's needed.
- The DOCX skill provides `docx-js.md` (~500 lines, loaded for creation) and `ooxml.md` (~600 lines, loaded for editing) — with "MANDATORY - READ ENTIRE FILE" directives.
- The skill-creator provides `references/workflows.md` (sequential and conditional workflow patterns) and `references/output-patterns.md` (template and example patterns).
- The internal-comms skill provides 4 example files: `3p-updates.md`, `company-newsletter.md`, `faq-answers.md`, `general-comms.md` — loaded based on which communication type is identified.
- The theme-factory provides 10 theme definition files in `themes/` — only the selected theme gets loaded.

---

## 8. Assets — Does the skill bundle reusable output resources?

- [ ] Does the skill include templates, fonts, images, or boilerplate that the AI uses in its output?
- [ ] Are assets files the AI uses (not reads into context)?

**Observed examples from Anthropic skills:**

- The canvas-design skill ships ~80 font files (ttf) in `canvas-fonts/` for typography in generated artwork.
- The algorithmic-art skill ships `templates/viewer.html` (the exact HTML template for interactive artifacts) and `templates/generator_template.js` (p5.js reference patterns).
- The web-artifacts-builder ships `scripts/shadcn-components.tar.gz` (pre-packaged UI component library).
- The theme-factory ships `theme-showcase.pdf` for visual preview of available themes.

---

## Additional Patterns

_This section is populated by team research. Each entry includes the skill where the pattern was observed and what it contributes to execution quality._

### Creative Skills (algorithmic-art, canvas-design, frontend-design, theme-factory, slack-gif-creator, web-artifacts-builder)

- **Two-phase creative pipeline (philosophy then implementation)**: Both `algorithmic-art/SKILL.md` and `canvas-design/SKILL.md` split the creative process into two mandatory phases: first, the AI writes an abstract philosophy/manifesto (4-6 paragraphs as a .md file), then separately implements it in code or on canvas. This forces the AI to commit to a coherent aesthetic direction before touching implementation, preventing the output from drifting into generic patterns during code generation. The philosophy becomes a binding contract that the implementation phase must honor.

- **Craftsmanship repetition as quality anchor**: `algorithmic-art/SKILL.md` (lines 48-50, 84) and `canvas-design/SKILL.md` (lines 48, 83) explicitly instruct the philosophy to "stress multiple times" and "repeat phrases like 'meticulously crafted,' 'the product of deep expertise,' 'painstaking attention'" — deliberately redundant phrasing that primes the AI to self-evaluate against a high bar during the implementation phase. This is a prompt engineering technique: repeating quality language in the context window raises the AI's internal quality threshold for the generated output.

- **Template as literal starting point with FIXED/VARIABLE zones**: `algorithmic-art/SKILL.md` (lines 105-127) and `algorithmic-art/templates/viewer.html` (lines 1-16 HTML comments) use explicit section markers to divide the template into "FIXED" elements (Anthropic branding, sidebar structure, seed controls, action buttons) and "VARIABLE" elements (algorithm, parameters, UI controls). The template includes inline comments like "WHAT TO KEEP" / "WHAT TO CREATIVELY EDIT" and the SKILL.md repeats this with checkmark/cross notation. This prevents the AI from rebuilding the entire UI from scratch while still allowing full creative freedom in the algorithm itself.

- **Explicit anti-convergence directive**: `frontend-design/SKILL.md` (line 38) states "NEVER converge on common choices (Space Grotesk, for example) across generations" — a directive that directly fights the AI's tendency to repeatedly select the same "safe" options across separate invocations. This targets a specific failure mode unique to AI-generated creative work: statistical mode collapse toward training data favorites. Similarly, line 38 says "Vary between light and dark themes, different fonts, different aesthetics."

- **Mandatory refinement pass baked into workflow**: `canvas-design/SKILL.md` (lines 122-127) includes a "FINAL STEP" section where the skill tells the AI that "The user ALREADY said 'It isn't perfect enough'" — simulating a revision request before the user ever asks. It then provides specific refinement guidance: "avoid adding more graphics; instead refine what has been created." This forces a second pass that focuses on polishing rather than adding, which counteracts the AI's tendency to respond to "make it better" by adding complexity rather than refining existing work.

- **Platform-specific constraint specification**: `slack-gif-creator/SKILL.md` (lines 12-19) defines precise platform constraints (128x128 for emoji, 480x480 for messages, 10-30 FPS, 48-128 colors, under 3 seconds for emoji) that the AI cannot know from training data alone. These constraints are then enforced programmatically by `core/validators.py` (the `validate_gif` function checks dimensions, frame count, and file size) and `core/gif_builder.py` (the `optimize_for_emoji` flag in the `save` method auto-resizes to 128x128, caps colors at 48, and reduces frames to ~12). The skill documents the constraint AND ships code that enforces it.

- **Utility library instead of rigid templates**: `slack-gif-creator/SKILL.md` (lines 236-248) explicitly states what the skill provides ("Knowledge, Utilities, Flexibility") vs. what it does NOT provide ("Rigid animation templates, pre-made functions, a library of pre-packaged graphics"). The `core/` directory ships composable building blocks — `easing.py` (12 easing functions + `interpolate` helper), `frame_composer.py` (primitive drawing functions), `gif_builder.py` (frame assembly + optimization) — that the AI composes freely rather than filling in template slots. This gives the AI creative latitude while preventing it from writing its own GIF optimization logic from scratch.

- **Easing function library for natural motion**: `slack-gif-creator/core/easing.py` ships 12+ easing functions (ease_in, ease_out, bounce, elastic, back_in/out) plus composite utilities (`apply_squash_stretch`, `calculate_arc_motion`, `interpolate`). The SKILL.md references these in animation concept descriptions (lines 145-148, 178-180, 197-199). Without this library, the AI would write inline math for each animation, producing inconsistent motion quality. The easing library standardizes motion feel across all generated GIFs.

- **Scaffolding scripts that produce complete project structure**: `web-artifacts-builder/scripts/init-artifact.sh` generates an entire React + TypeScript + Tailwind + shadcn/ui project in one command, including 40+ pre-installed UI components extracted from `shadcn-components.tar.gz`, Parcel bundling configuration, path aliases, and dark mode support. The companion `bundle-artifact.sh` collapses the entire project into a single self-contained HTML file. This eliminates the AI's need to configure build tooling, resolve dependency versions, or write boilerplate — it jumps straight to application logic.

- **Curated selection with visual preview before application**: `theme-factory/SKILL.md` (lines 21-23) prescribes a 4-step workflow: "Show the theme showcase PDF" → "Ask for their choice" → "Wait for selection" → "Apply the theme." The `theme-showcase.pdf` (124KB visual preview) and individual theme definition files (e.g., `themes/ocean-depths.md` with hex codes, font pairings, and "Best Used For" context) ensure the user makes an informed decision before the AI applies styling. The skill also supports on-the-fly theme generation (lines 58-59) for cases where no preset fits.

- **Explicit negative scope ("Don't use this for...")**: `web-artifacts-builder/SKILL.md` frontmatter description specifies "not for simple single-file HTML/JSX artifacts" — defining when NOT to use the skill. This routing signal prevents the AI from using a heavyweight React+Tailwind+shadcn pipeline when a simple HTML file would suffice, saving significant time and complexity.

- **Conceptual seed / subtle reference embedding**: `algorithmic-art/SKILL.md` (lines 90-98) and `canvas-design/SKILL.md` (lines 89-97) both include a "DEDUCING THE CONCEPTUAL SEED/SUBTLE REFERENCE" step that instructs the AI to embed a sophisticated, non-obvious reference to the user's request within the generated art — "so refined that it enhances the work's depth without announcing itself." This is a creative quality technique: it forces the AI to interpret the user's intent at a deeper level rather than producing a literal/surface-level representation, resulting in more sophisticated creative output.

### Document Skills (docx, pptx, xlsx, pdf)

- **Shared script library duplicated per skill for self-containment**: The `office/` directory (containing `unpack.py`, `pack.py`, `validate.py`, `soffice.py`, XSD schemas, and validators) is duplicated identically across docx, pptx, and xlsx skills. Each skill ships a complete, self-contained toolchain with no cross-skill dependencies. The AI can activate one skill without needing the others installed. Observed in: `docx/scripts/office/`, `pptx/scripts/office/`, `xlsx/scripts/office/`.

- **Environment shimming for sandboxed execution**: `soffice.py` (`docx/scripts/office/soffice.py`) detects at runtime whether AF_UNIX sockets are blocked (sandboxed VMs), and if so, compiles and LD_PRELOADs a C shim that replaces `socket()` with `socketpair()` to keep LibreOffice functional. This is invisible to the AI — it just calls `get_soffice_env()` and LibreOffice works. The pattern: scripts handle hostile runtime environments so the AI never encounters cryptic failures.

- **Unpack normalizes XML before AI editing**: `unpack.py` (`docx/scripts/office/unpack.py`) performs three normalizations: (1) pretty-prints XML so the AI can match on readable, indented strings rather than minified blobs, (2) merges adjacent `<w:r>` runs with identical formatting so text is in one run instead of fragmented across several, (3) converts smart quote Unicode characters to XML entities (`&#x201C;` etc.) so they survive round-trip editing. Without these steps, the AI's Edit tool would fail to match text that's split across runs or corrupted by encoding issues.

- **Pack reverses normalization (condense XML)**: `pack.py` (`docx/scripts/office/pack.py`) removes pretty-printing whitespace from all XML files before creating the ZIP archive. This ensures the output doesn't bloat with indentation whitespace and matches what Office applications expect. Pack also runs validation with auto-repair before creating the file. The pattern: unpack expands for editability, pack compresses for compatibility — a reversible transformation pair.

- **XSD schema validation against OOXML standards**: The `office/schemas/` directory ships 30+ actual ECMA-376 and ISO-IEC29500 XSD schema files that `validate.py` uses to validate edited XML against the Office Open XML standard. This catches malformed element nesting, missing attributes, and schema violations that would cause Word/PowerPoint/Excel to reject the file silently. Observed in: `docx/scripts/office/schemas/`, `pptx/scripts/office/schemas/`.

- **Semantic tracked-changes validator (redlining integrity)**: `RedliningValidator` (`docx/scripts/office/validators/redlining.py`) goes beyond schema validation: it strips the AI's tracked changes from both the original and modified documents, then compares the remaining text. If they differ, the AI made untracked edits — a silent data loss bug in legal/contract contexts. The validator produces `git diff --word-diff` output showing exactly what changed. This catches the specific bug where the AI modifies text inside another author's tracked change tags instead of nesting properly.

- **Multi-file boilerplate automation (comments)**: `comment.py` (`docx/scripts/comment.py`) handles cross-file boilerplate for Word comments: writes to `comments.xml`, `commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml`, creates them from templates if they don't exist, adds relationship entries to `document.xml.rels`, and adds Content-Type overrides to `[Content_Types].xml`. Without this script, the AI would need to coordinate edits across 6 XML files with correct IDs, paraIds, durableIds, and relationship types — each a silent failure point.

- **Coordinate system declaration prevents silent misplacement (PDF forms)**: The PDF forms workflow (`pdf/forms.md`) requires the AI to declare coordinates as either `pdf_width`/`pdf_height` (PDF points) or `image_width`/`image_height` (pixels) in `fields.json`. The `fill_pdf_form_with_annotations.py` script auto-detects the system and converts. This prevents the most common PDF form-filling failure: placing text at pixel coordinates in a PDF-point space (or vice versa), causing text to appear in the wrong location.

- **Runtime check routes to entirely different workflows (PDF forms)**: `check_fillable_fields.py` (`pdf/scripts/check_fillable_fields.py`) determines whether a PDF has native form fields. Fillable PDFs use `extract_form_field_info.py` + `fill_fillable_fields.py` (programmatic field setting). Non-fillable PDFs use `extract_form_structure.py` + visual analysis + `fill_pdf_form_with_annotations.py` (text annotation overlay). A hybrid approach handles mixed cases. The AI doesn't choose — the script output determines the path.

- **Pre-fill validation rejects bad input with diagnostics**: `check_bounding_boxes.py` (`pdf/scripts/check_bounding_boxes.py`) validates that no bounding boxes intersect and that entry boxes are tall enough for the specified font size. `fill_fillable_fields.py` (`pdf/scripts/fill_fillable_fields.py`) validates field IDs exist, page numbers match, checkbox values match exact checked/unchecked strings, radio groups match valid options, and choice fields match valid values — printing specific ERROR messages with the valid alternatives. The pattern: scripts reject bad input with diagnostic messages before producing bad output.

- **Zoom refinement technique for visual coordinate estimation (PDF forms)**: The PDF forms workflow (`pdf/forms.md`, Approach B) teaches the AI a structured technique: estimate rough coordinates, crop a zoomed region with ImageMagick, examine the crop to refine coordinates precisely, convert crop-local coordinates back to full-image coordinates. This replaces guessing with measurement, reducing coordinate errors from page-level to pixel-level precision.

- **Subagent delegation points specified in workflow**: The PPTX editing workflow (`pptx/editing.md`) explicitly marks where subagents should and should not be used: "do this yourself, not with subagents" for structural changes (step 4), but "use subagents here if available" for content editing (step 5), because slides are separate XML files editable in parallel. The subagent prompt is specified: include file paths, "Use the Edit tool for all changes", and the formatting rules. The pattern: the skill controls parallelization strategy.

- **Visual QA with mandated skepticism**: The PPTX skill (`pptx/SKILL.md`, QA section) states: "Assume there are problems. Your job is to find them." and "If you found zero issues on first inspection, you weren't looking hard enough." It mandates subagents for visual QA even for 2-3 slides ("You've been staring at the code and will see what you expect, not what's there. Subagents have fresh eyes.") and provides a 12-item QA prompt template. The pattern: the skill encodes professional skepticism to counter confirmation bias.

- **Design system for non-designers (PPTX)**: The PPTX skill (`pptx/SKILL.md`, Design Ideas section) provides a complete design system: 10 named color palettes with hex values, font pairing recommendations, size scales for text roles, spacing standards, and a list of anti-patterns including "NEVER use accent lines under titles — these are a hallmark of AI-generated slides." This is aesthetic judgment the AI cannot generate from training data, preventing the "generic AI presentation" failure mode.

- **Domain-specific formatting conventions (XLSX financial models)**: The XLSX skill (`xlsx/SKILL.md`) encodes industry-standard financial modeling conventions: blue text for hardcoded inputs, black for formulas, green for cross-sheet references, red for external links, yellow background for key assumptions. Number formatting rules specify years as text strings ("2024" not "2,024"), negative numbers in parentheses, zeros as dashes. These are correct-by-convention rather than correct-by-logic — the skill provides domain knowledge the AI cannot derive.

- **Library bug workarounds encapsulated in scripts**: `fill_fillable_fields.py` (`pdf/scripts/fill_fillable_fields.py`) contains `monkeypatch_pydpf_method()` that patches pypdf's `DictionaryObject.get_inherited` to handle choice fields returning `[export_value, display_text]` pairs instead of just export values. Called before form filling begins. The pattern: scripts encapsulate library workarounds so the AI never encounters the underlying bug.

- **Unicode glyph prohibition with correct alternative**: The PDF skill (`pdf/SKILL.md`, Subscripts section) states: "IMPORTANT: Never use Unicode subscript/superscript characters in ReportLab PDFs. The built-in fonts do not include these glyphs, causing them to render as solid black boxes." It provides the correct alternative (`<sub>` and `<super>` XML tags). The pattern: documents a silent failure mode (no error, just wrong visual output) and routes to the correct approach.

- **Cleanup scripts for structural consistency (PPTX)**: `clean.py` (`pptx/scripts/clean.py`) runs a multi-pass orphan removal loop: removes slides not in `sldIdLst`, removes unreferenced media/embeddings/charts/diagrams/drawings/ink/themes/notes, removes orphaned `.rels` files, and updates `[Content_Types].xml`. The loop repeats until no more orphans are found (removing one file can orphan another). The pattern: prevents structurally inconsistent ZIP archives that would fail to open.

- **Object mutation warning for JavaScript API (PPTX)**: `pptxgenjs.md` (`pptx/pptxgenjs.md`, Common Pitfalls section, item 7) warns: "NEVER reuse option objects across calls — PptxGenJS mutates objects in-place (e.g. converting shadow values to EMU). Sharing one object between multiple calls corrupts the second shape." The fix is a factory function that returns fresh objects. This documents a JavaScript library behavior that produces silent corruption — the file generates without errors but the second shape renders wrong.

- **Tool-specific rules that override general habits**: The DOCX skill (`docx/SKILL.md`, Step 2) states: "Use the Edit tool directly for string replacement. Do not write Python scripts." The PPTX editing doc (`pptx/editing.md`) similarly says: "Use the Edit tool, not sed or Python scripts. The Edit tool forces specificity about what to replace and where, yielding better reliability." This overrides the AI's general tendency to write scripts for XML manipulation, and provides the reason: forced specificity reduces errors.

- **Hardcode documentation requirements with source templates**: The XLSX skill (`xlsx/SKILL.md`, Documentation Requirements section) specifies exact citation formats for hardcoded values in financial models: "Source: Company 10-K, FY2024, Page 45, Revenue Note, [SEC EDGAR URL]". Four example citation patterns cover SEC filings, Bloomberg Terminal, FactSet, and quarterly reports. This ensures financial models are auditable — every hardcoded number traces back to its source.

### Developer/Workflow Skills (mcp-builder, skill-creator, webapp-testing, doc-coauthoring, internal-comms, brand-guidelines)

- **Phased workflow with gated reference loading**: The mcp-builder skill (`SKILL.md` lines 19-155) defines 4 explicit phases (Research/Planning, Implementation, Review/Test, Evaluations), and each phase links to the specific reference file that should be loaded at that point. For example, `reference/evaluation.md` is linked only under Phase 4, and the language-specific guides (`reference/node_mcp_server.md`, `reference/python_mcp_server.md`) are linked under Phase 2. This gates context loading to the phase where it is needed, rather than loading everything upfront. This differs from Section 7 (which notes reference files exist) because here the phasing directly controls when references enter context.

- **Automated evaluation harness with quantitative scoring**: The mcp-builder skill ships `scripts/evaluation.py` and `scripts/connections.py` that form a complete evaluation framework: the AI generates 10 QA pairs in XML format, then `evaluation.py` runs an agent loop that calls MCP tools, compares answers via string comparison, and produces an accuracy report with per-task metrics (duration, tool calls, feedback). This is qualitatively different from the verification patterns in Section 3 — those verify a single output is correct, while this evaluates the entire system's capability by running an autonomous agent against it.

- **Evaluation question design constraints that prevent shallow testing**: The mcp-builder `reference/evaluation.md` (lines 59-113) mandates 13 specific constraints on evaluation questions: must require deep exploration (multi-hop, sequential tool calls), must not be solvable with keyword search, must include ambiguous questions, must require dozens of tool calls, answers must be stable over time and verifiable by direct string comparison. This forces the AI to create genuinely difficult test cases rather than trivial validations.

- **Quality checklists as structured exit criteria**: Both `reference/node_mcp_server.md` (lines 916-970) and `reference/python_mcp_server.md` (lines 670-719) end with detailed checkbox-style quality checklists organized by category (Strategic Design, Implementation Quality, Code Quality, Testing). These checklists function as mandatory exit gates — the AI must verify each item before considering the implementation complete. This provides a deterministic "done" definition rather than relying on the AI's judgment of quality.

- **Degrees of freedom as a design parameter**: The skill-creator skill (`SKILL.md` lines 37-46) explicitly teaches the concept of calibrating instruction specificity to task fragility: "High freedom" for text-based instructions when multiple approaches are valid, "Medium freedom" for pseudocode when a preferred pattern exists, "Low freedom" for specific scripts when operations are fragile. This is a meta-pattern about skill design itself — it changes how the AI writes future skills by giving it a framework for deciding how much latitude to leave.

- **Progressive disclosure with explicit loading levels**: The skill-creator skill (`SKILL.md` lines 115-122) defines a three-level loading system: Level 1 is metadata (name + description, ~100 words, always in context), Level 2 is the SKILL.md body (<5k words, loaded when triggered), Level 3 is bundled resources (unlimited, loaded on demand). This architecture directly reduces context window pressure and is a structural design principle that affects every skill's construction.

- **Scaffolding scripts that enforce structural conventions**: The skill-creator ships `scripts/init_skill.py` which generates a new skill directory with a SKILL.md template containing TODO placeholders, example resource directories, and guidance about structural patterns (workflow-based, task-based, reference/guidelines, capabilities-based). The template itself (lines 18-103 of `init_skill.py`) teaches the AI about skill structure options. This ensures every new skill starts from a consistent, validated baseline rather than being created ad-hoc.

- **Validate-before-package gate**: The skill-creator's `scripts/package_skill.py` calls `validate_skill()` from `quick_validate.py` before creating the .skill archive. If validation fails, packaging is blocked. The validator checks: YAML frontmatter format, required fields (name, description), naming conventions (kebab-case), description constraints (no angle brackets, max 1024 chars), and rejects unexpected frontmatter keys. This is a hard gate that prevents malformed skills from being distributed.

- **Reconnaissance-then-action pattern for dynamic environments**: The webapp-testing skill (`SKILL.md` lines 65-81) defines a specific pattern: first navigate and wait for networkidle, then take screenshot or inspect DOM, then identify selectors from rendered state, then execute actions with discovered selectors. This is an explicit directive to observe before acting in environments where the state is not known ahead of time. The decision tree at lines 18-33 further routes the AI based on whether the target is static HTML, a dynamic app with no running server, or a dynamic app with a running server.

- **Scripts as black boxes with --help-first directive**: The webapp-testing skill (`SKILL.md` line 14) states: "Always run scripts with `--help` first. DO NOT read the source until you try running the script first and find that a customized solution is absolutely necessary." This explicitly prevents the AI from polluting its context window by reading large script source code. The AI treats scripts as executables with documented interfaces rather than code to understand.

- **Multi-stage collaborative workflow with explicit stage transitions**: The doc-coauthoring skill (`SKILL.md` lines 8-349) defines a 3-stage workflow (Context Gathering, Refinement & Structure, Reader Testing) with explicit exit conditions for each stage. Stage 1 exits when "questions show understanding — when edge cases and trade-offs can be asked about without needing basics explained." Stage 2 includes a quality check after 3 consecutive no-change iterations. Stage 3 exits when "Reader Claude consistently answers questions correctly." These are qualitative gates that require the AI to evaluate its own progress.

- **Reader testing via sub-agent with no context bleed**: The doc-coauthoring skill (`SKILL.md` lines 242-331) prescribes testing the completed document by invoking a fresh Claude instance (sub-agent) that has no context from the authoring conversation. This sub-agent receives only the document and test questions, then the AI evaluates whether "Reader Claude" got correct answers. This is a zero-shot validation pattern — it catches knowledge gaps that are invisible to the authors because they have accumulated context.

- **Brainstorm-curate-draft-refine cycle per section**: The doc-coauthoring skill (`SKILL.md` lines 152-221) prescribes a repeating cycle for each document section: (1) clarifying questions, (2) brainstorm 5-20 options, (3) user curates (keep/remove/combine), (4) gap check, (5) draft, (6) iterative refinement with surgical edits. This is a controlled generation pattern where the AI produces a wide set of options and the user narrows, rather than the AI generating a single draft.

- **Communication type routing with per-type example files**: The internal-comms skill (`SKILL.md` lines 8-29) routes the AI to load a specific example file based on the identified communication type (3P updates, newsletter, FAQ, general). Each example file contains type-specific formatting rules, tone guidance, and structural templates. For instance, `examples/3p-updates.md` mandates strict formatting with emoji prefix, team name, dates, and exactly 1-3 sentences per section. This routing prevents the AI from applying generic writing patterns when a specific format is required.

- **Tool-aware context gathering**: The internal-comms example files (`examples/3p-updates.md` lines 14-28, `examples/company-newsletter.md` lines 9-18, `examples/faq-answers.md` lines 10-14) each list specific tools (Slack, Google Drive, Email, Calendar) and describe what to look for in each tool for that communication type. For instance, the newsletter file says to look for "messages in channels with lots of people, with lots of reactions" in Slack. This changes what the AI retrieves based on the output type, rather than generic information gathering.

- **Exact design tokens as compact lookup data**: The brand-guidelines skill (`SKILL.md` lines 19-36) provides precise hex color values (#141413 for dark, #d97757 for orange accent, etc.) and exact font names with fallback chains (Poppins with Arial fallback for headings, Lora with Georgia fallback for body). This is reference data the AI cannot generate from training — it must use these exact values. Unlike Section 7's reference documentation pattern, this is a compact lookup table embedded directly in SKILL.md because the data is small enough to always be in context.

- **5-part tool description structure**: The mcp-builder reference files (`reference/node_mcp_server.md` lines 154-191, `reference/python_mcp_server.md` lines 281-327) prescribe a specific structure for tool descriptions: (1) what the tool does and does not do, (2) explicit Args with types and examples, (3) Returns with full schema structure, (4) Examples with "Use when" and "Don't use when" routing, (5) Error Handling listing specific error conditions. This structured format directly improves tool selection accuracy by providing the AI with disambiguation signals.
