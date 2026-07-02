#!/usr/bin/env bash
# .claude/scripts/session-init.sh
#
# Corrects stale sandbox state left over from a previous Claude Code session,
# before the agent starts: deprecated uv cert env var, stale proxy-pinned git
# config, out-of-date uv/prek. Purely corrective, no diagnostics — nothing
# here observes and reports without also fixing what it found. Produces no
# output: SessionStart hook stdout is added to Claude's context on every
# session, forever (https://code.claude.com/docs/en/hooks.md), so nothing is
# printed. Failures are swallowed (|| true) — this is best-effort background
# cleanup, not something worth interrupting the session over.
#
# Usage:
#   Wired as a SessionStart hook in .claude/settings.json.
#   Can also be run manually: bash .claude/scripts/session-init.sh
#   or sourced in an interactive shell to export vars directly: source .claude/scripts/session-init.sh

# When sourced, save the caller's shell options and restore them on exit so that
# enabling strict mode here does not permanently alter the caller's session.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    _session_init_saved_opts="$(set +o)"
    trap 'eval "${_session_init_saved_opts}"; unset _session_init_saved_opts; trap - RETURN' RETURN
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ─── 1. UV certificate environment ───────────────────────────────────────────
# UV_NATIVE_TLS is deprecated since uv 0.6.x; UV_SYSTEM_CERTS=true is the
# replacement. uv warns on ANY set value (true/false/1/0/yes), not just the
# literal string "true", so match on "is it set". `export` only affects this
# script's own process — CLAUDE_ENV_FILE is what actually persists into the
# session's later Bash calls. Also unset UV_NATIVE_TLS there so uv stops
# warning going forward; guard both appends against duplicates across
# repeated SessionStart firings (startup/resume/clear/compact all match
# matcher "" in settings.json).
if [[ -n "${UV_NATIVE_TLS:-}" ]]; then
    export UV_SYSTEM_CERTS=true
    unset UV_NATIVE_TLS
    if [[ -n "${CLAUDE_ENV_FILE:-}" ]]; then
        grep -q 'UV_SYSTEM_CERTS' "${CLAUDE_ENV_FILE}" 2>/dev/null || echo 'export UV_SYSTEM_CERTS=true' >>"${CLAUDE_ENV_FILE}"
        grep -q 'unset UV_NATIVE_TLS' "${CLAUDE_ENV_FILE}" 2>/dev/null || echo 'unset UV_NATIVE_TLS' >>"${CLAUDE_ENV_FILE}"
    fi
fi

# ─── 2. Stale git insteadOf cleanup in ~/.gitconfig ──────────────────────────
# Previous sessions may leave insteadOf URL rewrites pointing to wrong proxy
# ports or plain-HTTP proxy URLs. The current proxy handles SSH→HTTPS
# rewrites via gitConfigInjection — manual insteadOf entries conflict and
# break git. Filtered to local-proxy rewrites only — never touch unrelated
# insteadOf entries (e.g. corporate mirrors) a user may have configured.
stale=$(git config --global --get-regexp 'url\..*\.insteadOf' 2>/dev/null | grep -Ei '127\.0\.0\.1|local_proxy' || true)
if [[ -n "${stale}" ]]; then
    while IFS=' ' read -r key _value; do
        git config --global --unset-all "${key}" 2>/dev/null || true
    done <<<"${stale}"
fi

# ─── 3. Fix stale remote.origin.url in .git/config ───────────────────────────
# Each container may be cloned through a different proxy port, leaving the
# remote URL pointing to a local proxy address like
# http://local_proxy@127.0.0.1:<old-port>/git/... — replace with the real
# github.com URL for fetch and push to work.
raw_url=$(git -C "${REPO_ROOT}" config --local remote.origin.url 2>/dev/null) || raw_url=""

if [[ "${raw_url}" =~ 127\.0\.0\.1 ]] || [[ "${raw_url}" =~ local_proxy ]]; then
    # Extract owner/repo from the end of the URL (last two path segments).
    # The /git/ prefix form (http://user@127.0.0.1:PORT/git/owner/repo) is
    # stripped directly. The plain form (http://127.0.0.1:PORT/owner/repo)
    # has no /git/ segment, so ##*/git/ would be a no-op and leave the whole
    # URL in repo_path — strip scheme, credentials, and host:port instead.
    if [[ "${raw_url}" == */git/* ]]; then
        repo_path="${raw_url##*/git/}"
    else
        repo_path="${raw_url#*://}"
        repo_path="${repo_path#*@}"
        repo_path="${repo_path#*/}"
    fi
    repo_path="${repo_path%.git}"
    if [[ -n "${repo_path}" && "${repo_path}" == */* ]]; then
        if [[ -n "${GITHUB_TOKEN:-}" ]]; then
            new_url="https://x-access-token:${GITHUB_TOKEN}@github.com/${repo_path}"
        else
            new_url="https://github.com/${repo_path}"
        fi
        (cd "${REPO_ROOT}" && git remote set-url origin "${new_url}") 2>/dev/null || true
    fi
elif [[ "${raw_url}" == https://github.com/* ]] || [[ "${raw_url}" =~ ^https://[^@]+@github\.com/ ]]; then
    # URL already points to github.com (with or without embedded
    # credentials) — refresh the token if one is available and differs.
    if [[ "${raw_url}" == *"@github.com/"* ]]; then
        repo_path="${raw_url##*@github.com/}"
    else
        repo_path="${raw_url#https://github.com/}"
    fi
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        new_url="https://x-access-token:${GITHUB_TOKEN}@github.com/${repo_path}"
        if [[ "${raw_url}" != "${new_url}" ]]; then
            (cd "${REPO_ROOT}" && git remote set-url origin "${new_url}") 2>/dev/null || true
        fi
    fi
fi

# ─── 4. uv + prek maintenance ─────────────────────────────────────────────────
uv self update >/dev/null 2>&1 || true
(cd "${REPO_ROOT}" && uv run prek install \
    -t pre-commit -t commit-msg -t pre-rebase -t post-merge) >/dev/null 2>&1 || true
