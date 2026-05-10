---
title: PaperJSX Document Generation Library
subtitle: Generate PPTX, DOCX, XLSX, and PDF documents from structured JSON
category: skill-generation-tools
resource_url: https://github.com/ComposioHQ/awesome-codex-skills/tree/master/paperjsx
github_url: https://github.com/ComposioHQ/awesome-codex-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# PaperJSX Document Generation Library

PaperJSX is a Node.js-based document generation system that creates professional office documents (presentations, reports, spreadsheets, invoices, contracts) from structured JSON specifications. The library is generation-only—it creates new files but does not edit existing ones.

## Overview

**Purpose**: Programmatic generation of business documents using declarative JSON input.

**Target Formats**:
- PPTX presentations (corporate, modern, minimal, dark, gradient themes)
- DOCX reports, contracts, invoices (corporate, modern, classic, academic, minimal themes)
- XLSX spreadsheets with multi-sheet support
- PDF invoices, reports, chart documents (corporate, modern, minimal, academic, legal themes)

**Distribution Model**: Published as separate npm packages per format — `@paperjsx/json-to-pptx`, `@paperjsx/json-to-docx`, `@paperjsx/json-to-xlsx`, `@paperjsx/json-to-pdf`.

**Execution Model**: Import the package, build JSON spec matching the format schema, call the render method, write output buffer to disk.

SOURCE: Repository root README.md (verified 2026-05-10), SKILL.md lines 1–8, 38–45.

## Problem Addressed

Generating professional business documents requires either:
1. Building files with binary office format libraries (complex serialization)
2. Using cloud APIs with network overhead and authentication management
3. Using templating that couples logic with document structure

PaperJSX solves this by inverting the model: define document structure as data (JSON), pass it to a local-only rendering engine, get a file buffer back. No network calls, no API keys, declarative format, repeatable generation.

SOURCE: Repository README.md overview ("runs locally via `@paperjsx/mcp-server` — no API key, no network calls"), SKILL.md line 8 ("generation-only — it creates new files, it does not edit existing ones").

## Key Statistics

- **Package Count**: 4 separate npm packages (@paperjsx/json-to-pptx, @paperjsx/json-to-docx, @paperjsx/json-to-xlsx, @paperjsx/json-to-pdf)
- **Format Support**: 4 primary output formats (PPTX, DOCX, XLSX, PDF)
- **PPTX Slide Types**: 8 slide types documented (title, content, chart, two_column, quote, image, comparison, stats)
- **Document Themes**: 5 presentation themes (corporate, modern, minimal, dark, gradient); 5 report/invoice themes (corporate, modern, minimal/classic, academic, legal)
- **DOCX Document Types**: 3 types (report, contract, invoice)
- **PDF Document Types**: 3 types (invoice, report, chart document)
- **Spreadsheet Sheets**: Multi-sheet support with configurable row chunking (max 100K rows)
- **Aspect Ratios**: 2 presentation aspect ratios (16:9, 4:3)

SOURCE: SKILL.md lines 24–36 (installation packages), references/json-schema.md throughout (schema fields and types).

## Key Features

### 1. JSON-Driven Document Generation

Pass structured JSON to each format's render engine. The execution pattern is identical across all formats:

```javascript
// Pattern for all formats
const buffer = await Engine.render(jsonSpec);
fs.writeFileSync("output.pptx", buffer);
```

JSON schemas are format-specific and documented in `references/json-schema.md`. Each schema defines required fields, optional fields with defaults, field types, and constraints.

SOURCE: SKILL.md lines 49–116 (three complete examples showing PPTX, DOCX, XLSX patterns with identical structure: spec → render → writeFile).

### 2. Multiple Output Formats

**PPTX Presentations** (`@paperjsx/json-to-pptx`)
- Top-level fields: title (required), author, company, date, slides array (1–50 slides), theme, brand colors, logo URL, format (pptx or pdf), aspect ratio, slide numbers, footer
- 8 slide types: title, content (bullets), chart, two_column (left/right columns), quote, image, comparison, stats/metrics
- Chart support: line, bar, pie, area chart types with configurable series colors
- SOURCE: references/json-schema.md lines 7–121

**DOCX Documents** (`@paperjsx/json-to-docx`)
- 3 document types: report (sections, TOC, multi-level headings, markdown content), contract (parties, WHEREAS clauses, numbered clauses with subclauses, signature blocks), invoice (line items, sender/recipient blocks, tax/discount calculation)
- Report features: auto table-of-contents, page headers/footers, page numbering, configurable TOC depth (1–6 heading levels), markdown content support (headings, tables, code blocks, lists, links, images)
- Page sizes: A4, letter, legal; orientations: portrait, landscape
- 5 themes: corporate, modern, classic, academic, minimal
- SOURCE: references/json-schema.md lines 258–330

