import { randomBytes, timingSafeEqual } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const TOKEN_DIR = join(homedir(), '.claude', 'dot-dash');
const TOKEN_FILE = join(TOKEN_DIR, 'token');
let _token = null;
export function loadOrCreateToken() {
  if (_token) return _token;
  if (!existsSync(TOKEN_DIR)) mkdirSync(TOKEN_DIR, { recursive: true });
  if (!existsSync(TOKEN_FILE)) {
    const token = randomBytes(32).toString('hex');
    writeFileSync(TOKEN_FILE, token, { mode: 0o600 });
    _token = token;
  } else {
    _token = readFileSync(TOKEN_FILE, 'utf8').trim();
  }
  return _token;
}
export function validateToken(candidate) {
  const token = loadOrCreateToken();
  try {
    const a = Buffer.from(token);
    const b = Buffer.from(candidate);
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}
