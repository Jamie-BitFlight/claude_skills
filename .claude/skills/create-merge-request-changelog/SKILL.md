---
name: create-merge-request-changelog
description: Analyze git branches and generate structured MR/PR descriptions with domain-based change categorization — bug fixes, enhancements, technical debt, documentation, testing, build/CI, and non-functional changes. Use when preparing merge request descriptions, pull request bodies, writing changelogs from git diffs, documenting branch changes, or generating release notes. Works with GitHub and GitLab without requiring JIRA or issue tracker integration.
argument-hint: '[base-branch] [head-branch]'
---

# Create Merge Request Changelog

Generate comprehensive, business-focused merge request descriptions by analyzing git changes. This skill adapts the structured analysis approach from JIRA release notes to work purely with git data.

## Quick Start

```bash
# Analyze current branch against main
/create-merge-request-changelog

# Analyze specific branch
/create-merge-request-changelog feature/new-auth

# Analyze specific branch against custom target
/create-merge-request-changelog feature/new-auth develop

# Analyze specific commit range
/create-merge-request-changelog abc123f def456g
```

## Workflow

### Option A: From Git Branch (Most Common)

#### Step 1: Extract Git Data

Resolve each executable to its absolute path beneath this loaded skill's `scripts/` directory, then invoke it while retaining the target project's current working directory. Do not change into the skill directory.

```bash
uv run "$CHANGELOG_SCRIPT/analyze_git_changes.py" [base_ref] [head_ref] [output_dir]
```

```bash
# Current target branch versus main; output defaults to the target project's current directory.
uv run "$CHANGELOG_SCRIPT/analyze_git_changes.py"

# Specific target-project branch comparison written to a dedicated directory.
uv run "$CHANGELOG_SCRIPT/analyze_git_changes.py" develop feature/new-auth ./mr-analysis
```

The analysis writes `commits_oneline.txt`, `commits_detailed.txt`, `changes.diff`, `changes_stat.txt`, `changed_files.txt`, `changes_numstat.txt`, `summary.json`, and `summary.txt` to the selected directory.

### Option B: From an Existing GitLab MR

Fetch GitLab metadata from the target repository with the absolute packaged executable:

```bash
uv run "$CHANGELOG_SCRIPT/fetch_gitlab_mr.py" <mr-id> [--output OUTPUT_FILE] [--include-diff|--no-diff]
```

```bash
uv run "$CHANGELOG_SCRIPT/fetch_gitlab_mr.py" 123 --output ./mr-metadata.json
uv run "$CHANGELOG_SCRIPT/fetch_gitlab_mr.py" !123 --no-diff
uv run "$CHANGELOG_SCRIPT/fetch_gitlab_mr.py" https://gitlab.com/org/project/-/merge_requests/123
```

### Step 2: Analyze Changes with AI

Read `references/analysis_prompts.md`, provide the selected extraction output, and save the categorized JSON for the formatter.

### Step 3: Format MR Description

The formatter requires the analysis JSON as a positional argument. It writes `mr_description.md` by default; use `--output` to select a file and `--no-preview` to omit the JSON result's description field.

```bash
uv run "$CHANGELOG_SCRIPT/format_mr_description.py" <analysis-json> [--output OUTPUT_FILE] [--preview|--no-preview]
```

```bash
uv run "$CHANGELOG_SCRIPT/format_mr_description.py" ./mr-analysis/categorized.json --output ./MR_DESCRIPTION.md --no-preview
```

The formatter preserves every supplied file path in its output.

### Step 4: Use the Description

Use the generated Markdown file with the hosting CLI:

```bash
glab mr create --fill --description "$(cat ./MR_DESCRIPTION.md)"
gh pr create --fill --body-file ./MR_DESCRIPTION.md
```

## Change Categorization Guide

### Bug Fixes 🐛

**Indicators:**
- Commit keywords: "fix", "bug", "issue", "correct", "resolve"
- Diff patterns: Added error handling, validation, defensive checks

**What to capture:**
- What was broken
- How it's now fixed
- Who/what was affected
- Migration steps if behavior changed

### Enhancements ✨

**Indicators:**
- Commit keywords: "feat", "add", "improve", "enhance", "implement"
- Diff patterns: New functions/classes, expanded APIs, additional features

