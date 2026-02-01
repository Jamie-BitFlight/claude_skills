#!/usr/bin/env node
/**
 * Stop hook: audit the last assistant message for misinformation patterns.
 *
 * Goal: reduce "speculation as diagnosis" and invented causality/facts.
 *
 * Mechanism:
 * - Parse Stop hook input (stdin JSON).
 * - Read `transcript_path` (JSONL).
 * - Extract last main-chain assistant message text.
 * - If flagged, emit JSON: { "decision": "block", "reason": "..." } (exit 0).
 *
 * Notes:
 * - Uses a small per-session counter in OS tempdir to avoid infinite loops.
 * - Does not attempt to infer truth; it enforces language discipline and evidence signaling.
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function readStdinJson() {
  try {
    const stdin = fs.readFileSync(0, 'utf-8');
    return JSON.parse(stdin);
  } catch {
    return {};
  }
}

function safeReadFileText(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return '';
  }
}

function parseJsonl(text) {
  const entries = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      entries.push(JSON.parse(trimmed));
    } catch {
      // ignore non-JSON lines
    }
  }
  return entries;
}

function isSidechainEntry(entry) {
  return Boolean(entry?.isSidechain);
}

function extractTextFromMessageContent(content) {
  // Claude transcripts commonly store content as an array of blocks.
  // We only extract human-readable text; we ignore tool_use blocks.
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';

  const parts = [];
  for (const block of content) {
    if (!block || typeof block !== 'object') continue;
    if (block.type === 'tool_use') continue;

    // Common block shapes:
    // - { type: "text", text: "..." }
    // - { type: "output_text", text: "..." } (future-proof)
    // - { ... , content: "..." }
    if (typeof block.text === 'string' && block.text.trim()) {
      parts.push(block.text);
      continue;
    }
    if (typeof block.content === 'string' && block.content.trim()) {
      parts.push(block.content);
    }
  }
  return parts.join('\n').trim();
}

function getLastAssistantText(transcriptEntries) {
  // Find last main-chain assistant entry with message content.
  for (let i = transcriptEntries.length - 1; i >= 0; i--) {
    const entry = transcriptEntries[i];
    if (!entry || typeof entry !== 'object') continue;
    if (isSidechainEntry(entry)) continue;

    const type = entry.type;
    const message = entry.message;
    if (type !== 'assistant' || !message) continue;

    const content = message.content;
    const text = extractTextFromMessageContent(content);
    if (text) return text;
  }
  return '';
}

function normalizeForScan(text) {
  return text.replace(/\r\n/g, '\n');
}

function stripLowSignalRegions(text) {
  // Avoid false positives from quoted user text or code samples.
  // We only enforce these language rules on the assistant's narrative assertions.
  let out = text;

  // Remove fenced code blocks.
  out = out.replace(/```[\s\S]*?```/g, '');

  // Remove inline code spans.
  out = out.replace(/`[^`\n]*`/g, '');

  // Remove blockquote lines (often used for quoting user text or external sources).
  out = out
    .split('\n')
    .filter((line) => !line.trimStart().startsWith('>'))
    .join('\n');

  return out;
}

function isIndexWithinQuestion(text, idx) {
  // Heuristic: treat the containing "sentence" as a question if it includes a '?'
  // between the nearest prior sentence boundary and the next sentence boundary.
  const startBoundary = Math.max(
    text.lastIndexOf('\n', idx),
    text.lastIndexOf('.', idx),
    text.lastIndexOf('!', idx),
    text.lastIndexOf('?', idx),
  );
  const start = startBoundary === -1 ? 0 : startBoundary + 1;

  const nextNewline = text.indexOf('\n', idx);
  const nextDot = text.indexOf('.', idx);
  const nextBang = text.indexOf('!', idx);
  const nextQ = text.indexOf('?', idx);

  const candidates = [nextNewline, nextDot, nextBang, nextQ].filter((n) => n !== -1);
  const end = candidates.length ? Math.min(...candidates) + 1 : text.length;

  const segment = text.slice(start, end);
  return segment.includes('?');
}

function findTriggerMatches(text) {
  const matches = [];
  const haystack = stripLowSignalRegions(normalizeForScan(text));
  const lower = haystack.toLowerCase();

  // 1) Assumption/speculation language (explicitly discouraged by repo policy)
  const speculationPhrases = [
    'i think',
    'i believe',
    'probably',
    'likely',
    'it seems',
    'seems like',
    'should be',
    'i assume',
    'assume',
    'maybe',
    'might be',
    'could be',
    'presumably',
  ];
  for (const phrase of speculationPhrases) {
    const idx = lower.indexOf(phrase);
    if (idx !== -1) {
      // Questions like "Should I do that now?" are desirable—don't flag.
      if (isIndexWithinQuestion(haystack, idx)) continue;
      matches.push({ kind: 'speculation_language', evidence: phrase });
    }
  }

  // 2) Hard causality claims (heuristic trigger): "X because Y" / "due to" / "caused by"
  // We don't try to prove they're wrong; we require evidence wording when asserting causality.
  const causalityPhrases = [
    'caused by',
    'due to',
    'because',
    'as a result',
    'therefore',
    'this means',
  ];
  for (const phrase of causalityPhrases) {
    const idx = lower.indexOf(phrase);
    if (idx !== -1) {
      // Allow question-form hypotheses; only gate declarative causality.
      if (isIndexWithinQuestion(haystack, idx)) continue;
      matches.push({ kind: 'causality_language', evidence: phrase });
    }
  }

  // 3) Fake rigor / uncited quantification
  const fakeRigorRegexes = [/\b\d+(?:\.\d+)?\s*\/\s*10\b/i, /\b\d{1,3}(?:\.\d+)?\s*%\b/i];
  for (const re of fakeRigorRegexes) {
    const m = haystack.match(re);
    if (m) {
      matches.push({ kind: 'pseudo_quantification', evidence: m[0] });
    }
  }

  // 4) Over-claiming completeness (must be backed by explicit actions/observations)
  const completenessPhrases = [
    'all files checked',
    'comprehensive analysis',
    'everything is fixed',
    'fully resolved',
    'complete solution',
  ];
  for (const phrase of completenessPhrases) {
    if (lower.includes(phrase)) {
      matches.push({ kind: 'completeness_claim', evidence: phrase });
    }
  }

  return matches;
}

function loadLoopState(sessionId) {
  const statePath = path.join(
    os.tmpdir(),
    `claude-hallucination-audit-${sessionId || 'unknown'}.json`,
  );
  try {
    const raw = fs.readFileSync(statePath, 'utf-8');
    const data = JSON.parse(raw);
    if (typeof data === 'object' && data) return { statePath, data };
  } catch {
    // ignore
  }
  return { statePath, data: { blocks: 0 } };
}

function saveLoopState(statePath, data) {
  try {
    fs.writeFileSync(statePath, JSON.stringify(data), 'utf-8');
  } catch {
    // ignore
  }
}

function emitJson(obj) {
  process.stdout.write(`${JSON.stringify(obj)}\n`);
}

function main() {
  const input = readStdinJson();
  const transcriptPath = input.transcript_path || '';
  const sessionId = input.session_id || '';
  const stopHookActive = Boolean(input.stop_hook_active);

  if (!transcriptPath || !fs.existsSync(transcriptPath)) {
    process.exit(0);
  }

  const transcriptText = safeReadFileText(transcriptPath);
  if (!transcriptText.trim()) {
    process.exit(0);
  }

  const entries = parseJsonl(transcriptText);
  const lastAssistantText = getLastAssistantText(entries);
  if (!lastAssistantText) {
    process.exit(0);
  }

  const matches = findTriggerMatches(lastAssistantText);
  if (matches.length === 0) {
    const { statePath } = loadLoopState(sessionId);
    saveLoopState(statePath, { blocks: 0 });
    process.exit(0);
  }

  const { statePath, data } = loadLoopState(sessionId);
  const blocks = Number(data.blocks || 0);
  const nextBlocks = blocks + 1;

  // Avoid infinite loops: after 2 blocks in the same session, allow stop.
  if (nextBlocks > 2 && stopHookActive) {
    saveLoopState(statePath, { blocks: nextBlocks });
    process.exit(0);
  }

  saveLoopState(statePath, { blocks: nextBlocks });

  const uniqueKinds = [...new Set(matches.map((m) => m.kind))];
  const evidenceSnippets = matches
    .slice(0, 6)
    .map((m) => `- ${m.kind}: "${m.evidence}"`)
    .join('\n');

  const reason = [
    'Hallucination-detector STOP HOOK blocked this response.',
    '',
    'Detected trigger language in your last assistant message:',
    evidenceSnippets || '- (no snippets available)',
    '',
    'Rewrite the response to follow these rules:',
    '- Only state actions you actually took and what you actually observed.',
    '- If information is missing, say "I don\'t know yet" / "I don\'t have that information" / "I can check using my tools".',
    '- Do not assert causality unless you explicitly cite the observed evidence that supports it.',
    '- Remove speculative hedging (e.g., "probably", "likely", "seems"). Replace with verification steps or uncertainty statements.',
    '',
    `Kinds flagged: ${uniqueKinds.join(', ')}`,
  ].join('\n');

  emitJson({ decision: 'block', reason });
  process.exit(0);
}

main();
