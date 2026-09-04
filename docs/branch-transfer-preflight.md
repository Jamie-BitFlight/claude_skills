# Branch-Transfer Preflight

1. Before branch switching, selective checkout or cherry-pick, stash cleanup, or source-branch
   deletion, run
   `uv run scripts/audit_branch_transfer.py --source <source-ref> --base <base-ref> --target <target-ref> --manifest <manifest.json>`.
2. Build the compact JSON manifest using the schema in
   `uv run scripts/audit_branch_transfer.py --help`; record each source-only commit and changed
   path as transferred, intentionally excluded with a non-empty reason, or preserved by a named
   recovery ref.

Complete the operation only when the guard emits `{"ok":true}`: the manifest accounts for every
source-only commit and changed path.
