# Plugin project layout and isolation

Apply these product-boundary rules whenever creating, restructuring, or reviewing a plugin. In the claude_skills monorepo, the repository also carries a broader development-policy document; this bundled reference must remain sufficient when plugin-creator is installed without that source repository.

## Design gate

Before implementation, classify every proposed file as either:

- **plugin product**: required to operate, test, validate, or understand this plugin; place it under the plugin;
- **repository development policy**: lint, formatting, type-check policy, shared tooling versions, CI orchestration, or cross-plugin checks; keep it at repository root.

Do not create `plugins/<name>/pyproject.toml` or a plugin-local `uv.lock` merely to make a plugin self-contained. PEP 723 executable entry points own their execution dependencies. The root project owns monorepo development policy.

If the plugin owns pytest tests, require `plugins/<name>/run_pytests.py`. It owns the complete plugin test topology and must run without parent pytest configuration or root PYTHONPATH assumptions.

## Referential-integrity gate

Reject or redesign plugin runtime/test dependencies on repository-root cwd, root helper scripts, source-tree aliases, sibling-plugin implementation, or root PYTHONPATH. A path in documentation may describe repository maintenance and is not by itself a runtime dependency.

## Extraction gate

For a plugin intended to be extractable, verify its product boundary independently from repository policy. A future standalone repository replicates the root development-policy template after extraction; do not pre-install that scaffolding inside the monorepo plugin.

When reviewing an existing plugin, report each coupling as one of:

- runtime coupling;
- test coupling;
- development-policy coupling (allowed while in the monorepo);
- explicit external/plugin dependency.

Only the first two violate isolation.
