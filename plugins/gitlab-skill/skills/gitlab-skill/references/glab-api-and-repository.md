# glab API and Repository Selection

Evidence: command forms checked against installed `glab 1.118.0` and the live sandbox.

```bash
glab api --hostname "$HOST" user | jq '{id,username,name}'
glab api --hostname "$HOST" "projects/$PROJECT"
glab api --hostname "$HOST" "projects/$PROJECT/pipelines?per_page=100" | jq '...'
glab api --hostname "$HOST" --paginate --output ndjson "projects/$PROJECT/jobs" | jq '...'
glab api --hostname "$HOST" graphql -f 'query=query { currentUser { username } }'
git clone "$SSH_REPO" "$DESTINATION"
glab ci list --repo "$SSH_REPO" --output json
```

`HOST` is bare, without `https://`. Use `-f/--raw-field` for strings and `-F/--field` for typed
values. Fields select POST by default; pass `-X GET` for read requests with query fields. Use
`--input` for complete JSON and `--form` for multipart uploads. Repository-aware commands receive
the explicit SSH Git URL rather than current-directory inference.

Resolve Git transport once. Keep an explicit user-supplied URL in `GIT_TRANSPORT`. Otherwise inspect
the repository's remotes, select the remote for the target GitLab project, and resolve its URL. A
remote name is selected from repository state rather than assumed:

```bash
if test -z "${GIT_TRANSPORT:-}"; then
  git remote -v
  : "${GIT_REMOTE:?select the target remote from repository context}"
  GIT_TRANSPORT="$(git remote get-url "$GIT_REMOTE")"
fi
```

Before a manual SHA refspec or tag push, fetch through the resolved transport and prove the object is
a local commit:

```bash
git fetch "$GIT_TRANSPORT" "$TARGET_REF"
git cat-file -e "$SHA^{commit}"
git push "$GIT_TRANSPORT" "$SHA:refs/tags/$TAG"
```

Proceed to push only after `git cat-file` exits zero.

Safety boundary: this branch supplies general API mechanics; mutation requires the task-specific
branch that defines its inputs and criterion.

Completion criterion: direct user and project reads identify the intended host/path, and the Git
transport equals the supplied URL or resolved selected remote without printing credentials.

SOURCE: <https://docs.gitlab.com/cli/api/> (accessed 2026-09-22; installed-help and live-request verified)
SOURCE: <https://docs.gitlab.com/cli/> (reviewed 2026-09-22; repository selector installed-help and live verified)
