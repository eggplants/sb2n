"""Converter from Scrapbox notation to Notion blocks."""

import logging
from typing import Any

from sb2n.notion_service import (
    BookmarkBlock,
    BulletedListBlock,
    CodeBlock,
    HeadingBlock,
    ImageBlock,
    NotionService,
    ParagraphBlock,
)
from sb2n.parser import ParsedLine, ScrapboxParser

logger = logging.getLogger(__name__)


class NotionBlockConverter:
    """Converter from Scrapbox notation to Notion blocks.

    This class takes parsed Scrapbox lines and converts them into
    Notion block objects that can be appended to a page.
    """

    def __init__(self, notion_service: NotionService) -> None:
        """Initialize the converter.

        Args:
            notion_service: Notion service for creating block objects
        """
        self.notion_service = notion_service

    def convert_to_blocks(self, text: str) -> list[dict[str, Any]]:
        """Convert Scrapbox text to Notion blocks.

        Args:
            text: Full Scrapbox page text

        Returns:
            List of Notion block objects
        """
        parsed_lines = ScrapboxParser.parse_text(text)
        blocks = []

        for parsed_line in parsed_lines:
            block = self._convert_line_to_block(parsed_line)
            if block:
                blocks.append(block)

        logger.debug(f"Converted {len(parsed_lines)} lines to {len(blocks)} blocks")
        return blocks

    def _convert_line_to_block(
        self, parsed_line: ParsedLine
    ) -> ParagraphBlock | HeadingBlock | CodeBlock | ImageBlock | BookmarkBlock | BulletedListBlock | None:
        """Convert a single parsed line to a Notion block.

        Args:
            parsed_line: Parsed line from Scrapbox

        Returns:
            Notion block object or None if line should be skipped
        """
        # Skip empty lines
        if not parsed_line.content and parsed_line.line_type == "paragraph":
            return None

        # Heading blocks
        if parsed_line.line_type in ["heading_2", "heading_3"]:
            level = int(parsed_line.line_type.split("_")[1])
            return self.notion_service.create_heading_block(parsed_line.content, level)

        # Code blocks
        if parsed_line.line_type == "code":
            return self.notion_service.create_code_block(parsed_line.content, parsed_line.language)

        # Image blocks
        if parsed_line.line_type == "image":
            return self.notion_service.create_image_block(parsed_line.content)

        # URL/Bookmark blocks
        if parsed_line.line_type == "url":
            return self.notion_service.create_bookmark_block(parsed_line.content)

        # List items
        if parsed_line.line_type == "list":
            return self.notion_service.create_bulleted_list_block(parsed_line.content)

        # Paragraph (default)
        if parsed_line.content:
            return self.notion_service.create_paragraph_block(parsed_line.content)

        return None
