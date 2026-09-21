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
