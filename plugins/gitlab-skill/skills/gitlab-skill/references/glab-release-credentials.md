# glab Release Credential and Protected-Ref Operations

Evidence: **LIVE-VERIFIED** project-access-token adapter with `glab 1.118.0`. The universal lifecycle
allows another credential implementation satisfying the same interface.

Start from a user-supplied numeric ID or URL-encoded namespaced project selector and read canonical
identity before setup:

```bash
PROJECT_JSON="$(glab api --hostname "$HOST" "projects/$PROJECT_SELECTOR")"
PROJECT_ID="$(printf '%s' "$PROJECT_JSON" | jq -er '.id')"
PROJECT_PATH="$(printf '%s' "$PROJECT_JSON" | jq -er '.path_with_namespace')"
DEFAULT_BRANCH="$(printf '%s' "$PROJECT_JSON" | jq -er '.default_branch')"
REPO="$(printf '%s' "$PROJECT_JSON" | jq -er '.ssh_url_to_repo')"
VARIABLE_KEY="${VARIABLE_KEY:-RELEASE_PUSH_TOKEN}"
: "${RELEASE_TAG_PREFIX:?RELEASE_TAG_PREFIX must come from the resolved base tag contract}"
TAG_PATTERN="${RELEASE_TAG_PREFIX}*"
unset PROJECT_JSON
```

`RELEASE_PUSH_TOKEN` is an overrideable variable-key policy default, not project identity. The
protected wildcard derives from the required resolved prefix. Supply token name, role, duration,
branch/tag access levels, and variable scope explicitly.

Resolve numeric project ID, repository, default branch, tag wildcard, minimum access levels, token
role/scope/expiry, variable key, and environment scope. Encode the branch path segment before
inspection:

```bash
case "$PROJECT_ID" in ''|*[!0-9]*) exit 1 ;; esac
DEFAULT_BRANCH_PATH="$(printf '%s' "$DEFAULT_BRANCH" | jq -sRr @uri)"
glab api --hostname "$HOST" "projects/$PROJECT_ID/protected_branches/$DEFAULT_BRANCH_PATH" |
  jq '{name,push_access_levels,merge_access_levels}'
glab api --hostname "$HOST" "projects/$PROJECT_ID/protected_tags" |
  jq --arg pattern "$TAG_PATTERN" '.[] | select(.name == $pattern) | {name,create_access_levels}'
glab token list --repo "$REPO" --output json |
  jq --arg name "$TOKEN_NAME" '.[] | select(.name == $name) | {id,name,scopes,access_level,active,revoked,expires_at}'
```

Reuse exact matching resources. Create only absent authorized resources. Stop for an explicit
decision when metadata differs, a token name is ambiguous, or a variable exists without a selected
replacement secret.

```bash
glab api --hostname "$HOST" -X POST "projects/$PROJECT_ID/protected_branches" \
  -f "name=$DEFAULT_BRANCH" -F "push_access_level=$BRANCH_ACCESS_LEVEL" \
  -F "merge_access_level=$BRANCH_ACCESS_LEVEL" --silent
glab api --hostname "$HOST" -X POST "projects/$PROJECT_ID/protected_tags" \
  -f "name=$TAG_PATTERN" -F "create_access_level=$TAG_ACCESS_LEVEL" --silent
TOKEN_JSON="$(glab token create "$TOKEN_NAME" --repo "$REPO" \
  --access-level "$TOKEN_ACCESS_ROLE" --scope write_repository \
  --duration "$TOKEN_DURATION" --output json)"
TOKEN_ID="$(printf '%s' "$TOKEN_JSON" | jq -er '.id')"
TOKEN_SECRET="$(printf '%s' "$TOKEN_JSON" | jq -er '.token')"
printf '%s' "$TOKEN_SECRET" | glab variable set "$VARIABLE_KEY" \
  --repo "$REPO" --masked --hidden --protected --raw --scope "$VARIABLE_SCOPE" >/dev/null
unset TOKEN_SECRET TOKEN_JSON
```

Verify token IDs with string normalization and variable metadata without retrieving its value:

```bash
glab token list --repo "$REPO" --output json |
  jq --arg token_id "$TOKEN_ID" \
  '.[] | select((.id | tostring) == $token_id) | {id,name,scopes,access_level,active,revoked,expires_at}'
glab api --hostname "$HOST" graphql \
  -f 'query=query($fullPath: ID!) { project(fullPath: $fullPath) { ciVariables { nodes { key variableType protected masked hidden raw environmentScope } } } }' \
  -f "fullPath=$PROJECT_PATH" |
  jq --arg key "$VARIABLE_KEY" '.data.project.ciVariables.nodes[] | select(.key == $key)'
```

## Rotation

```bash
ROTATED_JSON="$(glab token rotate "$TOKEN_ID" --repo "$REPO" \
  --duration "$TOKEN_DURATION" --output json)"
NEW_TOKEN_ID="$(printf '%s' "$ROTATED_JSON" | jq -er '.id')"
NEW_TOKEN_SECRET="$(printf '%s' "$ROTATED_JSON" | jq -er '.token')"
printf '%s' "$NEW_TOKEN_SECRET" | glab variable update "$VARIABLE_KEY" \
  --repo "$REPO" --masked --protected --raw --scope "$VARIABLE_SCOPE" >/dev/null
unset NEW_TOKEN_SECRET ROTATED_JSON
```

Rotation revokes the old token before variable update. On timeout or failed update, report metadata
and stop for operator decision. Listing cannot recover a secret, and metadata cannot prove which
value is installed. Exercise the new credential separately before labeling it exercised.

Safety boundary: one-time secrets are captured without printing; indeterminate rotation has no
automatic retry or reconciliation.

Completion criterion: protected refs, token role/scope/state/expiry, and variable
flags/type/environment scope equal the resolved contract; the token authorizes the tag and any
selected release commit.

SOURCE: <https://docs.gitlab.com/cli/token/create/> (accessed 2026-09-22; project-token adapter live verified)
SOURCE: <https://docs.gitlab.com/cli/token/rotate/> (accessed 2026-09-22; rotation `563 -> 564` live verified, token `564` not subsequently exercised)
SOURCE: <https://docs.gitlab.com/cli/variable/> (accessed 2026-09-22; set/update and metadata projection live verified)
SOURCE: <https://docs.gitlab.com/user/project/protected_branches/> (accessed 2026-09-22; default-branch metadata live verified)
SOURCE: <https://docs.gitlab.com/user/project/protected_tags/> (accessed 2026-09-22; protected-tag setup live verified)
