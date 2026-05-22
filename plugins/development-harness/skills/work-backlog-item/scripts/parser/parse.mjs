#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

function printErrorAndExit(message) {
  console.error(message);
  process.exit(1);
}

function loadRegistry() {
  try {
    const __dirname = dirname(fileURLToPath(import.meta.url));
    const registryPath = join(__dirname, 'command-routes.json');
    const data = readFileSync(registryPath, 'utf-8');
    return JSON.parse(data).commands || {};
  } catch (err) {
    printErrorAndExit(`Failed to load command-routes.json: ${err.message}`);
  }
}

try {
  const commands = loadRegistry();
  const registryKeys = Object.keys(commands);

  // If the user passes the entire invocation as a single quoted string (e.g., to prevent bash from treating # as a comment),
  // we need to split it back into an array of arguments, respecting quotes.
  let rawArgv = process.argv.slice(2);
  if (rawArgv.length === 1) {
    // Basic split by space, but this doesn't handle internal quotes well.
    // However, for this specific CLI, we mostly care about splitting by spaces.
    // A more robust approach is to use a regex that respects quotes.
    const match = rawArgv[0].match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g);
    if (match) {
      rawArgv = match.map((arg) => {
        // Strip surrounding quotes if present
        if (
          (arg.startsWith('"') && arg.endsWith('"')) ||
          (arg.startsWith("'") && arg.endsWith("'"))
        ) {
          return arg.slice(1, -1);
        }
        return arg;
      });
    } else {
      rawArgv = [];
    }
  }

  // Normalize mobile autocorrect: em dash (U+2014) and en dash (U+2013) attached to a word
  // are treated as double-hyphen prefix. e.g. –auto → --auto, —language → --language.
  // Standalone — and – are also normalised to -- so the delimiter check below catches them.
  rawArgv = rawArgv.map((arg) =>
    arg.startsWith('—') || arg.startsWith('–') ? '--' + arg.slice(1) : arg,
  );

  // 1. Find freetext delimiter
  const delimiters = ['--', '—', '–'];
  let delimiterIndex = -1;
  for (let i = 0; i < rawArgv.length; i++) {
    if (delimiters.includes(rawArgv[i])) {
      delimiterIndex = i;
      break;
    }
  }

  let prefix = [];
  let suffix = [];

  if (delimiterIndex !== -1) {
    prefix = rawArgv.slice(0, delimiterIndex);
    suffix = rawArgv.slice(delimiterIndex + 1);
  } else {
    prefix = rawArgv;
  }

  // 2. Remove script-only tokens from prefix only
  const prefixWithoutScriptOpts = prefix.filter((arg) => arg !== '--help' && arg !== '-h');

  if (prefix.includes('--help') || prefix.includes('-h')) {
    process.exit(0);
  }

  // 3. Parse prefix
  const flags = {};
  const positionals = [];

  for (let i = 0; i < prefixWithoutScriptOpts.length; i++) {
    const token = prefixWithoutScriptOpts[i];

    if (token === '--language') {
      if (
        i + 1 >= prefixWithoutScriptOpts.length ||
        prefixWithoutScriptOpts[i + 1].startsWith('-')
      ) {
        printErrorAndExit('Missing value for --language');
      }
      flags.language = prefixWithoutScriptOpts[++i];
    } else if (token === '--stack') {
      if (
        i + 1 >= prefixWithoutScriptOpts.length ||
        prefixWithoutScriptOpts[i + 1].startsWith('-')
      ) {
        printErrorAndExit('Missing value for --stack');
      }
      flags.stack = prefixWithoutScriptOpts[++i];
    } else if (token === '--force') {
      flags.force = true;
    } else if (token === '--auto') {
      flags.auto = true;
    } else if (token === '--quick') {
      flags.quick = true;
    } else {
      positionals.push(token);
    }
  }

  // 4. Find discriminators in positionals
  const issueRegex = /^(?:#\d+|\d+|https:\/\/github\.com\/[^/]+\/[^/]+\/issues\/\d+(?:\?.*)?)$/i;

  /**
   * Backlog item reference for output.item_ref: `#N` for numeric input, else full issue URL as given.
   * @returns {string | null}
   */
  function parseIssue(token) {
    if (/^#\d+$/.test(token)) {
      return `#${parseInt(token.slice(1), 10)}`;
    }
    if (/^\d+$/.test(token)) {
      return `#${parseInt(token, 10)}`;
    }
    if (/^https:\/\/github\.com\/[^/]+\/[^/]+\/issues\/\d+/i.test(token)) {
      return token;
    }
    return null;
  }

  const discriminators = [];

  for (let i = 0; i < positionals.length; i++) {
    const token = positionals[i];
    // Registry commands must be the first positional — they are subcommand verbs, not title words.
    // Scanning all positionals caused words like "close" inside a title to steal the route.
    if (i === 0 && registryKeys.includes(token)) {
      discriminators.push({ type: 'registry', value: token, index: i });
    } else if (issueRegex.test(token)) {
      discriminators.push({ type: 'item_ref', value: token, index: i, parsed: parseIssue(token) });
    }
  }

  let route = null;
  let reference = null;
  let itemRef = null;
  let userText = null;

  const hasDelimiter = delimiterIndex !== -1;

  if (discriminators.length === 0) {
    if (positionals.length === 0) {
      if (Object.keys(flags).length === 0 && (!hasDelimiter || suffix.length === 0)) {
        route = 'none';
      } else {
        route = 'title_substring';
        userText = hasDelimiter ? suffix.join(' ') : null;
      }
    } else {
      route = 'title_substring';
      userText = hasDelimiter ? suffix.join(' ') : positionals.join(' ');
    }
  } else if (discriminators.length === 1) {
    const disc = discriminators[0];
    if (disc.type === 'registry') {
      route = disc.value;
      reference = commands[disc.value];

      // Remove discriminator from positionals
      const remainingPos = positionals.filter((_, idx) => idx !== disc.index);
      userText = hasDelimiter
        ? suffix.join(' ')
        : remainingPos.length > 0
          ? remainingPos.join(' ')
          : null;
    } else if (disc.type === 'item_ref') {
      route = 'issue';
      itemRef = disc.parsed;

      const remainingPos = positionals.filter((_, idx) => idx !== disc.index);
      userText = hasDelimiter
        ? suffix.join(' ')
        : remainingPos.length > 0
          ? remainingPos.join(' ')
          : null;
    }
  } else {
    // Multiple discriminators
    const registryDiscs = discriminators.filter((d) => d.type === 'registry');
    const itemRefDiscs = discriminators.filter((d) => d.type === 'item_ref');

    if (registryDiscs.length === 1 && itemRefDiscs.length === 1) {
      const regDisc = registryDiscs[0];
      const itemRefDisc = itemRefDiscs[0];

      // One subcommand + one item-ref token (e.g. groom #50, close #42, resume #1).
      route = regDisc.value;
      reference = commands[regDisc.value];
      itemRef = itemRefDisc.parsed;

      if (hasDelimiter) {
        userText = suffix.join(' ');
      } else {
        const remainingPos = positionals.filter(
          (_, idx) => idx !== regDisc.index && idx !== itemRefDisc.index,
        );
        userText = remainingPos.length > 0 ? remainingPos.join(' ') : null;
      }
    } else {
      printErrorAndExit(
        `Multiple conflicting discriminators found: ${discriminators.map((d) => d.value).join(', ')}`,
      );
    }
  }

  if (userText === '') {
    userText = null;
  }

  const output = {
    mode: flags.auto ? 'auto' : 'interactive',
    route,
  };

  if (reference) {
    output.reference = reference;
  }

  if (Object.keys(flags).length > 0) {
    output.flags = flags;
  }

  if (itemRef) {
    output.item_ref = itemRef;
  }

  if (userText !== null) {
    output.user_text = userText;
  }

  console.log(JSON.stringify(output));
} catch (err) {
  printErrorAndExit(`Unhandled error: ${err.message}`);
}
