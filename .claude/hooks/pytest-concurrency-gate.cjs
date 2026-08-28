#!/usr/bin/env node
'use strict';

const fs = require('node:fs');

const pytestTokenPattern =
  /(?:^|[\s;|&`$<>()#'"])(?:[^\s;|&`$<>()#'"]*\/)?pytest(?:\.exe)?(?=$|[\s;|&`$<>()#'"])/;
const canonicalWrapperPattern =
  /^uv run --script scripts\/run_bounded\.py --timeout-seconds [1-9][0-9]* -- uv run pytest(?: [^\r\n;&|`$<>()#]*)?$/;
const unsafeShellSyntaxPattern = /[\r\n;&|`$<>()#]/;

function readEvent() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    return null;
  }
}

function isCanonicalWrapper(command) {
  return !unsafeShellSyntaxPattern.test(command) && canonicalWrapperPattern.test(command);
}

const event = readEvent();
const command = typeof event?.tool_input?.command === 'string' ? event.tool_input.command : '';

if (pytestTokenPattern.test(command) && !isCanonicalWrapper(command)) {
  process.stderr.write(
    'Run pytest through the shared host lock: uv run --script scripts/run_bounded.py --timeout-seconds 300 -- uv run pytest <args>\n',
  );
  process.exit(2);
}
