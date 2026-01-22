"""Adapter to convert Lark parser output to legacy ParsedLine format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lark.exceptions import LarkError

from sb2n.legacy_parser import LineType, ParsedLine, RichTextElement
from sb2n.models.ast import (
    CalloutNode,
    CodeBlockNode,
    CommandNode,
    DecorationNode,
    HashtagNode,
    ImageNode,
    InlineCodeNode,
    LinkNode,
    PageLinkNode,
    ParagraphNode,
    QuoteNode,
    StrongNode,
    TableNode,
    TextNode,
)

if TYPE_CHECKING:
    from sb2n.lark_parser import ScrapboxLarkParser
    from sb2n.models.ast import (
        ContentNode,
        DocumentNode,
        InlineNode,
        LineNode,
    )
else:
    # Runtime imports to avoid circular dependencies
    ContentNode = object
    DocumentNode = object
    InlineNode = object
    LineNode = object


class LarkParserAdapter:
    """Adapter to convert Lark parser output to legacy ParsedLine format."""

    @staticmethod
    def convert_document(document: DocumentNode) -> list[ParsedLine]:
        """Convert Lark DocumentNode to list of ParsedLine.

        Args:
            document: Parsed document from Lark parser

        Returns:
            List of ParsedLine objects
        """
        parsed_lines: list[ParsedLine] = []

        for line in document.lines:
            parsed_line = LarkParserAdapter._convert_line(line)
            if parsed_line:
                parsed_lines.append(parsed_line)

        return parsed_lines

    @staticmethod
    def _convert_line(line: LineNode) -> ParsedLine | None:
        """Convert a LineNode to ParsedLine.

        Args:
            line: LineNode from Lark parser

        Returns:
            ParsedLine or None if line is empty
        """
        if line.content is None:
            # Empty line - create paragraph with empty content
            return ParsedLine(
                original="",
                line_type=LineType.PARAGRAPH,
                content="",
                indent_level=line.indent,
            )

        return LarkParserAdapter._convert_content(line.content, line.indent)

    @staticmethod
    def _convert_content(content: ContentNode, indent: int) -> ParsedLine:
        """Convert ContentNode to ParsedLine.

        Args:
            content: Content node
            indent: Indentation level

        Returns:
            ParsedLine object
        """
        if isinstance(content, CodeBlockNode):
            return LarkParserAdapter._convert_code_block(content, indent)

        if isinstance(content, TableNode):
            return LarkParserAdapter._convert_table(content, indent)

        if isinstance(content, QuoteNode):
            return LarkParserAdapter._convert_quote(content, indent)

        if isinstance(content, CalloutNode):
            return LarkParserAdapter._convert_callout(content, indent)

        if isinstance(content, CommandNode):
            return LarkParserAdapter._convert_command(content, indent)

        if isinstance(content, ParagraphNode):
            return LarkParserAdapter._convert_paragraph(content, indent)

        # Fallback - should not reach here
        return ParsedLine(
            original=str(content),
            line_type=LineType.PARAGRAPH,
            content=str(content),
            indent_level=indent,
        )

    @staticmethod
    def _convert_code_block(content: CodeBlockNode, indent: int) -> ParsedLine:
        """Convert CodeBlockNode to ParsedLine."""
        return ParsedLine(
            original=f"code:{content.language}",
            line_type=LineType.CODE,
            content="",  # Code content comes in subsequent lines
            indent_level=indent,
            language=content.language,
        )

    @staticmethod
    def _convert_table(content: TableNode, indent: int) -> ParsedLine:
        """Convert TableNode to ParsedLine."""
        return ParsedLine(
            original=f"table:{content.name}",
            line_type=LineType.TABLE,
            content=content.name,
            indent_level=indent,
            table_rows=[],  # Table rows come in subsequent lines
        )

    @staticmethod
    def _convert_quote(content: QuoteNode, indent: int) -> ParsedLine:
        """Convert QuoteNode to ParsedLine."""
        return ParsedLine(
            original=f"> {content.content}",
            line_type=LineType.QUOTE,
            content=content.content.strip(),
            indent_level=indent,
        )

    @staticmethod
    def _convert_callout(content: CalloutNode, indent: int) -> ParsedLine:
        """Convert CalloutNode to ParsedLine (treat as quote with special formatting)."""
        # Callout doesn't have a specific LineType, treat as paragraph or quote
        return ParsedLine(
            original=f"? {content.content}",
            line_type=LineType.PARAGRAPH,
            content=f"💡 {content.content.strip()}",
            indent_level=indent,
        )

    @staticmethod
    def _convert_command(content: CommandNode, indent: int) -> ParsedLine:
        """Convert CommandNode to ParsedLine (treat as code)."""
        return ParsedLine(
            original=f"{content.prefix}{content.content}",
            line_type=LineType.CODE,
            content=f"{content.prefix}{content.content}",
            indent_level=indent,
            language="shell",
        )

    @staticmethod
    def _convert_paragraph(content: ParagraphNode, indent: int) -> ParsedLine:
        """Convert ParagraphNode to ParsedLine."""
        # Check if this is a list item (has indent)
        line_type = LineType.LIST if indent > 0 else LineType.PARAGRAPH

        # Convert inline elements to rich text
        rich_text = LarkParserAdapter._convert_inline_elements(content.content)

        # Extract plain text content
        plain_content = LarkParserAdapter._extract_plain_text(content.content)

        return ParsedLine(
            original=plain_content,
            line_type=line_type,
            content=plain_content,
            indent_level=indent,
            rich_text=rich_text if rich_text else None,
        )

    @staticmethod
    def _convert_inline_elements(elements: list[InlineNode]) -> list[RichTextElement]:
        """Convert inline elements to RichTextElement list.

        Args:
            elements: List of inline nodes

        Returns:
            List of RichTextElement objects
        """
        rich_text: list[RichTextElement] = []

        for element in elements:
            # Plain string
            if isinstance(element, str):
                if element:  # Skip empty strings
                    rich_text.append(RichTextElement(text=element))
                continue

            # Hashtag
            if isinstance(element, HashtagNode):
                rich_text.append(
                    RichTextElement(
                        text=f"#{element.tag}",
                        link_url=None,  # Could be converted to a link
                    )
                )
                continue

            # Inline code
            if isinstance(element, InlineCodeNode):
                rich_text.append(
                    RichTextElement(
                        text=element.code,
                        code=True,
                    )
                )
                continue

            # Page link
            if isinstance(element, PageLinkNode):
                rich_text.append(
                    RichTextElement(
                        text=f"[{element.page}]",
                        link_url=None,  # Internal links handled separately
                    )
                )
                continue

            # Image
            if isinstance(element, ImageNode):
                rich_text.append(
                    RichTextElement(
                        text=f"[{element.url}]",
                        link_url=element.url,
                    )
                )
                continue

            # Link with text
            if isinstance(element, LinkNode):
                text = element.text or element.url
                rich_text.append(
                    RichTextElement(
                        text=text,
                        link_url=element.url,
                    )
                )
                continue

            # Strong (bold) - extract the nested content
            if isinstance(element, StrongNode):
                # Extract text from the content node
                text = ""
                if isinstance(element.content, TextNode):
                    text = element.content.text
                elif isinstance(element.content, PageLinkNode):
                    text = element.content.page
                elif isinstance(element.content, ImageNode):
                    text = element.content.url
                else:
                    text = str(element.content)

                rich_text.append(
                    RichTextElement(
                        text=text,
                        bold=True,
                    )
                )
                continue

            # Decoration
            if isinstance(element, DecorationNode):
                rich_text.append(
                    RichTextElement(
                        text=element.text,
                        bold=element.bold,
                        italic=element.italic,
                        strikethrough=element.strike,
                        underline=element.underline,
                    )
                )
                continue

            # NOTE: Other inline node types not yet implemented
            # For now, convert to plain text
            rich_text.append(RichTextElement(text=str(element)))

        return rich_text

    @staticmethod
    def _extract_plain_text(elements: list[InlineNode]) -> str:
        """Extract plain text from inline elements.

        Args:
            elements: List of inline nodes

        Returns:
            Plain text string
        """
        parts: list[str] = []

        for element in elements:
            if isinstance(element, str):
                parts.append(element)
            elif isinstance(element, HashtagNode):
                parts.append(f"#{element.tag}")
            elif isinstance(element, InlineCodeNode):
                parts.append(f"`{element.code}`")
            elif isinstance(element, PageLinkNode):
                parts.append(f"[{element.page}]")
            elif isinstance(element, ImageNode):
                parts.append(f"[{element.url}]")
            elif isinstance(element, LinkNode):
                parts.append(element.text or element.url)
            elif isinstance(element, StrongNode):
                # Extract text from the strong node content
                if isinstance(element.content, TextNode):
                    text = element.content.text
                elif isinstance(element.content, PageLinkNode):
                    text = element.content.page
                elif isinstance(element.content, ImageNode):
                    text = element.content.url
                else:
                    text = str(element.content)
                parts.append(f"[[{text}]]")
            elif isinstance(element, DecorationNode):
                # Format with decoration symbols
                parts.append(f"[{element.symbols} {element.text}]")
            else:
                # NOTE: Other types not yet implemented
                parts.append(str(element))

        return "".join(parts)

    @staticmethod
    def extract_tags(text: str, parser: ScrapboxLarkParser) -> list[str]:
        """Extract hashtags from Scrapbox text using Lark parser.

        This method parses the text and extracts all hashtags, excluding those
        inside code blocks and inline code.

        Args:
            text: Scrapbox text to extract tags from
            parser: ScrapboxLarkParser instance to use for parsing

        Returns:
            List of unique tag names (without '#' prefix)
        """
        try:
            # Parse the document
            document = parser.parse(text)
            tags: set[str] = set()

            # Walk through all lines
            for line in document.lines:
                # Skip code blocks
                if isinstance(line.content, CodeBlockNode):
                    continue

                # Extract hashtags only from ParagraphNode (which has elements)
                if isinstance(line.content, ParagraphNode):
                    tags.update(LarkParserAdapter._extract_hashtags_from_elements(line.content.content))

            return sorted(tags)  # Return sorted for consistency

        except (LarkError, AttributeError):
            # Fallback: return empty list if parsing fails
            return []

    @staticmethod
    def _extract_hashtags_from_elements(elements: list[InlineNode]) -> set[str]:
        """Extract hashtag strings from inline elements.

        Args:
            elements: List of inline nodes

        Returns:
            Set of tag names (without '#' prefix)
        """
        tags: set[str] = set()

        for element in elements:
            if isinstance(element, HashtagNode):
                tags.add(element.tag)
            # NOTE: InlineCodeNode should not have its hashtags extracted
            # NOTE: Other bracket types may contain hashtags, but not implemented yet

        return tags
