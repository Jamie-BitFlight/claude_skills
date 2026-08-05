# Already Implemented Check (Step 2.1)

Before planning work, verify the described feature/fix hasn't already been implemented:

1. **Search for commits and merged PRs matching the item's topic** (use keywords from the title):

   ```bash
   git log --oneline --all -30 --grep="{keyword from title}"
   git log --oneline --all -30 --merges --grep="{keyword from title}"
   ```

2. **Spot-check the codebase** — read the file(s) at the suggested location and verify whether the described behavior already exists.

If evidence shows the work is already done:

- Resolve via the CLI:

  ```bash
  uv run plugins/development-harness/sam_schema/cli.py backlog resolve \
    --selector "{title}" \
    --summary "Already implemented via PR #{pr} / commit {sha}"
  ```

- Report to the user and stop — no planning needed.

When <mode/> is `auto`: log `[AUTO] Work already implemented — closing #{N} with evidence: {sha/PR}` and stop.

If no evidence, proceed to [github-sync.md](./github-sync.md) (Step 2.2).
