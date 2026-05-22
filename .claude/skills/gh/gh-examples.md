**Repository**: `Jamie-BitFlight/claude_skills`

---

## Pull Requests

```bash
# List open PRs
gh pr list -R Jamie-BitFlight/claude_skills

# View PR details
gh pr view <number> -R Jamie-BitFlight/claude_skills

# Check PR CI status
gh pr checks <number> -R Jamie-BitFlight/claude_skills

# Create PR
gh pr create -R Jamie-BitFlight/claude_skills --title "title" --body "body"

# View PR comments
gh api repos/Jamie-BitFlight/claude_skills/pulls/<number>/comments
```

## Issues

```bash
# List issues
gh issue list -R Jamie-BitFlight/claude_skills

# List by label
gh issue list -R Jamie-BitFlight/claude_skills --label "priority:p1" --state open

# Create issue with labels and milestone
gh issue create -R Jamie-BitFlight/claude_skills \
  --title "feat: add feature X" \
  --label "priority:p1" --label "type:feature" \
  --milestone "v1.0"

# View issue
gh issue view <number> -R Jamie-BitFlight/claude_skills

# Close issue with comment
gh issue close <number> -R Jamie-BitFlight/claude_skills --comment "Implemented in PR #N"

# Edit labels on issue
gh issue edit <number> -R Jamie-BitFlight/claude_skills \
  --add-label "status:in-progress" \
  --remove-label "status:needs-grooming"
```

## Labels

```bash
# List all labels
gh label list -R Jamie-BitFlight/claude_skills

# Create label
gh label create "priority:p1" --color "E99695" \
  --description "High priority" -R Jamie-BitFlight/claude_skills

# Setup full label taxonomy (automation script)
uv run .claude/skills/gh/scripts/github_project_setup.py labels \
  --repo Jamie-BitFlight/claude_skills
```

## Projects V2

```bash
# List projects
gh project list --owner Jamie-BitFlight

# Create project
gh project create --owner Jamie-BitFlight --title "Backlog"

# Add issue to project
gh project item-add 1 --owner Jamie-BitFlight \
  --url https://github.com/Jamie-BitFlight/claude_skills/issues/42

# Full project setup (automation script)
uv run .claude/skills/gh/scripts/github_project_setup.py setup \
  --repo Jamie-BitFlight/claude_skills
```

## Milestones

`gh` has no native `milestone` subcommand — use `gh api` with the REST endpoint:

```bash
# List milestones
gh api repos/Jamie-BitFlight/claude_skills/milestones

# Create milestone
gh api repos/Jamie-BitFlight/claude_skills/milestones \
  -X POST -f title="v1.0" -f due_on="2026-03-31T00:00:00Z"

# Assign milestone to issue
gh api repos/Jamie-BitFlight/claude_skills/issues/42 \
  -X PATCH -F milestone=1
```

## Workflow Runs

```bash
# List recent runs
gh run list -R Jamie-BitFlight/claude_skills --limit 5

# View specific run
gh run view <run-id> -R Jamie-BitFlight/claude_skills

# View failed job logs
gh run view <run-id> -R Jamie-BitFlight/claude_skills --log-failed
```

## Releases

```bash
# List releases
gh release list -R Jamie-BitFlight/claude_skills

# View latest release
gh release view --repo Jamie-BitFlight/claude_skills
```

## API (Direct)

```bash
# GET request
gh api repos/Jamie-BitFlight/claude_skills

# POST with fields
gh api repos/Jamie-BitFlight/claude_skills/issues -f title="Bug" -f body="Details"

# GraphQL
gh api graphql -f query='{ viewer { login } }'

# Paginated results
gh api repos/Jamie-BitFlight/claude_skills/contributors --paginate
```

## Repository

```bash
# Clone
gh repo clone Jamie-BitFlight/claude_skills

# View repo info
gh repo view -R Jamie-BitFlight/claude_skills
```

## Output Formatting

```bash
# JSON output
gh pr list -R Jamie-BitFlight/claude_skills --json number,title,state

# JQ filtering
gh pr list -R Jamie-BitFlight/claude_skills --json number,title --jq '.[].title'

# Template formatting
gh pr list -R Jamie-BitFlight/claude_skills --json number,title \
  --template '{{range .}}#{{.number}} {{.title}}{{"\n"}}{{end}}'
```
