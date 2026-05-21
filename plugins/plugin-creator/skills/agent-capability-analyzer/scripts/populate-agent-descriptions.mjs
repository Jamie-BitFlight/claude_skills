#!/usr/bin/env node

/**
 * populate-agent-descriptions.mjs
 *
 * Reads the `description` field from agent `.md` frontmatter and calls
 * `node update-agent-map.mjs --name <id> --description "<value>"` for each.
 *
 * Usage:
 *   node populate-agent-descriptions.mjs
 */

import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPTS_DIR = dirname(fileURLToPath(import.meta.url));
// Repo root is 3 levels up: scripts/ → agent-capability-analyzer/ → skills/ → plugin-creator/ → plugins/ → repo root
const CWD = resolve(SCRIPTS_DIR, '../../../../..');
const UPDATE_SCRIPT = resolve(SCRIPTS_DIR, 'update-agent-map.mjs');

// ── Frontmatter parser ────────────────────────────────────────────────────────

/**
 * Extracts the YAML frontmatter block from a markdown file's content.
 * Returns null if no valid frontmatter block is present.
 *
 * @param {string} content - Full file content
 * @returns {string | null} - Raw YAML content between the `---` delimiters
 */
function extractFrontmatterBlock(content) {
  const trimmed = content.trimStart();
  if (!trimmed.startsWith('---')) return null;

  const afterFirst = trimmed.slice(3);
  // The first line after `---` must be a newline (block delimiter, not `---x`)
  if (afterFirst.length > 0 && afterFirst[0] !== '\n' && afterFirst[0] !== '\r') {
    return null;
  }

  const closeIndex = afterFirst.indexOf('\n---');
  if (closeIndex === -1) return null;

  return afterFirst.slice(0, closeIndex);
}

/**
 * Parses the `description` field from a raw YAML frontmatter string.
 *
 * Handles:
 *   - Single-line unquoted:  `description: some text`
 *   - Single-line double-quoted: `description: "some text with: colons"`
 *   - Single-line single-quoted: `description: 'some text'`
 *   - Block scalar folded (`>`):  multi-line, whitespace collapsed
 *   - Block scalar literal (`|`): multi-line, newlines preserved then collapsed
 *
 * @param {string} yaml - Raw YAML block content (between `---` delimiters)
 * @returns {string | null} - Extracted description string, or null if not found
 */
