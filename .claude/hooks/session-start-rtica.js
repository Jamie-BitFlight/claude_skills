#!/usr/bin/env node
/**
 * SessionStart hook that injects RT-ICA checkpoint reminder into context.
 * Cross-platform (works on Windows, macOS, Linux).
 */

const output = {
  hookSpecificOutput: {
    hookEventName: 'SessionStart',
    additionalContext: `<rt-ica-checkpoint>
RT-ICA CHECKPOINT REQUIRED: Before creating plans, delegating to agents, or defining acceptance criteria for any spec, PRD, ticket, RFC, or multi-step engineering task, invoke the rt-ica skill to perform Reverse Thinking - Information Completeness Assessment. Block planning until prerequisites are verified.
</rt-ica-checkpoint>`,
  },
};

console.log(JSON.stringify(output));
