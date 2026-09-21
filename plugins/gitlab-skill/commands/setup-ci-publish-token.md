---
description: Create a GitLab project access token for CI/CD operations that require elevated permissions
---

# Setup CI Publishing Token

Creates a GitLab project access token for CI/CD operations that cannot use a job token, then adds it as a protected, masked, hidden CI/CD variable.

## Problem

The preferred release-asset route uses the predefined `CI_JOB_TOKEN`, CI auto-login with `GLAB_ENABLE_CI_AUTOLOGIN=true`, and `glab release create --use-package-registry`. Use this command only when another CI/CD operation requires the broader permissions of a project access token.

## Solution

Run the setup script which automatically:

1. Verifies your personal access token has required permissions (`api` scope and Maintainer access)
2. Checks whether the active `ci-publish-token` project access token has reached its expiration date
3. Checks whether the `CI_PUBLISH_TOKEN` CI/CD variable exists and reports hidden metadata
4. Takes appropriate action based on current state

## Prerequisites

- `GITLAB_TOKEN` or `GL_TOKEN` set to a personal access token with `api` scope and Maintainer+ access to the project; project and job tokens cannot create project access tokens
- `jq` installed
- `glab` installed; the script authenticates from the token environment variable
- Running from the git repository root
- On GitLab.com, a Premium or Ultimate subscription; project access tokens are available with any license on GitLab Self-Managed and Dedicated

## Usage

Create the script at `.claude/commands/setup-ci-publish-token.sh`:

