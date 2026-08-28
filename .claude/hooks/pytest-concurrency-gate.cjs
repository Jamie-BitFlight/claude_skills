#!/usr/bin/env node
'use strict';

const fs = require('node:fs');

const pytestCommandPattern =
  /^(?:command\s+)?(?:env(?:\s+[A-Za-z_][A-Za-z0-9_]*=[^\s]+)*\s+)?(?:(?:uv\s+run(?:\s+--?[^\s]+)*\s+)|(?:python(?:3(?:\.\d+)?)?\s+-m\s+))?(?:[^\s]*\/)?pytest(?:\.exe)?(?:\s|$)/;
const canonicalWrapperPattern =
  /^uv\s+run\s+--script\s+(?:[^\s]*\/)?scripts\/run_bounded\.py\s+--timeout-seconds\s+[^\s]+\s+--\s+(.+)$/;

function readEvent() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    return null;
  }
}

function isRawPytestCommand(command) {
  return command.split(/&&|\|\||;|\|/).some((segment) => pytestCommandPattern.test(segment.trim()));
}

function isCanonicalWrapper(command) {
  const withoutComment = command.split('#', 1)[0].trim();
  const match = canonicalWrapperPattern.exec(withoutComment);
  return match !== null && !/[;&|]/.test(match[1]) && pytestCommandPattern.test(match[1].trim());
}

const event = readEvent();
const command = typeof event?.tool_input?.command === 'string' ? event.tool_input.command : '';

if (isRawPytestCommand(command) && !isCanonicalWrapper(command)) {
  process.stderr.write(
    'Run pytest through the shared host lock: uv run --script scripts/run_bounded.py --timeout-seconds 300 -- uv run pytest <args>\n',
  );
  process.exit(2);
}
