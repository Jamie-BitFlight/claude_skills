# semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with semantic-release `25.0.9`; the reusable component is
derived from that evidence.

Include `assets/release-components/templates/semantic-release-version.yml` from a dedicated
component project. Pass a unique job name, the consumer's version stage and rules, a digest-pinned
Node image, an exact tool version, tag prefix, selected Git remote name, explicit credential-free
repository URL, and the dedicated version environment. It passes the URL as semantic-release's
`repositoryUrl` and keeps only commit analysis so the tag pipeline owns notes, build, publication,
and Release creation.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git in the selected image;
- selected remote exists and the explicit repository URL identifies its release target;
- `CI_DEFAULT_BRANCH` present and the consumer's prefix, regex, and protected wildcard aligned; and
- successful no-release output when no configured commit warrants release.

Apply the exact variable scope and secret-handling boundary from the
[component-project README](../assets/release-components/README.md).

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

Apply the structure, composition, credential, and main
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://semantic-release.org/foundation/plugins/> (accessed 2026-09-22; semantic-release `25.0.9` behavior live verified)
SOURCE: <https://semantic-release.org/usage/configuration/#repositoryurl> (accessed 2026-09-22; explicit repository target)
SOURCE: <https://semantic-release.org/usage/configuration/#dryrun> (accessed 2026-09-22; dry-run behavior documentation-verified)
SOURCE: <https://docs.gitlab.com/ci/environments/#limit-the-environment-scope-of-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/environments/#access-an-environment-for-preparation-or-verification-purposes> (accessed 2026-09-22)
