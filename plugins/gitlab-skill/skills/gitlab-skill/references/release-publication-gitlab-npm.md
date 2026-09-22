# GitLab npm Publication Adapter

Evidence: **DOCUMENTATION-VERIFIED, NOT LIVE-TESTED**.

Create a runtime `.npmrc` for
`https://${CI_SERVER_HOST}/api/v4/projects/${CI_PROJECT_ID}/packages/npm/`, set that registry's
`_authToken` to `${CI_JOB_TOKEN}`, then publish and read back:

```bash
npm publish
npm view "__PACKAGE_NAME__@__PACKAGE_VERSION__" version \
  --registry "https://${CI_SERVER_HOST}/api/v4/projects/${CI_PROJECT_ID}/packages/npm/"
```

Define durable-link authorization separately.

Apply the composition, tag, and per-destination read-back
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://docs.gitlab.com/user/packages/npm_registry/> (accessed 2026-09-22; documentation-verified, not live-tested)
