#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.0.0",
# ]
# ///
"""Minimal example: Preventing Rich Console word wrapping in CI/non-TTY environments.

Problem: Rich Console wraps text at default width (80 chars in non-TTY), breaking:
- URLs in log output
- Long command strings
- Stack traces
- Structured log parsing

Solution: Use crop=False + overflow="ignore" on console.print() calls.
"""

from __future__ import annotations

from rich.console import Console

# Sample long text that would wrap at 80 characters
long_url = (
    "https://raw.githubusercontent.com/python/cpython/main/Lib/asyncio/base_events.py"
    "#L1000-L1100?ref=docs-example&utm_source=rich-demo&utm_medium=terminal"
    "&utm_campaign=long-url-wrapping-behavior-test"
)
long_command = """
[bold cyan]:sparkles: v3.13.0 Release Highlights :sparkles:[/bold cyan] New JIT optimizations, faster startup, improved error messages, richer tracebacks, "
better asyncio diagnostics, enhanced typing features, smoother virtualenv workflows, and a refined standard library experience for developers everywhere.
[green]:rocket: Performance & Reliability :rocket:[/green] Lower latency event loops, smarter garbage collection heuristics, adaptive I/O backpressure, fine-tuned file system operations, reduced memory fragmentation, and sturdier cross-platform behavior in cloud-native deployments.
[magenta]:hammer_and_wrench: Developer Experience :hammer_and_wrench:[/magenta] More precise type hints, clearer deprecation warnings, friendlier REPL niceties, first-class debugging hooks, expanded `typing` utilities, and streamlined packaging stories for modern Python projects of all sizes.",
[yellow]:shield: Security & Ecosystem :shield:[/yellow] Hardened TLS defaults, safer subprocess handling, improved sandboxing hooks, more robust hashing algorithms, curated secure defaults across modules, and deeper ecosystem integration for auditing, scanning, and compliance workflows.
"""
long_traceback = "Traceback (most recent call last): File /very/long/path/to/module/that/contains/the/failing/code/in/production/environment.py line 42 in process_data"

console = Console()

print("=" * 80)
print("PROBLEM: Default console.print() wraps long lines")
print("=" * 80)
console.print(f"URL: {long_url}")
console.print(f"Command: {long_command}")
console.print(f"Error: {long_traceback}")

print("\n" + "=" * 80)
print("SOLUTION: Use crop=False + overflow='ignore'")
print("=" * 80)
console.print(f"URL: {long_url}", crop=False, overflow="ignore")
console.print(f"Command: {long_command}", crop=False, overflow="ignore")
console.print(f"Error: {long_traceback}", crop=False, overflow="ignore")
