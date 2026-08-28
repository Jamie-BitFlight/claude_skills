# Groom finalize hardening provenance

Two rules in `references/workflows/groom/finalize.md` were added in response to a real failure,
not designed speculatively — don't regress them when editing that file:

- The RT-ICA Final Pass citation requirement (no condition status may change to AVAILABLE without
  a pasted tool-output or user-message citation).
- The Diagnostic Gate (identify why a required section is absent or empty before retrying or
  writing directly).

Source: session observation, #1899 groom failure diagnosis, 2026-04-23.

## Output Validation Gate retry — same model only

The retry logic (Diagnostic Gate → 1st/2nd retry → BLOCKED after 3 attempts) never escalates to a
more capable model. The observed failure mode for a missing/malformed required section is an
interrupted agent (token exhaustion, network timeout, session terminated), not a model capability
gap — every model calls the same MCP tool fields, so a bigger model doesn't address an interrupted
write. Don't add a model-escalation branch to this retry logic without addressing that mismatch.
