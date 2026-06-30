#!/usr/bin/env bash
# .claude/scripts/session-init.sh
#
# Initializes a Claude Code remote sandbox session.
# Fixes known environment issues, cleans stale git config, and installs git hooks.
#
# Usage:
#   bash .claude/scripts/session-init.sh        — apply fixes (env vars NOT exported to caller shell)
#   source .claude/scripts/session-init.sh      — apply fixes AND export env vars to current shell
#
# To add to CLAUDE.md session-start instructions:
#   !`source .claude/scripts/session-init.sh`
#
# Validation: the script tests that each critical tool works THROUGH the proxy.
# All outbound HTTPS in this sandbox is routed through HTTPS_PROXY — the goal is
# correct configuration through the proxy, not bypassing it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log()  { echo "[session-init] $*"; }
warn() { echo "[session-init] WARNING: $*" >&2; }
ok()   { echo "[session-init] OK: $*"; }

echo "━━━ session-init: Claude Code sandbox environment setup ━━━"
echo ""

# ─── 1. UV certificate environment ───────────────────────────────────────────
# UV_NATIVE_TLS is deprecated since uv 0.6.x; UV_SYSTEM_CERTS=true is the replacement.
# This export works when sourced; when run as a subshell it affects child processes only.
if [[ "${UV_NATIVE_TLS:-}" == "true" ]]; then
    export UV_SYSTEM_CERTS=true
    log "Exported UV_SYSTEM_CERTS=true (replaces deprecated UV_NATIVE_TLS)"
    log "Infrastructure fix needed: replace UV_NATIVE_TLS=true with UV_SYSTEM_CERTS=true"
else
    ok "UV cert env already correct"
fi

# ─── 2. Verify CA bundle ─────────────────────────────────────────────────────
CA_BUNDLE="${SSL_CERT_FILE:-}"
if [[ -f "${CA_BUNDLE}" ]]; then
    ok "CA bundle: ${CA_BUNDLE}"
else
    warn "SSL_CERT_FILE not set or file missing — proxy TLS will fail"
fi

# ─── 3. Proxy connectivity check ─────────────────────────────────────────────
# Extract port from HTTPS_PROXY=http://127.0.0.1:<port>  using greedy strip to last colon.
PROXY_PORT="${HTTPS_PROXY##*:}"
if [[ -n "${PROXY_PORT}" ]] && \
   curl -sS --max-time 2 "http://127.0.0.1:${PROXY_PORT}/__agentproxy/status" >/dev/null 2>&1; then
    ok "Proxy reachable at port ${PROXY_PORT}"
else
    warn "Proxy not reachable at port ${PROXY_PORT:-unknown} — all outbound HTTPS will fail"
    warn "HTTPS_PROXY=${HTTPS_PROXY:-unset}"
fi

# ─── 4. Stale git insteadOf cleanup in ~/.gitconfig ──────────────────────────
# Previous sessions may leave insteadOf URL rewrites pointing to wrong proxy ports
# or plain-HTTP proxy URLs. The current proxy handles SSH→HTTPS rewrites via
# gitConfigInjection — manual insteadOf entries conflict and break git.
echo ""
log "Checking for stale git insteadOf entries in ~/.gitconfig..."
stale=$(git config --global --get-regexp 'url\..*\.insteadOf' 2>/dev/null || true)
if [[ -n "${stale}" ]]; then
    warn "Found stale insteadOf entries from a previous session:"
    while IFS=' ' read -r key _value; do
        echo "  removing: ${key}"
        git config --global --unset-all "${key}" 2>/dev/null || true
    done <<< "${stale}"
    ok "Stale insteadOf entries removed"
else
    ok "git insteadOf: clean"
fi

