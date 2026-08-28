#!/usr/bin/env node
'use strict';

const fs = require('node:fs');

const rawPytestPattern =
  /(^|(?:&&|\|\||[;|])\s*)(?:uv\s+run\s+(?:-m\s+)?pytest|python(?:3(?:\.\d+)?)?\s+-m\s+pytest|pytest)(?:\s|$)/;
const boundedWrapperPattern = /(?:^|\s)(?:\S+\/)?scripts\/run_bounded\.py(?:\s|$)/;

function readEvent() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    return null;
  }
}

const event = readEvent();
const command = typeof event?.tool_input?.command === 'string' ? event.tool_input.command : '';

if (rawPytestPattern.test(command) && !boundedWrapperPattern.test(command)) {
  process.stderr.write(
    'Run pytest through the shared host lock: uv run --script scripts/run_bounded.py --timeout-seconds 300 -- uv run pytest <args>\n',
  );
  process.exit(2);
}
