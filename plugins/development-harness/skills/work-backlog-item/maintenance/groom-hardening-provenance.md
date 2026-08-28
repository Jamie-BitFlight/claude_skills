# Groom finalize hardening provenance

Two rules in `references/workflows/groom/finalize.md` were added in response to a real failure,
not designed speculatively — don't regress them when editing that file:

- The RT-ICA Final Pass citation requirement (no condition status may change to AVAILABLE without
  a pasted tool-output or user-message citation).
- The Diagnostic Gate (identify why a required section is absent or empty before retrying or
  writing directly).

Source: session observation, #1899 groom failure diagnosis, 2026-04-23.
