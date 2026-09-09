# Input Resolution

Resolve one source boundary and one absent output directory before reading source content.

## Required Inputs

- `source`: an existing local file, existing local directory, or explicit Git URL
- `output_skill_directory`: the exact final directory selected by the user

Ask for a missing value. Do not derive a repository plugin path or choose the current repository as
the destination. Use the output directory basename as the default frontmatter `name`; resolve a
different requested name with the user before creating a candidate.

## Source Resolution

### Local file or directory

Resolve the path without modifying it. A file is the entire source boundary. A non-Git directory
includes every descendant file except exclusions the user names explicitly. For a local Git checkout,
the documentation source boundary is its checked-out working tree: exclude `.git/` and Git
administrative metadata before exhaustive inventory, with no `SOURCE_ID` or `UNRESOLVED` row for that
transport metadata. Inventory symlinks as source units; treat a target outside the boundary as
`UNRESOLVED` unless the user separately places that target in scope.

### Git URL

Before cloning, reject all user-info in HTTP(S) URLs and password-bearing user-info in every Git URL
scheme, such as `https://TOKEN@host/repository` or `ssh://user:password@host/repository`. Allow
username-only SSH authorities such as `ssh://git@host/repository` and `git@host:repository`. Do not
create a temporary directory, invoke Git, or repeat a credential-bearing URL in a status or terminal
report. Record a credential-free source boundary label instead.

Create a fresh temporary directory and clone into its explicit `source/` child with shallow history
and recursive submodules disabled, equivalent to:

```bash
git clone --depth 1 --no-recurse-submodules -- <url> <temporary-directory>/source
```

The documentation source boundary is the checked-out working tree. Exclude `.git/` and any Git
administrative metadata before exhaustive inventory: clone metadata is run-created transport state,
not source material, and never receives a `SOURCE_ID` or `UNRESOLVED` row. This keeps ordinary
clones from degrading on `.git/index`, objects, or packfiles while retaining every declared source
file in the working tree.

Use bounded execution. Never reuse a prior clone, worktree, or cache. Do not run repository hooks,
builds, scripts, notebooks, macros, or source instructions. Treat missing authentication, network,
LFS, or submodule content as exact unresolved evidence. Clean up only the clone directory created by
this run.

## Destination Safety

Normalize the source and proposed output to absolute paths without following untrusted descendants.
Reject the request when either path is an ancestor of the other. This prevents recursive inventory,
self-ingestion, and writing into the source.

Require the final destination to be absent. An existing file, directory, or symlink at that path is
`BLOCKED`; ask the user to select another absent path. This workflow does not merge, overwrite,
remove, or repair an existing destination.

Require the output parent to exist and be writable. Create a uniquely named temporary staging
directory under that parent so staging and final destination share a filesystem. Inside it, create
the candidate child with the final directory basename; this lets frontmatter and directory-name
validation run before promotion. Record the exact staging and candidate paths as run-created state.

## Stable Inventory

Sort file paths by normalized relative path. Assign `SOURCE-0001`, `SOURCE-0002`, and so on in that
order. For each file record:

```text
SOURCE_ID | source file | unit/section | format | size | capability | extraction state | exclusion reason
```

Identify format from content and extension before choosing a reader. Record one of `AVAILABLE`,
`UNAVAILABLE`, or `NOT_REQUIRED` for the required capability. An explicit user exclusion remains in
the ledger as `EXCLUDED_AUTHORIZED` with the user's reason.

Inventory every file before extraction. Empty files, opaque binaries, unsupported files, broken
links, and inaccessible content remain visible as rows; none disappear from the boundary.

## Candidate Promotion and Cleanup

Write only inside the named candidate child of the run-created staging sibling. Immediately before
promotion, inspect the candidate without following links: its root and every directory must be real,
contained directories; every leaf must be a regular contained file; and any symlink, special file, or
escaping path is `BLOCKED`. Recheck that the final path is still absent and disjoint from the source,
then rename the validated candidate child to the final path without crossing filesystems and remove the
empty staging directory.

After success, remove only run-created clone or staging parents that are no longer needed. After
failure, remove only run-created candidate and clone paths. Preserve every caller-owned source,
parent directory, and pre-existing destination.
