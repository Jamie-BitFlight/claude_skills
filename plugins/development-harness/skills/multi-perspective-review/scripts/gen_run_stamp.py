#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Print a collision-resistant run stamp for multi-perspective-review slugs.

A UTC timestamp alone only has whole-second resolution, so two review runs for
the same review_base starting within the same second would derive the same
review_slug and collide on the plan address. secrets.token_hex draws
from the OS CSPRNG (os.urandom) on every platform Python runs on, unlike bash's
${RANDOM} builtin (weak, seeded from the shell's PID and start time, so sibling
processes launched together can draw correlated values) or piping /dev/urandom
through od (POSIX-only device file, needs MSYS2/WSL emulation on Windows).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime


def main() -> None:
    """Print "{UTC timestamp}-{16 hex chars}" to stdout."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    print(f"{timestamp}-{secrets.token_hex(8)}")


if __name__ == "__main__":
    main()
