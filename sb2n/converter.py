"""Converter from Scrapbox notation to Notion blocks."""

import logging
from typing import TYPE_CHECKING, Any

from sb2n.parser import LineType, ParsedLine, RichTextElement, ScrapboxParser

if TYPE_CHECKING:
    from sb2n.models import BlockObject
    from sb2n.notion_service import NotionService
    from sb2n.scrapbox_service import ScrapboxService

logger = logging.getLogger(__name__)


class NotionBlockConverter:
    """Converter from Scrapbox notation to Notion blocks.

    This class takes parsed Scrapbox lines and converts them into
    Notion block objects that can be appended to a page.
    """

    def __init__(
        self,
        notion_service: NotionService,
        scrapbox_service: ScrapboxService | None = None,
        *,
        enable_icon: bool = False,
    ) -> None:
        """Initialize the converter.

        Args:
            notion_service: Notion service for creating block objects
            scrapbox_service: Optional Scrapbox service for downloading images and fetching icons
            enable_icon: If True, fetch and convert Scrapbox icon notation
        """
        self.notion_service = notion_service
        self.scrapbox_service = scrapbox_service
        self.enable_icon = enable_icon
        self.scrapbox_service = scrapbox_service

    def convert_to_blocks(self, text: str) -> list[BlockObject]:
        """Convert Scrapbox text to Notion blocks.

        Args:
            text: Full Scrapbox page text

        Returns:
            List of Notion block objects
        """
        project_name = self.scrapbox_service.project_name if self.scrapbox_service else None
        parsed_lines = ScrapboxParser.parse_text(text, project_name)
        blocks = []

        # Stack to track parent blocks and their dictionaries at each indent level
        # Store: `(indent_level, block_object, block_dict)`
        # block_dict is what gets modified when adding children
        list_stack: list[tuple[int, BlockObject, dict[str, Any]]] = []

        for parsed_line in parsed_lines:
            # Handle list items with nesting
            if parsed_line.line_type == LineType.LIST:
                # Notion API only supports 2 levels of nesting (3 total levels including top)
                effective_indent = min(parsed_line.indent_level, 2)

                # Pop stack until we find the correct parent level
                # Parent should have indent_level < current indent_level
                while list_stack and list_stack[-1][0] >= effective_indent:
                    list_stack.pop()

                # Create the list item block
                block = self._convert_line_to_block(parsed_line)
                if block:
                    # _convert_line_to_block may return a list of blocks (e.g., split code blocks)
                    blocks_to_add = block if isinstance(block, list) else [block]

                    for single_block in blocks_to_add:
                        if list_stack:
                            # Convert to dict immediately
                            block_dict = single_block.model_dump(mode="json", exclude_none=True)

                            # Add as child to the most recent parent
                            _, _, parent_dict = list_stack[-1]
                            # Ensure parent has children array
                            # parent_dict might be the full block dict or just the bulleted_list_item dict
                            item_dict = parent_dict.get("bulleted_list_item", parent_dict)
                            if "children" not in item_dict:  # noqa: PLR2004
                                item_dict["children"] = []

                            # Notion API limit: bulleted_list_item.children.length should be ≤ 100
                            if len(item_dict["children"]) >= 100:
                                logger.warning(
                                    "List item has %(count)d children (max 100). Creating new top-level list item instead.",  # noqa: E501
                                    {"count": len(item_dict["children"])},
                                )
                                # Add as top-level block instead
                                blocks.append(single_block)
                                # Clear list stack to prevent further nesting issues
                                list_stack = []
                            else:
                                # Add block dict to parent's children
                                item_dict["children"].append(block_dict)
                                # Add current block dict to stack so it can have children too
                                if single_block == blocks_to_add[0]:  # Only first block goes on stack
                                    list_stack.append(
                                        (effective_indent, single_block, block_dict["bulleted_list_item"])
                                    )
                        else:
                            # Top-level list item - we need to use the pydantic object's internal dict
                            # so that modifications to it will be reflected in the final output
                            blocks.append(single_block)
                            # Get reference to the block's internal dict for modifications
                            if single_block == blocks_to_add[0]:  # Only first block goes on stack
                                block_dict = single_block.bulleted_list_item  # ty:ignore[possibly-missing-attribute]
                                list_stack.append((effective_indent, single_block, block_dict))
            else:
                # For non-list items, check if they should be nested in a list item
                block = self._convert_line_to_block(parsed_line)
                if block:
                    # _convert_line_to_block may return a list of blocks (e.g., split code blocks)
                    blocks_to_add = block if isinstance(block, list) else [block]

                    for single_block in blocks_to_add:
                        # Tables cannot be nested inside list items in Notion API
                        # So treat them as top-level blocks and clear the list stack
                        if parsed_line.line_type == LineType.TABLE:
                            blocks.append(single_block)
                            list_stack = []  # Clear stack as tables break nesting
                        # If the block has an indent level and there's an active list context
                        elif parsed_line.indent_level > 0 and list_stack:
                            # Pop stack until we find a parent with lower indent level
                            while list_stack and list_stack[-1][0] >= parsed_line.indent_level:
                                list_stack.pop()

                            if list_stack:
                                # Add this block as child to the most recent list item
                                block_dict = single_block.model_dump(mode="json", exclude_none=True)
                                _, _, parent_dict = list_stack[-1]
                                item_dict = parent_dict.get("bulleted_list_item", parent_dict)
                                if "children" not in item_dict:  # noqa: PLR2004
                                    item_dict["children"] = []

                                # Notion API limit: bulleted_list_item.children.length should be ≤ 100
                                if len(item_dict["children"]) >= 100:
                                    logger.warning(
                                        "List item has %(count)d children (max 100). Creating new top-level block instead.",  # noqa: E501
                                        {"count": len(item_dict["children"])},
                                    )
                                    # Add as top-level block instead
                                    blocks.append(single_block)
                                    list_stack = []
                                else:
                                    item_dict["children"].append(block_dict)
                            else:
                                # No suitable parent, add to top level
                                blocks.append(single_block)
                                list_stack = []  # Clear stack
                        else:
                            # Top-level block (no indent or no list context)
                            blocks.append(single_block)
                            list_stack = []  # Clear stack for top-level non-list items

        logger.debug(
            "Converted %(parsed_lines)d lines to %(blocks)d blocks",
            {"parsed_lines": len(parsed_lines), "blocks": len(blocks)},
        )
        return blocks

    def _convert_line_to_block(self, parsed_line: ParsedLine) -> BlockObject | list[BlockObject] | None:
        """Convert a single parsed line to a Notion block.

        Args:
            parsed_line: Parsed line from Scrapbox

        Returns:
            Notion block object, list of block objects (for split blocks), or None if line should be skipped
        """
        # Skip empty lines
        if not parsed_line.content and parsed_line.line_type == LineType.PARAGRAPH:
            return None

        # Heading blocks
        if parsed_line.line_type in [LineType.HEADING_1, LineType.HEADING_2, LineType.HEADING_3]:
            level = int(parsed_line.line_type.value.split("_")[1])
            # Use rich_text if available, otherwise use plain content
            text = parsed_line.rich_text or parsed_line.content
            return self.notion_service.create_heading_block(text, level)

        # Quote blocks
        if parsed_line.line_type == LineType.QUOTE:
            text = parsed_line.rich_text or parsed_line.content
            return self.notion_service.create_quote_block(text)

        # Code blocks
        if parsed_line.line_type == LineType.CODE_START:
            return self.notion_service.create_code_block(parsed_line.content, parsed_line.language)  # ty:ignore[invalid-return-type]

        if parsed_line.line_type == LineType.CODE:
            return self.notion_service.create_code_block(parsed_line.content, parsed_line.language)  # ty:ignore[invalid-return-type]

        # Image blocks
        if parsed_line.line_type == LineType.IMAGE:
            block = self._create_image_block(parsed_line.content)
            return block or None

        # Icon blocks - fetch icon URL from Scrapbox and create image block
        if parsed_line.line_type == LineType.ICON:
            # Only process icons if enable_icon is True
            if self.enable_icon and self.scrapbox_service and parsed_line.icon_page_name:
                icon_url = self.scrapbox_service.get_page_icon_url(parsed_line.icon_page_name, parsed_line.icon_project)
                if icon_url:
                    block = self._create_image_block(icon_url)
                    if block:
                        return block
                # If no icon found, create a paragraph with the original text
                logger.warning(
                    "Icon not found for page: %(page_name)s, creating paragraph instead",
                    {"page_name": parsed_line.icon_page_name},
                )
            # If icon migration is disabled or service unavailable, preserve original format
            # Use original text to preserve [/icons/hr.icon] format
            return self.notion_service.create_paragraph_block(parsed_line.original.strip())

        # External link with display text
        if parsed_line.line_type == LineType.EXTERNAL_LINK:
            # Create a paragraph with a link
            if parsed_line.link_text:
                link_element = RichTextElement(
                    text=parsed_line.link_text,
                    link_url=parsed_line.content,
                )
                return self.notion_service.create_paragraph_block([link_element])
            # Fallback to bookmark
            block = self.notion_service.create_bookmark_block(parsed_line.content)
            return block or None

        # URL/Bookmark blocks - convert to paragraph with link
        if parsed_line.line_type == LineType.URL:
            # Create a rich text element with the URL as both text and link
            rich_text = [RichTextElement(text=parsed_line.content, link_url=parsed_line.content)]
            return self.notion_service.create_paragraph_block(rich_text)

        # Table blocks
        if parsed_line.line_type == LineType.TABLE:
            if parsed_line.table_rows:
                # create_table_block may return a single table or a list of tables (if split)
                return self.notion_service.create_table_block(parsed_line.table_rows)  # type: ignore[return-value]
            # Fallback if no rows
            return self.notion_service.create_heading_block(f"Table: {parsed_line.table_name}", 3)

        # Table start (shouldn't happen with new parser, but keep for safety)
        if parsed_line.line_type == LineType.TABLE_START:
            # For now, just create a heading to indicate table start
            # Full table implementation would require parsing subsequent lines
            return self.notion_service.create_heading_block(f"Table: {parsed_line.table_name}", 3)

        # List items
        if parsed_line.line_type == LineType.LIST:
            text = parsed_line.rich_text or parsed_line.content
            return self.notion_service.create_bulleted_list_block(text)

        # Paragraphs
        if parsed_line.content:
            text = parsed_line.rich_text or parsed_line.content
            return self.notion_service.create_paragraph_block(text)

        return None

    def _create_image_block(self, image_url: str) -> BlockObject | None:
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
                filename = (
                    image_url.rsplit("/", maxsplit=1)[-1]
                    if "/" in image_url  # noqa: PLR2004
                    else "image.png"
                )
                # Ensure filename has an extension
                if "." not in filename:  # noqa: PLR2004
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
