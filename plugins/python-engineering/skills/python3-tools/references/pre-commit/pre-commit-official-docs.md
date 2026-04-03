# Pre-commit Official Documentation References

Complete reference links for pre-commit framework official documentation.

## Official Documentation URLs

### Primary Documentation

| Resource                  | URL                                                                | Description                    |
| ------------------------- | ------------------------------------------------------------------ | ------------------------------ |
| Official Site             | <https://pre-commit.com/>                                          | Main documentation hub         |
| GitHub Repository         | <https://github.com/pre-commit/pre-commit>                         | Source code and issue tracking |
| Creating New Hooks        | <https://pre-commit.com/#creating-new-hooks>                       | Hook development guide         |
| Supported Git Hooks       | <https://pre-commit.com/#supported-git-hooks>                      | Complete stage reference       |
| Confining Hooks to Stages | <https://pre-commit.com/#confining-hooks-to-run-at-certain-stages> | Stage configuration            |
| Command Line Interface    | <https://pre-commit.com/#command-line-interface>                   | CLI reference                  |

### Git Hooks Documentation

| Resource           | URL                                                     | Description                           |
| ------------------ | ------------------------------------------------------- | ------------------------------------- |
| Git Hooks Overview | <https://git-scm.com/docs/githooks>                     | Official git hooks documentation      |
| prepare-commit-msg | <https://git-scm.com/docs/githooks#_prepare_commit_msg> | prepare-commit-msg hook specification |
| commit-msg         | <https://git-scm.com/docs/githooks#_commit_msg>         | commit-msg hook specification         |
| pre-commit         | <https://git-scm.com/docs/githooks#_pre_commit>         | pre-commit hook specification         |
| pre-push           | <https://git-scm.com/docs/githooks#_pre_push>           | pre-push hook specification           |

## Configuration Schema References

### .pre-commit-config.yaml Schema

Complete schema specification from official documentation:

- Top-level properties: <https://pre-commit.com/#pre-commit-configyaml---top-level>
- Repository mapping: <https://pre-commit.com/#pre-commit-configyaml---repos>
- Hook configuration: <https://pre-commit.com/#config-hooks>

### .pre-commit-hooks.yaml Schema

Hook definition schema for hook authors:

- Hook definition properties: <https://pre-commit.com/#creating-new-hooks>
- Language support: <https://pre-commit.com/#supported-languages>
- Arguments and entry points: <https://pre-commit.com/#arguments-pattern-in-hooks>

## Language Support

| Language | Documentation URL                |
| -------- | -------------------------------- |
| Python   | <https://pre-commit.com/#python> |
| Node     | <https://pre-commit.com/#node>   |
| Ruby     | <https://pre-commit.com/#ruby>   |
| Rust     | <https://pre-commit.com/#rust>   |
| Go       | <https://pre-commit.com/#golang> |
| Docker   | <https://pre-commit.com/#docker> |
| System   | <https://pre-commit.com/#system> |

## CLI Commands

### Installation Commands

- `pre-commit install`: <https://pre-commit.com/#pre-commit-install>
- `pre-commit install-hooks`: <https://pre-commit.com/#pre-commit-install-hooks>
- `pre-commit uninstall`: <https://pre-commit.com/#pre-commit-uninstall>

### Execution Commands

- `pre-commit run`: <https://pre-commit.com/#pre-commit-run>
- `pre-commit autoupdate`: <https://pre-commit.com/#pre-commit-autoupdate>
- `pre-commit clean`: <https://pre-commit.com/#pre-commit-clean>
- `pre-commit gc`: <https://pre-commit.com/#pre-commit-gc>

### Testing Commands

- `pre-commit try-repo`: <https://pre-commit.com/#pre-commit-try-repo>
- `pre-commit sample-config`: <https://pre-commit.com/#pre-commit-sample-config>
- `pre-commit validate-config`: <https://pre-commit.com/#pre-commit-validate-config>
- `pre-commit validate-manifest`: <https://pre-commit.com/#pre-commit-validate-manifest>

