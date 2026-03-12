# Code Examples

## Comprehensive Validation Script

```bash
#!/bin/bash
# validate-perl.sh

FILE="${1}"
ERRORS=0

if [[ ! -f "$FILE" ]]; then
    echo "Usage: validate-perl.sh <file.pl>"
    exit 1
fi

echo "=== Validating: $FILE ==="
echo ""

# 1. Syntax check
echo "--- Syntax Check ---"
if perl -wc "$FILE" 2>&1; then
    echo "PASS: Syntax OK"
else
    echo "FAIL: Syntax errors"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 2. Pragmas
echo "--- Essential Pragmas ---"
if grep -q 'use strict' "$FILE"; then
    echo "PASS: use strict found"
else
    echo "FAIL: Missing 'use strict'"
    ERRORS=$((ERRORS + 1))
fi

if grep -q 'use warnings' "$FILE"; then
    echo "PASS: use warnings found"
else
    echo "FAIL: Missing 'use warnings'"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 3. Security patterns
echo "--- Security Checks ---"
if grep -q 'open\s\+[A-Z]\+\s*,' "$FILE"; then
    echo "WARN: Possible bareword filehandle (check manually)"
else
    echo "PASS: No bareword filehandles detected"
fi

if grep -q '`.*\$' "$FILE"; then
    echo "WARN: Backticks with variables (potential injection)"
else
    echo "PASS: No unsafe backticks"
fi
echo ""

# 4. Documentation
echo "--- Documentation ---"
if podchecker "$FILE" 2>&1 | grep -q 'pod syntax OK'; then
    echo "PASS: POD syntax OK"
elif grep -q '^=head1' "$FILE"; then
    echo "WARN: POD present but may have issues"
else
    echo "INFO: No POD documentation"
fi
echo ""

# Summary
echo "=== Summary ==="
if [[ $ERRORS -eq 0 ]]; then
    echo "All critical checks passed."
    exit 0
else
    echo "Found $ERRORS critical issue(s)."
    exit 1
fi
```
