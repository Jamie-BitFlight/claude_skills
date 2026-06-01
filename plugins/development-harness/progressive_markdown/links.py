"""Extract link and image references from a parsed markdown document.

Uses the ParserResult token stream to find inline links, images,
and reference definitions from the environment dict.
"""

from __future__ import annotations

from typing import Any

from .models import LinkKind, LinkRef, MarkdownDocument, SourceSpan
from .parser import ParserResult

__all__ = ["LinkExtractor"]


class LinkExtractor:
    """Extract LinkRef objects from a ParserResult and attach them to a MarkdownDocument.

    Example::

        extractor = LinkExtractor()
        extractor.extract(parser_result, document)
    """

    def extract(self, result: ParserResult, document: MarkdownDocument) -> None:
        """Extract links from result and populate document.links.

        Modifies document in place by adding LinkRef entries to document.links
        and updating section link_ref_ids.

        Args:
            result: Parser output containing the token stream and environment.
            document: Document to populate with extracted links.
        """
        link_counter = 0

        # Process inline tokens for links and images.
        for token in result.tokens:
            if token.type != "inline" or not token.children:
                continue

            span: SourceSpan | None = None
            if token.map:
                span = SourceSpan(start_line=token.map[0], end_line=token.map[1] - 1)

            i = 0
            children = token.children
            while i < len(children):
                child = children[i]

                if child.type == "link_open":
                    href = child.attrs.get("href", "") if child.attrs else ""
                    title_attr = child.attrs.get("title") if child.attrs else None
                    # Collect link text from next text token(s).
                    text_parts: list[str] = []
                    j = i + 1
                    while j < len(children) and children[j].type not in ("link_close",):
                        if children[j].content:
                            text_parts.append(children[j].content)
                        j += 1

                    link_counter += 1
                    link_id = f"link_{link_counter:04d}"
                    link_ref = LinkRef(
                        id=link_id,
                        text=" ".join(text_parts),
                        target=str(href),
                        title=str(title_attr) if title_attr is not None else None,
                        kind=LinkKind.link,
                        span=span,
                        source_token_type="link_open",
                    )
                    document.links[link_id] = link_ref
                    _attach_to_section(document, link_id, span)

                elif child.type == "image":
                    src = child.attrs.get("src", "") if child.attrs else ""
                    alt = child.content or ""
                    title_attr = child.attrs.get("title") if child.attrs else None

                    link_counter += 1
                    link_id = f"link_{link_counter:04d}"
                    link_ref = LinkRef(
                        id=link_id,
                        text=alt,
                        target=str(src),
                        title=str(title_attr) if title_attr is not None else None,
                        kind=LinkKind.image,
                        span=span,
                        source_token_type="image",
                    )
                    document.links[link_id] = link_ref
                    _attach_to_section(document, link_id, span)

                i += 1

        # Process reference definitions from the environment.
        references: dict[str, Any] = result.env.get("references", {})
        for label, ref_data in references.items():
            link_counter += 1
            link_id = f"link_{link_counter:04d}"
            ref_map = ref_data.get("map")
            ref_span: SourceSpan | None = None
            if ref_map:
                ref_span = SourceSpan(start_line=ref_map[0], end_line=ref_map[1] - 1)

            link_ref = LinkRef(
                id=link_id,
                text=label,
                target=ref_data.get("href", ""),
                title=ref_data.get("title"),
                kind=LinkKind.reference_definition,
                span=ref_span,
                source_token_type="reference_definition",
            )
            document.links[link_id] = link_ref
            _attach_to_section(document, link_id, ref_span)


def _attach_to_section(
    document: MarkdownDocument,
    link_id: str,
    span: SourceSpan | None,
) -> None:
    """Attach a link to the section containing its span.

    Args:
        document: The document with sections to search.
        link_id: ID of the link to attach.
        span: Source span of the link. When None, no attachment is performed.
    """
    if span is None:
        return
    line = span.start_line
    for section in document.sections.values():
        if section.span.start_line <= line <= section.span.end_line:
            if link_id not in section.link_ref_ids:
                section.link_ref_ids.append(link_id)
            break