## Environment Variables

| Variable                        | Documentation URL                                     | Purpose                                         |
| ------------------------------- | ----------------------------------------------------- | ----------------------------------------------- |
| `SKIP`                          | <https://pre-commit.com/#temporarily-disabling-hooks> | Skip specific hooks                             |
| `PRE_COMMIT_HOME`               | <https://pre-commit.com/#environment-variables>       | Override cache location                         |
| `PRE_COMMIT_COMMIT_MSG_SOURCE`  | Git documentation                                     | Commit message source (prepare-commit-msg only) |
| `PRE_COMMIT_COMMIT_OBJECT_NAME` | Git documentation                                     | Commit SHA (prepare-commit-msg only)            |

## Hook Repositories

### Official Hook Collections

| Repository       | URL                                              | Description                |
| ---------------- | ------------------------------------------------ | -------------------------- |
| pre-commit-hooks | <https://github.com/pre-commit/pre-commit-hooks> | Standard hooks collection  |
| mirrors-prettier | <https://github.com/pre-commit/mirrors-prettier> | Prettier formatter         |
| mirrors-eslint   | <https://github.com/pre-commit/mirrors-eslint>   | ESLint linter              |
| pygrep-hooks     | <https://github.com/pre-commit/pygrep-hooks>     | Python-specific grep hooks |

### Third-Party Hook Collections

| Repository      | URL                                                           | Description            |
| --------------- | ------------------------------------------------------------- | ---------------------- |
| black           | <https://github.com/psf/black>                                | Python code formatter  |
| ruff-pre-commit | <https://github.com/astral-sh/ruff-pre-commit>                | Ruff Python linter     |
| commitlint      | <https://github.com/alessandrojcm/commitlint-pre-commit-hook> | Commit message linting |

## Version History

### Version 3.2.0+ Changes

- Stage names match git hook names directly
- Deprecated `commit`, `push`, `merge-commit` stage aliases
- Introduction of `pre-rebase` stage support

Reference: <https://github.com/pre-commit/pre-commit/releases/tag/v3.2.0>

### Version 4.0.0+ Changes

Reference: <https://github.com/pre-commit/pre-commit/releases/tag/v4.0.0>

## Troubleshooting Resources

| Issue                           | Documentation URL                                                            |
| ------------------------------- | ---------------------------------------------------------------------------- |
| Hooks not running               | <https://pre-commit.com/#i-installed-pre-commit-but-the-hooks-arent-running> |
| Performance optimization        | <https://pre-commit.com/#improving-performance>                              |
| CI/CD integration               | <https://pre-commit.com/#usage-in-continuous-integration>                    |
| Hook development best practices | <https://pre-commit.com/#developing-hooks-interactively>                     |

## Community Resources

| Resource       | URL                                                     | Description                      |
| -------------- | ------------------------------------------------------- | -------------------------------- |
| Discussions    | <https://github.com/pre-commit/pre-commit/discussions>  | Community Q&A                    |
| Issues         | <https://github.com/pre-commit/pre-commit/issues>       | Bug reports and feature requests |
| Stack Overflow | <https://stackoverflow.com/questions/tagged/pre-commit> | Community support                |

## Related Tools

| Tool           | URL                                      | Relationship                     |
| -------------- | ---------------------------------------- | -------------------------------- |
| pre-commit.ci  | <https://pre-commit.ci/>                 | Hosted CI service for pre-commit |
| detect-secrets | <https://github.com/Yelp/detect-secrets> | Secret detection hook            |
| commitizen     | <https://github.com/commitizen/cz-cli>   | Interactive commit message tool  |

## Source Attribution

All documentation links reference official pre-commit framework documentation at <https://pre-commit.com/> and official git documentation at <https://git-scm.com/docs/githooks>.

Last verified: 2025-01-15
