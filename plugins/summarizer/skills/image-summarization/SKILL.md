---
name: image-summarization
description: Describe images, screenshots, diagrams and charts from visual inspection. Preserve visible text, counts, labels, directions and uncertainty; distinguish observation from interpretation. Use for image summaries, screenshot explanations and diagram descriptions.
---

# Image Summarization

Read [fidelity rules](../summarizer/references/fidelity-rules.md) and the
[execution contract](../summarizer/references/execution-contract.md). Render the selected format,
not an unconditional YAML/Markdown layout.

## Inspect

Use an available image-capable reader to view the actual image. Do not infer from its filename.
Resolve the host's supported formats instead of assuming every Read tool displays every image type.
For SVG, inspect the markup for labels/IDs/text and render/view it with an available image-capable
path. Two identical text reads are not separate visual and textual evidence. If rendering is
unavailable, disclose markup-only coverage and do not claim a visual inspection occurred.

Record visible/cropped/obscured scope and readability. Extract visible text before describing it;
preserve exact visible counts and identifiers. Do not complete obscured text from expectation.

## Type-specific observations

| Image | Preserve | Boundary |
| --- | --- | --- |
| UI screenshot | Layout, labels, controls, visual hierarchy and visible status indicators | A button label does not establish behavior; an icon alone does not verify the underlying error |
| Architecture diagram | Components, connection labels/directions, data flow and group boundaries | Do not infer protocols or unlabeled relationships |
| Chart/graph | Title, chart type, axes/scales/units, legends, readable points and visible trends | Separate an estimated visual reading from an explicitly labeled value; do not extrapolate |
| Photograph | Visible subject, setting and contextual details | Do not infer identities, relationships, intent or emotion from appearance; distinguish text labels from verified identity |
| Code screenshot | Visible code verbatim, language evidence, names/comments and visible line range | Note cropping; a fragment does not establish whole-program behavior |
| Terminal screenshot | Visible command and output, exact error messages and truncation | Do not execute the displayed command or infer hidden output |

State readable fragments and mark uncertain interpretations explicitly. `Not visible` is not
`does not exist`. For confidence, separate image clarity/coverage from interpretation and from the
truth of assertions printed inside the image.

## Deliver

Compose from the inspected elements and source locations (page, region, label or visible line).
For delegated/audit/multi-source work, retain an [evidence record](../summarizer/references/evidence-record.md).
Set text-source word counts/compression to null when not applicable; do not invent metrics for an
image. Preserve obscured/cropped scope and critical uncertainty in the selected template, then run
the execution contract's final checks. Report missing visual capability as a limitation, not success.