```sh
#!/usr/bin/env sh
# setup-ci-publish-token.sh
# Creates or renews CI_PUBLISH_TOKEN for GitLab CI/CD publishing

set -eu

# Constants
TOKEN_NAME="ci-publish-token"
VAR_NAME="CI_PUBLISH_TOKEN"

# Load existing .env if present and non-empty
# shellcheck source=/dev/null
[ -s .env ] && . ./.env

# Project access-token creation requires personal access-token authentication.
GITLAB_TOKEN="${GITLAB_TOKEN:-${GL_TOKEN:-}}"
export GITLAB_TOKEN

if [ -z "${GITLAB_TOKEN:-}" ]; then
    echo "ERROR: Set GITLAB_TOKEN or GL_TOKEN to a personal access token with the api scope."
    exit 1
fi

if [ ! -d .git ]; then
    echo "ERROR: You must be in the git root directory to do this."
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: You need jq installed. Try 'brew install jq'"
    exit 1
fi

if ! command -v glab >/dev/null 2>&1; then
    echo "ERROR: You need glab installed. Try 'brew install glab'"
    exit 1
fi

in_dotenv() { [ -e .env ] && grep -q "^$1=" .env; }
in_env() { env | grep -q "^$1="; }

# --- Environment variable detection ---

if ! in_env GITLAB_HOST && ! in_dotenv GITLAB_HOST; then
    if [ -z "${CI_SERVER_HOST:-}" ]; then
        GITLAB_HOST="$(sed -n 's/.*url = git@\([^:]*\):.*/\1/p; s/.*url = https:\/\/\([^/]*\)\/.*/\1/p' .git/config | head -1)"
    else
        GITLAB_HOST="${CI_SERVER_HOST}"
    fi
fi

if ! in_env CI_PROJECT_PATH && ! in_dotenv CI_PROJECT_PATH; then
    CI_PROJECT_PATH="$(sed -n 's/.*url = git@[^:]*:\(.*\)\.git$/\1/p; s/.*url = https:\/\/[^/]*\/\(.*\)\.git$/\1/p' .git/config | head -1)"
fi

if ! in_env GITLAB_USER_ID && ! in_dotenv GITLAB_USER_ID; then
    GITLAB_USER_ID="$(glab api user | jq '.id')"
fi

# --- Persist to .env if not in CI ---

if [ -z "${GITLAB_CI:-}" ]; then
    [ ! -e .env ] && touch .env
    [ ! -e .gitignore ] && touch .gitignore
    grep -qE '^\s*/?\.env\s*$' .gitignore || printf "# Ignore localized environment variables\n.env\n" >>.gitignore
    # shellcheck source=/dev/null
    [ -s .env ] && . ./.env
    in_dotenv GITLAB_HOST || echo "GITLAB_HOST=${GITLAB_HOST}" >>.env
    in_dotenv CI_PROJECT_PATH || echo "CI_PROJECT_PATH=${CI_PROJECT_PATH}" >>.env
    in_dotenv GITLAB_USER_ID || echo "GITLAB_USER_ID=${GITLAB_USER_ID}" >>.env
fi

# URL-encode the project path for API calls
CI_PROJECT_PATH_ENCODED=$(printf '%s' "${CI_PROJECT_PATH}" | sed 's/\//%2F/g')

export GITLAB_HOST CI_PROJECT_PATH GITLAB_USER_ID CI_PROJECT_PATH_ENCODED

# --- Permission checks ---

has_api_scope() {
    if glab api personal_access_tokens/self | jq -e '.scopes | index("api")' >/dev/null 2>&1; then
        return 0
    else
        echo "ERROR: The current GITLAB_TOKEN does not have the 'api' scope."
        exit 1
    fi
}

has_maintainer_access() {
    access_level=$(glab api "projects/${CI_PROJECT_PATH_ENCODED}/members/all/${GITLAB_USER_ID}" | jq -r '.access_level')
    if [ "${access_level:-0}" -ge 40 ]; then
        return 0
    else
        echo "ERROR: The current GITLAB_TOKEN does not have Maintainer (40) or higher access to ${CI_PROJECT_PATH}."
        exit 1
    fi
}

has_api_scope
has_maintainer_access

# --- Check token and variable status ---

token_json=$(glab token list --repo "${CI_PROJECT_PATH}" --active --output json)
token_matches=$(printf '%s' "${token_json}" | jq -c --arg name "${TOKEN_NAME}" --arg prefix "${TOKEN_NAME}-" \
    '[(. // [])[] | select(.name == $name or (.name | startswith($prefix)))] | sort_by(.id)')
token_count=$(printf '%s' "${token_matches}" | jq -r 'length')

if [ "${token_count}" -gt 1 ]; then
    token_ids=$(printf '%s' "${token_matches}" | jq -r 'map(.id | tostring) | join(", ")')
    echo "ERROR: Multiple active '${TOKEN_NAME}' tokens exist (IDs: ${token_ids}). Revoke all but one and retry."
    exit 1
fi

token_info=$(printf '%s' "${token_matches}" | jq -c 'if length == 1 then .[0] else empty end')

variable_json=""
if variable_json=$(glab variable get "${VAR_NAME}" --repo "${CI_PROJECT_PATH}" --output json 2>/dev/null); then
    var_exists="true"
    var_hidden=$(printf '%s' "${variable_json}" | jq -r \
        'if (.hidden | type) == "boolean" then (.hidden | tostring) else "unknown" end')
else
    var_exists="false"
    var_hidden="absent"
fi

set_ci_variable() {
    if [ "${var_exists}" = "true" ]; then
        echo "INFO: Replacing CI variable '${VAR_NAME}' so its value is hidden..."
        glab variable delete "${VAR_NAME}" --repo "${CI_PROJECT_PATH}"
    else
        echo "INFO: Setting CI variable '${VAR_NAME}'..."
    fi

    printf '%s' "${NEW_TOKEN}" | glab variable set "${VAR_NAME}" \
        --repo "${CI_PROJECT_PATH}" \
        --hidden \
        --masked \
        --protected \
        --description "Project access token for CI/CD release publishing and artifact uploads"
}

# --- Decision logic ---

# Case 4: No token exists - CREATE NEW
if [ -z "${token_info}" ]; then
    echo "INFO: Creating project access token '${TOKEN_NAME}'..."
    new_token_name="${TOKEN_NAME}-$(date -u +%Y%m%d%H%M%S)-$$"
    NEW_TOKEN=$(glab token create "${new_token_name}" \
        --repo "${CI_PROJECT_PATH}" \
        --access-level maintainer \
        --scope api \
        --duration 8760h \
        --description "CI/CD token for publishing releases and uploading artifacts" \
        --output text)

    set_ci_variable
    unset NEW_TOKEN

    echo "DONE: Token and variable created."
    exit 0
fi

# Token exists - check expiry
expires_at=$(echo "${token_info}" | jq -r '.expires_at')
token_id=$(echo "${token_info}" | jq -r '.id')
today=$(date -u +%Y-%m-%d)

# Convert YYYY-MM-DD to integer for POSIX-compatible comparison
expires_int=$(echo "${expires_at}" | tr -d '-')
today_int=$(echo "${today}" | tr -d '-')

# Case 2: Token expired - RENEW
if [ "${expires_int}" -le "${today_int}" ]; then
    echo "INFO: Token expired (${expires_at}). Creating a replacement..."
    new_token_name="${TOKEN_NAME}-$(date -u +%Y%m%d%H%M%S)-$$"
    NEW_TOKEN=$(glab token create "${new_token_name}" \
        --repo "${CI_PROJECT_PATH}" \
        --access-level maintainer \
        --scope api \
        --duration 8760h \
        --description "CI/CD token for publishing releases and uploading artifacts" \
        --output text)

    set_ci_variable
    unset NEW_TOKEN

    echo "DONE: Replacement token and variable created."
    exit 0
fi

# Case 3: Token valid but variable missing - ROTATE to get new value
if [ "${var_exists}" = "false" ]; then
    echo "INFO: Token '${TOKEN_NAME}' exists (expires ${expires_at}) but CI variable '${VAR_NAME}' is missing."
    echo "INFO: Rotating token to obtain a new value..."
    NEW_TOKEN=$(glab token rotate "${token_id}" --repo "${CI_PROJECT_PATH}" --duration 8760h --output text)

    set_ci_variable
    unset NEW_TOKEN

    echo "DONE: Token rotated and variable created."
    exit 0
fi

# Case 1: Token valid and legacy variable is not hidden - MIGRATE
if [ "${var_hidden}" = "false" ]; then
    if ! NEW_TOKEN=$(printf '%s' "${variable_json}" | jq -er '.value | strings | select(length > 0)'); then
        echo "ERROR: CI variable '${VAR_NAME}' is not hidden, but its current value was not returned; no change was made."
        exit 1
    fi

    echo "INFO: CI variable '${VAR_NAME}' is not hidden. Recreating it with hidden storage..."
    set_ci_variable
    unset NEW_TOKEN variable_json

    echo "DONE: Existing variable recreated with hidden storage."
    exit 0
fi

# Case 1: Token valid and variable exists, but hidden state is unavailable - SKIP
if [ "${var_hidden}" = "unknown" ]; then
    echo "OBSERVED: CI variable '${VAR_NAME}' exists, but current output did not report boolean hidden metadata."
    echo "OBSERVED: No change was made; hidden storage was not verified. Token '${TOKEN_NAME}' expires ${expires_at}."
    exit 0
fi

# Case 1: Token valid and hidden variable exists - SKIP
echo "OK: Already configured with hidden variable storage. Token '${TOKEN_NAME}' expires ${expires_at}."
exit 0

```

