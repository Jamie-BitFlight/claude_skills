The purpose and explicit goals of the skill root-cause-tracing-process:

1. Guarantee the actual failure is reproduced firsthand (not inferred from transcripts, docs, or memory) before source code is read or theorized about
2. Classify reproduction risk (bound vs. unbound constraints) and gate autonomous execution vs. user check-ins accordingly, batching all safety questions into one interaction
3. Produce a fully-cited evidence chain (command output, file:line citations, direct observation only — never docs, training recall, absence-inference, or analogy) linking symptom to root cause via explicit DEPENDS-ON dependencies
4. Eliminate hedged/unverified causal claims by banning words like "probably"/"likely"/"I think" and requiring every unverifiable claim to be explicitly flagged with what evidence would resolve it
5. Deliver a structured, falsifiable final report (QUESTION, SUCCESS CRITERIA MET, EVIDENCE CHAIN, ROOT CAUSE, UNVERIFIED ITEMS) instead of a narrative explanation
6. Turn a failure that does not reproduce into a reproduction by falsifying H0/Ha hypotheses through experiments that run the operation with one condition set and unset
