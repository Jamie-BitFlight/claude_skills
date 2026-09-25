# GitLab Generic Publication Adapter

Apply the publication and read-back observations in [live evidence](./release-live-evidence.md)
only to their recorded revisions; a changed component requires new pipeline evidence.

Include `assets/release-components/templates/generic-package.yml` from the dedicated component
project. Pass the consumer build through the `needs` input and identify its artifact with typed
inputs. Use a curl image providing `cmp`, `mktemp`, and `rm`. The component uploads with
`CI_JOB_TOKEN`, downloads the same package/version/file into a temporary file, and compares it
byte-for-byte with the unchanged build artifact. An upload or read-back error, or different bytes,
fails the publication job; temporary downloads are removed on exit. Keep the separate `gitlab-release`
component dependent on successful publication so Release creation cannot bypass this check.

The component defaults package name to `CI_PROJECT_NAME`; package version is `CI_COMMIT_TAG`;
project and API coordinates use `CI_PROJECT_ID` and `CI_API_V4_URL`. Artifact path and name remain
explicit inputs because the component does not own the project build.

Apply the structure, composition, tag, and destination
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://docs.gitlab.com/user/packages/generic_packages/> (accessed 2026-09-22; publication and read-back live verified twice)
