# Merge Request Changelog Scripts

This directory contains Python CLI scripts for analyzing git changes and generating merge request descriptions. The scripts follow modern Python best practices with Typer CLI framework and Rich terminal output.

## Scripts Overview

### 1. `analyze_git_changes.py`

Extracts commits, diffs, and statistics from git changes between two references.

**Replaces:** The bash script `analyze_git_changes.sh` with a more robust, type-safe Python implementation.

**Features:**
- Extract commit history (oneline and detailed formats)
- Generate unified diffs and statistics
- Calculate lines added/deleted and files changed
- Output both machine-readable JSON and human-readable summaries
- Rich progress indicators and formatted output

**Usage:**
```bash
# Analyze changes from main to HEAD (default)
./analyze_git_changes.py

# Analyze specific branch range
./analyze_git_changes.py develop feature-branch

# Specify output directory
./analyze_git_changes.py main HEAD /tmp/analysis

# Show help
./analyze_git_changes.py --help
```

**Output Files:**
- `commits_oneline.txt` - One-line commit list
- `commits_detailed.txt` - Full commit messages with metadata
- `changes.diff` - Unified diff of all changes
- `changes_stat.txt` - Diffstat summary
- `changed_files.txt` - List of changed files with status (A/M/D)
- `changes_numstat.txt` - Per-file line changes
- `summary.json` - Machine-readable summary
- `summary.txt` - Human-readable summary

### 2. `fetch_gitlab_mr.py`

Fetches merge request metadata and changes from GitLab via the python-gitlab API.

**Features:**
- Extract MR ID from URL or direct ID
- Fetch MR metadata (title, description, author, labels, etc.)
- Retrieve commit list with details
- Optional unified diff inclusion
- Rich formatted output with tables

**Requirements:**
- `GITLAB_TOKEN` or `GITLAB_PRIVATE_TOKEN` environment variable set

**Usage:**
```bash
# Fetch by MR ID
./fetch_gitlab_mr.py 123

# Fetch by !ID notation
./fetch_gitlab_mr.py !456

# Fetch by full URL
./fetch_gitlab_mr.py https://gitlab.com/org/project/-/merge_requests/789

# Specify output file
./fetch_gitlab_mr.py 123 --output custom_name.json

# Exclude diff from output (faster)
./fetch_gitlab_mr.py 123 --no-diff

# Show help
./fetch_gitlab_mr.py --help
```

**Output Format (JSON):**
```json
{
  "id": "123",
  "iid": "45",
  "title": "feat: Add new feature",
  "description": "Detailed description...",
  "state": "opened",
  "source_branch": "feature-branch",
  "target_branch": "main",
  "author": {
    "username": "user",
    "name": "User Name"
  },
  "web_url": "https://gitlab.com/...",
  "labels": ["enhancement", "needs-review"],
  "created_at": "2024-02-04T10:00:00Z",
  "updated_at": "2024-02-04T11:00:00Z",
  "merged_at": null,
  "commits": [
    {
      "sha": "abc123...",
      "title": "feat: Add feature",
      "author": "User Name"
    }
  ],
  "commit_count": 5,
  "has_conflicts": false,
  "work_in_progress": false,
  "diff": "unified diff content..."
}
```

### 3. `format_mr_description.py`

Formats AI-analyzed change data into polished merge request descriptions.

**Features:**
- Parse structured analysis JSON from AI processing
- Apply standardized markdown templates
- Format changes by category (bug fixes, enhancements, etc.)
- Preserve every supplied file path
- Rich markdown preview in terminal

**Usage:**
```bash
# Format analysis with preview
./format_mr_description.py analysis.json

# Specify output file
./format_mr_description.py analysis.json --output custom_mr.md

# Disable preview
./format_mr_description.py analysis.json --no-preview

# Show help
./format_mr_description.py --help
```

