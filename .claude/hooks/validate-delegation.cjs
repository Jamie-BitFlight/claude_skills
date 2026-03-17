#!/usr/bin/env node
'use strict';

/**
 * PreToolUse hook — validates Agent/Task tool prompts follow the delegation template.
 *
 * Reads JSON from stdin (Claude Code hook event), checks the prompt field against
 * the required delegation template structure, and exits code 2 with stderr feedback
 * if validation fails. Exits code 0 silently on pass or when skipped.
 *
 * Required template sections (from .claude/skills/delegate/SKILL.md):
 *   1. Starts with "Your ROLE_TYPE is sub-agent."
 *   2. Contains DEFINITION OF SUCCESS section
 *   3. Does NOT prescribe HOW (no bare code blocks with implementation)
 *
 * Resume calls are skipped — no new prompt is validated.
 *
 * Skill pass-through prompts are skipped — prompts that primarily invoke
 * a Skill() call (routing patterns from /implement-feature, /start-task, etc.)
 * get their context from the skill, not the delegation prompt.
 */

const fs = require('node:fs');

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
 * Validates a prompt against the 5 delegation template rules.
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

  // Rule 3: must NOT prescribe HOW — detect fenced code blocks that contain
  // implementation-style content (line assignments, function/method calls on
  // specific lines, etc.). A single inline code mention is acceptable; a fenced
  // block with actual implementation lines is the anti-pattern.
  //
  // Heuristic: find ``` fenced blocks; if any block body contains 3+ lines
  // that look like implementation code (assignments, function calls, imports),
  // flag it as prescribing HOW.
  const fencedBlockPattern = /```[^\n]*\n([\s\S]*?)```/g;
  const implementationLinePattern =
    /^\s*(const |let |var |import |export |function |class |return |if \(|for \(|\w+\s*=\s*|\w+\.\w+\()/m;

  for (
    let fenceMatch = fencedBlockPattern.exec(prompt);
    fenceMatch !== null;
    fenceMatch = fencedBlockPattern.exec(prompt)
  ) {
    const blockBody = fenceMatch[1] ?? '';
    const lines = blockBody.split('\n').filter((l) => l.trim().length > 0);
    const implLines = lines.filter((l) => implementationLinePattern.test(l));
    // If more than half the non-empty lines look like implementation code,
    // treat the block as prescribing HOW.
    if (lines.length >= 3 && implLines.length >= Math.ceil(lines.length / 2)) {
      violations.push(
        'Rule 3: Prompt contains implementation code block (prescribes HOW). ' +
          'Use OBSERVATIONS/CONTEXT constraints instead of code snippets.',
      );
      break; // one violation is enough
    }
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
  if (!raw || !raw.trim()) {
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
  // not the delegation prompt. Detected by: prompt body (after trimming
  // whitespace lines) is dominated by Skill() invocations or is very short
  // (under 5 non-empty lines) and contains a Skill() call.
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
      'Required template (.claude/skills/delegate/SKILL.md):',
      '',
      '  Your ROLE_TYPE is sub-agent.',
      '',
      '  [Task Identification - one sentence]',
      '',
      '  OBSERVATIONS:',
      '  - [Factual observations already in your context]',
      '  - [Verbatim error messages if applicable]',
      '  - [Environment or system state if relevant]',
      '',
      '  DEFINITION OF SUCCESS:',
      '  - [Specific measurable outcome]',
      '  - [Acceptance criteria]',
      '',
      '  CONTEXT:',
      '  - Location: [Where to look]',
      '  - Scope: [Boundaries]',
      '  - Constraints: [Hard requirements vs Preferences]',
      '',
      '  ECOSYSTEM CONTEXT:',
      '  - [Session-specific facts the agent cannot find in CLAUDE.md or tool descriptions]',
      '',
      '  YOUR TASK:',
      '  1. ...',
      '',
      'Fix the prompt and retry.',
      '--- End Validation ---',
    ].join('\n')}\n`,
  );

  process.exit(2);
}

main();
