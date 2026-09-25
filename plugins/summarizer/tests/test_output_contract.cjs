'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');
const { validate } = require('../hooks/output-contract.cjs');
const { decide, AGENTS } = require('../hooks/validate-summarizer-output.cjs');

const foot = 'Source: fixture.txt | Confidence: high | Read 2026-09-25';
const metadata = {
  source_type: 'file', source_path: 'fixture.txt', summarized_at: '2026-09-25T00:00:00Z',
  method: 'extractive', word_count_source: 12, word_count_summary: 7,
  confidence: 'high', confidence_notes: 'Complete source, direct quotation.',
};
const outputs = {
  structured: `---\n${Object.entries(metadata).map(([k, v]) => `${k}: ${v}`).join('\n')}\n---\n`
    + '## Summary\nThe source says feature X is not supported.\n## What Was Found\n'
    + '- Feature X is not supported (source: line 1).\n## What Was NOT Found\nNone\n'
    + '## Uncertain\nNone\n## Sources\nfixture.txt, read 2026-09-25\n',
  bullets: `## Key Findings\n- 7 of 10 found (source: line 1).\n## Not Found\nNone\n## Uncertain\nNone\n${foot}`,
  tldr: `**TL;DR**: 7 of 10 found; 3 requests timed out.\n${foot}`,
  json: JSON.stringify({ metadata, summary: '7 of 10 found; 3 requests timed out.',
    findings: [{ item: '7 of 10 found', source_ref: 'line 1' }], not_found: [], uncertain: [],
    sources: [{ path: 'fixture.txt', accessed: '2026-09-25' }] }),
  table: '## Summary\n7 of 10 found.\n| Finding | Detail | Source | Status |\n|---|---|---|---|\n'
    + '| Count | 7 of 10 | line 1 | Found |\n| None identified | No searched gaps | N/A | Not Found |\n'
    + `| None identified | No ambiguity | N/A | Uncertain |\n${foot}`,
  outline: `## Outline\n- Results\n  - 7 of 10 found (source: line 1).\n## Not Found\nNone\n## Uncertain\nNone\n${foot}`,
};

function payload(t, format, output, agent = 'summarizer:file-summarizer', extra = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'summarizer-contract-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const transcript = path.join(dir, 'trace.jsonl');
  const task = `SUMMARIZER_FORMAT: ${format}\n${extra.control || ''}\nSummarize the supplied source.`;
  fs.writeFileSync(transcript, [
    { type: 'user', message: { role: 'user', content: task } },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: output }] } },
  ].map((record) => JSON.stringify(record)).join('\n'));
  return { hook_event_name: 'SubagentStop', agent_type: agent, agent_transcript_path: transcript };
}

for (const [format, output] of Object.entries(outputs)) {
  test(`accept requested ${format} without an output format declaration`, (t) => {
    assert.deepEqual(validate(output, format), []);
    assert.equal(decide(payload(t, format, output)).code, 0);
    assert.equal(decide(payload(t, format, output)).notice, undefined);
  });
  test(`reject missing structure for ${format}`, () => {
    assert.ok(validate('The API does something.', format).length > 0);
  });
}

test('plugin namespace is exact and matches configured hook', () => {
  const config = JSON.parse(fs.readFileSync(path.join(__dirname, '../hooks/hooks.json'), 'utf8'));
  const matcher = new RegExp(config.hooks.SubagentStop[0].matcher);
  for (const value of ['file-summarizer', 'summarizer:file-summarizer', 'summarizer:image-summarizer', 'summarizer:url-summarizer']) {
    assert.equal(AGENTS.test(value), true);
    assert.equal(matcher.test(value), true);
  }
  for (const value of ['other:file-summarizer', 'summarizer:other', 'general-purpose']) {
    assert.equal(AGENTS.test(value), false);
    assert.equal(matcher.test(value), false);
  }
});

