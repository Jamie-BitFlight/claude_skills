# GitLab MR provider facts

Read for GitLab MRs. Bind the MR IID to its project and host; resolve ambiguous targets before acting.

- System notes are provider metadata. Named approvers and explicit review signals are inputs; zero required approvals does not establish an actor's approval.
- GitLab has no established equivalent to GitHub's Codex-specific approval convention.
- Replies use stable discussion references; top-level feedback uses MR notes. Some discussions cannot be resolved, so retain the confirmed response and report resolution capability accurately.
- Collect resolved history and relevant approval signals when assessing review patterns. Connected tools or `glab` supply their own invocation details.

Provider documentation: [glab API](https://docs.gitlab.com/cli/api/), [discussions](https://docs.gitlab.com/api/discussions/), [notes](https://docs.gitlab.com/api/notes/), [approvals](https://docs.gitlab.com/api/merge_request_approvals/).
