"""Extract link and image references from a parsed markdown document.

Uses the ParserResult token stream to find inline links, images,
and reference definitions from the environment dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import LinkKind, LinkRef, LinkTokenOrigin, MarkdownDocument, SourceSpan

if TYPE_CHECKING:
    from .parser import ParserResult

__all__ = ["LinkExtractor"]


def _build_link_ref(
    link_id: str,
    text: str,
    target: str,
    title: str | None,
    kind: LinkKind,
    span: SourceSpan | None,
    source_token_type: LinkTokenOrigin,
) -> LinkRef:
    """Construct a LinkRef from its constituent fields.

    Centralises LinkRef construction to keep :meth:`LinkExtractor.extract`
    within the local-variable limit (PLR0914).

    Args:
        link_id: Stable unique identifier assigned by the extractor.
        text: Display text or alt text for images.
        target: URL or path the link points to.
        title: Optional link title attribute.
        kind: Classification of the link type.
        span: Source span within the document, when available.
        source_token_type: Extraction origin identifying the parser token type.

    Returns:
        A fully constructed LinkRef.
    """
    return LinkRef(
        id=link_id, text=text, target=target, title=title, kind=kind, span=span, source_token_type=source_token_type
    )


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
                    # Collect link text from next text token(s).
                    text_parts: list[str] = []
                    j = i + 1
                    while j < len(children) and children[j].type != "link_close":
                        if children[j].content:
                            text_parts.append(children[j].content)
                        j += 1

                    link_counter += 1
                    link_id = f"link_{link_counter:04d}"
                    document.links[link_id] = _build_link_ref(
                        link_id=link_id,
                        text=" ".join(text_parts),
                        target=str(child.attrs.get("href", "") if child.attrs else ""),
                        title=(
                            str(child.attrs.get("title"))
                            if child.attrs and child.attrs.get("title") is not None
                            else None
                        ),
                        kind=LinkKind.link,
                        span=span,
                        source_token_type=LinkTokenOrigin.link_open,
                    )
                    _attach_to_section(document, link_id, span)

                elif child.type == "image":
                    link_counter += 1
                    link_id = f"link_{link_counter:04d}"
                    document.links[link_id] = _build_link_ref(
                        link_id=link_id,
                        text=child.content or "",
                        target=str(child.attrs.get("src", "") if child.attrs else ""),
                        title=(
                            str(child.attrs.get("title"))
                            if child.attrs and child.attrs.get("title") is not None
                            else None
                        ),
                        kind=LinkKind.image,
                        span=span,
                        source_token_type=LinkTokenOrigin.image,
                    )
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

            document.links[link_id] = _build_link_ref(
                link_id=link_id,
                text=label,
                target=ref_data.get("href", ""),
                title=ref_data.get("title"),
                kind=LinkKind.reference_definition,
                span=ref_span,
                source_token_type=LinkTokenOrigin.reference_definition,
            )
            _attach_to_section(document, link_id, ref_span)


def _attach_to_section(document: MarkdownDocument, link_id: str, span: SourceSpan | None) -> None:
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
