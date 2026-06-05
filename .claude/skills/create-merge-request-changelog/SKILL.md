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

Run the Python CLI to gather commits, diffs, and statistics:

```bash
uv run scripts/analyze_git_changes.py [base_ref] [head_ref] --output-dir /tmp/mr-analysis
```

**Examples:**

```bash
# Current branch vs main (default)
uv run scripts/analyze_git_changes.py

# Specific branch vs develop
uv run scripts/analyze_git_changes.py develop feature/new-auth

# Specific commit range
uv run scripts/analyze_git_changes.py abc123f def456g

# Custom output directory
uv run scripts/analyze_git_changes.py main HEAD --output-dir ./analysis-output
```

**Output files created:**
- `commits_oneline.txt` - Concise commit list
- `commits_detailed.txt` - Full commit messages with metadata
- `changes.diff` - Complete unified diff
- `changes_stat.txt` - Diffstat summary
- `changed_files.txt` - File list with change status (A/M/D)
- `changes_numstat.txt` - Per-file line changes
- `summary.json` - Machine-readable statistics

### Option B: From Existing GitLab MR

#### Step 1: Fetch MR Data

Use the GitLab CLI integration to fetch existing MR data:

```bash
uv run scripts/fetch_gitlab_mr.py <mr-id> --output /tmp/mr-data.json
```

**Examples:**

```bash
# By MR ID
uv run scripts/fetch_gitlab_mr.py 123

# By !notation
uv run scripts/fetch_gitlab_mr.py !123

# By full URL
uv run scripts/fetch_gitlab_mr.py https://gitlab.com/org/project/-/merge_requests/123

# Without diff (faster)
uv run scripts/fetch_gitlab_mr.py 123 --no-diff

# Custom output file
uv run scripts/fetch_gitlab_mr.py 123 --output ./mr-metadata.json
```

**Output:** JSON file with MR metadata, commits, and diffs

### Step 2: Analyze Changes with AI

Load the analysis prompts and use them to categorize changes:

1. **Read the primary analysis prompt** from `references/analysis_prompts.md`
2. **Load the extracted git data** from Step 1 output files
3. **Run the analysis** using the prompt template with your git data
4. **Get structured JSON** with categorized changes

The AI analysis will:
- Categorize changes into domains (bug fixes, enhancements, tech debt, docs, testing, build/CI, non-functional)
- Extract intent from commit messages and diff patterns
- Identify breaking changes and migration requirements
- Determine affected components
- Assess impact on users and developers

### Step 3: Format MR Description

Use the Python formatter to generate polished markdown from AI analysis:

```bash
uv run scripts/format_mr_description.py <analysis-json> --output /tmp/mr-description.md
```

**Examples:**

```bash
# With markdown preview (default)
python scripts/format_mr_description.py analysis.json

# Without preview
python scripts/format_mr_description.py analysis.json --no-preview

# Custom output file
python scripts/format_mr_description.py analysis.json --output ./MR_DESCRIPTION.md

# With custom title
python scripts/format_mr_description.py analysis.json --title "feat: Add authentication system"
```

The formatter automatically:
- Applies templates from `references/output_template.md`
- Formats each category (bug fixes, enhancements, tech debt, etc.)
- Truncates long file lists (>5 files)
- Highlights breaking changes
- Generates deployment notes if needed
- Renders markdown preview with Rich

### Step 4: Use the Description

The final MR description is ready to:
- Copy to clipboard (from preview or file)
- Paste into GitLab/GitHub MR/PR
- Save as documentation
- Use in release notes

**Integration examples:**

```bash
# GitLab MR creation
python scripts/format_mr_description.py analysis.json --output /tmp/mr.md --no-preview
glab mr create --fill --description "$(cat /tmp/mr.md)"

# GitHub PR creation
python scripts/format_mr_description.py analysis.json --output /tmp/pr.md --no-preview
gh pr create --fill --body-file /tmp/pr.md

# Copy to clipboard (macOS)
python scripts/format_mr_description.py analysis.json --no-preview --output - | pbcopy

# Copy to clipboard (Linux)
python scripts/format_mr_description.py analysis.json --no-preview --output - | xclip -selection clipboard
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

## Complete Workflow Examples

### Example 1: New MR from Git Branch

```bash
# 1. Extract git data
python scripts/analyze_git_changes.py main feature/auth-system --output-dir /tmp/analysis

