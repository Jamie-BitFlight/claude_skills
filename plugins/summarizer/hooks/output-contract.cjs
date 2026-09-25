#!/usr/bin/env node
'use strict';

// Structural validation only. Source support and omission require evidence review.
const fs = require('node:fs');
const { parseArgs } = require('node:util');

const FORMATS = ['structured', 'bullets', 'tldr', 'json', 'table', 'outline'];
const METADATA = [
  'source_type',
  'source_path',
  'summarized_at',
  'method',
  'word_count_source',
  'word_count_summary',
  'confidence',
  'confidence_notes',
];
const SECTIONS = ['Summary', 'What Was Found', 'What Was NOT Found', 'Uncertain', 'Sources'];

function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function visibleMarkdown(text) {
  const normalized = text.replace(/\r\n/g, '\n');
  const withoutFrontmatter = normalized.replace(/^---\n[\s\S]*?\n---(?:\n|$)/, '');
  const withoutComments = withoutFrontmatter.replace(/<!--[\s\S]*?-->/g, '');
  const lines = withoutComments.split('\n');
  let fence = null;
  return lines
    .filter((line) => {
      const marker = line.match(/^\s*(`{3,}|~{3,})/);
      if (marker) {
        if (!fence) fence = marker[1];
        else if (marker[1][0] === fence[0] && marker[1].length >= fence.length) fence = null;
        return false;
      }
      return !fence;
    })
    .join('\n');
}

function headings(text) {
  return [...visibleMarkdown(text).matchAll(/^#{1,6}\s+(.+?)\s*#*\s*$/gm)].map((m) => m[1]);
}

function footer(text) {
  const last = text.trim().split('\n').at(-1) || '';
  return /^Source:\s*\S.*\|\s*Confidence:\s*(high|medium|low)\s*\|\s*\S.+$/i.test(last);
}

function validateJson(text) {
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    return ['Output must be raw, parseable JSON.'];
  }
  if (!object(value)) return ['JSON output must be an object.'];
  const errors = [];
  for (const key of ['metadata', 'summary', 'findings', 'not_found', 'uncertain', 'sources']) {
    if (!(key in value)) errors.push(`Missing JSON key: ${key}`);
  }
  if (!object(value.metadata)) errors.push('metadata must be an object.');
  else {
    for (const key of METADATA) {
      if (!(key in value.metadata)) errors.push(`Missing metadata.${key}`);
    }
    if (!['file', 'url', 'image', 'multi-source'].includes(value.metadata.source_type))
      errors.push('Invalid source_type.');
    const sourcePath = value.metadata.source_path;
    if (
      !(
        (typeof sourcePath === 'string' && sourcePath.trim()) ||
        (Array.isArray(sourcePath) &&
          sourcePath.length > 0 &&
          sourcePath.every((item) => typeof item === 'string' && item.trim()))
      )
    )
      errors.push('source_path must be a nonempty string or array of nonempty strings.');
    if (typeof value.metadata.summarized_at !== 'string' || !value.metadata.summarized_at.trim())
      errors.push('summarized_at must be a nonempty string.');
    if (!['extractive', 'abstractive', 'hybrid'].includes(value.metadata.method))
      errors.push('Invalid method.');
    if (
      value.metadata.word_count_source !== null &&
      (!Number.isInteger(value.metadata.word_count_source) || value.metadata.word_count_source < 0)
    )
      errors.push('word_count_source must be a nonnegative integer or null.');
    if (!Number.isInteger(value.metadata.word_count_summary) || value.metadata.word_count_summary < 0)
      errors.push('word_count_summary must be a nonnegative integer.');
    if (
      'compression_ratio' in value.metadata &&
      value.metadata.compression_ratio !== null &&
      (typeof value.metadata.compression_ratio !== 'number' ||
        !Number.isFinite(value.metadata.compression_ratio) ||
        value.metadata.compression_ratio < 0)
    )
      errors.push('compression_ratio must be a nonnegative finite number or null.');
    if (!['high', 'medium', 'low'].includes(value.metadata.confidence))
      errors.push('Invalid confidence.');
    if (
      typeof value.metadata.confidence_notes !== 'string' ||
      !value.metadata.confidence_notes.trim()
    ) {
      errors.push('confidence_notes must explain the assessment.');
    }
  }
  if (typeof value.summary !== 'string' || !value.summary.trim())
    errors.push('summary must be nonempty.');
  for (const key of ['findings', 'not_found', 'uncertain', 'sources']) {
    if (!Array.isArray(value[key])) errors.push(`${key} must be an array.`);
  }
  for (const key of ['not_found', 'uncertain']) {
    for (const item of Array.isArray(value[key]) ? value[key] : []) {
      if (typeof item !== 'string' || !item.trim())
        errors.push(`Each ${key} item must be a nonempty string.`);
    }
  }
  for (const finding of Array.isArray(value.findings) ? value.findings : []) {
    if (
      !object(finding) ||
      typeof finding.item !== 'string' ||
      !finding.item.trim() ||
      typeof finding.source_ref !== 'string' ||
      !finding.source_ref.trim()
    ) {
      errors.push('Each finding requires nonempty item and source_ref strings.');
    }
  }
  for (const source of Array.isArray(value.sources) ? value.sources : []) {
    if (
      !object(source) ||
      typeof source.path !== 'string' ||
      !source.path.trim() ||
      typeof source.accessed !== 'string' ||
      !source.accessed.trim()
    ) {
      errors.push('Each source requires path and accessed strings.');
    }
  }
  return errors;
}

function validate(text, format) {
  if (!FORMATS.includes(format)) return [`Unsupported format: ${format}`];
  if (typeof text !== 'string' || !text.trim()) return ['Summary is empty.'];
  if (format === 'json') return validateJson(text);
  const normalized = text.replace(/\r\n/g, '\n');
  const body = visibleMarkdown(normalized);
  const found = headings(normalized);
  const errors = [];
  if (format === 'structured') {
    const fm = normalized.match(/^---\n([\s\S]*?)\n---(?:\n|$)/);
    if (!fm) errors.push('Missing YAML frontmatter.');
    else {
      for (const key of METADATA) {
        if (!new RegExp(`^${key}\\s*:`, 'm').test(fm[1]))
          errors.push(`Missing frontmatter: ${key}`);
      }
    }
    let previous = -1;
    for (const section of SECTIONS) {
      const index = found.indexOf(section);
      if (index <= previous || index < 0)
        errors.push(`Missing or out-of-order section: ${section}`);
      previous = index;
    }
  } else {
    if (!footer(body)) errors.push('Missing source/confidence/date footer.');
    if (format === 'tldr') {
      if (!/^\*\*TL;DR\*\*/m.test(body)) errors.push('Missing TL;DR paragraph.');
      if (/Confidence:\s*low/i.test(body) && !/^\*\*TL;DR\*\*[^\n]*low confidence/i.test(body)) {
        errors.push('State low confidence in the TL;DR paragraph.');
      }
    } else if (format === 'table') {
      const rows = body
        .split('\n')
        .filter((line) => /^\s*\|/.test(line))
        .map((line) =>
          line
            .trim()
            .slice(1, -1)
            .split(/(?<!\\)\|/)
            .map((cell) => cell.trim()),
        );
      const header = rows[0] || [];
      const required = ['Finding', 'Detail', 'Source', 'Status'];
      if (!required.every((name) => header.includes(name))) errors.push('Missing table columns.');
      else {
        const statuses = new Set();
        for (const row of rows.slice(2)) {
          const status = row[header.indexOf('Status')];
          statuses.add(status);
          if (
            row.length !== header.length ||
            !['Found', 'Not Found', 'Uncertain'].includes(status)
          ) {
            errors.push('Invalid findings table row.');
          }
          const source = row[header.indexOf('Source')];
          if (status === 'Found' && (!source || /^(N\/A|None)$/i.test(source))) {
            errors.push('Found rows require a source reference.');
          }
        }
        for (const status of ['Not Found', 'Uncertain']) {
          if (!statuses.has(status))
            errors.push(`Missing ${status} row (use None identified when empty).`);
        }
      }
      if (!found.includes('Summary')) errors.push('Missing Summary section.');
    } else {
      const required =
        format === 'bullets'
          ? ['Key Findings', 'Not Found', 'Uncertain']
          : ['Outline', 'Not Found', 'Uncertain'];
      for (const section of required)
        if (!found.includes(section)) errors.push(`Missing section: ${section}`);
    }
  }
  return errors;
}

if (require.main === module) {
  try {
    const { values } = parseArgs({
      options: { format: { type: 'string' }, input: { type: 'string' } },
    });
    if (!values.format || !values.input) throw new Error('Required: --format <id> --input <path>');
    const issues = validate(fs.readFileSync(values.input, 'utf8'), values.format);
    console.log(JSON.stringify({ status: issues.length ? 'INVALID' : 'STRUCTURE_VALID', issues }));
    process.exitCode = issues.length ? 1 : 0;
  } catch (error) {
    console.log(JSON.stringify({ status: 'UNVERIFIED', issues: [error.message] }));
    process.exitCode = 2;
  }
}
module.exports = { FORMATS, validate };
