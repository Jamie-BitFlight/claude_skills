# Obsolete Steps-to-Functions Migration

Use this mapping only to interpret or migrate existing obsolete configuration.

| Obsolete | Current |
|---|---|
| CI/CD Steps | GitLab Functions |
| `step:` | `func:` |
| `step.yml` | `func.yml` |
| `${{ step_dir }}` | `${{ func_dir }}` |
| `${{ job.<variable_name> }}` | `${{ vars.<variable_name> }}` |

Current authoring uses only the Current column. After migration, load the core authoring reference
for interface and composition rules.

Completion criterion: active configuration contains current names and no obsolete mapping term.

SOURCE: <https://docs.gitlab.com/ci/functions/#migrate-from-cicd-steps> (accessed 2026-09-21)