**XLSX Spreadsheets** (`@paperjsx/json-to-xlsx`)
- Multi-sheet support with named sheets
- Cell types: string, number, boolean
- Render options: deterministic output, large_dataset flag, row_chunk_size (max 100K rows), string_strategy (auto, sharedStrings, inlineStrings)
- Auto-validation with optional repair on generation error
- SOURCE: references/json-schema.md lines 220–254

**PDF Documents** (`@paperjsx/json-to-pdf`)
- 3 document types: invoice (line items, tax/discount, multi-currency support), report (markdown content, auto-TOC, cover page, configurable fonts and page formats), chart document (1–4 charts, analysis text, key insights bullets, optional raw data table)
- Invoice currencies: USD, EUR, GBP, INR, BRL, AUD, CAD, JPY, CNY, CHF, SGD, HKD (12 currencies)
- PDF report fonts: sans, serif, mono; page formats: a4, letter, legal
- Chart types in PDF: line, bar, pie, area, scatter, composed
- SOURCE: references/json-schema.md lines 124–216

### 3. Theme and Styling Options

Every format supports at least 5 themes (corporate, modern, minimal, academic, and either dark/gradient for PPTX or classic/legal for others). Colors are specified as hex values for brand customization (primary_color, secondary_color fields).

SOURCE: SKILL.md lines 28–29 (PPTX example uses `theme: "corporate"`, `primary_color`, `secondary_color`), references/json-schema.md theme enums throughout (lines 21, 144, 172, 198, 271, 328).

### 4. Local-Only Execution

No external API calls or authentication required. The library runs entirely in Node.js using local rendering engines. Files are generated as buffers and written to disk by the caller.

SOURCE: Repository README.md ("runs locally via `@paperjsx/mcp-server` — no API key, no network calls"), SKILL.md line 8.

### 5. Validation and Error Handling

XLSX generation includes post-render validation with optional auto-repair on malformed output. PDF and DOCX generation surfaces full error messages to the caller when the rendering engine fails.

SOURCE: SKILL.md lines 118–132 (validation pattern), references/json-schema.md line 230 (XLSX validate_after_render and attempt_repair_if_needed options).

## Technical Architecture

PaperJSX is organized as a family of format-specific engines, each exposing a render method that accepts JSON and returns a binary buffer.

### Component Structure

1. **@paperjsx/json-to-pptx Engine**
   - Exports `PaperEngine` class
   - Static method `render(spec)` → buffer
   - Handles slide layout, theme application, chart rendering, media embedding

2. **@paperjsx/json-to-docx Engine**
   - Exports `renderToDocx` function
   - Accepts JSON, returns `{ buffer, metadata }`
   - Supports markdown parsing in report content
   - Handles multi-level section nesting and TOC generation

3. **@paperjsx/json-to-xlsx Engine**
   - Exports `SpreadsheetEngine` class
   - Static method `render(spec)` → buffer
   - Handles multi-sheet layout, cell type mapping, row chunking

4. **@paperjsx/json-to-pdf Engine**
   - Shared with DOCX package (`@paperjsx/json-to-pdf`)
   - Supports invoice, report, and chart document generation
   - Markdown content rendering via report type
   - Multi-currency invoice calculation

### Data Flow

```
JSON Spec
  ↓
Format Engine (PaperEngine | renderToDocx | SpreadsheetEngine)
  ↓
Buffer (in-memory binary document)
  ↓
fs.writeFileSync(filename, buffer)
  ↓
Output File (.pptx | .docx | .xlsx | .pdf)
```

### Extension Points

No documented plugin or extensibility mechanism. The library is static—themes and document types are fixed by the rendering engine. Custom output requires:
1. Modifying the JSON spec to use documented fields
2. Selecting from available themes, slide types, and chart types
3. Generating new files rather than editing existing ones

SOURCE: SKILL.md line 45 ("Do **not** write imperative PaperJSX API code. The execution model is always: JSON spec in, document file out").

## Installation & Usage

### Installation

Install format-specific packages:

```bash
npm install @paperjsx/json-to-pptx
npm install @paperjsx/json-to-docx
npm install @paperjsx/json-to-xlsx
npm install @paperjsx/json-to-pdf
```

SOURCE: SKILL.md lines 25–36.

### Complete Usage Pattern

1. Build JSON spec matching the format schema (see `references/json-schema.md`)
2. Import the engine
3. Call render with JSON
4. Write buffer to disk
5. Validate output file exists and is non-zero bytes

```javascript
import { PaperEngine } from "@paperjsx/json-to-pptx";
import fs from "node:fs";

const spec = {
  type: "Document",
  meta: { title: "Q4 Review" },
  slides: [
    {
      type: "Slide",
      children: [
        { type: "Text", content: "Q4 2025 Business Review", style: { fontSize: 36, bold: true } }
      ]
    }
  ]
};

const buffer = await PaperEngine.render(spec);
fs.writeFileSync("presentation.pptx", buffer);
console.log("Generated presentation.pptx");
```

