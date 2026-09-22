# semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with semantic-release `25.0.9`; generalized assets are
**DERIVED + CI-LINT-VERIFIED**.

Copy `assets/release-playbook/semantic-release.gitlab-ci.yml` and `.releaserc.json`. Replace the
actual default branch, exact tag format, immutable Node image digest, and selected tool version.
Keep only commit analysis so the tag pipeline owns notes, build, publication, and Release creation.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git in the selected image;
- protected Git credential exposed as `GL_TOKEN` only in the version job;
- all `.releaserc.json` markers replaced; and
- successful no-release output when no configured commit warrants release.

Validation gate: apply **Gates G2, G3, and G5** from the universal lifecycle.

SOURCE: <https://semantic-release.org/foundation/plugins/> (accessed 2026-09-22; semantic-release `25.0.9` behavior live verified)