**Input Format (JSON):**
```json
{
  "title": "feat: Add authentication system",
  "summary": "High-level overview of changes...",
  "change_categories": {
    "bug_fixes": [
      {
        "title": "Fix race condition in auth flow",
        "description": "What was broken and fix",
        "impact": "User-facing impact",
        "files_affected": ["src/auth.py"],
        "commits": ["abc123"],
        "technical_details": ["Implementation specifics"]
      }
    ],
    "enhancements": [...],
    "tech_debt": [...],
    "documentation": [...],
    "testing": [...],
    "build_ci": [...],
    "non_functional": [...]
  },
  "components_affected": ["auth", "api", "database"],
  "breaking_changes": [...],
  "statistics": {
    "commits": 15,
    "files_changed": 42,
    "lines_added": 1523,
    "lines_deleted": 847
  }
}
```

**Output Format:**
Markdown following the template in `references/output_template.md` with:
- Title and summary
- Statistics table
- Changes organized by category with emoji icons
- Component list
- Breaking changes section (if any)
- Footer with generation attribution

## Dependencies

Each executable declares its PEP 723 dependencies. Run the packaged scripts directly from this directory; if direct execution is unavailable, use `uv run <script-path>`. Do not install dependencies into the target project.

Additional requirements:
- **analyze_git_changes.py**: Git installed and repository context
- **fetch_gitlab_mr.py**: `GITLAB_TOKEN` or `GITLAB_PRIVATE_TOKEN` for live retrieval
- **format_mr_description.py**: valid analysis JSON input

## Design Principles

These scripts follow the **python-cli-enhanced-guide.mdc** patterns:

### Type Safety
- Full type annotations throughout
- Proper exception hierarchy with custom exceptions
- Type-safe subprocess handling

### Rich CLI Experience
- Typer for argument parsing with `Annotated` syntax
- Rich progress indicators during long operations
- Formatted tables for summary display
- Panels for success/error messages
- Markdown rendering for previews

### Error Handling
- Custom exceptions for domain-specific errors
- Clear error messages with actionable guidance
- Graceful KeyboardInterrupt handling
- Proper exit codes (1 for errors, 130 for Ctrl+C)

### Modern Python
- Python 3.11+ features (`|` union types, `from __future__ import annotations`)
- Pathlib for all file operations
- Explicit encoding for text operations
- List/dict comprehensions where appropriate

### Code Quality
- Google-style docstrings
- Separation of concerns (functions do one thing well)
- No defensive try/except blocks (let errors propagate)
- Functional programming patterns where beneficial

## Integration with Skill Workflow

These scripts are designed to work together in the following workflow:

1. **Analyze Changes**: `analyze_git_changes.py` extracts raw git data
2. **AI Processing**: External AI analysis categorizes and understands changes
3. **Format Output**: `format_mr_description.py` creates polished MR description

Alternative workflow with GitLab MR:

1. **Fetch MR Data**: `fetch_gitlab_mr.py` retrieves existing MR metadata
2. **AI Processing**: Analyze MR commits and diffs
3. **Format Output**: `format_mr_description.py` generates updated description

## Testing

Run each packaged executable with `--help` from this directory to inspect its current contract. The GitLab retrieval command requires `GITLAB_TOKEN` or `GITLAB_PRIVATE_TOKEN` for a live request; use its help command for a network-free check.

## Common Patterns

```bash
# Generate analysis. The output directory is positional.
./analyze_git_changes.py main feature-branch /tmp/analysis

# Process with AI (pseudocode).
ai-analyze --input /tmp/analysis/commits_detailed.txt \
           --diff /tmp/analysis/changes.diff \
           --output /tmp/ai-analysis.json

# Format final description.
./format_mr_description.py /tmp/ai-analysis.json --output mr_description.md
```

### Error Handling
All scripts use proper exit codes:
- `0`: Success
- `1`: Error (validation, processing, etc.)
- `130`: User cancelled (Ctrl+C)

### Rich Output Customization
Set environment variable to disable Rich features if needed:
```bash
export NO_COLOR=1  # Disable colors
export TERM=dumb   # Disable Rich formatting
```

## Contributing

When modifying these scripts:
1. Maintain type annotations
2. Update docstrings
3. Follow existing error handling patterns
4. Test with `--help` to verify argument descriptions
5. Ensure Rich output remains accessible (proper fallbacks)

## References

- **Analysis Prompts**: `references/analysis_prompts.md`
- **Output Template**: `references/output_template.md`
- **Python CLI Guide**: `python-cli-enhanced-guide.mdc` (project root)
