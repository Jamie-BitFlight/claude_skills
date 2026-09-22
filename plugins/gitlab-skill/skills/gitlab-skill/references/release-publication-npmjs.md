# npmjs.com Publication Adapter

Evidence: **DOCUMENTATION-VERIFIED, NOT LIVE-TESTED**.

Use documented GitLab.com trusted-publishing runner/runtime constraints and `NPM_ID_TOKEN` audience
`npm:registry.npmjs.org`, or a destination-issued granular token with publish permission and the
required unattended 2FA policy. Publish and read back:

```bash
npm publish
npm view "__PACKAGE_NAME__@__PACKAGE_VERSION__" version --registry https://registry.npmjs.org/
```

Define any Release link separately.

Validation gate: apply **Gates G2, G3, G6, and G7**. This destination is outside G8.

SOURCE: <https://docs.npmjs.com/trusted-publishers/> (accessed 2026-09-22; documentation-verified, not live-tested)
