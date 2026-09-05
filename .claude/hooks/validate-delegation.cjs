#!/usr/bin/env node
'use strict';

/**
 * PreToolUse hook — validates Agent/Task tool prompts follow the delegation template.
 *
 * Reads JSON from stdin (Claude Code hook event), checks the prompt field against
 * the required delegation template structure, and exits code 2 with stderr feedback
 * if validation fails. Exits code 0 silently on pass or when skipped.
 *
 * Required template sections (from plugins/agent-orchestration/skills/delegate/SKILL.md):
 *   1. Starts with "Your ROLE_TYPE is sub-agent."
 *   2. Contains DEFINITION OF SUCCESS section
 *   3. Contains a PHASE: line whose value is one of the nine phase names
 *   4. Contains OBSERVATIONS: and CONTEXT: (specialist mode) or FILES: (generic mode)
 *   5. Contains DELIVERY: section
 *
 * Resume calls are skipped — no new prompt is validated.
 *
 * Skill pass-through prompts are skipped — prompts that primarily invoke
 * a Skill() call (routing patterns from /implement-feature, /start-task, etc.)
 * get their context from the skill, not the delegation prompt.
 */

const fs = require('node:fs');

const PHASES = [
  'read',
  'gather',
  'process',
  'verify',
  'write',
  'validate',
  'test',
  'report',
  'review',
];

/**
 * Returns true if the prompt is a skill pass-through — a routing prompt that
 * primarily invokes Skill() and relies on the skill for context.
 *
 * Patterns detected:
 *   - Prompt contains Skill(skill=...) invocation
 *   - Prompt body is short (fewer than 8 non-empty lines)
 *
 * This covers /implement-feature → start-task routing and similar patterns.
 * @param {string} prompt
 * @returns {boolean}
 */
function isSkillPassthrough(prompt) {
  const hasSkillCall = /Skill\s*\(\s*skill\s*[=:]/i.test(prompt);
  if (!hasSkillCall) return false;

  const nonEmptyLines = prompt.split('\n').filter((l) => l.trim().length > 0);
  // Short prompts with a Skill() call are pass-through routing
  return nonEmptyLines.length < 8;
}

/**
 * Checks whether the prompt text contains a section header matching the pattern.
 * Accepts "SECTION NAME" and "SECTION NAME (anything)" at line start.
 * @param {string} prompt
 * @param {string} sectionName - uppercase section name, e.g. "OBSERVATIONS"
 * @returns {boolean}
 */
function hasSection(prompt, sectionName) {
  // Match line starting with the section name, optionally followed by space/colon/paren content
  const pattern = new RegExp(`^${sectionName}(\\s|:|\\(|$)`, 'm');
  return pattern.test(prompt);
}

/**
 * Validates a prompt against the delegation template rules.
 * @param {string} prompt
 * @returns {{ valid: boolean, violations: string[] }}
 */
function validatePrompt(prompt) {
  const violations = [];

  // Rule 1: must start with the role declaration
  if (!prompt.trimStart().startsWith('Your ROLE_TYPE is sub-agent.')) {
    violations.push('Rule 1: Prompt must start with "Your ROLE_TYPE is sub-agent."');
  }

  // Rule 2: must contain DEFINITION OF SUCCESS section
  if (!hasSection(prompt, 'DEFINITION OF SUCCESS')) {
    violations.push('Rule 2: Missing DEFINITION OF SUCCESS section');
  }

  // Rule 3: must contain a PHASE: line with one of the nine phase names
  const phaseMatch = /^PHASE:[ \t]*(\S+)[ \t]*$/m.exec(prompt);
  if (!phaseMatch) {
    violations.push(`Rule 3: Missing PHASE: line (one of ${PHASES.join('|')})`);
  } else if (!PHASES.includes(phaseMatch[1])) {
    violations.push(`Rule 3: PHASE value "${phaseMatch[1]}" is not one of ${PHASES.join('|')}`);
  }

  // Rule 4: specialist mode (OBSERVATIONS + CONTEXT) or generic mode (FILES)
  const specialist = hasSection(prompt, 'OBSERVATIONS') && hasSection(prompt, 'CONTEXT');
  const generic = hasSection(prompt, 'FILES');
  if (!specialist && !generic) {
    violations.push(
      'Rule 4: Missing OBSERVATIONS + CONTEXT sections (specialist mode) or FILES section (generic mode)',
    );
  }

  // Rule 5: must contain DELIVERY section
  if (!hasSection(prompt, 'DELIVERY')) {
    violations.push('Rule 5: Missing DELIVERY section');
  }

  return { valid: violations.length === 0, violations };
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
  if (!raw?.trim()) {
    // No input — nothing to validate
    process.exit(0);
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    // Malformed JSON — cannot validate, let the tool proceed
    process.exit(0);
  }

  const toolInput = event.tool_input ?? {};
  const prompt = typeof toolInput.prompt === 'string' ? toolInput.prompt : '';
  const subagentType = toolInput.subagent_type ?? '';

  // Skip resume calls — no new prompt to validate
  if (toolInput.resume) {
    process.exit(0);
  }

  // Skip if there is no prompt to validate
  if (!prompt.trim()) {
    process.exit(0);
  }

  // Skip skill pass-through prompts — routing patterns where the prompt
  // primarily invokes a Skill() call. These get context from the skill itself,
  // not the delegation prompt.
  if (isSkillPassthrough(prompt)) {
    process.exit(0);
  }

  const { valid, violations } = validatePrompt(prompt);

  if (valid) {
    process.exit(0);
  }

  // Exit code 2 blocks the tool call and shows stderr as feedback to Claude
  process.stderr.write(
    `${[
      '--- Delegation Template Validation Failed ---',
      '',
      `Agent type: ${subagentType || '(not specified)'}`,
      '',
      'Violations:',
      ...violations.map((v) => `  - ${v}`),
      '',
      'Required template (plugins/agent-orchestration/skills/delegate/SKILL.md, specialist mode):',
      '',
      '  Your ROLE_TYPE is sub-agent. Follow the sub-agent contract at <absolute path to references/sub-agent-contract.md>.',
      '',
      '  PHASE: <one of the phase names>',
      '  TASK: <one sentence>',
      '',
      '  OBSERVATIONS:',
      '  - <facts already in your context: user statements, prior STATUS reports, verbatim errors, file:line if known>',
      '',
      '  DEFINITION OF SUCCESS:',
      '  - <measurable outcome>',
      '  - <acceptance criteria>',
      '  - <how it is verified — a command and its expected result, or the reviewer that will check>',
      '',
      '  DELIVERY:',
      '  - Return STATUS as the first line. Write anything longer than a line to .tmp/scratch/reports/<YYYYMMDD>-<slug>.md and return the path.',
      '',
      '  CONTEXT:',
      '  - Location: <where to look>',
      '  - Scope: <boundaries>',
      '  - Constraints: <user-mandated requirements; existing patterns to follow>',
      '  - Commands: <the project\'s quality gates for validate/test, or "discover the ones this project defines">',
      '',
      '  ECOSYSTEM CONTEXT:  (omit the section if empty)',
      '  - <session facts the agent cannot read anywhere: authenticated CLIs, a PR under review, another agent live on the same files>',
      '',
      '  YOUR TASK:',
      "  <the phase's row from the table below, verbatim>",
      '',
      'Generic mode (general-purpose / Explore) replaces OBSERVATIONS + CONTEXT with a FILES: section.',
      '',
      'Fix the prompt and retry.',
      '--- End Validation ---',
    ].join('\n')}\n`,
  );

  process.exit(2);
}

main();