**What to capture:**
- New capability added
- Benefits to users/developers
- How to use it
- API additions or changes

### Technical Debt 🏗️

**Indicators:**
- Commit keywords: "refactor", "cleanup", "simplify", "optimize"
- Diff patterns: Code reorganization, reduced duplication, dependency updates

**What to capture:**
- Why refactoring was needed
- What changed internally
- How it improves maintainability/performance
- Developer-facing improvements

### Documentation 📚

**Indicators:**
- File patterns: `*.md`, `*.rst`, README, docs/
- Diff patterns: Only documentation files or comments changed

**What to capture:**
- What documentation was added/updated
- Where to find it
- Why it helps users/developers

### Testing 🧪

**Indicators:**
- File patterns: `test_*.py`, `*.spec.js`, `tests/`, `__tests__/`
- Commit keywords: "test", "coverage", "spec"

**What to capture:**
- What's now tested
- Test type (unit/integration/e2e)
- Coverage improvements

### Build & CI 🔧

**Indicators:**
- File patterns: `.github/workflows/`, `.gitlab-ci.yml`, `Dockerfile`, build scripts
- Commit keywords: "ci", "build", "deploy", "docker"

**What to capture:**
- Build/deployment changes
- Workflow improvements
- Developer experience enhancements

### Non-Functional 🧹

**Indicators:**
- Commit keywords: "chore", "style", "format", "lint"
- Diff patterns: Whitespace, formatting, import ordering, minor config

**What to capture:**
- Type (formatting/linting/config/deps)
- Brief description
- Files affected

## Breaking Changes Detection

Automatically detect and highlight breaking changes:

**Detection patterns:**
- Commit messages: "BREAKING CHANGE", "breaking:", "incompatible"
- API changes: Removed public functions, changed signatures
- Configuration: Required new environment variables
- Database: Schema migrations, data migrations

**Required information:**
- What changed and why it breaks compatibility
- Migration steps for users
- Affected APIs or components
- Commit references

## Advanced Usage

### Custom Component Mapping

Map files to logical components for better organization:

```json
{
  "src/auth/*": "Authentication",
  "src/api/*": "API Layer",
  "src/database/*": "Data Layer",
  "tests/*": "Test Suite",
  "docs/*": "Documentation"
}
```

### Conventional Commits Integration

The skill automatically recognizes conventional commit prefixes:

- `fix:` → Bug Fixes
- `feat:` → Enhancements
- `refactor:` → Technical Debt
- `docs:` → Documentation
- `test:` → Testing
- `chore:` → Non-Functional
- `ci:` → Build & CI
- `perf:` → Performance (Enhancement with perf tag)
- `style:` → Non-Functional (formatting)

### GitLab/GitHub CLI Integration

Use with GitLab or GitHub CLI tools:

```bash
# Generate description and create GitLab MR
/create-merge-request-changelog
# ... Copy output to clipboard ...
glab mr create --fill --description "$(pbpaste)"

# Generate description and create GitHub PR
/create-merge-request-changelog
# ... Save output to file ...
gh pr create --fill --body-file /tmp/mr-description.md
```

## Example Output

