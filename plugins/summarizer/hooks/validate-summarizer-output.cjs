#!/usr/bin/env node
'use strict';

/**
 * SubagentStop hook — validates summarizer sub-agent output quality.
 *
 * Fires on: SubagentStop with matcher "^(file-summarizer|url-summarizer|image-summarizer)$"
 *           in hooks.json (matched against agent_type field in the hook payload).
 * Action: blocking (exit 2 + reason on stderr) when format requirements or fidelity
 *         rules are violated. The redundant agent_type check below handles cases where
 *         the hook fires without matcher filtering.
 *
 * Blocking protocol: exit 2 with reason written to stderr (JSON on stdout is ignored
 *                    by Claude Code on exit 2).
 *
 * Test command:
 *   echo '{"hook_event_name":"SubagentStop","agent_type":"general-purpose","agent_transcript_path":"/tmp/test.jsonl"}' \
 *     | node ./plugins/summarizer/hooks/validate-summarizer-output.cjs
 */

const fs = require('node:fs');

const SUMMARIZER_AGENT_TYPES = new Set(['file-summarizer', 'url-summarizer', 'image-summarizer']);

/**
 * Extract the text content from the last assistant message in a JSONL transcript.
 * @param {string} transcriptPath
 * @returns {string} Combined text content, or empty string on any error.
 */
function extractLastAssistantText(transcriptPath) {
  let raw;
  try {
    raw = fs.readFileSync(transcriptPath, 'utf8');
  } catch {
    return '';
  }

  const lines = raw.split('\n').filter((l) => l.trim().length > 0);
  let lastAssistantText = '';

  for (const line of lines) {
    let record;
    try {
      record = JSON.parse(line);
    } catch {
      continue;
    }

    if (record.type !== 'assistant') continue;
    const message = record.message;
    if (!message || message.role !== 'assistant') continue;
    const content = Array.isArray(message.content) ? message.content : [];
    const textParts = content
      .filter((c) => c && c.type === 'text' && typeof c.text === 'string')
      .map((c) => c.text);
    if (textParts.length > 0) {
      lastAssistantText = textParts.join('\n');
    }
  }

  return lastAssistantText;
}

/**
 * Detect the format_id from the agent's output or prompt context.
 * Falls back to 'structured' (the default format).
 * @param {string} text Last assistant message text.
 * @returns {string} One of: structured, bullets, tldr, json, table, outline.
 */
function detectFormat(text) {
  // Look for explicit format declaration in the text (e.g. from task metadata)
  const match = text.match(
    /\bformat[:\s]+['""]?(structured|bullets|tldr|json|table|outline)['""]?/i,
  );
  if (match) return match[1].toLowerCase();
  return 'structured';
}

/**
 * Validate 'structured' format output.
 * @param {string} text
 * @returns {string[]} List of missing items (empty = pass).
 */
