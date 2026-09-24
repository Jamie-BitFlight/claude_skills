# Plugin Lifecycle — Large Phase Gate Diagrams

These two phase gate diagrams are large enough to live in their own reference file. The orchestrator consults the relevant diagram when entering Phase 5 or Phase 7. All other phase gate diagrams are small enough to remain inline in `SKILL.md`.

Both diagrams are authoritative procedures — execute steps in the exact order shown, including branches, decision points, and stop conditions.

---

## Phase 5 — Debug Error Routing

Load this diagram when entering Phase 5 (Debug). It routes each validator error type to its specific fix and loops back to re-validate.

```mermaid
flowchart TD
    %% Entry: run validator to get current error list
    RunValidator["Run: uvx skilllint@latest check PATH<br>Capture full output"] --> HasErrors{"Exit code 0<br>AND 0 errors in output?<br>(warnings are acceptable)"}
    HasErrors -->|"Yes — 0 errors, validation passes"| Next["Proceed to Phase 6 — Optimize"]
    HasErrors -->|"No — errors remain"| Q{"Error type in validator output?"}

    %% Route each error type to its fix, then loop back to re-validate
    Q -->|"SK007 — skill exceeds token limit (hard error)"| Split["Activate /plugin-creator:refactor-skill<br>Context = oversized SKILL.md path<br>Output = split skill files at same plugin path"]
    Q -->|"SK006 — skill approaching token limit (warning)"| Extract["Extract content to references/ directory<br>Update SKILL.md to reference extracted files<br>Output = reduced SKILL.md + new references/ file"]
    Q -->|"Broken link error (LINK01 or similar)"| Links["Read the file containing the broken link<br>Verify the target path exists on disk<br>Fix with Edit tool — update or remove the broken reference"]
    Q -->|"Frontmatter issues (FM-series errors)"| Lint["Activate /plugin-creator:lint --fix PATH<br>Context = file path + validator output<br>Output = corrected frontmatter in the file"]
    Q -->|"Tool format issues (array instead of string)"| Tools["Activate /plugin-creator:lint --fix PATH<br>Output = corrected tool field"]
    Q -->|"Other structural errors"| Manual["Read the validator error message<br>Identify the file and line referenced<br>Apply Edit fix directly to that file<br>Verify fix is consistent with plugin schema"]

    %% All fix paths loop back to re-validate
    Split --> RunValidator
    Extract --> RunValidator
    Links --> RunValidator
    Lint --> RunValidator
    Tools --> RunValidator
    Manual --> RunValidator
```

---

## Phase 7 — Verify 4-Layer Validation Gate

Load this diagram when entering Phase 7 (Verify). It encodes the 4-layer validation gate: structural validation, runtime validation, token complexity, and cross-reference integrity.

```mermaid
flowchart TD
    %% Layer 1: structural validator
    VL1{"Layer 1 — Run: uvx skilllint@latest check PATH<br>Exit code 0 AND 0 errors in output?"}
    VL1 -->|"Yes — structural validation passes"| VL2{"Layer 2 — Run: claude plugin validate PATH<br>Exit code 0?"}
    VL1 -->|"No — structural errors found"| Fail1["Capture Layer 1 error details<br>Proceed to Phase 5 — Debug with these errors"]

    %% Layer 2: runtime validator
    VL2 -->|"Yes — runtime validation passes"| VL3{"Layer 3 — Does skilllint output<br>contain SK006 or SK007 for any skill?"}
    VL2 -->|"No — runtime validation fails"| Fail2["Capture Layer 2 error details<br>If a manifest exists, check custom paths start with ./<br>If manifestless, validate the default component directory<br>Proceed to Phase 5 — Debug with these errors"]

    %% Layer 3: token complexity
    VL3 -->|"No SK006/SK007 — all skills within token limits"| VL4{"Layer 4 — For every internal link in all SKILL.md and agent files:<br>does the target file exist on disk?<br>For every skill in plugin.json: does the SKILL.md exist?<br>For every agent reference in skills: does the agent .md exist?"}
    VL3 -->|"Yes — SK006 or SK007 present"| Fail3["Identify which skills triggered SK006/SK007<br>Proceed to Phase 5 — Debug targeting those skills"]

    %% Layer 4: cross-reference integrity — attempt inline fix before returning to Debug
    VL4 -->|"Yes — all cross-references resolve"| Done(["Write .plugin-creator/plans/NAME/SUMMARY.md<br>Plugin is marketplace-ready"])
    VL4 -->|"No — one or more broken cross-references"| Fail4["List each broken reference with file path and line<br>Fix with Edit tool directly<br>Re-run Layer 4 check"]
    Fail4 --> VL4

    %% Layers 1-3 failures route to Phase 5
    Fail1 --> DebugReturn["Proceed to Phase 5 — Debug"]
    Fail2 --> DebugReturn
    Fail3 --> DebugReturn
```
