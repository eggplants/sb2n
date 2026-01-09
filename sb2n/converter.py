"""Converter from Scrapbox notation to Notion blocks."""

import logging
from typing import TYPE_CHECKING

from sb2n.parser import ParsedLine, RichTextElement, ScrapboxParser

if TYPE_CHECKING:
    from pydantic_api.notion.models.objects import BlockObject

    from sb2n.notion_service import NotionService
    from sb2n.scrapbox_service import ScrapboxService

logger = logging.getLogger(__name__)


class NotionBlockConverter:
    """Converter from Scrapbox notation to Notion blocks.

    This class takes parsed Scrapbox lines and converts them into
    Notion block objects that can be appended to a page.
    """

    def __init__(self, notion_service: NotionService, scrapbox_service: ScrapboxService | None = None) -> None:
        """Initialize the converter.

        Args:
            notion_service: Notion service for creating block objects
            scrapbox_service: Optional Scrapbox service for downloading images
        """
        self.notion_service = notion_service
        self.scrapbox_service = scrapbox_service

    def convert_to_blocks(self, text: str) -> list[BlockObject]:
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

        logger.debug(
            "Converted %(parsed_lines)d lines to %(blocks)d blocks",
            {"parsed_lines": len(parsed_lines), "blocks": len(blocks)},
        )
        return blocks

    def _convert_line_to_block(self, parsed_line: ParsedLine) -> BlockObject | None:  # noqa: C901, PLR0911
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
            # Use rich_text if available, otherwise use plain content
            text = parsed_line.rich_text if parsed_line.rich_text else parsed_line.content
            return self.notion_service.create_heading_block(text, level)

        # Quote blocks
        if parsed_line.line_type == "quote":
            text = parsed_line.rich_text if parsed_line.rich_text else parsed_line.content
            return self.notion_service.create_quote_block(text)

        # Code blocks
        if parsed_line.line_type == "code":
            return self.notion_service.create_code_block(parsed_line.content, parsed_line.language)

        # Image blocks
        if parsed_line.line_type == "image":
            return self._create_image_block(parsed_line.content)

        # External link with display text
        if parsed_line.line_type == "external_link":
            # Create a paragraph with a link
            if parsed_line.link_text:
                link_element = RichTextElement(
                    text=parsed_line.link_text,
                    link_url=parsed_line.content,
                )
                return self.notion_service.create_paragraph_block([link_element])
            # Fallback to bookmark
            return self.notion_service.create_bookmark_block(parsed_line.content)

        # URL/Bookmark blocks
        if parsed_line.line_type == "url":
            return self.notion_service.create_bookmark_block(parsed_line.content)

        # Table start (create as paragraph for now - full table support would require more complex logic)
        if parsed_line.line_type == "table_start":
            # For now, just create a heading to indicate table start
            # Full table implementation would require parsing subsequent lines
            return self.notion_service.create_heading_block(f"Table: {parsed_line.table_name}", 3)

        # List items
        if parsed_line.line_type == "list":
            text = parsed_line.rich_text if parsed_line.rich_text else parsed_line.content
            return self.notion_service.create_bulleted_list_block(text)

        # Paragraphs
        if parsed_line.content:
            text = parsed_line.rich_text if parsed_line.rich_text else parsed_line.content
            return self.notion_service.create_paragraph_block(text)

        return None

    def _create_image_block(self, image_url: str):  # noqa: ANN202
        """Create an image block, downloading from Scrapbox if necessary.

        Args:
            image_url: Image URL from Scrapbox

        Returns:
            Image block object or None if creation failed
        """
        # Download and upload all images using Scrapbox's get_file
        if self.scrapbox_service:
            try:
                # Download image from Scrapbox using get_file
                # get_file supports various image URLs including Gyazo, Scrapbox internal, etc.
                logger.debug("Downloading image from Scrapbox: %(image_url)s", {"image_url": image_url})
                image_data = self.scrapbox_service.download_file(image_url)

                # Extract filename from URL
                filename = image_url.split("/")[-1] if "/" in image_url else "image.png"
                # Ensure filename has an extension
                if "." not in filename:
                    filename += ".png"

                # Upload to Notion
                file_upload_id = self.notion_service.upload_image(image_data, filename)
                return self.notion_service.create_image_block(image_url, file_upload_id)

            except Exception:
                logger.exception("Failed to download/upload image: %(image_url)s", {"image_url": image_url})
                # Fall back to external URL
                return self.notion_service.create_image_block(image_url)
        else:
            # No Scrapbox service available, use external URL directly
            return self.notion_service.create_image_block(image_url)
