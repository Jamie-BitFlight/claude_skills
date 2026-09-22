# glab Merge Request Command Composition

Evidence: exact non-interactive forms live verified in sandbox merge requests `!7` through `!10`.

```bash
glab mr create --repo "$REPO" \
  --source-branch "$SOURCE_BRANCH" --target-branch "$TARGET_BRANCH" \
  --title "$TITLE" --description "$DESCRIPTION" \
  --remove-source-branch --yes
glab mr merge "$MR_IID" --repo "$REPO" --yes --remove-source-branch
```

Supply every create input as a flag. Obtain the IID from command/API output. `mr merge` accepts an
IID or branch positionally. For a scratch-clone commit, keep identity command-local:

```bash
git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" commit -m "$MESSAGE"
```

Safety boundary: compose these mutation commands from resolved inputs; execution remains an explicit
operator action unless the user separately authorizes it.

Completion criterion: command text identifies repository, source/target, title/description, and IID
without prompts or hard-coded sandbox identifiers.

SOURCE: <https://docs.gitlab.com/cli/mr/create/> (accessed 2026-09-22; live verified in sandbox MRs `!7` through `!10`)
SOURCE: <https://docs.gitlab.com/cli/mr/merge/> (accessed 2026-09-22; live verified in sandbox MRs `!7` through `!10`)
