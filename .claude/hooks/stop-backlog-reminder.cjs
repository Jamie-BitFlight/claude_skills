#!/usr/bin/env node
/**
 * Stop hook — reminds to capture new ideas and close completed items.
 */

const output = {
  additionalContext: `<backlog-reminder>
New ideas or deferred work discovered this session? → Skill(skill: "dh:work-backlog-item", args: "create --auto {title}") to add and track.
Completed items? → Skill(skill: "dh:work-backlog-item", args: "close {title}") to verify and close.
</backlog-reminder>`,
};

console.log(JSON.stringify(output));
