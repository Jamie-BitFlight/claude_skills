# Duplicate Detection

Shared by Default Mode and Batch Mode. Runs before spawning `@research-curator` for a URL.

Check whether `./research/` already contains an entry for the URL's resource. If found:

1. Read the entry's Freshness Tracking section.
2. Compute days since Last Verified (integer: today minus Last Verified date).
3. Emit: `Entry is N days old (last verified: YYYY-MM-DD, vX.Y.Z). Proceeding with refresh.`
4. Pass `--rerun ./research/{category}/{name}.md` to the agent instead of a fresh-URL prompt.

If the Freshness Tracking section is absent or Last Verified is unreadable, emit:
`Entry exists but freshness data unavailable. Proceeding with refresh.`
and pass `--rerun ./research/{category}/{name}.md` to the agent instead of a fresh-URL prompt.
