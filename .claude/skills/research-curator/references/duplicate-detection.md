# Duplicate Detection

Shared by Default Mode and Batch Mode. Runs before spawning `@research-curator` for a URL.

Check whether `./research/` already contains an entry for the URL's resource. If found:

1. Read Last Verified and Version at Verification: check frontmatter first
   (`freshness_tracking.last_verified` / `freshness_tracking.version_at_verification`, or bare
   `last_verified` / `version_at_verification` keys); if neither is present in frontmatter, fall
   back to the body `## Freshness Tracking` table (legacy text-header entries).
2. Compute days since Last Verified (integer: today minus Last Verified date).
3. Emit: `Entry is N days old (last verified: YYYY-MM-DD, vX.Y.Z). Proceeding with refresh.`
4. Pass `--rerun ./research/{category}/{name}.md` to the agent instead of a fresh-URL prompt.

If Last Verified is present in neither frontmatter nor a body section, or is unreadable, emit:
`Entry exists but freshness data unavailable. Proceeding with refresh.`
and pass `--rerun ./research/{category}/{name}.md` to the agent instead of a fresh-URL prompt.