For validation:

```javascript
import fs from "node:fs";

const stats = fs.statSync("output.pptx");
if (stats.size === 0) {
  throw new Error("Generated file is empty");
}
console.log(`Output file: ${stats.size} bytes`);
```

SOURCE: SKILL.md lines 49–130 (complete PPTX, DOCX, XLSX examples + validation pattern).

## Relevance to Claude Code Development

### Direct Use Cases

1. **Automated Report Generation**: Skills and agents can generate quarterly reviews, technical reports, or status documents directly from data structures without templating overhead.

2. **Dynamic Presentation Creation**: Multi-agent workflows can produce slide decks from conversation transcripts or meeting notes (e.g., summarizer agent outputs → PaperJSX → PPTX).

3. **Batch Invoice/Contract Generation**: Billing systems or legal workflows can generate documents from database records without manual formatting.

4. **Data Visualization**: Spreadsheets and PDF charts can be generated from analysis results, enabling agents to produce downloadable artifacts alongside text output.

### Integration Points

- **MCP Server**: Repository documents an `@paperjsx/mcp-server` for integration with Model Context Protocol tooling.
- **Skill Context**: The paperjsx/ directory in the Composio awesome-codex-skills repository is published as a Codex skill with SKILL.md metadata and references/json-schema.md for schema lookup.

### Architectural Fit

PaperJSX aligns with Claude Code's generation-focused model: it is a pure function (spec → file), requires no user interaction or iteration, and produces deterministic output suitable for multi-agent workflows where document generation is a discrete task step.

SOURCE: Repository structure (awesome-codex-skills/paperjsx/ contains SKILL.md + references/) and README.md categorization under Composio skills.

## Limitations and Caveats

1. **Generation-Only Model**: Cannot edit existing documents. Every operation creates a new file. Updating content requires regenerating the entire document.

2. **No Built-In Template Inheritance**: Themes are fixed per format. Custom styling beyond the 5 theme options requires modifying the JSON spec to approximate desired appearance (e.g., using hex colors for brand customization).

3. **Schema Rigidity**: Document structure is constrained by the documented JSON schemas. Fields and types are fixed; no way to extend or customize field validation.

4. **No Markdown Support in Presentations**: PPTX generation does not parse markdown in slide content. Text must be provided as plain strings; formatting (bold, italic) is specified via explicit style objects.

5. **DOCX Markdown Parsing**: Report DOCX supports markdown content but contract DOCX and invoice DOCX do not—those require structured field input (parties array, clause array, line items array).

6. **Chart Type Limitations**:
   - PDF charts support 6 types (line, bar, pie, area, scatter, composed)
   - PPTX charts support 4 types (line, bar, pie, area)
   - Composed charts (for stacking/mixed charts) are PDF-only

7. **Error Surface**: When rendering fails, the engine throws an exception with a message. Full error context is the responsibility of the caller to surface to the user; no built-in logging or debug modes documented.

8. **No Batch Optimization**: Each document is rendered independently. Large batch operations (generating 100 invoices) perform no caching or pooling of render engines.

SOURCE: SKILL.md lines 7–8 ("generation-only"), 45 ("Do not write imperative PaperJSX API code"), references/json-schema.md field schemas show no extensibility mechanisms, PPTX schema (line 65) supports 4 chart types vs. PDF schema (line 206) supports 6 types.

## References

- **GitHub Repository**: <https://github.com/ComposioHQ/awesome-codex-skills/tree/master/paperjsx> (accessed 2026-05-10)
  - SKILL.md — skill metadata and usage guide
  - references/json-schema.md — complete schema documentation for all formats
  - LICENSE.txt — Apache License 2.0

- **NPM Packages**:
  - @paperjsx/json-to-pptx — PPTX engine
  - @paperjsx/json-to-docx — DOCX engine
  - @paperjsx/json-to-xlsx — XLSX engine
  - @paperjsx/json-to-pdf — PDF engine

- **Related Resources**:
  - Composio awesome-codex-skills repository — integration point for Codex agents
  - MCP server adapter documented in repository README.md

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---------------|-------|
| Identity/Metadata | high | 2026-05-10 | Package names, license, formats verified from source |
| Features | high | 2026-05-10 | All 4 formats, 8 PPTX slide types, 3 DOCX types, 3 PDF types extracted from json-schema.md |
| Technical Architecture | high | 2026-05-10 | Component structure and data flow inferred from SKILL.md examples and schema organization |
| Installation & Usage | high | 2026-05-10 | Installation commands and code examples extracted verbatim from SKILL.md |
| Limitations | high | 2026-05-10 | Explicitly documented in SKILL.md line 8 and schema files |
| Relevance | medium | 2026-05-10 | Integration with Claude Code and MCP Server noted in repository README; direct use cases inferred from feature set |

**Next Review**: 2026-08-10 (3 months from creation)

**Change Log**: Initial entry created 2026-05-10.
