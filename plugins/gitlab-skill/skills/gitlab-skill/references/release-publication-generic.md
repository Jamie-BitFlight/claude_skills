# GitLab Generic Publication Adapter

Evidence: **LIVE-VERIFIED** publication and read-back; the reusable component is derived from that
evidence.

Include `assets/release-components/templates/generic-package.yml` from the dedicated component
project. Pass the consumer build through the `needs` input and identify its artifact with typed
inputs. The component uploads the artifact with `CI_JOB_TOKEN`. Include the separate
`gitlab-release` component once for the complete lifecycle.

The component defaults package name to `CI_PROJECT_NAME`; package version is `CI_COMMIT_TAG`;
project and API coordinates use `CI_PROJECT_ID` and `CI_API_V4_URL`. Artifact path and name remain
explicit inputs because the component does not own the project build.

Apply the structure, composition, tag, and destination
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://docs.gitlab.com/user/packages/generic_packages/> (accessed 2026-09-22; publication and read-back live verified twice)