# 2. Analyze with AI (using prompts from references/analysis_prompts.md)
# - Read commits and diffs from /tmp/analysis
# - Categorize changes using the primary analysis prompt
# - Save categorized JSON to /tmp/analysis/categorized.json

# 3. Format into MR description
python scripts/format_mr_description.py /tmp/analysis/categorized.json --output /tmp/mr-desc.md

# 4. Create GitLab MR
glab mr create --fill --description "$(cat /tmp/mr-desc.md)"
```

### Example 2: Update Existing GitLab MR

```bash
# 1. Fetch existing MR data
python scripts/fetch_gitlab_mr.py 123 --output /tmp/mr-data.json

# 2. Analyze with AI (enhance existing description)
# - Read MR metadata from /tmp/mr-data.json
# - Re-analyze commits/diffs with updated prompts
# - Save enhanced JSON to /tmp/enhanced.json

# 3. Format improved description
python scripts/format_mr_description.py /tmp/enhanced.json --output /tmp/updated-mr.md

# 4. Update MR description
glab mr update 123 --description "$(cat /tmp/updated-mr.md)"
```

### Example 3: Quick Analysis for Review

```bash
# Quick preview without saving files
python scripts/analyze_git_changes.py | \
  python scripts/format_mr_description.py --preview
```

## CLI Scripts Reference

### analyze_git_changes.py

Extracts git data between two references.

**Usage:** `python scripts/analyze_git_changes.py [BASE_REF] [HEAD_REF] [OPTIONS]`

**Options:**
- `--output-dir PATH`: Output directory (default: current directory)

**Defaults:** BASE_REF=main, HEAD_REF=HEAD

### fetch_gitlab_mr.py

Fetches GitLab MR data using the python-gitlab API.

**Usage:** `python scripts/fetch_gitlab_mr.py MR_ID [OPTIONS]`

**Options:**
- `--output PATH`: Output JSON file (default: stdout)
- `--no-diff`: Skip diff fetching (faster)

**MR ID formats:** `123`, `!123`, or full URL

### format_mr_description.py

Formats AI analysis into markdown MR description.

**Usage:** `python scripts/format_mr_description.py ANALYSIS_JSON [OPTIONS]`

**Options:**
- `--output PATH`: Output file (default: stdout, `-` for explicit stdout)
- `--title TEXT`: Custom MR title
- `--no-preview`: Skip markdown preview
- `--max-files INT`: Max files to show per change (default: 5)

## CLI Scripts Reference

### analyze_git_changes.py

Extracts git data between two references.

**Usage:** `python scripts/analyze_git_changes.py [BASE_REF] [HEAD_REF] [OPTIONS]`

**Options:**
- `--output-dir PATH`: Output directory (default: current directory)

**Defaults:** BASE_REF=main, HEAD_REF=HEAD

### fetch_gitlab_mr.py

Fetches GitLab MR data using the python-gitlab API.

**Usage:** `python scripts/fetch_gitlab_mr.py MR_ID [OPTIONS]`

**Options:**
- `--output PATH`: Output JSON file (default: stdout)
- `--no-diff`: Skip diff fetching (faster)

**MR ID formats:** `123`, `!123`, or full URL

### format_mr_description.py

Formats AI analysis into markdown MR description.

**Usage:** `python scripts/format_mr_description.py ANALYSIS_JSON [OPTIONS]`

**Options:**
- `--output PATH`: Output file (default: stdout, `-` for explicit stdout)
- `--title TEXT`: Custom MR title
- `--no-preview`: Skip markdown preview
- `--max-files INT`: Max files to show per change (default: 5)

## Resources

- **scripts/analyze_git_changes.py**: Python CLI to extract git data
- **scripts/fetch_gitlab_mr.py**: Python CLI to fetch GitLab MR data via python-gitlab API
- **scripts/format_mr_description.py**: Python CLI to format AI analysis into markdown
- **scripts/README.md**: Comprehensive CLI documentation and examples
- **references/analysis_prompts.md**: AI prompts for categorization and formatting
- **references/output_template.md**: MR description template structure

## Daily Releases

Use the `/daily-releases` skill to create AI-analyzed GitHub Releases for every day with commits. It uses this skill's `analyze_git_changes.py`, `analysis_prompts.md`, and `format_mr_description.py` as the rendering pipeline.
