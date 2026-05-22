# Dangling Thread Checklist

Answer each question before marking any task complete.
All "yes, unaddressed" answers must be resolved before proceeding.

---

- [ ] Is there a thread that can be tied off in under 5 minutes?
- [ ] Is the current solution a workaround when the real fix exists?
- [ ] Was search performed before building anything new?
- [ ] Were tests run — or is there an explicit reason they cannot be?
- [ ] Does any output contain a hard-coded truncation or length limit?

---

Run the automated checker:

```bash
uv run .claude/skills/boil/scripts/check_completion.py [file_or_dir]
```

Exit 0 = no automated violations.
Non-zero = review flagged lines, apply fixes, re-run until exit 0.
