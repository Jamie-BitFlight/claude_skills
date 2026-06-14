#!/usr/bin/env node
'use strict';

/**
 * SubagentStop hook — validates that rewrite-room agents include a STATUS block
 * contract in their output before they complete.
 *
 * Fires on: SubagentStop — matcher: ^rewrite-room-
 * Action: blocking (exit 2) when any required STATUS block field is absent or invalid
 *
 * Required fields: STATUS (DONE|BLOCKED|FAILED), SUMMARY, ARTIFACTS, VALIDATION
 * Optional field:  NOTES (absence is NOT a violation)
 *
 * Test command:
 *   echo '{"hook_event_name":"SubagentStop","agent_id":"def456","agent_transcript_path":"/tmp/test.jsonl"}' \
 *     | node ./plugins/the-rewrite-room/hooks/validate-status-block.cjs
 */

const fs = require('node:fs');

const VALID_STATUS_VALUES = new Set(['DONE', 'BLOCKED', 'FAILED']);

/**
 * Extract the text content from the last assistant message in a JSONL transcript.
 * Each line is a JSON record. Records with type "assistant" carry the message.
 * @param {string} transcriptPath
 * @returns {string} Combined text content, or empty string on any error
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

    // Records have shape: {type:"assistant", message:{role:"assistant", content:[{type:"text",text:"..."}]}}
    if (record.type !== 'assistant') continue;

    const message = record.message;
    if (message?.role !== 'assistant') continue;

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
 * Validate the STATUS block contract in the given text.
 * @param {string} text
 * @returns {{ valid: boolean, missingFields: string[], statusValue: string }}
 */
function validateStatusBlock(text) {
  const missingFields = [];

  // STATUS: DONE|BLOCKED|FAILED
  const statusMatch = text.match(/^\s*STATUS:\s*(\S+)/m);
  let statusValue = '';
  if (!statusMatch) {
    missingFields.push('STATUS');
  } else {
    statusValue = statusMatch[1].trim();
    if (!VALID_STATUS_VALUES.has(statusValue)) {
      missingFields.push(`STATUS (invalid value: ${statusValue})`);
    }
  }

  // SUMMARY: non-empty
  const summaryMatch = text.match(/^\s*SUMMARY:\s*(.+)/m);
  if (!summaryMatch?.[1].trim()) {
    missingFields.push('SUMMARY');
  }

  // ARTIFACTS: non-empty (value may be "none" — that is acceptable)
  const artifactsMatch = text.match(/^\s*ARTIFACTS:\s*(.+)/m);
  if (!artifactsMatch?.[1].trim()) {
    missingFields.push('ARTIFACTS');
  }

  // VALIDATION: non-empty
  const validationMatch = text.match(/^\s*VALIDATION:\s*(.+)/m);
  if (!validationMatch?.[1].trim()) {
    missingFields.push('VALIDATION');
  }

  return { valid: missingFields.length === 0, missingFields, statusValue };
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
    // Unparseable input — allow stop
    process.exit(0);
  }

  const transcriptPath = data.agent_transcript_path || '';
  if (!transcriptPath) {
    // No transcript to validate — allow stop
    process.exit(0);
  }

  const lastAssistantText = extractLastAssistantText(transcriptPath);
  if (!lastAssistantText) {
    // No assistant message found — allow stop (agent may have produced no output)
    process.exit(0);
  }

  const { valid, missingFields } = validateStatusBlock(lastAssistantText);
  if (valid) {
    process.exit(0);
  }

  process.stderr.write(
    `CONTRACT_VIOLATION: missing fields: ${missingFields.join(', ')}. STATUS value must be DONE, BLOCKED, or FAILED.\n`,
  );
  process.exit(2);
});