test('output cannot choose its own format', (t) => {
  const result = decide(payload(t, 'json', `format: tldr\n${outputs.tldr}`));
  assert.equal(result.code, 2);
});

test('explicit source negatives and unquantified source prose are not regex failures', () => {
  assert.deepEqual(validate(outputs.structured.replace('feature X', 'most features'), 'structured'), []);
});

test('JSON field types and evidence references are checked', () => {
  const value = JSON.parse(outputs.json);
  value.findings = [{ item: 'claim', source_ref: '' }];
  assert.ok(validate(JSON.stringify(value), 'json').length);
  value.metadata = [];
  assert.ok(validate(JSON.stringify(value), 'json').length);
});

test('headings inside a quoted code fence do not satisfy the structure contract', () => {
  const fake = outputs.structured.replace('## What Was Found', '```\n## What Was Found\n```');
  assert.ok(validate(fake, 'structured').length);
});

test('optional compression_ratio is not required and CRLF works', () => {
  assert.deepEqual(validate(outputs.structured.replaceAll('\n', '\r\n'), 'structured'), []);
});

test('unavailable metadata is visible and is not success evidence', () => {
  const result = decide({ hook_event_name: 'SubagentStop', agent_type: 'summarizer:file-summarizer' });
  assert.equal(result.code, 0);
  assert.match(result.notice, /NOT_VALIDATED/);
});

test('unrelated agents do not access transcripts', () => {
  assert.deepEqual(decide({ hook_event_name: 'SubagentStop', agent_type: 'general-purpose' }), { code: 0 });
});

test('one correction attempt cannot produce an unbounded stop loop', (t) => {
  const input = payload(t, 'json', 'bad JSON');
  assert.equal(decide(input).code, 2);
  const retry = decide({ ...input, stop_hook_active: true });
  assert.equal(retry.code, 0);
  assert.match(retry.notice, /NOT_VALIDATED/);
});

test('blocked caller envelope is preserved instead of demanding a successful summary', (t) => {
  const result = decide(payload(t, 'json', 'STATUS: BLOCKED\nHTTP 403 on source A.'));
  assert.equal(result.code, 0);
  assert.match(result.notice, /non-success status/);
});

test('caller-assigned artifact, not STATUS envelope, is validated', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'summarizer-artifact-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const artifact = path.join(dir, 'summary with spaces.json');
  fs.writeFileSync(artifact, outputs.json);
  const input = payload(t, 'json', `STATUS: DONE\nSummary: ${artifact}`, undefined,
    { control: `SUMMARIZER_OUTPUT: ${artifact}` });
  assert.equal(decide(input).notice, undefined);
  fs.writeFileSync(artifact, 'not JSON');
  assert.equal(decide(input).code, 2);
});

test('latest message wins over older transcript text', (t) => {
  const input = payload(t, 'json', outputs.json);
  assert.equal(decide({ ...input, last_assistant_message: 'broken' }).code, 2);
});

test('missing artifact reference is unverified, never accepted from an arbitrary response path', (t) => {
  const input = payload(t, 'json', 'STATUS: DONE\nSummary: /unassigned/path', undefined,
    { control: 'SUMMARIZER_OUTPUT: /assigned/path' });
  assert.match(decide(input).notice, /NOT_VALIDATED/);
});

test('standalone validation uses explicit caller format and nonzero failures', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'summarizer-cli-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'summary.json');
  fs.writeFileSync(file, outputs.json);
  const command = path.join(__dirname, '../hooks/output-contract.cjs');
  const valid = spawnSync(process.execPath, [command, '--format', 'json', '--input', file], { encoding: 'utf8' });
  assert.equal(valid.status, 0);
  assert.equal(JSON.parse(valid.stdout).status, 'STRUCTURE_VALID');
  const invalid = spawnSync(process.execPath, [command, '--format', 'tldr', '--input', file], { encoding: 'utf8' });
  assert.equal(invalid.status, 1);
});
