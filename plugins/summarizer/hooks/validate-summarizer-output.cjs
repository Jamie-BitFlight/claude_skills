#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { FORMATS, validate } = require('./output-contract.cjs');
const AGENTS = /^(?:summarizer:)?(?:file|url|image)-summarizer$/;

function textOf(message) {
  if (typeof message?.content === 'string') return message.content;
  return (Array.isArray(message?.content) ? message.content : [])
    .filter((part) => part?.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text).join('\n');
}

function requestFrom(records) {
  const first = records.find((record) => record.type === 'user' && record.message?.role === 'user');
  const text = textOf(first?.message);
  const formats = [...text.matchAll(/^SUMMARIZER_FORMAT:\s*(\S+)\s*$/gm)];
  const outputs = [...text.matchAll(/^SUMMARIZER_OUTPUT:[ \t]*(.+?)[ \t]*\r?$/gm)];
  if (formats.length !== 1 || !FORMATS.includes(formats[0][1]) || outputs.length > 1) {
    throw new Error('Expected one caller SUMMARIZER_FORMAT control in the initial task.');
  }
  const output = outputs[0]?.[1];
  if (output && !path.isAbsolute(output)) throw new Error('SUMMARIZER_OUTPUT must be an absolute caller-assigned path.');
  return { format: formats[0][1], output };
}

function decide(data) {
  if (data?.hook_event_name !== 'SubagentStop' || !AGENTS.test(data.agent_type || '')) return { code: 0 };
  try {
    if (!data.agent_transcript_path) throw new Error('No transcript available for caller controls.');
    const records = fs.readFileSync(data.agent_transcript_path, 'utf8').split('\n')
      .filter((line) => line.trim()).map((line) => JSON.parse(line));
    const request = requestFrom(records);
    const last = records.filter((r) => r.type === 'assistant' && r.message?.role === 'assistant').at(-1);
    const message = typeof data.last_assistant_message === 'string' ? data.last_assistant_message : textOf(last?.message);
    if (/^STATUS: (BLOCKED|PARTIAL)\r?\n/.test(message)) {
      return { code: 0, notice: 'NOT_VALIDATED: caller received a non-success status; preserve its reasons and remaining scope.' };
    }
    let text = message;
    if (request.output) {
      if (!message.includes(request.output)) throw new Error('Final response does not reference the assigned summary artifact.');
      text = fs.readFileSync(request.output, 'utf8');
    }
    const issues = validate(text, request.format);
    if (!issues.length) return { code: 0 };
    const reason = `Format ${request.format}: ${issues.join('; ')}`;
    if (data.stop_hook_active === true) {
      return { code: 0, notice: `NOT_VALIDATED after correction attempt: ${reason}. Caller must validate before accepting DONE.` };
    }
    return { code: 2, reason: `${reason}. Correct once; if blocked, return STATUS: BLOCKED with the reason.` };
  } catch (error) {
    return { code: 0, notice: `NOT_VALIDATED: ${error.message}. Run explicit validation before accepting the result.` };
  }
}

if (require.main === module) {
  let result;
  try { result = decide(JSON.parse(fs.readFileSync(0, 'utf8'))); }
  catch (error) { result = { code: 0, notice: `NOT_VALIDATED: ${error.message}` }; }
  if (result.reason) process.stderr.write(`[summarizer-hook] ${result.reason}\n`);
  if (result.notice) process.stdout.write(`${JSON.stringify({ systemMessage: `[summarizer-hook] ${result.notice}` })}\n`);
  process.exitCode = result.code;
}
module.exports = { AGENTS, decide, requestFrom };