function validateStructured(text) {
  const missing = [];

  // YAML frontmatter with all required fields
  const frontmatterMatch = text.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatterMatch) {
    missing.push('YAML frontmatter block');
  } else {
    const fm = frontmatterMatch[1];
    for (const field of [
      'source_type',
      'source_path',
      'summarized_at',
      'method',
      'word_count_source',
      'word_count_summary',
      'compression_ratio',
      'confidence',
      'confidence_notes',
    ]) {
      if (!new RegExp(`^${field}\\s*:`, 'm').test(fm)) {
        missing.push(`frontmatter field: ${field}`);
      }
    }
  }

  if (!/#+\s*Summary/i.test(text)) missing.push('Summary section (BLUF style)');
  if (!/#+\s*What Was Found/i.test(text)) missing.push('What Was Found section');
  if (!/#+\s*What Was NOT Found/i.test(text)) missing.push('What Was NOT Found section');
  if (!/#+\s*Uncertain/i.test(text)) missing.push('Uncertain section');
  if (!/#+\s*Sources/i.test(text)) missing.push('Sources section');

  return missing;
}

/**
 * Validate 'bullets' format output.
 * @param {string} text
 * @returns {string[]} List of missing items.
 */
function validateBullets(text) {
  const missing = [];
  if (!/#+\s*Key Findings/i.test(text)) missing.push('Key Findings section');
  if (!/#+\s*Not Found/i.test(text)) missing.push('Not Found section');
  if (!/#+\s*Uncertain/i.test(text)) missing.push('Uncertain section');
  if (!/Source[\s:]/i.test(text) || !/Confidence[\s:]/i.test(text)) {
    missing.push('footer line with Source and Confidence');
  }
  return missing;
}

/**
 * Validate 'tldr' format output.
 * @param {string} text
 * @returns {string[]} List of missing items.
 */
function validateTldr(text) {
  const missing = [];
  // TL;DR paragraph: 2-4 sentences — check for TL;DR marker
  if (!/TL[;:]?DR/i.test(text)) missing.push('TL;DR paragraph');
  if (!/Source[\s:]/i.test(text) || !/Confidence[\s:]/i.test(text)) {
    missing.push('footer line with Source and Confidence');
  }
  // Low confidence must be stated
  const confidenceMatch = text.match(/Confidence[\s:]+([^\n]+)/i);
  if (confidenceMatch) {
    const level = confidenceMatch[1].toLowerCase();
    if (level.includes('low') && !/low/i.test(text.split('\n').slice(0, 6).join('\n'))) {
      missing.push('TL;DR must state low confidence when confidence is low');
    }
  }
  return missing;
}

/**
 * Validate 'json' format output.
 * @param {string} text
 * @returns {string[]} List of missing items.
 */
function validateJson(text) {
  const missing = [];
  // Find JSON block
  const jsonMatch = text.match(/```json\n([\s\S]*?)```/) || text.match(/(\{[\s\S]*\})/);
  if (!jsonMatch) {
    return ['valid JSON output'];
  }
  let parsed;
  try {
    parsed = JSON.parse(jsonMatch[1]);
  } catch {
    return ['parseable JSON output'];
  }
  for (const key of ['metadata', 'summary', 'findings', 'not_found', 'uncertain', 'sources']) {
    if (!(key in parsed)) missing.push(`JSON key: ${key}`);
  }
  if (parsed.metadata && typeof parsed.metadata === 'object') {
    if (!('confidence' in parsed.metadata)) missing.push('metadata.confidence');
    if (!('confidence_notes' in parsed.metadata)) missing.push('metadata.confidence_notes');
  }
  if (Array.isArray(parsed.findings)) {
    const withoutSourceRef = parsed.findings.filter((f) => f && !('source_ref' in f));
    if (withoutSourceRef.length > 0) missing.push('source_ref on all findings array items');
  }
  return missing;
}

/**
 * Validate 'table' format output.
 * @param {string} text
 * @returns {string[]} List of missing items.
 */
function validateTable(text) {
  const missing = [];
  // Check that all four required columns appear in the header row (order-independent).
  const hasColumn = (col) => new RegExp(`\\|\\s*${col}\\s*\\|`, 'i').test(text);
  const missingCols = ['Finding', 'Detail', 'Source', 'Status'].filter((c) => !hasColumn(c));
  if (missingCols.length > 0) {
    missing.push(`markdown table missing required columns: ${missingCols.join(', ')}`);
  }
  if (!/\|\s*(Not Found|Uncertain|None identified)/i.test(text)) {
    missing.push('at least one Not Found, Uncertain, or None identified row');
  }
  if (!/Source[\s:]/i.test(text) || !/Confidence[\s:]/i.test(text)) {
    missing.push('footer line with Source and Confidence');
  }
  return missing;
}

/**
 * Validate 'outline' format output.
 * @param {string} text
 * @returns {string[]} List of missing items.
 */
function validateOutline(text) {
  const missing = [];
  if (!/#+\s*Not Found/i.test(text)) missing.push('Not Found section');
  if (!/#+\s*Uncertain/i.test(text)) missing.push('Uncertain section');
  if (!/Source[\s:]/i.test(text) || !/Confidence[\s:]/i.test(text)) {
    missing.push('footer line with Source and Confidence');
  }
  return missing;
}

/**
 * Check for fidelity violations applicable to all formats.
 * @param {string} text
 * @returns {string[]} List of violations found.
 */
function checkFidelityViolations(text) {
  const violations = [];
  if (/\b(most|several|some)\b/i.test(text) && !/\b\d+\b/.test(text)) {
    violations.push("vague quantifiers ('most', 'several', 'some') used without exact counts");
  }
  if (/doesn'?t exist|is not supported/i.test(text)) {
    violations.push("'not found' upgraded to 'doesn't exist' or 'is not supported'");
  }
  if (!/confidence/i.test(text)) {
    violations.push('missing confidence assessment');
  }
  return violations;
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let data = {};
  try {
    data = JSON.parse(input);
  } catch {
    // Unparseable input — allow stop silently
    process.exit(0);
  }

  // STEP 1 — Agent type gate: exit 0 silently for non-summarizer agents
  const agentType = (data.agent_type || '').toLowerCase();
  if (!SUMMARIZER_AGENT_TYPES.has(agentType)) {
    process.exit(0);
  }

  // STEP 2 — Extract last assistant message from transcript
  const transcriptPath = data.agent_transcript_path || '';
  if (!transcriptPath) {
    process.exit(0);
  }
  const text = extractLastAssistantText(transcriptPath);
  if (!text) {
    process.exit(0);
  }

  // STEP 3 — Detect format and validate
  const formatId = detectFormat(text);
  let missingItems = [];

  switch (formatId) {
    case 'bullets':
      missingItems = validateBullets(text);
      break;
    case 'tldr':
      missingItems = validateTldr(text);
      break;
    case 'json':
      missingItems = validateJson(text);
      break;
    case 'table':
      missingItems = validateTable(text);
      break;
    case 'outline':
      missingItems = validateOutline(text);
      break;
    default:
      missingItems = validateStructured(text);
  }

  // STEP 4 — Fidelity violations (all formats)
  const fidelityViolations = checkFidelityViolations(text);

  // STEP 5 — Output decision
  if (missingItems.length === 0 && fidelityViolations.length === 0) {
    // Pass: output empty object (no stdout noise on success)
    process.exit(0);
  }

  const parts = [];
  if (missingItems.length > 0) parts.push(`Missing: ${missingItems.join('; ')}`);
  if (fidelityViolations.length > 0)
    parts.push(`Fidelity violations: ${fidelityViolations.join('; ')}`);

  // Exit 2 with reason on stderr — Claude Code ignores JSON on stdout when exit code is 2.
  process.stderr.write(`[summarizer-hook] BLOCKED. Format: ${formatId}. ${parts.join('. ')}.\n`);
  process.exit(2);
});
