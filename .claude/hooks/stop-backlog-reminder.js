#!/usr/bin/env node
/**
 * Stop hook that reminds about backlog maintenance.
 * Prompts to add discovered ideas and update completed items.
 */

const output = {
  hookSpecificOutput: {
    hookEventName: 'Stop',
    additionalContext: `<backlog-reminder>
Before ending session, consider:
1. Add any new ideas or deferred work to .claude/BACKLOG.md
2. Move completed items to the Completed section
3. Update summary counts if items were added/completed
</backlog-reminder>`,
  },
};

console.log(JSON.stringify(output));
