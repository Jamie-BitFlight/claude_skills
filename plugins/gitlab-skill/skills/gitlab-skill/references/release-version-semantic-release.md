# semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with semantic-release `25.0.9`; generalized assets are
**DERIVED + CI-LINT-VERIFIED**.

Copy `assets/release-playbook/semantic-release.gitlab-ci.yml` and `.releaserc.cjs`. The environment-
aware config requires `CI_DEFAULT_BRANCH` and the base-provided `RELEASE_TAG_PREFIX`, then derives
`tagFormat`. Resolve immutable Node image digest and tool version. Keep only commit analysis so the tag
pipeline owns notes, build, publication, and Release creation.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git in the selected image;
- protected Git credential exposed as `GL_TOKEN` only in the version job;
- `CI_DEFAULT_BRANCH` present and the resolved prefix/regex/wildcard contract aligned; and
- successful no-release output when no configured commit warrants release.

## First-Release Forecast

Before labeling a planned main push no-release, fetch complete history/tags, identify the latest tag
matching the configured format, and inspect the full analyzed commit range. With no matching tag,
the range is the complete relevant history; a docs-only setup commit does not imply no-release when
older `feat:` or `fix:` commits remain in that range.

```bash
git fetch --tags "$GIT_TRANSPORT" "$DEFAULT_BRANCH"
LATEST_MATCHING_TAG="$(git for-each-ref --count=1 --sort=-version:refname \
  --format='%(refname:short)' "refs/tags/$TAG_GLOB")"
if test -n "$LATEST_MATCHING_TAG"; then
  git log --oneline "$LATEST_MATCHING_TAG..FETCH_HEAD"
else
  git log --oneline "FETCH_HEAD"
fi
npx --yes semantic-release@__SEMANTIC_RELEASE_VERSION__ --dry-run
```

Resolve `GIT_TRANSPORT` through [API and Repository Selection](./glab-api-and-repository.md) before
this forecast.

The verified dry run performs release analysis without creating the tag or Release. Run it from a
checkout satisfying the configured release branch. A candidate-branch dry run is not equivalent to
future merged default-branch history; report that distinction and forecast the prospective complete
range rather than converting candidate output into a main outcome claim.

Validation gate: apply **Gates G2, G3, and G5** from the universal lifecycle.

SOURCE: <https://semantic-release.org/foundation/plugins/> (accessed 2026-09-22; semantic-release `25.0.9` behavior live verified)
SOURCE: <https://semantic-release.gitbook.io/semantic-release/usage/configuration#dryrun> (accessed 2026-09-22; dry-run behavior documentation-verified)
