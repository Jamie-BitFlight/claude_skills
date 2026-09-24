# Marketplaces and Distribution

Read this reference when creating `.claude-plugin/marketplace.json`, selecting a source type,
configuring enterprise restrictions, or distributing private plugins.

## Marketplace Shape

```json
{
  "name": "company-tools",
  "owner": {"name": "DevTools Team"},
  "plugins": [
    {"name": "formatter", "source": "./plugins/formatter"},
    {"name": "deploy", "source": {"source": "github", "repo": "company/deploy"}}
  ]
}
```

`name`, `owner`, and `plugins` are required. Anthropic reserves its official marketplace names;
validate the current list against the primary marketplace documentation rather than caching it.

## Sources

- Relative sources work when the marketplace itself is acquired through Git; they do not resolve
  from a direct URL to `marketplace.json`.
- GitHub sources use `repo`, with optional `ref` and full 40-character `sha`.
- Generic Git sources use an HTTPS or SSH `url`, with optional `ref` and `sha`.
- Archive sources require HTTPS, reject loopback/link-local/cloud-metadata hosts, cap archives at
  256 MiB, and may verify `sha256`. The plugin manifest must be at the archive root or under one
  top-level directory.
- Marketplace-relative paths stay below the marketplace root and cannot contain `../`.

## Enterprise and Private Sources

Use `extraKnownMarketplaces` and `enabledPlugins` in project settings to prompt teams toward a
marketplace and default plugins. Managed `strictKnownMarketplaces` controls allowed sources:
undefined permits additions, `[]` blocks additions, and a list allows exact sources or declared
host patterns. Validation occurs before network or filesystem access.

Manual Git installation uses existing credential helpers. Background updates use provider tokens
such as `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GL_TOKEN`, or `BITBUCKET_TOKEN`.

SOURCE: [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) and [Plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-24)
