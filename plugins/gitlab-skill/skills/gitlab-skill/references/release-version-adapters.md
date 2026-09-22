# Version Adapter Index

Select exactly one branch:

- [semantic-release](./release-version-semantic-release.md) - Load when Node-based Conventional
  Commit analysis should calculate and push the tag without a release commit.
- [python-semantic-release](./release-version-python-semantic-release.md) - Load when Python tooling
  should update project version state, push a release commit, and push the tag.

Do not load the sibling implementation after selection.

SOURCE: <https://docs.gitlab.com/ci/> (reviewed 2026-09-22; adapter selection follows the composed lifecycle)
