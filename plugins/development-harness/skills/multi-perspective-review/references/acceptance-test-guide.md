# Acceptance Test Guide — Multi-Perspective Review

Manual acceptance test procedures for AC4 (Security REJECT), AC5 (Accessibility SKIP), and
AC6 (summary format). These tests require the full `dh:multi-perspective-review` skill to be
operational and must be run after T6 (skill implementation) completes.

**Scope note**: AC4, AC5, and AC6 are behavioral acceptance criteria that require live skill
execution against real diff inputs. They are NOT covered by the plan's T0/TN bookend checks
(which verify only structural ACs 1–2–7: file existence and schema correctness). This is a
deliberate scope decision — the bookend system verifies static artifacts; behavioral runtime
verification is manual-only.

---

## Prerequisites

Before running any test below:

1. Confirm the multi-perspective-review skill is installed:
   ```bash
   /dh:multi-perspective-review --help
   ```
2. Confirm the four reviewer agents are registered:
   ```bash
   ls plugins/development-harness/agents/reviewer-*.md
   ```
3. Apply a fixture diff to a scratch branch:
   ```bash
   git checkout -b test/acceptance-scratch
   git apply .tmp/test-fixtures/<fixture>.diff
   ```

---

## AC4 — Security REJECT on Hardcoded Secret

**Fixture**: `.tmp/test-fixtures/security-issue.diff`

The fixture introduces `config/aws_config.py` containing the line:
```
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
```
This matches the pattern `/AKIA[A-Z0-9]{16}/` and must trigger a BLOCKER finding in the
security perspective.

**Invocation** (from repository root, after applying the fixture):
```bash
git apply .tmp/test-fixtures/security-issue.diff
/dh:multi-perspective-review --diff HEAD~1..HEAD
```

Or against a specific git range:
```bash
/dh:multi-perspective-review --diff main..HEAD
```

**Expected exit code**: `1` (non-zero — gate FAIL)

**Expected stdout patterns** (all must appear):
- `Security: REJECT` — security perspective issued a REJECT verdict
- `BLOCKER` — at least one BLOCKER finding present
- `AKIAIOSFODNN7EXAMPLE` or `no-hardcoded-secrets` — finding references the secret or rule

**Example expected summary line (AC6 format)**:
```
Security: REJECT (1 finding) | Performance: APPROVE (...) | Quality: APPROVE (...) | Accessibility: APPROVE/SKIP (...)
```

**Verification command**:
```bash
/dh:multi-perspective-review --diff HEAD~1..HEAD; echo "Exit: $?"
# Expected: Exit: 1
```

---

## AC5 — Accessibility SKIP When No UI Changes

**Fixture**: `.tmp/test-fixtures/no-ui-changes.diff`

The fixture modifies only `.py` files (`backlog_core/models.py`,
`backlog_core/backend_protocol.py`). None of these match the UI file pattern list defined in
`references/verdict-schema.md §2.3`. The accessibility reviewer must emit `verdict: SKIP`
without scanning file contents.

**Invocation** (from repository root, after applying the fixture):
```bash
git apply .tmp/test-fixtures/no-ui-changes.diff
/dh:multi-perspective-review --diff HEAD~1..HEAD
```

**Expected exit code**: `0` (gate PASS — SKIP counts as pass for that perspective)

**Expected stdout patterns** (all must appear):
- `Accessibility: SKIP` — accessibility perspective issued SKIP
- `no UI` or `no ui changes` — skip_reason references absence of UI files

**Stdout pattern that must NOT appear**:
- `Accessibility: REJECT` — accessibility must not reject a non-UI diff

**Verification command**:
```bash
/dh:multi-perspective-review --diff HEAD~1..HEAD; echo "Exit: $?"
# Expected: Exit: 0
# stdout must contain "Accessibility: SKIP"
```

---

## AC6 — Canonical Summary Line Format

**Context**: AC6 requires the orchestrating skill to emit one summary line per perspective in
the canonical format defined in `references/verdict-schema.md §2.2`.

**Canonical format**:
```text
Security: APPROVE (0 findings) | Performance: APPROVE (0 findings) | Quality: APPROVE (0 findings) | Accessibility: SKIP (no UI changes)
```

The summary line uses ` | ` (space-pipe-space) as separator. Token formats per verdict:

| Verdict | Token format |
|---------|-------------|
| `APPROVE` with 0 findings | `APPROVE (0 findings)` |
| `APPROVE` with N minor findings | `APPROVE ({N} minor)` |
| `REJECT` with 1 blocker | `REJECT (1 finding)` |
| `REJECT` with N blockers | `REJECT ({N} findings)` |
| `SKIP` | `SKIP ({skip_reason})` |

**Test using the no-ui-changes fixture** (covers Accessibility SKIP token):
```bash
git apply .tmp/test-fixtures/no-ui-changes.diff
/dh:multi-perspective-review --diff HEAD~1..HEAD 2>&1 | grep -E '^Security:|^Performance:|^Quality:|^Accessibility:'
```

**Expected output structure** (exact tokens depend on findings; format must match):
```
Security: APPROVE (0 findings) | Performance: APPROVE (0 findings) | Quality: APPROVE (0 findings) | Accessibility: SKIP (no UI changes)
```

**All-SKIP edge case**: If all four perspectives return SKIP (e.g. completely empty diff), the
gate still passes but stdout must contain:
```
NOTE: No perspectives reviewed — all skipped
```

**Verification command for format compliance**:
```bash
output=$(/dh:multi-perspective-review --diff HEAD~1..HEAD 2>&1)
echo "$output" | grep -qE 'Security: (APPROVE|REJECT|SKIP)' && echo "AC6 Security token OK"
echo "$output" | grep -qE 'Performance: (APPROVE|REJECT|SKIP)' && echo "AC6 Performance token OK"
echo "$output" | grep -qE 'Quality: (APPROVE|REJECT|SKIP)' && echo "AC6 Quality token OK"
echo "$output" | grep -qE 'Accessibility: (APPROVE|REJECT|SKIP)' && echo "AC6 Accessibility token OK"
```

---

## Cleanup

After each test run, reset the scratch branch:
```bash
git checkout main
git branch -D test/acceptance-scratch
```

Or undo only the applied diff:
```bash
git apply --reverse .tmp/test-fixtures/<fixture>.diff
```
