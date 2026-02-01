#!/usr/bin/env node
/**
 * SessionStart hook that shows backlog summary.
 * Reads .claude/BACKLOG.md and extracts item counts by priority.
 */

const fs = require("fs");
const path = require("path");

const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const backlogPath = path.join(projectDir, ".claude", "BACKLOG.md");

let summary = "Backlog not found";

try {
  if (fs.existsSync(backlogPath)) {
    const content = fs.readFileSync(backlogPath, "utf8");

    // Extract counts from summary table
    const p0Match = content.match(/\| P0\s*\|\s*(\d+)\s*\|/);
    const p1Match = content.match(/\| P1\s*\|\s*(\d+)\s*\|/);
    const p2Match = content.match(/\| P2\s*\|\s*(\d+)\s*\|/);
    const ideasMatch = content.match(/\| Ideas\s*\|\s*(\d+)\s*\|/);

    const p0 = p0Match ? parseInt(p0Match[1]) : 0;
    const p1 = p1Match ? parseInt(p1Match[1]) : 0;
    const p2 = p2Match ? parseInt(p2Match[1]) : 0;
    const ideas = ideasMatch ? parseInt(ideasMatch[1]) : 0;
    const total = p0 + p1 + p2 + ideas;

    if (total > 0) {
      summary = `Backlog: ${total} items (P0:${p0} P1:${p1} P2:${p2} Ideas:${ideas}). Review with: cat .claude/BACKLOG.md`;
    } else {
      summary = "Backlog empty";
    }
  }
} catch (e) {
  summary = "Backlog read error: " + e.message;
}

const output = {
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: `<backlog-summary>${summary}</backlog-summary>`,
  },
};

console.log(JSON.stringify(output));
