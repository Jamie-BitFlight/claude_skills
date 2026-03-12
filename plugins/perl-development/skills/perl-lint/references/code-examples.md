# Code Examples

## Lint and Fix Script

```bash
#!/bin/bash
# lint-perl.sh

FILE="${1}"

if [[ ! -f "$FILE" ]]; then
    echo "Usage: lint-perl.sh <file.pl>"
    exit 1
fi

echo "=== Syntax Check ==="
perl -c "$FILE" || exit 1

echo ""
echo "=== Perl::Critic ==="
if command -v perlcritic >/dev/null; then
    perlcritic --severity 4 "$FILE"
else
    echo "perlcritic not installed. Run: cpanm Perl::Critic"
fi

echo ""
echo "=== Formatting Check ==="
if command -v perltidy >/dev/null; then
    if ! perltidy -st "$FILE" | diff -q - "$FILE" >/dev/null 2>&1; then
        echo "File needs formatting. Run: perltidy $FILE"
    else
        echo "File is properly formatted."
    fi
else
    echo "perltidy not installed. Run: cpanm Perl::Tidy"
fi
```
