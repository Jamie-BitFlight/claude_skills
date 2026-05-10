# Improvement Proposals: gh-skill

**Research entry**: ./research/developer-tools/gh-skill.md
**Generated**: 2026-05-10
**Patterns assessed**: 7
**Backlog items created**: 2 (issues: #2245, #2247)
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Detect git remote / proxy host in setup_gh.py and write a default --repo config

**Source pattern**: "Proxy detection: Enhance setup_gh.py to detect and document proxy configuration so agents don't need to manually pass `-R` flags" — Integration Opportunities, line 238 of `./research/developer-tools/gh-skill.md`
**Local system**: `./.claude/skills/gh/scripts/setup_gh.py` and `./.claude/skills/gh/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #2245 created

### Current state

`setup_gh.py` (lines 1-770) performs platform detection, binary download, SHA256 verification, and PATH installation, but never inspects git remote configuration. There is zero occurrence of `remote`, `proxy`, `127.0.0.1`, or `git config` in the script (verified via grep on 2026-05-10).

`SKILL.md` lines 73-79 hardcode the literal string `Jamie-BitFlight/claude_skills` as the example owner/repo, and that exact string appears 30+ times across the rest of the file (lines 76, 93, 96, 99, 102, 105, 112, 115, 118, 124, ...). Agents reading the skill must either substitute the correct owner/repo themselves or copy the literal string verbatim. There is no machine-readable record of the canonical owner/repo for the current checkout.

The CLAUDE.md `<gh_cli_usage>` block (lines 446-470 of `./.claude/CLAUDE.md`) repeats the same hardcoded `-R Jamie-BitFlight/claude_skills` examples — drift between the example string and the actual remote is undetectable.

### Target state

`setup_gh.py` adds a `--detect-repo` step (run by default during install, also exposed as a standalone subcommand) that:

1. Reads `git config --get remote.origin.url` from the current working directory
2. Parses the URL — extracts `owner/repo` from `github.com:owner/repo.git`, `https://github.com/owner/repo.git`, OR a proxy URL of the form `http://127.0.0.1:PORT/owner/repo.git` (the proxy pattern documented in SKILL.md lines 65-71)
3. Writes the detected `owner/repo` plus a flag `is_proxy_remote: true|false` to `~/.config/gh-skill/repo.json` (or `$XDG_CONFIG_HOME/gh-skill/repo.json`)
4. Emits a one-line summary line on stdout: `repo=<owner/repo> proxy=<true|false>`

Agents that need to issue `gh` commands read `~/.config/gh-skill/repo.json` to obtain the canonical `-R` value rather than relying on a hardcoded literal in SKILL.md. SKILL.md is updated to reference the config file (e.g., `gh pr list -R "$(cat ~/.config/gh-skill/repo.json | jq -r .repo)"`) instead of the hardcoded `Jamie-BitFlight/claude_skills` literal.

### Measurable signal

Run: `./.claude/skills/gh/scripts/setup_gh.py --detect-repo` from the repo root.

- Output line contains `repo=Jamie-BitFlight/claude_skills proxy=true` (the current dev environment uses a 127.0.0.1 proxy per CLAUDE.md `<gh_cli_usage>`).
- File `~/.config/gh-skill/repo.json` exists and contains a JSON object with keys `repo` and `is_proxy_remote`.
- `grep -c "Jamie-BitFlight/claude_skills" ./.claude/skills/gh/SKILL.md` decreases — at least one example uses the config-file lookup pattern instead of the hardcoded string.

---

## Improvement 2: Cache GitHub release metadata locally in setup_gh.py to avoid redundant API calls

**Source pattern**: "Cached metadata: Cache GitHub release information (version, checksums) locally to reduce API calls during multi-agent workflows" — Integration Opportunities, line 239 of `./research/developer-tools/gh-skill.md`
**Local system**: `./.claude/skills/gh/scripts/setup_gh.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #2247 created

### Current state

`setup_gh.py` `fetch_latest_release()` (lines 230-279) issues an unconditional HTTPS GET to `https://api.github.com/repos/cli/cli/releases/latest` on every invocation. `fetch_checksums()` (lines 320-354) issues a second HTTPS GET for the checksums asset. There is no cache lookup before these calls — verified by grep for `cache`, `json.load`, `TTL`, `expir` against `setup_gh.py` on 2026-05-10 (only match: a docstring mention of "expired token").

In multi-agent workflows where several spawned agents each ensure `gh` is installed, every agent re-fetches the same release metadata. With unauthenticated requests the rate limit is 60 requests/hour (per the research entry's caveat #5); with `GITHUB_TOKEN` the limit is 5000/hour but each call still adds latency to setup. The script already does an installed-version short-circuit (lines 730-735) when the installed version matches the latest, but determining "the latest" still requires the network call.

### Target state

`setup_gh.py` adds a cache layer in `fetch_latest_release()`:

1. Before the network call, read `~/.cache/gh-skill/latest-release.json` (or `$XDG_CACHE_HOME/gh-skill/latest-release.json`)
2. If the cache file exists AND its mtime is within a TTL window (default: 6 hours, override via `--cache-ttl-seconds N` CLI option), return the cached `(tag_name, assets)` tuple without a network call
3. On cache miss or stale cache: perform the existing network call, then write the response payload to the cache file atomically (write-temp then rename)
4. Add `--no-cache` CLI flag that skips both reads and writes
5. Apply the same caching to `fetch_checksums()` keyed by asset name

The cache stores the parsed `ReleaseAsset` list and the checksums map serialized as JSON. Stale-cache detection uses file mtime, not embedded timestamps, so the cache invalidates correctly across timezone changes.

### Measurable signal

Run, from a fresh state (cache file absent):

```bash
rm -f ~/.cache/gh-skill/latest-release.json
time ./.claude/skills/gh/scripts/setup_gh.py --dry-run    # cold — issues network calls
time ./.claude/skills/gh/scripts/setup_gh.py --dry-run    # warm — reads cache
```

- The first invocation prints `Fetching latest gh release...` and takes longer (network round-trip).
- The second invocation prints a new line `Using cached release metadata from ~/.cache/gh-skill/latest-release.json (age <N>s)` and is measurably faster (no HTTPS call observed via `strace -e network` or equivalent).
- File `~/.cache/gh-skill/latest-release.json` exists after the first run; mtime updates only on cold runs or when `--no-cache` is passed.
- `--cache-ttl-seconds 0` forces a refresh on every call (verifiable: mtime updates on every invocation).

---

## Deferred Proposals (confidence too low to backlog)

None. All assessed patterns are either high-confidence actionable or already-covered.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Extractive installation with SHA256 verification | Already implemented — `verify_sha256` at lines 453-471 of `./.claude/skills/gh/scripts/setup_gh.py` performs the verification; `find_checksums_asset` at lines 302-314 fetches the checksums file. |
| Automatic authentication from environment (GITHUB_TOKEN) | Already implemented — `_build_headers` at lines 201-215 reads `GITHUB_TOKEN`; `fetch_latest_release` at lines 246-258 attempts authenticated request and falls back on 401/403 with a visible warning (line 254-257). |
| Structured output modes (--json, --jq, Go templates) | Already documented in `./.claude/skills/gh/SKILL.md` lines 244-256 with three concrete examples covering `--json`, `--jq`, and `--template`. |
| Backlog sync via MCP server functions for gh subcommands | Already implemented via `mcp__plugin_dh_backlog__*` tools — see CLAUDE.md `<backlog_operations>` block, lines 412-430. The MCP server uses `gh` under the hood and exposes typed CRUD operations as MCP tools. |
| Silent authentication fallback caveat | Already addressed — `setup_gh.py` lines 254-257 print a yellow warning `:warning: Authenticated request failed (HTTP {status_code}), retrying anonymously` rather than falling back silently. The research entry's caveat #5 is incorrect about the current state. |
