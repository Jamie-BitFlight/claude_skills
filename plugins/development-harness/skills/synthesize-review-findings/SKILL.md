---
name: synthesize-review-findings
description: Synthesize multiple independent structured review verdicts into one lossless deduplicated punch list. Use when findings from several review perspectives must be merged without inventing, dropping, or changing source verdicts.
---
# Synthesize Review Findings

Consume only supplied reviewer verdicts. Preserve each source verdict and finding text as evidence. Merge findings only when they identify the same defect at the same logical location; shared line numbers alone do not prove duplication. A merged entry retains every contributing perspective and the highest source severity. Order by severity, then independent corroboration, then stable location. Preserve missing/skipped perspective coverage explicitly. Verify conservation: every source finding maps to exactly one output entry contribution and no output defect lacks a source finding. Return the verdict coverage plus the deduplicated punch list.
