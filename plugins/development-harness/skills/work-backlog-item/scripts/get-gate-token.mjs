#!/usr/bin/env node
import { randomBytes } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';

const sessionId = process.env.CLAUDE_CODE_SESSION_ID;
if (!sessionId) {
  process.stdout.write('[gate-token-error: CLAUDE_CODE_SESSION_ID not set in environment]');
  process.exit(0);
}

const dhRoot = process.env.DH_STATE_HOME
  ? resolve(process.env.DH_STATE_HOME)
  : join(homedir(), '.dh');
const tokenDir = join(dhRoot, 'sessions', sessionId);
const tokenPath = join(tokenDir, '.gate-token');

const token = `${sessionId}:${randomBytes(32).toString('hex')}`;
mkdirSync(tokenDir, { recursive: true });
writeFileSync(tokenPath, token, 'utf8');
process.stdout.write(token);
