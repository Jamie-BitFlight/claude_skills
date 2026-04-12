#!/usr/bin/env node
'use strict';

/**
 * PreToolUse hook — blocks Agent invocations that route analysis/reasoning
 * tasks to the Explore subagent.
 *
 * Reason: .claude/CLAUDE.md <sub_agent_selection> documents that the Explore
 * agent is haiku-based with ~50% hallucination rate on ambiguous/reasoning
 * queries (validated 2026-02-02, 2/4 accuracy). It is permitted only for
 * exact file pattern or keyword search — never for reasoning, interpretation,
 * or analysis. .claude/rules/model-selection.md routes "Analyze architecture,
 * plan approaches, reason about trade-offs, design systems" to opus.
 *
 * This hook reads the JSON event from stdin, inspects tool_input for
 * subagent_type=Explore, and if the description or prompt contains analysis
 * keywords, exits code 2 with stderr feedback so Claude reroutes to a
 * reasoning-class agent.
 *
 * Skipped when subagent_type is anything other than Explore.
 */

const fs = require('node:fs');

/**
 * Keywords that signal a reasoning/analysis task. Matched case-insensitively
 * against both `description` and `prompt` fields of the Agent tool input.
 *
 * Each entry is matched as a whole word or whole phrase (word-boundary
 * anchored). 'analyze' matches 'analyze', 'Analyze', and 'ANALYZE' but
 * not 'analyzer' or 'canalize'.
 */
const ANALYSIS_KEYWORDS = [
  'analyze',
  'analysis',
  'analyse',
  'assess',
  'assessment',
  'audit',
  'review',
  'evaluate',
  'evaluation',
  'compare',
  'comparison',
  'critique',
  'design',
  'architect',
  'architecture',
  'recommend',
  'recommendation',
  'propose',
  'proposal',
  'improve',
  'improvement',
  'refactor',
  'trade-off',
  'tradeoff',
  'plan',
  'planning',
  'diagnose',
  'diagnosis',
  'root cause',
  'why does',
  'why is',
  'reason about',
  'reasoning',
  'judgement',
  'judgment',
  'opinion',
  'best approach',
  'best way',
  'how should',
  'should i',
  'what should',
];

/**
 * Builds a single regex that matches any analysis keyword as a whole word
 * (or whole phrase). Compiled once at module load.
 */
const KEYWORD_PATTERN = new RegExp(
  `\\b(${ANALYSIS_KEYWORDS.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`,
  'i',
);

/**
 * Strips quoted substrings so that keywords appearing as search targets
 * (e.g. `grep for the word 'review'` or "find files mentioning \"audit\"")
 * do not trigger the analysis-keyword match. Covers single-quoted,
 * double-quoted, and backticked spans. Escaped quotes inside strings are
 * not handled — the hook only needs a coarse filter, not a full parser.
 * @param {string} text
 * @returns {string}
 */
function stripQuotedSpans(text) {
  return text
    .replace(/`[^`]*`/g, ' ')
    .replace(/'[^']*'/g, ' ')
    .replace(/"[^"]*"/g, ' ');
}

/**
 * Returns the first analysis keyword found in the given text, or null.
 * Quoted/backticked substrings are stripped first so that keywords used
 * as search targets do not block legitimate pattern-search tasks.
 * @param {string} text
 * @returns {string|null}
 */
function findAnalysisKeyword(text) {
  if (!text) return null;
  const stripped = stripQuotedSpans(text);
  const match = KEYWORD_PATTERN.exec(stripped);
  return match ? match[1] : null;
}

/** Reads all of stdin synchronously and returns the string. */
function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function main() {
  const raw = readStdin();
  if (!raw || !raw.trim()) {
    process.exit(0);
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    // Malformed JSON — let the tool proceed; another hook may handle it
    process.exit(0);
  }

  // Skip enforcement for subagent sessions — only the orchestrator is gated.
  // When running inside a subagent, the hook input includes agent_id and
  // agent_type fields that are absent in the orchestrator session. Matches
  // the pattern used by prevent-bash-tool-misuse.cjs, pre-tool-diagnostic-
  // command-gate.cjs, and pre-tool-orchestrator-read-warning.cjs (verified
  // 2026-03-23).
  if (event.agent_id) {
    process.exit(0);
  }

  // Only act on Agent/Task tool calls
  const toolName = event.tool_name ?? '';
  if (toolName !== 'Agent' && toolName !== 'Task') {
    process.exit(0);
  }

  const toolInput = event.tool_input ?? {};
  const subagentType = String(toolInput.subagent_type ?? '');

  // Only block when targeting the Explore agent
  if (subagentType !== 'Explore') {
    process.exit(0);
  }

  const description = String(toolInput.description ?? '');
  const prompt = String(toolInput.prompt ?? '');

  // Check description first (shorter, more signal-dense), then prompt
  const descKeyword = findAnalysisKeyword(description);
  const promptKeyword = descKeyword ? null : findAnalysisKeyword(prompt);
  const hit = descKeyword ?? promptKeyword;

  if (!hit) {
    // Pure search/lookup task — Explore is permitted
    process.exit(0);
  }

  const source = descKeyword ? 'description' : 'prompt';

  process.stderr.write(
    `${[
      '--- Explore Agent Blocked for Analysis Task ---',
      '',
      `Subagent type: Explore`,
      `Detected analysis keyword: "${hit}" (in ${source})`,
      '',
      'The Explore agent is haiku-based and documented in CLAUDE.md as having',
      '~50% hallucination rate on ambiguous/reasoning queries. It is permitted',
      'only for exact file pattern or keyword search — never for reasoning,',
      'interpretation, or analysis.',
      '',
      'Reroute to a reasoning-class agent. Per .claude/rules/model-selection.md:',
      '',
      '  - Architecture analysis, trade-off reasoning, system design → opus',
      '    (general-purpose with model: "opus", or specialist opus agents)',
      '  - Code review with structured process → sonnet',
      '    (code-reviewer, python-cli-architect, etc.)',
      '  - Cross-checking lists, running commands, comparing data → haiku',
      '    (codebase-analyzer, context-gathering, doc-drift-auditor)',
      '',
      'For the current task, suggested subagent_type values:',
      '  - "general-purpose" with model: "opus"',
      '  - "Plan" (software architect agent for design/trade-off work)',
      '  - "dh:codebase-analyzer" (haiku — but follows a structured process)',
      '  - "context-gathering" (haiku — for repo convention discovery)',
      '',
      'If this task is genuinely a pure file-pattern/keyword search and the',
      'keyword match is a false positive, rephrase the description and prompt',
      'to remove analysis verbs and retry.',
      '',
      'Rule source: .claude/CLAUDE.md <sub_agent_selection>,',
      '             .claude/rules/model-selection.md',
      '--- End ---',
    ].join('\n')}\n`,
  );

  process.exit(2);
}

main();
