# Improvement Proposals: OpenBao

**Research entry**: ./research/llm-infrastructure/openbao.md
**Generated**: 2026-03-28
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 5

---

## Deferred Proposals (confidence too low to backlog)

No proposals reached medium or low confidence. All patterns were skipped outright.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| AI Agent Secret Management | Infrastructure deployment pattern — describes deploying OpenBao as a credential source for agents. No local skill, agent, or workflow file has a "credential source" or "secret retrieval" mechanism to extend. The local system uses environment variables (e.g., `GITHUB_TOKEN`) set externally. Implementing this would require building new infrastructure, not extending an existing file. |
| Development Environment Secrets | Infrastructure deployment pattern — describes centralizing credentials across multi-agent instances. No local centralized secret store or credential distribution mechanism exists. Too abstract to express as an observable before/after state in a file or command. |
| Audit and Compliance | Infrastructure deployment pattern — describes audit trails for secret access. No local audit system for secret access exists. The pattern has no concrete mapping to a skill, agent, or workflow file. |
| Plugin Development (OpenBao SDK) | Describes building OpenBao plugins using the Go SDK. This is about extending OpenBao itself, not about improving Claude Code skills or workflows. No local system maps to this pattern. |
| Encryption-as-a-Service | Infrastructure deployment pattern — describes using the Transit engine for data encryption. No local encryption mechanism or encryption-as-a-service abstraction exists to extend. Would require new infrastructure rather than extending existing files. |