Run it:

```bash
chmod +x .claude/commands/setup-ci-publish-token.sh && .claude/commands/setup-ci-publish-token.sh
```

## Script Behavior

| Token Exists? | Token Valid? | Variable State          | Script Action                                      |
| ------------- | ------------ | ----------------------- | -------------------------------------------------- |
| No            | N/A          | Any                     | Creates token and hidden variable                  |
| Yes           | Expired      | Any                     | Creates replacement token and hidden variable      |
| Yes           | Valid        | Missing                 | Rotates token to get value, creates hidden variable |
| Yes           | Valid        | Exists, not hidden      | Preserves value, deletes, and recreates as hidden  |
| Yes           | Valid        | Exists, hidden          | No action needed                                   |
| Yes           | Valid        | Hidden state unavailable | Reports observed state; makes no hidden claim       |

## Output Messages

The script uses consistent prefixes for parsing:

- `ERROR:` - Fatal error, script exits with non-zero status
- `INFO:` - Progress information
- `DONE:` - Successful completion with changes made
- `OK:` - Successful completion, no changes needed
- `OBSERVED:` - Existing state could not be fully verified; no change made

## Preferred release-asset authentication

For release assets, use `CI_JOB_TOKEN`, enable CI auto-login with `GLAB_ENABLE_CI_AUTOLOGIN=true`, and upload through the generic package registry:

```bash
GLAB_ENABLE_CI_AUTOLOGIN=true glab release create "${CI_COMMIT_TAG}" ./dist/* --use-package-registry
```

Do not assign `CI_JOB_TOKEN` to `GITLAB_TOKEN`; `glab` sends these token types in different headers.

## Using the project access token

For an operation that needs the project access token, provide it directly through the documented environment variable without persisting a login:

```bash
GITLAB_TOKEN="${CI_PUBLISH_TOKEN}" glab api projects/:id
```

If a persistent login is required outside CI, pass the token on standard input instead of placing it in process arguments:

```bash
printf '%s' "${CI_PUBLISH_TOKEN}" | glab auth login --hostname "${GITLAB_HOST}" --stdin
```

## Token Details

The script creates tokens with:

- **Name:** A unique name prefixed with `ci-publish-token-`
- **Access level:** Maintainer
- **Scope:** `api`
- **Duration:** 1 year (8760h)

The CI variable is created with:

- **Protected:** Yes (available to pipelines on protected branches or protected tags, and optionally to eligible merge-request pipelines)
- **Masked:** Yes (exact matching output is replaced with `[MASKED]`, subject to GitLab's masking limitations)
- **Hidden:** Yes (the value cannot be revealed in the UI after creation)

## Troubleshooting

**ERROR: The current GITLAB_TOKEN does not have the 'api' scope**

Your personal access token needs the `api` scope. Create a new token at Settings > Access Tokens with `api` scope enabled.

**ERROR: The current GITLAB_TOKEN does not have Maintainer (40) or higher access**

You need Maintainer or Owner role on the project to manage project access tokens and CI variables.

**401 Unauthorized errors persist after setup:**

- Verify the job runs on a protected branch or protected tag (the variable is protected)
- Check token hasn't expired: `glab token list`
- For release assets, verify CI auto-login is enabled and `--use-package-registry` is present

**Variable not available in job:**

- Protected variables are available to pipelines on protected branches or protected tags, and optionally to eligible merge-request pipelines
- For a branch, verify the ref under Settings > Repository > Branch rules
- For a tag, verify the ref under Settings > Repository > Protected tags

## Related Documentation

- [GitLab Project Access Tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ci/variables/)
- [glab token documentation](https://docs.gitlab.com/cli/token/)
