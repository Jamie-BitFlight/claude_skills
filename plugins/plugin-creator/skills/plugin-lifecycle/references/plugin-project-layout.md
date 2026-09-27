# Plugin project layout and isolation

Apply these product-boundary rules whenever creating, restructuring, or reviewing a plugin. In the claude_skills monorepo, the repository also carries a broader development-policy document; this bundled reference must remain sufficient when plugin-creator is installed without that source repository.

## Design gate

Before implementation, classify every proposed file as either:

- **plugin product**: required to operate, test, validate, or understand this plugin; place it under the plugin;
- **repository development policy**: lint, formatting, type-check policy, shared tooling versions, CI orchestration, or cross-plugin checks; keep it at repository root.

Do not create `plugins/<name>/pyproject.toml` or a plugin-local `uv.lock` merely to make a plugin self-contained. PEP 723 executable entry points own their execution dependencies. The root project owns monorepo development policy.

If the plugin owns pytest tests, require `plugins/<name>/run_pytests.py`. It owns the complete plugin test topology and must run without parent pytest configuration or root PYTHONPATH assumptions. Commit its script lockfile, `run_pytests.py.lock`, created with `uv lock --script run_pytests.py` and refreshed whenever the PEP 723 block changes, so the runner can be run with `uv run --locked --script`.

## Referential-integrity gate

Reject or redesign plugin runtime/test dependencies on repository-root cwd, root helper scripts, source-tree aliases, sibling-plugin implementation, or root PYTHONPATH. A path in documentation may describe repository maintenance and is not by itself a runtime dependency.

## Extraction gate

For a plugin intended to be extractable, verify its product boundary independently from repository policy: copy the plugin directory alone to an empty location and run its validation and `run_pytests.py` there. Do not pre-install standalone-repository scaffolding inside the monorepo plugin.

After extraction, the new standalone repository must recreate this development policy, which the plugin directory does not carry:

1. Python and tool versions.
2. Lint, format, and type-check configuration.
3. Shared pytest markers and policy that the plugin's tests rely on.
4. CI quality gates that apply to the plugin, including running `run_pytests.py`.
5. A repository lockfile, created there. Keep PEP 723 blocks as the executable dependency source; do not add a second runtime dependency list.

When reviewing an existing plugin, report each coupling as one of:

- runtime coupling;
- test coupling;
- development-policy coupling (allowed while in the monorepo);
- explicit external/plugin dependency.

Only the first two violate isolation.
