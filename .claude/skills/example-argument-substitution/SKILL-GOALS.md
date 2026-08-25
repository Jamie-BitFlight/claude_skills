The purpose and explicit goals of the skill `example-argument-substitution`:

1. `Verify empirically, before touching real skills, exactly which $N/$ARGUMENTS forms Claude Code substitutes at load time (bare $N, ${N} braces, single-quoted awk fields, backslash-escaped \$N) versus which are safe`
2. `Practice and validate the pre-declaration pattern (capture $0-$9/$ARGUMENTS into named XML tags at the top of SKILL.md, then reference only the tags) as the correct way to route/dispatch on arguments without corrupting prose or output`
3. `Learn the correct placement rule for shell/code examples containing $N — they belong in references/*.md (not substituted), never inline in SKILL.md body`
4. `Provide a repeatable 0-arg vs 10-arg (CANARY) comparison procedure an agent can run to confirm or refute a substitution hypothesis before generalizing it to other skills`
5. `Establish a "test here first" discipline: any new escape/substitution pattern must be canary-tested in this harness and the verified result recorded in the reference file before being applied elsewhere in the repo`
