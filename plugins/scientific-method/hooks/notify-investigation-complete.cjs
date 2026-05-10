#!/usr/bin/env node
'use strict';

/**
 * SubagentStop hook — detects completed scientific investigations and notifies
 * the user that the retrospective-analyst agent is available.
 *
 * Fires on: SubagentStop (no matcher — fires on all agents, fast grep only)
 * Action: non-blocking — emits systemMessage when status: resolved-verified
 *         is found in section 14 of the Unified Investigation Template output.
 *
 * Replaces the former "prompt" type hook, which made an LLM call on every
 * SubagentStop. This script does a text search on the transcript instead.
 *
 * Test:
 *   echo '{"hook_event_name":"SubagentStop","agent_type":"general-purpose","agent_transcript_path":"/tmp/test.jsonl"}' \
 *     | node ./plugins/scientific-method/hooks/notify-investigation-complete.cjs
 */

const fs = require('node:fs');

const NOTIFICATION =
  'Investigation complete (resolved-verified). The retrospective-analyst agent can produce a mermaid timeline and structured retrospective from this investigation. Invoke it with the full investigation output as input.';

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

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let data = {};
  try {
    data = JSON.parse(input || '{}');
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const transcriptPath = data.agent_transcript_path || '';
  if (!transcriptPath) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const text = extractLastAssistantText(transcriptPath);
  if (!text) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Look for status: resolved-verified anywhere in the output
  if (/status:\s*resolved-verified/i.test(text)) {
    process.stdout.write(JSON.stringify({ systemMessage: NOTIFICATION }));
    process.exit(0);
  }

  process.stdout.write(JSON.stringify({}));
  process.exit(0);
});
