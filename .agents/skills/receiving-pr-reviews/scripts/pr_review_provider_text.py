"""Provider-neutral review-response rendering."""

from __future__ import annotations

import re


def reference_present(body: str, reference: str) -> bool:
    """Match a stable reference without accepting a longer numeric identifier.

    Returns:
        Whether the exact reference is present.
    """
    suffix = r"(?!\d)" if reference and reference[-1].isdigit() else ""
    return re.search(re.escape(reference) + suffix, body) is not None


def render_top_level_body(body: str, references: list[str]) -> str:
    """Append each exact missing stable reference once.

    Returns:
        The body containing every requested reference.
    """
    missing = [reference for reference in references if not reference_present(body, reference)]
    if not missing:
        return body
    rendered_references = "\n".join(missing)
    return f"{body}\n\n{rendered_references}"