function parseDescription(yaml) {
  const lines = yaml.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = line.match(/^description\s*:\s*(.*)/);
    if (match === null) continue;

    const valueRaw = match[1].trimEnd();

    // Block scalar: `description: |` or `description: >`
    if (valueRaw === '|' || valueRaw === '>' || valueRaw.match(/^[|>][0-9+-]*$/)) {
      const blockLines = [];
      for (let j = i + 1; j < lines.length; j++) {
        const bl = lines[j];
        // Block content is indented; stop at unindented lines (next key or end)
        if (bl.length > 0 && bl[0] !== ' ' && bl[0] !== '\t') break;
        blockLines.push(bl.trimStart());
      }
      // Collapse to a single line, trimming trailing empty lines
      const collapsed = blockLines
        .map((l) => l.trimEnd())
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();
      return collapsed.length > 0 ? collapsed : null;
    }

    // Double-quoted string — handle escaped quotes inside
    if (valueRaw.startsWith('"')) {
      // Find the closing unescaped `"`
      let end = -1;
      for (let k = 1; k < valueRaw.length; k++) {
        if (valueRaw[k] === '"' && valueRaw[k - 1] !== '\\') {
          end = k;
          break;
        }
      }
      if (end !== -1) {
        return valueRaw.slice(1, end).replace(/\\"/g, '"').trim();
      }
      // Multi-line double-quoted (rare) — fall through to unquoted handling
      return valueRaw.slice(1).replace(/\\"/g, '"').trim();
    }

    // Single-quoted string
    if (valueRaw.startsWith("'")) {
      const end = valueRaw.indexOf("'", 1);
      if (end !== -1) {
        return valueRaw.slice(1, end).trim();
      }
      return valueRaw.slice(1).trim();
    }

    // Unquoted value
    return valueRaw.trim() || null;
  }

  return null;
}

/**
 * Reads a markdown file and returns the parsed `description` from its frontmatter.
 *
 * @param {string} filePath - Absolute path to the `.md` file
 * @returns {string | null} - Description string, or null if unavailable
 */
function readDescription(filePath) {
  let content;
  try {
    content = readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }

  const block = extractFrontmatterBlock(content);
  if (block === null) return null;

  return parseDescription(block);
}

// ── Version resolution ────────────────────────────────────────────────────────

/**
 * Compares two version strings using semver ordering where possible.
 * Falls back to string comparison for non-semver identifiers (e.g. git hashes).
 * Returns positive if `a > b`, negative if `a < b`, 0 if equal.
 *
 * @param {string} a
 * @param {string} b
 * @returns {number}
 */
function compareVersions(a, b) {
  const semverRe = /^(\d+)\.(\d+)\.(\d+)/;
  const ma = semverRe.exec(a);
  const mb = semverRe.exec(b);

  if (ma && mb) {
    for (let i = 1; i <= 3; i++) {
      const diff = parseInt(ma[i], 10) - parseInt(mb[i], 10);
      if (diff !== 0) return diff;
    }
    return 0;
  }

  // Non-semver: fall back to string comparison (lexicographic)
  return a < b ? -1 : a > b ? 1 : 0;
}

/**
 * Returns the name of the "latest" version directory inside `pluginDir`.
 * For semver directories, picks the highest semver.
 * For git-hash directories, picks the most recently modified (by mtime).
 *
 * @param {string} pluginDir - Absolute path to the plugin's root directory
 * @returns {string | null} - Directory name of the latest version, or null
 */
function resolveLatestVersion(pluginDir) {
  let entries;
  try {
    entries = readdirSync(pluginDir, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name);
  } catch {
    return null;
  }

  if (entries.length === 0) return null;

  const semverRe = /^\d+\.\d+\.\d+/;
  const hasSemver = entries.some((e) => semverRe.test(e));

  if (hasSemver) {
    // Filter to only semver entries, then pick highest
    const semverEntries = entries.filter((e) => semverRe.test(e));
    return semverEntries.reduce((best, cur) => (compareVersions(cur, best) > 0 ? cur : best));
  }

  // Hash-based: pick by most recent mtime
  let bestName = null;
  let bestMtime = -Infinity;
  for (const name of entries) {
    try {
      const st = statSync(join(pluginDir, name));
      if (st.mtimeMs > bestMtime) {
        bestMtime = st.mtimeMs;
        bestName = name;
      }
    } catch {
      // ignore stat errors
    }
  }
  return bestName;
}

/**
 * Resolves the full path to an agent `.md` file inside a plugin's cache.
 *
 * Tries two layouts:
 *   1. `pluginDir/<version>/agents/<agentFile>` (standard layout)
 *   2. `pluginDir/<version>/<agentFile>`         (flat layout, e.g. voltagent)
 *
 * @param {string} pluginDir - Absolute path to the plugin's root cache dir
 * @param {string} agentFile - Filename of the agent (e.g. `code-architect.md`)
 * @returns {string | null} - Resolved path or null if not found
 */
function resolvePluginAgentPath(pluginDir, agentFile) {
  const version = resolveLatestVersion(pluginDir);
  if (version === null) return null;

  const withAgentsSubdir = join(pluginDir, version, 'agents', agentFile);
  try {
    statSync(withAgentsSubdir);
    return withAgentsSubdir;
  } catch {
    // Fall through to flat layout
  }

  const flat = join(pluginDir, version, agentFile);
  try {
    statSync(flat);
    return flat;
  } catch {
    return null;
  }
}

// ── Agent definitions ─────────────────────────────────────────────────────────

const USER_AGENTS_DIR = '/home/ubuntulinuxqa2/.claude/agents';
const PROJECT_AGENTS_DIR = '/home/ubuntulinuxqa2/repos/claude_skills/.claude/agents';
const PLUGIN_CACHE_DIR = '/home/ubuntulinuxqa2/.claude/plugins/cache';

/**
 * Agent entry: { key, filePath }
 *
 * @typedef {{ key: string, filePath: string }} AgentEntry
 */

/**
 * Builds the flat list of agents to process.
 * Project-dir entries shadow user-dir entries with the same key.
 *
 * @returns {AgentEntry[]}
 */
function buildAgentList() {
  /** @type {Map<string, string>} key → filePath */
  const agents = new Map();

  // ── User agents ─────────────────────────────────────────────────────────────
  /** @type {Array<{ key: string, file: string }>} */
  const userAgents = [
    { key: 'c-systems-programmer', file: 'c-systems-programmer.md' },
    { key: 'code-refactorer-agent', file: 'refactor-agent.md' },
    { key: 'code-review', file: 'code-review.md' },
    { key: 'comprehensive-researcher', file: 'comprehensive-researcher.md' },
    { key: 'context-gathering', file: 'context-gathering.md' },
    { key: 'context-refinement', file: 'context-refinement.md' },
    { key: 'doc-drift-auditor', file: 'doc-drift-auditor.md' },
    { key: 'doc-freshness-guardian', file: 'doc-freshness-guardian.md' },
    { key: 'documentation-expert', file: 'documentation-expert.md' },
    { key: 'embedded-dev-specialist', file: 'embedded-dev-specialist.md' },
    { key: 'github-project-manager', file: 'github-project-manager.md' },
    { key: 'gitlab-docs-expert', file: 'gitlab-docs-expert.md' },
    { key: 'gsd-codebase-mapper', file: 'gsd-codebase-mapper.md' },
    { key: 'gsd-debugger', file: 'gsd-debugger.md' },
    { key: 'gsd-executor', file: 'gsd-executor.md' },
    { key: 'gsd-integration-checker', file: 'gsd-integration-checker.md' },
    { key: 'gsd-phase-researcher', file: 'gsd-phase-researcher.md' },
    { key: 'gsd-plan-checker', file: 'gsd-plan-checker.md' },
    { key: 'gsd-planner', file: 'gsd-planner.md' },
    { key: 'gsd-project-researcher', file: 'gsd-project-researcher.md' },
    { key: 'gsd-research-synthesizer', file: 'gsd-research-synthesizer.md' },
    { key: 'gsd-roadmapper', file: 'gsd-roadmapper.md' },
    { key: 'gsd-verifier', file: 'gsd-verifier.md' },
    { key: 'live-api-integration-tester', file: 'live-api-integration-tester.md' },
    { key: 'logging', file: 'logging.md' },
    { key: 'metadata-vault-manager', file: 'metadata-vault-manager.md' },
    { key: 'qa-devops-lead', file: 'qa-devops-lead.md' },
    { key: 'service-documentation', file: 'service-documentation.md' },
    { key: 'spec-analyst', file: 'spec-analyst.md' },
    { key: 'spec-developer', file: 'spec-developer.md' },
    { key: 'spec-orchestrator', file: 'spec-orchestrator.md' },
    { key: 'spec-reviewer', file: 'spec-reviewer.md' },
    { key: 'spec-tester', file: 'spec-tester.md' },
    { key: 'spec-validator', file: 'spec-validator.md' },
    { key: 'subagent-generator', file: 'subagent-generator.md' },
    { key: 'subagent-refactorer', file: 'subagent-refactorer.md' },
    { key: 'system-architect', file: 'system-architect.md' },
    { key: 'technical-researcher', file: 'technical-researcher.md' },
    { key: 'test-architect', file: 'test-architect.md' },
    { key: 'test-quality-auditor', file: 'test-quality-auditor.md' },
    { key: 'trace-protocol-investigator', file: 'trace-protocol-investigator.md' },
  ];

  for (const { key, file } of userAgents) {
    agents.set(key, join(USER_AGENTS_DIR, file));
  }

  // ── Project agents (shadow user agents with same key) ───────────────────────
  /** @type {Array<{ key: string, file: string }>} */
  const projectAgents = [
    {
      key: 'backlog-item-groomer',
      file: 'plugins/development-harness/agents/backlog-item-groomer.md',
    },
    { key: 'c-systems-programmer', file: 'c-systems-programmer.md' },
    { key: 'code-review', file: 'code-review.md' },
    { key: 'context-gathering', file: 'context-gathering.md' },
    { key: 'context-refinement', file: 'context-refinement.md' },
    { key: 'fact-checker', file: 'fact-checker.md' },
    { key: 'javascript-pro', file: 'javascript-pro.md' },
    { key: 'logging', file: 'logging.md' },
    { key: 'plugin-docs-writer', file: 'plugin-docs-writer.md' },
    { key: 'process-siren', file: 'process-siren.md' },
    { key: 'research-context-agent', file: 'research-context-agent.md' },
    { key: 'research-curator', file: 'research-curator.md' },
    { key: 'topic-specialist', file: 'topic-specialist.md' },
    { key: 'typescript-pro', file: 'typescript-pro.md' },
  ];

  for (const { key, file } of projectAgents) {
    // Overwrites any same-keyed user agent entry
    agents.set(key, join(PROJECT_AGENTS_DIR, file));
  }

  // ── Plugin agents ────────────────────────────────────────────────────────────
  /**
   * @type {Array<{
   *   key: string,
   *   pluginDir: string,
   *   agentFile: string
   * }>}
   */
  const pluginAgents = [
    {
      key: 'episodic-memory:search-conversations',
      pluginDir: join(PLUGIN_CACHE_DIR, 'superpowers-marketplace/episodic-memory'),
      agentFile: 'search-conversations.md',
    },
    {
      key: 'feature-dev:code-architect',
      pluginDir: join(PLUGIN_CACHE_DIR, 'claude-plugins-official/feature-dev'),
      agentFile: 'code-architect.md',
    },
    {
      key: 'feature-dev:code-explorer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'claude-plugins-official/feature-dev'),
      agentFile: 'code-explorer.md',
    },
    {
      key: 'feature-dev:code-reviewer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'claude-plugins-official/feature-dev'),
      agentFile: 'code-reviewer.md',
    },
    {
      key: 'holistic-linting:linting-root-cause-resolver',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/holistic-linting'),
      agentFile: 'linting-root-cause-resolver.md',
    },
    {
      key: 'holistic-linting:post-linting-architecture-reviewer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/holistic-linting'),
      agentFile: 'post-linting-architecture-reviewer.md',
    },
    {
      key: 'plugin-creator:agent-creator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'agent-creator.md',
    },
    {
      key: 'plugin-creator:ai-doc-optimizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'ai-doc-optimizer.md',
    },
    {
      key: 'plugin-creator:skill-auditor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'skill-auditor.md',
    },
    {
      key: 'plugin-creator:skill-content-updater',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'skill-content-updater.md',
    },
    {
      key: 'plugin-creator:hook-creator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'hook-creator.md',
    },
    {
      key: 'plugin-creator:plugin-assessor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'plugin-assessor.md',
    },
    {
      key: 'plugin-creator:refactor-executor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'refactor-executor.md',
    },
    {
      key: 'plugin-creator:refactor-planner',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'refactor-planner.md',
    },
    {
      key: 'plugin-creator:refactor-validator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'refactor-validator.md',
    },
    {
      key: 'plugin-creator:subagent-refactorer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/plugin-creator'),
      agentFile: 'subagent-refactorer.md',
    },
    {
      key: 'process-siren:process-siren',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/process-siren'),
      agentFile: 'process-siren.md',
    },
    {
      key: 'python3-development:code-reviewer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'python-code-reviewer.md',
    },
    {
      key: 'python3-development:codebase-analyzer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'codebase-analyzer.md',
    },
    {
      key: 'python3-development:context-gathering',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'context-gathering.md',
    },
    {
      key: 'python3-development:context-refinement',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'context-refinement.md',
    },
    {
      key: 'python3-development:doc-drift-auditor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'doc-drift-auditor.md',
    },
    {
      key: 'python3-development:ecosystem-researcher',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'ecosystem-researcher.md',
    },
    {
      key: 'python3-development:feature-researcher',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'feature-researcher.md',
    },
    {
      key: 'python3-development:feature-verifier',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'feature-verifier.md',
    },
    {
      key: 'python3-development:integration-checker',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'integration-checker.md',
    },
    {
      key: 'python3-development:plan-validator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'plan-validator.md',
    },
    {
      key: 'python3-development:python-cli-architect',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'python-cli-architect.md',
    },
    {
      key: 'python3-development:python-cli-design-spec',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'python-cli-design-spec.md',
    },
    {
      key: 'python3-development:python-code-reviewer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'python-code-reviewer.md',
    },
    {
      key: 'python3-development:python-pytest-architect',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/python3-development'),
      agentFile: 'python-pytest-architect.md',
    },
    {
      key: 'rwr:rewrite-room-auditor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/rwr'),
      agentFile: 'rewrite-room-auditor.md',
    },
    {
      key: 'rwr:rewrite-room-author',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/rwr'),
      agentFile: 'rewrite-room-author.md',
    },
    {
      key: 'rwr:rewrite-room-doc-converter',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/rwr'),
      agentFile: 'rewrite-room-doc-converter.md',
    },
    {
      key: 'rwr:rewrite-room-optimizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/rwr'),
      agentFile: 'rewrite-room-optimizer.md',
    },
    {
      key: 'summarizer:file-summarizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/summarizer'),
      agentFile: 'file-summarizer.md',
    },
    {
      key: 'summarizer:image-summarizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/summarizer'),
      agentFile: 'image-summarizer.md',
    },
    {
      key: 'summarizer:url-summarizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'jamie-bitflight-skills/summarizer'),
      agentFile: 'url-summarizer.md',
    },
    {
      key: 'superpowers:code-reviewer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'claude-plugins-official/superpowers'),
      agentFile: 'code-reviewer.md',
    },
    {
      key: 'voltagent-dev-exp:build-engineer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'build-engineer.md',
    },
    {
      key: 'voltagent-dev-exp:cli-developer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'cli-developer.md',
    },
    {
      key: 'voltagent-dev-exp:dependency-manager',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'dependency-manager.md',
    },
    {
      key: 'voltagent-dev-exp:documentation-engineer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'documentation-engineer.md',
    },
    {
      key: 'voltagent-dev-exp:dx-optimizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'dx-optimizer.md',
    },
    {
      key: 'voltagent-dev-exp:git-workflow-manager',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'git-workflow-manager.md',
    },
    {
      key: 'voltagent-dev-exp:legacy-modernizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'legacy-modernizer.md',
    },
    {
      key: 'voltagent-dev-exp:mcp-developer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'mcp-developer.md',
    },
    {
      key: 'voltagent-dev-exp:powershell-module-architect',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'powershell-module-architect.md',
    },
    {
      key: 'voltagent-dev-exp:powershell-ui-architect',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'powershell-ui-architect.md',
    },
    {
      key: 'voltagent-dev-exp:refactoring-specialist',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'refactoring-specialist.md',
    },
    {
      key: 'voltagent-dev-exp:slack-expert',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'slack-expert.md',
    },
    {
      key: 'voltagent-dev-exp:tooling-engineer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-dev-exp'),
      agentFile: 'tooling-engineer.md',
    },
    {
      key: 'voltagent-meta:agent-organizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'agent-organizer.md',
    },
    {
      key: 'voltagent-meta:context-manager',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'context-manager.md',
    },
    {
      key: 'voltagent-meta:error-coordinator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'error-coordinator.md',
    },
    {
      key: 'voltagent-meta:it-ops-orchestrator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'it-ops-orchestrator.md',
    },
    {
      key: 'voltagent-meta:knowledge-synthesizer',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'knowledge-synthesizer.md',
    },
    {
      key: 'voltagent-meta:multi-agent-coordinator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'multi-agent-coordinator.md',
    },
    {
      key: 'voltagent-meta:performance-monitor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'performance-monitor.md',
    },
    {
      key: 'voltagent-meta:task-distributor',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'task-distributor.md',
    },
    {
      key: 'voltagent-meta:workflow-orchestrator',
      pluginDir: join(PLUGIN_CACHE_DIR, 'voltagent-subagents/voltagent-meta'),
      agentFile: 'workflow-orchestrator.md',
    },
  ];

  for (const { key, pluginDir, agentFile } of pluginAgents) {
    const resolved = resolvePluginAgentPath(pluginDir, agentFile);
    if (resolved !== null) {
      agents.set(key, resolved);
    } else {
      process.stderr.write(
        `WARN: Could not resolve path for plugin agent "${key}" in ${pluginDir}\n`,
      );
    }
  }

  return Array.from(agents.entries()).map(([key, filePath]) => ({ key, filePath }));
}

// ── Main ──────────────────────────────────────────────────────────────────────

/**
 * Calls `node update-agent-map.mjs --name <key> --description <desc>`.
 *
 * @param {string} key - Agent identifier
 * @param {string} description - Description string to store
 */
function updateAgentMap(key, description) {
  execFileSync('node', [UPDATE_SCRIPT, '--name', key, '--description', description], {
    cwd: CWD,
    stdio: 'pipe',
  });
}

const agents = buildAgentList();

let populated = 0;
let skipped = 0;

for (const { key, filePath } of agents) {
  const description = readDescription(filePath);

  if (description === null || description === '') {
    process.stderr.write(`WARN: Skipping "${key}" — no description found in ${filePath}\n`);
    skipped++;
    continue;
  }

  try {
    updateAgentMap(key, description);
    process.stdout.write(`OK  ${key}\n`);
    populated++;
  } catch (err) {
    process.stderr.write(`WARN: Skipping "${key}" — update-agent-map failed: ${err.message}\n`);
    skipped++;
  }
}

process.stdout.write(`\nPopulated ${populated} agents, skipped ${skipped}\n`);
