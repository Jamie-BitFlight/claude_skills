# Reproduction Integrity

A reproduction must demonstrate the failure in the ACTUAL conditions, not in conditions you constructed to match your hypothesis.

Before any `env -i`, `docker run`, mock, or simulated environment: run the equivalent check in the real environment first.

Wrong order: hypothesize → build synthetic env → confirm → act
Right order: hypothesize → check real env → if real env matches → reproduce → act

Proof template:

1. "The actual value is: [observed via tool]"
2. "My hypothesis predicts failure when: [condition]"
3. "The actual environment [does/does not] have that condition"
4. If does not: hypothesis rejected. Stop.
