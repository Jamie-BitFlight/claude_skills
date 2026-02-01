#!/usr/bin/env node
/**
 * SessionStart hook that shows backlog summary.
 * Reads .claude/BACKLOG.md frontmatter and extracts item counts by priority.
 */

const fs = require('node:fs');
const path = require('node:path');

const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const backlogPath = path.join(projectDir, '.claude', 'BACKLOG.md');

let summary = 'Backlog not found';

/**
 * Parse YAML frontmatter from markdown content.
 * @param {string} content - File content
 * @returns {Object} Parsed frontmatter key-value pairs
 */
function parseFrontmatter(content) {
  const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatterMatch) return {};

  const frontmatter = {};
  const lines = frontmatterMatch[1].split('\n');
  for (const line of lines) {
    const match = line.match(/^([a-z0-9-]+):\s*(.+)$/i);
    if (match) {
      const key = match[1].trim();
      let value = match[2].trim();
      // Parse numbers
      if (/^\d+$/.test(value)) {
        value = parseInt(value, 10);
      }
      frontmatter[key] = value;
    }
  }
  return frontmatter;
}

try {
  if (fs.existsSync(backlogPath)) {
    const content = fs.readFileSync(backlogPath, 'utf8');
    const fm = parseFrontmatter(content);

    const p0 = fm['p0-count'] || 0;
    const p1 = fm['p1-count'] || 0;
    const p2 = fm['p2-count'] || 0;
    const ideas = fm['ideas-count'] || 0;
    const total = p0 + p1 + p2 + ideas;

    if (total > 0) {
      summary = `Backlog: ${total} items (P0:${p0} P1:${p1} P2:${p2} Ideas:${ideas}). Review with: cat .claude/BACKLOG.md`;
    } else {
      summary = 'Backlog empty';
    }
  }
} catch (e) {
  summary = `Backlog read error: ${e.message}`;
}

const output = {
  hookSpecificOutput: {
    hookEventName: 'SessionStart',
    additionalContext: `<backlog-summary>${summary}</backlog-summary>`,
  },
};

console.log(JSON.stringify(output));
