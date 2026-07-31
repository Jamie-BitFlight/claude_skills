---
description: Create GitLab project access token for CI/CD publishing and add as masked CI variable
---

# Setup CI Publishing Token

Creates a GitLab project access token with permissions for publishing releases and uploading artifacts, then adds it as a protected, masked CI/CD variable.

## Problem

GitLab CI `CI_JOB_TOKEN` has limited permissions and cannot upload release assets, causing `401 Unauthorized` errors when using `glab release create` with file attachments.

## Solution

Run the setup script which automatically:

1. Verifies your GITLAB_TOKEN has required permissions (api scope + Maintainer access)
2. Checks if `ci-publish-token` project access token exists
3. Checks if `CI_PUBLISH_TOKEN` CI/CD variable exists
4. Takes appropriate action based on current state

## Prerequisites

- `GITLAB_TOKEN` environment variable set with `api` scope and Maintainer+ access to the project
- `jq` installed
- `glab` installed and authenticated
- Running from the git repository root

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
[ -s .env ] && . ./.env

# Set the token for the environment
GITLAB_TOKEN="${GITLAB_TOKEN:-${GL_TOKEN:-${CI_JOB_TOKEN:-}}}"
export GITLAB_TOKEN

if [ -z "${GITLAB_TOKEN:-}" ]; then
    echo "ERROR: You need a GITLAB_TOKEN set in your environment to do this."
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

token_json=$(glab token list --repo "${CI_PROJECT_PATH}" --output json)
token_info=$(echo "${token_json}" | jq -r "if . == null then empty else .[] | select(.name == \"${TOKEN_NAME}\") end")

# Filter out the "Listing variables..." line, default to empty array if no match
var_json=$(glab variable list --repo "${CI_PROJECT_PATH}" --output json 2>/dev/null | grep '^\[' || echo '[]')
if echo "${var_json}" | jq -e ".[] | select(.key == \"${VAR_NAME}\")" >/dev/null 2>&1; then
    var_exists="true"
else
    var_exists="false"
fi

# --- Decision logic ---

# Case 4: No token exists - CREATE NEW
if [ -z "${token_info}" ]; then
    echo "INFO: Creating project access token '${TOKEN_NAME}'..."
    NEW_TOKEN=$(glab token create "${TOKEN_NAME}" \
        --repo "${CI_PROJECT_PATH}" \
        --access-level maintainer \
        --scope api \
        --scope write_repository \
        --duration 8760h \
        --description "CI/CD token for publishing releases and uploading artifacts" \
        --output text)

    echo "INFO: Setting CI variable '${VAR_NAME}'..."
    echo "${NEW_TOKEN}" | glab variable set "${VAR_NAME}" \
        --repo "${CI_PROJECT_PATH}" \
        --masked \
        --protected \
        --description "Project access token for CI/CD release publishing and artifact uploads"

    echo "DONE: Token and variable created."
    exit 0
fi

# Token exists - check expiry
expires_at=$(echo "${token_info}" | jq -r '.expires_at')
today=$(date +%Y-%m-%d)

# Convert YYYY-MM-DD to integer for POSIX-compatible comparison
expires_int=$(echo "${expires_at}" | tr -d '-')
today_int=$(echo "${today}" | tr -d '-')

# Case 2: Token expired - RENEW
if [ "${expires_int}" -lt "${today_int}" ]; then
    echo "INFO: Token expired (${expires_at}). Rotating..."
    NEW_TOKEN=$(glab token rotate "${TOKEN_NAME}" --repo "${CI_PROJECT_PATH}" --output text)

    echo "INFO: Updating CI variable '${VAR_NAME}'..."
    echo "${NEW_TOKEN}" | glab variable update "${VAR_NAME}" --repo "${CI_PROJECT_PATH}"

    echo "DONE: Token rotated and variable updated."
    exit 0
fi

