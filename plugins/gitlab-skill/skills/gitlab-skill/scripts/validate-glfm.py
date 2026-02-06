#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28.1",
# ]
# ///
"""GitLab Flavored Markdown Validation Script.

Validates GLFM rendering by calling the GitLab markdown API.
Usage:
    ./validate-glfm.py --file <path>
    ./validate-glfm.py --markdown "# Text"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def get_gitlab_token() -> str | None:
    """Get GitLab token from environment or .bashrc.

    Returns:
        Token string if found in environment or ~/.bashrc, None otherwise.
    """
    # Check environment first
    token = os.environ.get("GITLAB_TOKEN")
    if token:
        return token

    # Try reading from .bashrc
    bashrc_path = Path.home() / ".bashrc"
    if bashrc_path.exists():
        try:
            with Path(bashrc_path).open(encoding="utf-8") as f:
                for line in f:
                    if line.startswith("export GITLAB_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError as e:
            print(f"Warning: Could not read .bashrc: {e}", file=sys.stderr)

    return None


def validate_markdown(
    markdown_text: str,
    gitlab_url: str,
    token: str,
    project: str | None = None,
    verbose: bool = False,
) -> str | None:
    """Call GitLab markdown API and return rendered HTML.

    Returns:
        Rendered HTML string on success, None on failure.
    """
    api_url = f"{gitlab_url}/api/v4/markdown"

    headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}

    payload: dict[str, str | bool] = {"text": markdown_text, "gfm": True}

    if project:
        payload["project"] = project

    if verbose:
        print(f"API URL: {api_url}", file=sys.stderr)
        print(f"Request payload: {json.dumps(payload, indent=2)}", file=sys.stderr)

    try:
        response = httpx.post(api_url, headers=headers, json=payload, timeout=30)
    except httpx.RequestError as e:
        print(f"Request Error: {e}", file=sys.stderr)
        return None

    if verbose:
        print(f"Response status: {response.status_code}", file=sys.stderr)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(
            f"HTTP Error {e.response.status_code}: {e.response.text}", file=sys.stderr
        )
        return None

    try:
        result = response.json()
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}", file=sys.stderr)
        print(f"Response text: {response.text}", file=sys.stderr)
        return None

    if "html" in result:
        return str(result["html"])
    if "error" in result:
        print(f"API Error: {result['error']}", file=sys.stderr)
        return None
    print(f"Unexpected response: {result}", file=sys.stderr)
    return None


def main() -> int:
    """Parse arguments and validate markdown content against GitLab API.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    parser = argparse.ArgumentParser(
        description="Validate GitLab Flavored Markdown rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file firmware/README.md
  %(prog)s --markdown "> [!note]\\n> Test alert"
  %(prog)s --file test.md --output rendered.html --verbose
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--file", "-f", type=Path, help="Path to markdown file to validate"
    )
    input_group.add_argument(
        "--markdown", "-m", type=str, help="Markdown text to validate (inline)"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save rendered HTML to file (default: print to stdout)",
    )

    parser.add_argument(
        "--project",
        "-p",
        type=str,
        help="GitLab project path for reference resolution (e.g., 'group/project')",
    )

    parser.add_argument(
        "--gitlab-url",
        type=str,
        default="https://sourcery.assaabloy.net",
        help="GitLab instance URL (default: https://sourcery.assaabloy.net)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output with request/response details",
    )

    args = parser.parse_args()

    # Get GitLab token
    token = get_gitlab_token()
    if not token:
        print(
            "Error: GITLAB_TOKEN not found in environment or ~/.bashrc", file=sys.stderr
        )
        print("Set it with: export GITLAB_TOKEN='your-token'", file=sys.stderr)
        sys.exit(1)

    # Get markdown text
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        try:
            markdown_text = args.file.read_text()
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
        else:
            if args.verbose:
                print(
                    f"Read {len(markdown_text)} characters from {args.file}",
                    file=sys.stderr,
                )
    else:
        markdown_text = args.markdown

    # Validate markdown
    html = validate_markdown(
        markdown_text,
        args.gitlab_url,
        token,
        project=args.project,
        verbose=args.verbose,
    )

    if html is None:
        sys.exit(1)

    # Output result
    if args.output:
        try:
            args.output.write_text(html)
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Rendered HTML saved to: {args.output}", file=sys.stderr)
    else:
        print(html)

    return 0


if __name__ == "__main__":
    sys.exit(main())
