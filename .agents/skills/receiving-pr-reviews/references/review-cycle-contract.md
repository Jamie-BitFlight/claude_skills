# Review outcome contract

Use this contract when assessing review evidence or deciding whether a PR/MR review cycle is complete. It applies to local CLI and connected MCP workflows alike. The bundled helper is the preferred implementation when available and working. Its Pydantic state and validators apply when using that helper; other transports establish the same outcomes through their own provider evidence.

## Evidence and validity

Evidence is an inspectable observation with enough context to support or contradict a claim. A valid observation does not automatically justify the reviewer's proposed implementation. Establish relevance to the intended runtime consumer, including whether the behavior is already handled elsewhere. Where facts are missing, state the uncertainty and the focused question.

Treat review findings as a body of evidence: recurring symptoms may expose one root cause, an unsuitable mechanism, or accumulating maintenance churn. Group findings by shared cause before deciding what to change. Preserve each input's identity and outcome, including approvals and already-resolved history.

## Intake and response

Check submitted reviews, review threads and their nested comments, top-level comments, approvals, and applicable provider state. A new review submission or thread is inbound even when authored by the authenticated account; multiple agents may share that account. A reply within an existing thread is a response candidate, established by its relationship and content rather than account identity alone.

For each relevant input, retain enough of its stable provider reference, latest content, assessment, disposition, implementation evidence, response, and resolution to determine what remains outstanding. Match an acknowledgment to the actual input and current content; an attempted call or a generic reaction alone does not prove a response.

A useful disposition is an evidence-backed change, no-change decision, supersession, or focused clarification. Verify accepted changes and preserve an inspectable revision when citing them. Distinguish a provisional question from a completed fix.

## Authorized actions

Read-only review checks do not imply permission to edit source or mutate provider state. Before consequential writes, inspect the current target and relevant provider evidence, respect available capabilities and authorization, and account for concurrent changes. For multiple actions, establish the intended actions before executing them.

Confirm communication before resolution. If resolution fails after a successful reply, preserve the reply and retry only the remaining resolution. Record unavailable resolution capabilities truthfully. Clarification stays open until answered.

## Recheck and completion

After responding, check for new, edited, unresponded, or unresolved inputs. Reassess decisions affected by changed evidence; reuse unaffected assessments. Report completion only when current relevant review work has been accounted for, accepted outcomes are verified, responses are observed, and no required clarification or other outstanding work remains.

A quiet watch window, approval alone, or a locally recorded action is not completion evidence. When using the preferred CLI helper, its `validate-projection`, `validate-cycle`, and `complete-cycle` commands enforce its own stricter state representation; MCP workflows establish the same review outcomes through provider observations without producing that representation.
