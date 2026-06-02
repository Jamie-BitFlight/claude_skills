"""Code block extraction and stub rendering.

Provides CodeBlockExtractor for post-processing and CodeBlockStubRenderer
for replacing code block spans with inline stub strings in section body text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CodeBlock, MarkdownDocument

__all__ = ["CodeBlockExtractor", "CodeBlockStubRenderer"]

_STUB_TEMPLATE = '[code: {id} | lang={lang} | lines={start}-{end} | {summary_brief} | view: view_code("{id}")]'


class CodeBlockStubRenderer:
    """Replace code blocks in section body text with inline stubs.

    Stub replacement is line-based: the absolute line range of each code
    block is converted to a body-relative offset and replaced with a single
    stub line. This approach is unconditional — it never leaves a raw code
    fence in the body.

    Example::

        renderer = CodeBlockStubRenderer()
        stubbed_body = renderer.render_stubs(body_text, section, document)
    """

    def render_stubs(
        self, body: str, code_block_ids: list[str], body_start_line: int, document: MarkdownDocument
    ) -> str:
        """Replace code blocks in body with stub strings.

        Args:
            body: Section body text starting at body_start_line.
            code_block_ids: Ordered list of code block IDs to stub out.
            body_start_line: Absolute 0-based line index where body begins.
            document: The full document for looking up CodeBlock data.

        Returns:
            Modified body text with code blocks replaced by stub strings.
        """
        if not code_block_ids:
            return body

        lines = body.splitlines(keepends=True)

        replacements: list[tuple[int, int, str]] = []
        for code_id in code_block_ids:
            block = document.code_blocks.get(code_id)
            if block is None or block.span is None:
                continue
            rel_start = block.span.start_line - body_start_line
            rel_end = block.span.end_line - body_start_line
            if rel_start < 0 or rel_start >= len(lines):
                continue
            replacements.append((rel_start, rel_end, _render_stub(block)))

        # Apply from bottom to top to preserve earlier line indices.
        for rel_start, rel_end, stub in sorted(replacements, key=lambda t: -t[0]):
            safe_end = min(rel_end + 1, len(lines))
            lines[rel_start:safe_end] = [stub + "\n"]

        return "".join(lines)


class CodeBlockExtractor:
    """Re-index code blocks into a document from raw content.

    This class is a no-op post-processor when code blocks are already
    extracted by the indexer. It provides a single attach-by-line-range
    method used when reprocessing existing documents.

    Example::

        extractor = CodeBlockExtractor()
        extractor.assign_to_sections(document)
    """

    def assign_to_sections(self, document: MarkdownDocument) -> None:
        """Assign each code block to its containing section by line range.

        Modifies section.code_block_ids in-place for any block whose span
        is not already assigned.

        Args:
            document: Document whose sections and code_blocks to reconcile.
        """
        for code_id, block in document.code_blocks.items():
            if block.section_id is not None:
                continue
            if block.span is None:
                continue
            line = block.span.start_line
            for section in document.sections.values():
                if section.span.start_line <= line <= section.span.end_line:
                    if code_id not in section.code_block_ids:
                        section.code_block_ids.append(code_id)
                    break


def _render_stub(block: CodeBlock) -> str:
    """Render a code block as an inline stub string.

    Args:
        block: The code block to stub out.

    Returns:
        Single-line stub string.
    """
    lang = block.language or "text"
    content_lines = block.content.splitlines()
    n_lines = len(content_lines)
    first_line = content_lines[0][:30].strip() if content_lines else ""
    summary_brief = f"{n_lines} lines, starts: {first_line}"
    start = block.span.start_line if block.span else 0
    end = block.span.end_line if block.span else 0
    return _STUB_TEMPLATE.format(id=block.id, lang=lang, start=start, end=end, summary_brief=summary_brief)