# Case 3: Token valid but variable missing - ROTATE to get new value
if [ "${var_exists}" = "false" ]; then
    echo "INFO: Token '${TOKEN_NAME}' exists (expires ${expires_at}) but CI variable '${VAR_NAME}' is missing."
    echo "INFO: Rotating token to obtain a new value..."
    NEW_TOKEN=$(glab token rotate "${TOKEN_NAME}" --repo "${CI_PROJECT_PATH}" --output text)

    echo "INFO: Setting CI variable '${VAR_NAME}'..."
    echo "${NEW_TOKEN}" | glab variable set "${VAR_NAME}" \
        --repo "${CI_PROJECT_PATH}" \
        --masked \
        --protected \
        --description "Project access token for CI/CD release publishing and artifact uploads"

    echo "DONE: Token rotated and variable created."
    exit 0
fi

# Case 1: Token valid and variable exists - SKIP
echo "OK: Already configured. Token '${TOKEN_NAME}' expires ${expires_at}."
exit 0

```

Run it:

```bash
chmod +x .claude/commands/setup-ci-publish-token.sh && .claude/commands/setup-ci-publish-token.sh
```

## Script Behavior

| Token Exists? | Token Valid? | Variable Exists? | Script Action                                |
| ------------- | ------------ | ---------------- | -------------------------------------------- |
| No            | N/A          | Any              | Creates token and variable                   |
| Yes           | Expired      | Yes              | Rotates token, updates variable              |
| Yes           | Valid        | No               | Rotates token to get value, creates variable |
| Yes           | Valid        | Yes              | No action needed (already configured)        |

## Output Messages

The script uses consistent prefixes for parsing:

- `ERROR:` - Fatal error, script exits with non-zero status
- `INFO:` - Progress information
- `DONE:` - Successful completion with changes made
- `OK:` - Successful completion, no changes needed

## Examples of how to use the new token

In your `.gitlab-ci.yml` or CI scripts, prefer `CI_PUBLISH_TOKEN` for operations requiring elevated permissions. eg.:

```bash
PUBLISH_TOKEN="${CI_PUBLISH_TOKEN:-${GITLAB_TOKEN:-${GL_TOKEN:-}}}"
if [ -n "${PUBLISH_TOKEN}" ]; then
  glab auth login --hostname "${CI_SERVER_HOST}" --token "${PUBLISH_TOKEN}"
else
  glab auth login --hostname "${CI_SERVER_HOST}" --job-token "${CI_JOB_TOKEN}"
fi
```

In Python scripts you can now check for it:

```python
token = (
    os.environ.get("CI_PUBLISH_TOKEN")
    or os.environ.get("GITLAB_TOKEN")
    or os.environ.get("GL_TOKEN")
    or os.environ.get("CI_JOB_TOKEN")
)
```

## Token Details

The script creates tokens with:

- **Name:** `ci-publish-token`
- **Access level:** Maintainer
- **Scopes:** `api`, `write_repository`
- **Duration:** 1 year (8760h)

The CI variable is created with:

- **Protected:** Yes (only available on protected branches)
- **Masked:** Yes (hidden in job logs)

## Troubleshooting

**ERROR: The current GITLAB_TOKEN does not have the 'api' scope**

Your personal access token needs the `api` scope. Create a new token at Settings > Access Tokens with `api` scope enabled.

**ERROR: The current GITLAB_TOKEN does not have Maintainer (40) or higher access**

You need Maintainer or Owner role on the project to manage project access tokens and CI variables.

**401 Unauthorized errors persist after setup:**

- Verify the job runs on a protected branch (the variable is protected)
- Check token hasn't expired: `glab token list`
- Verify your CI script is using `CI_PUBLISH_TOKEN`, not `CI_JOB_TOKEN`

**Variable not available in job:**

- Protected variables only work on protected branches
- Verify the branch/tag is protected in Settings > Repository > Protected branches

## Related Documentation

- [GitLab Project Access Tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ci/variables/)
- [glab token documentation](https://gitlab.com/gitlab-org/cli/-/blob/main/docs/source/token/index.md)
