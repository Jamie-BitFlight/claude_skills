"""Renderers that produce text blocks from document structures.

Each renderer converts structured document data into a list of text blocks
suitable for passing to Paginator. Renderers have no knowledge of pagination
or token budgets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .codeblocks import CodeBlockStubRenderer
    from .models import CodeBlock, MarkdownDocument, SectionNode

__all__ = [
    "CodeBlockRenderer",
    "DocumentMapRenderer",
    "LinkInventoryRenderer",
    "SectionBodyRenderer",
    "SectionMapRenderer",
]


class DocumentMapRenderer:
    """Render the full document map as a list of text blocks.

    Each block represents one section with its selector, id, slug, title,
    level, line range, child count, code count, and link count.

    Example::

        renderer = DocumentMapRenderer()
        blocks = renderer.render_blocks(document)
    """

    def render_blocks(self, document: MarkdownDocument) -> list[str]:
        """Render all sections as individual text blocks.

        Args:
            document: The parsed markdown document.

        Returns:
            List of text blocks, one per section in document order.
        """
        blocks: list[str] = []
        for section in document.sections.values():
            block = (
                f"[{section.selector}] {section.title}\n"
                f"  id={section.id}  slug={section.slug}  level={section.level}\n"
                f"  lines={section.span.start_line}-{section.span.end_line}"
                f"  children={len(section.child_ids)}"
                f"  code={len(section.code_block_ids)}"
                f"  links={len(section.link_ref_ids)}\n"
            )
            blocks.append(block)
        return blocks


class SectionMapRenderer:
    """Render a section map showing parent breadcrumb and immediate children.

    Example::

        renderer = SectionMapRenderer()
        blocks = renderer.render_blocks(document, section)
    """

    def render_blocks(self, document: MarkdownDocument, section: SectionNode) -> list[str]:
        """Render the parent breadcrumb and children of a section.

        Args:
            document: The parsed markdown document.
            section: The parent section whose children to map.

        Returns:
            List of text blocks: breadcrumb block followed by child blocks.
        """
        blocks: list[str] = []

        # Breadcrumb: show ancestry chain.
        breadcrumb_parts: list[str] = []
        current: SectionNode | None = section
        while current is not None:
            breadcrumb_parts.insert(0, f"[{current.selector}] {current.title}")
            if current.parent_id:
                parent = document.sections.get(current.parent_id)
                current = parent
            else:
                current = None
        blocks.append("Path: " + " > ".join(breadcrumb_parts) + "\n")

        # Immediate children only.
        if section.child_ids:
            blocks.append("Children:\n")
            for child_id in section.child_ids:
                child = document.sections.get(child_id)
                if child is None:
                    continue
                child_block = (
                    f"  [{child.selector}] {child.title}"
                    f"  (children={len(child.child_ids)}, code={len(child.code_block_ids)})\n"
                )
                blocks.append(child_block)

        return blocks


class SectionBodyRenderer:
    """Render the body of a section with code blocks replaced by stubs.

    Reconstructs body text from document lines using the section's body_span.
    Does not include child section content.

    Args:
        stub_renderer: CodeBlockStubRenderer used for code block replacement.

    Example::

        renderer = SectionBodyRenderer(CodeBlockStubRenderer())
        body = renderer.render(document, section)
    """

    def __init__(self, stub_renderer: CodeBlockStubRenderer) -> None:
        """Initialise with a CodeBlockStubRenderer.

        Args:
            stub_renderer: Renderer used to replace code blocks with stubs.
        """
        self._stub_renderer = stub_renderer

    def render(self, document: MarkdownDocument, section: SectionNode) -> str:
        """Render the section body as a string with code stubs.

        Extracts lines from body_span, then replaces code block spans with
        stub strings. Does not include text from child sections.

        Args:
            document: The parsed markdown document.
            section: The section whose body to render.

        Returns:
            Section body text with code blocks replaced by stubs.
        """
        start = section.body_span.start_line
        end = section.body_span.end_line + 1
        lines = document.lines
        body_lines = lines[start:end]
        body = "\n".join(body_lines)
        if body_lines and not body.endswith("\n"):
            body += "\n"

        return self._stub_renderer.render_stubs(
            body,
            section.code_block_ids,
            start,
            document,
        )


class LinkInventoryRenderer:
    """Render the full link inventory as a list of text blocks.

    Example::

        renderer = LinkInventoryRenderer()
        blocks = renderer.render_blocks(document)
    """

    def render_blocks(self, document: MarkdownDocument) -> list[str]:
        """Render all links as individual text blocks.

        Args:
            document: The parsed markdown document.

        Returns:
            List of text blocks, one per link.
        """
        blocks: list[str] = []
        for link in document.links.values():
            span_str = ""
            if link.span:
                span_str = f"  line={link.span.start_line}"
            block = (
                f"[{link.id}] {link.kind.value}: {link.text!r} → {link.target}"
                + (f" ({link.title})" if link.title else "")
                + span_str
                + "\n"
            )
            blocks.append(block)
        return blocks


class CodeBlockRenderer:
    """Render a single code block with its fence markers.

    Example::

        renderer = CodeBlockRenderer()
        text = renderer.render(code_block)
    """

    def render(self, code_block: CodeBlock) -> str:
        """Render a code block with original language fence.

        Args:
            code_block: The code block to render.

        Returns:
            Fenced code block string including opening and closing fences.
        """
        lang = code_block.language or ""
        return f"```{lang}\n{code_block.content}```\n"