# ─── 5. Fix stale remote.origin.url in .git/config ───────────────────────────
# Each container may be cloned through a different proxy port, leaving the remote
# URL pointing to a local proxy address like http://local_proxy@127.0.0.1:<old-port>/git/...
# This must be replaced with the real github.com URL for fetch and push to work.
echo ""
log "Checking remote.origin.url..."
raw_url=$(cd "${REPO_ROOT}" && git config --local remote.origin.url 2>/dev/null || true)

# Detect stale local proxy URLs (pattern: http(s)://...@127.0.0.1:.../git/<owner>/<repo>)
# or plain http://127.0.0.1:... URLs from previous proxy injection
if [[ "${raw_url}" =~ 127\.0\.0\.1 ]] || [[ "${raw_url}" =~ local_proxy ]]; then
    warn "remote.origin.url is a stale local proxy URL: ${raw_url}"
    # Extract owner/repo from the end of the URL (last two path segments)
    repo_path="${raw_url##*/git/}"     # strip everything up to /git/
    if [[ -n "${repo_path}" && "${repo_path}" == */* ]]; then
        if [[ -n "${GITHUB_TOKEN:-}" ]]; then
            new_url="https://x-access-token:${GITHUB_TOKEN}@github.com/${repo_path}"
        else
            new_url="https://github.com/${repo_path}"
        fi
        (cd "${REPO_ROOT}" && git remote set-url origin "${new_url}")
        ok "remote.origin.url fixed: https://github.com/${repo_path}"
    else
        warn "Could not parse owner/repo from: ${raw_url}"
        warn "Set remote URL manually: git remote set-url origin https://github.com/<owner>/<repo>"
    fi
elif [[ "${raw_url}" == https://github.com/* ]] || [[ "${raw_url}" =~ ^https://[^@]+@github\.com/ ]]; then
    # URL points to github.com (with or without embedded credentials) — refresh token
    bare_url=$(echo "${raw_url}" | sed 's|https://[^@]*@github\.com/|https://github.com/|')
    repo_path="${bare_url#https://github.com/}"
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        new_url="https://x-access-token:${GITHUB_TOKEN}@github.com/${repo_path}"
        if [[ "${raw_url}" != "${new_url}" ]]; then
            (cd "${REPO_ROOT}" && git remote set-url origin "${new_url}")
            ok "remote.origin.url: refreshed GITHUB_TOKEN for github.com/${repo_path}"
        else
            ok "remote.origin.url: already has current GITHUB_TOKEN"
        fi
    else
        ok "remote.origin.url: github.com URL (no GITHUB_TOKEN — push will require credentials)"
    fi
else
    warn "remote.origin.url is unrecognized: ${raw_url}"
fi

# ─── 6. uv update ────────────────────────────────────────────────────────────
echo ""
log "Updating uv..."
uv self update 2>&1 | tail -1 | sed 's/^/[session-init] /' || true

# ─── 7. prek hook installation ───────────────────────────────────────────────
# Installs git hook scripts into .git/hooks/ (fast, no network required).
# Hook venvs are created lazily on first hook run.
echo ""
log "Installing git hooks via prek..."
if (cd "${REPO_ROOT}" && uv run prek install \
        -t pre-commit -t commit-msg -t pre-rebase -t post-merge 2>&1); then
    ok "prek: git hook scripts installed"
else
    warn "prek install failed — hooks may not run on commit"
fi

# ─── 8. Validation: test that tooling works correctly through the proxy ───────
# All outbound HTTPS goes through HTTPS_PROXY. These tests confirm each tool
# can reach the internet correctly with the current proxy and cert configuration.
echo ""
log "Validating tool connectivity through proxy..."

# Test 1: git fetch (exercises GIT_SSL_CAINFO + proxy HTTPS CONNECT)
if (cd "${REPO_ROOT}" && git fetch --dry-run origin 2>/dev/null); then
    ok "git fetch:      proxy + SSL ✓"
else
    warn "git fetch FAILED — check GIT_SSL_CAINFO (${GIT_SSL_CAINFO:-unset}) and proxy"
fi

# Test 2: Python HTTPS (exercises SSL_CERT_FILE + HTTPS_PROXY env)
if uv run python -c "
import urllib.request, ssl, os
ctx = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE'))
urllib.request.urlopen('https://pypi.org/simple/', context=ctx, timeout=5)
" 2>/dev/null; then
    ok "Python HTTPS:   proxy + SSL ✓"
else
    warn "Python HTTPS FAILED — check SSL_CERT_FILE (${SSL_CERT_FILE:-unset}) and HTTPS_PROXY"
fi

# Test 3: PyPI HTTPS via curl (exercises proxy + sandbox cert bundle for pip/uv downloads)
if curl -sS --max-time 5 \
        --cacert "${SSL_CERT_FILE:-/root/.ccr/ca-bundle.crt}" \
        "https://pypi.org/simple/pip/" 2>/dev/null | grep -q 'pip'; then
    ok "PyPI HTTPS:     proxy + SSL ✓"
else
    warn "PyPI HTTPS FAILED — pip/uv downloads will fail; check SSL_CERT_FILE and proxy"
fi

# ─── 9. shellcheck availability ──────────────────────────────────────────────
echo ""
if command -v shellcheck >/dev/null 2>&1; then
    ok "shellcheck: $(command -v shellcheck) ($(shellcheck --version | head -2 | tail -1))"
else
    warn "shellcheck not in PATH"
    warn "  Pre-commit hook 'shellcheck-py' will fail: pip downloads a ~2.5MB binary"
    warn "  from GitHub releases and the proxy drops large streaming downloads."
    warn "  Use --no-verify for commits that trigger shellcheck until fixed."
    warn "  Permanent fix: see infrastructure requirements below."
fi

# ─── 10. Infrastructure requirements ─────────────────────────────────────────
echo ""
echo "━━━ Infrastructure requirements (must be fixed at sandbox provisioning) ━━━"
echo ""
echo "  Environment variables (set at sandbox creation):"
echo ""
echo "    CHANGE: UV_NATIVE_TLS=true  →  UV_SYSTEM_CERTS=true  (deprecated since uv 0.6)"
echo "    OK:     SSL_CERT_FILE=/root/.ccr/ca-bundle.crt"
echo "    OK:     REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt"
echo "    OK:     GIT_SSL_CAINFO=/root/.ccr/ca-bundle.crt"
echo "    OK:     NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt"
echo "    OK:     PIP_CERT=/root/.ccr/ca-bundle.crt"
echo "    OK:     CARGO_HTTP_CAINFO=/root/.ccr/ca-bundle.crt"
echo ""
echo "  Base image packages (proxy cannot stream large binary downloads):"
echo ""
if command -v shellcheck >/dev/null 2>&1; then
    echo "    OK: shellcheck already in base image: $(command -v shellcheck)"
    echo "        Replace shellcheck-py hook in .pre-commit-config.yaml with a local hook"
    echo "        that calls the system binary — eliminates the binary download on pip install:"
    echo ""
    echo "          - repo: local"
    echo "            hooks:"
    echo "              - id: shellcheck"
    echo "                name: shellcheck"
    echo "                language: system"
    echo "                entry: shellcheck"
    echo "                types: [shell]"
else
    echo "    MISSING: shellcheck — apt-get install -y shellcheck"
    echo ""
    echo "    Root cause: shellcheck-py downloads a ~2.5MB tar.xz from GitHub releases"
    echo "    during 'pip install'. The proxy drops the connection mid-stream"
    echo "    (IncompleteRead after ~200KB). This is NOT a certificate issue."
    echo ""
    echo "    After adding shellcheck to the base image, replace the pre-commit hook:"
    echo ""
    echo "      - repo: local"
    echo "        hooks:"
    echo "          - id: shellcheck"
    echo "            name: shellcheck"
    echo "            language: system"
    echo "            entry: shellcheck"
    echo "            types: [shell]"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
log "session-init complete"