```markdown
# feat: Add user authentication with JWT and refresh tokens

## Summary

This merge request implements a complete user authentication system using JWT tokens with refresh token rotation. The implementation includes password hashing with bcrypt, token expiration handling, and secure session management.

## Statistics

- **Commits**: 12
- **Files Changed**: 18
- **Lines Added**: 1,247
- **Lines Deleted**: 89

## Changes by Category

### ✨ Enhancements

- **JWT-based authentication system with refresh token rotation**
  - **Feature:** Complete authentication flow with access tokens (15min) and refresh tokens (7 days)
  - **Benefits:** Secure, stateless authentication with automatic token refresh for better UX
  - **Usage:** POST /api/auth/login with credentials, use returned access token in Authorization header
  - **Files:** `src/auth/jwt_service.py`, `src/auth/token_store.py`, `src/api/auth_routes.py`
  - **Technical Details:** Uses RS256 algorithm, tokens stored in Redis, automatic cleanup of expired tokens

- **Password strength validation and bcrypt hashing**
  - **Feature:** Enforces strong passwords (min 12 chars, mixed case, numbers, symbols) with bcrypt hashing
  - **Benefits:** Prevents weak passwords and protects against rainbow table attacks
  - **Usage:** Automatic validation on user registration and password changes
  - **Files:** `src/auth/password_validator.py`, `src/models/user.py`

### 🧪 Testing

- **Comprehensive authentication test suite**: Added 47 unit tests and 12 integration tests covering all auth flows
  - **Type:** unit, integration
  - **Files:** `tests/unit/test_jwt_service.py`, `tests/integration/test_auth_flow.py`

### 📚 Documentation

- **Authentication API documentation with examples**: Complete API docs with curl examples and error codes
  - **Location:** `docs/api/authentication.md`, added to main README
  - **Importance:** Enables developers to integrate authentication without trial-and-error

## Components Affected

- **Authentication**: Complete new authentication system
- **API Layer**: New /api/auth endpoints
- **User Model**: Added password hashing and token tracking
- **Database**: New refresh_tokens table

## Breaking Changes ⚠️

- **User model now requires password hashing**
  - **Migration:** Run `python scripts/migrate_passwords.py` to hash existing plaintext passwords
  - **Affected:** `src/models/user.py`, all user creation code
  - **Commits:** abc123f, def456g

---

*Generated by Claude Code `/create-merge-request-changelog` skill*
```

## Tips for Best Results

1. **Use descriptive commit messages**: The AI analysis works better with clear commit messages
2. **Follow conventional commits**: Helps with automatic categorization
3. **Break up large MRs**: Smaller, focused changes generate clearer descriptions
4. **Review and edit**: The AI-generated description is a starting point - edit for your specific context
5. **Include context**: Add project-specific details or link to related issues/docs

## Troubleshooting

### Issue: Analysis script fails

**Check:**
- Are you in a git repository?
- Does the base branch exist?
- Are there commits between base and head?

**Solution:**
```bash
git rev-parse --git-dir  # Verify git repo
git branch -a | grep <branch-name>  # Verify branch exists
git log <base>..<head>  # Verify commits exist
```

### Issue: Too many files in diff

**Solution:** Use filters to focus analysis:
```bash
# Exclude generated files
git diff <base>..<head> -- . ':(exclude)dist/*' ':(exclude)*.lock'
```

### Issue: AI categorization incorrect

**Solution:** The analysis is based on patterns - you can:
- Override categories manually in the final description
- Improve commit messages for future MRs
- Add project-specific detection patterns to the prompts

## Complete Workflow Example

```bash
# Keep the target repository cwd; the packaged path is absolute.
uv run "$CHANGELOG_SCRIPT/analyze_git_changes.py" main feature/auth-system /tmp/analysis

# Analyze /tmp/analysis with references/analysis_prompts.md and save categorized JSON.

# Format the categorized JSON and create a GitLab MR.
uv run "$CHANGELOG_SCRIPT/format_mr_description.py" /tmp/analysis/categorized.json --output /tmp/mr-desc.md --no-preview
glab mr create --fill --description "$(cat /tmp/mr-desc.md)"
```

## CLI Scripts Reference

Resolve `CHANGELOG_SCRIPT` to this loaded skill's absolute `scripts` directory; retain the target project's cwd for every invocation.

| Script | Invocation |
| --- | --- |
| `analyze_git_changes.py` | `[BASE_REF] [HEAD_REF] [OUTPUT_DIR]`; defaults: `main`, `HEAD`, current directory |
| `fetch_gitlab_mr.py` | `MR_ID [--output OUTPUT_FILE] [--include-diff|--no-diff]`; default output: `mr_data.json` |
| `format_mr_description.py` | `ANALYSIS_JSON [--output OUTPUT_FILE] [--preview|--no-preview]`; default output: `mr_description.md` |

Run each absolute script path with `--help` to inspect the installed CLI before using an uncommon option. No root forwarding shim is required or supported.

## Resources

- `scripts/analyze_git_changes.py` — Git extraction CLI
- `scripts/fetch_gitlab_mr.py` — GitLab MR retrieval CLI
- `scripts/format_mr_description.py` — Markdown formatter CLI
- `scripts/README.md` — complete CLI reference
- `references/analysis_prompts.md` — categorization and formatting prompts
- `references/output_template.md` — output structure

## Daily Releases

Use `/daily-releases` to create AI-analyzed GitHub Releases with this extraction and formatting pipeline.
