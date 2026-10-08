---
name: reuse-before-build
description: Review a proposed or implemented new script, tool, library, module, or bespoke capability for missed existing solutions. Use during planning, implementation, or code review to decide whether to adopt, adapt, or justify building.
user-invocable: true
---

# Reuse Before Build

Read [the shared decision procedure](../../docs/reuse-before-build.md). Apply it to the
specific capability, not every changed function. In review mode, remain read-only: do
not replace the implementation or modify files.

1. **Identify the capability.** From the diff and its consumers, establish the
   intended behavior, decisive requirement, and why a new mechanism was introduced.
   Skip unchanged mechanisms and incidental glue with no independent capability.
2. **Recover the design decision.** Look for an applicable prior reuse decision and
   verify its requirements, environment, and assumptions still hold. If absent or
   stale, repeat only the missing discovery: repository/platform features, installed
   dependencies, available tools/skills, then external candidates as justified.
3. **Challenge fit.** Read authoritative candidate documentation. Test the hardest
   discriminating requirement safely when practical; otherwise mark it unverified.
   Compare integration, licensing, maintenance, security, and replacement cost only
   where they could change the choice. Stop when more research is unlikely to alter it.
4. **Report a disposition.** ADOPT an existing fit, ADAPT via minimal integration,
   BUILD JUSTIFIED with demonstrated gaps, or UNRESOLVED with the cheapest decisive
   check. A plausible alternative alone is not proof the implementation is wrong.

For code review, report the affected file/lines, candidate evidence, why the
current choice is or is not justified, and the minimum corrective action. Classify
a finding as blocking only when a consequential requirement or review acceptance
criterion is violated; otherwise offer a nonblocking improvement. Continue other
review work if the decision remains unresolved. Do not invent new task fields or
require a standalone research artifact.
