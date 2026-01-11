"""Link restorer for converting Scrapbox internal links to Notion page mentions."""

import logging
import re
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from re import Pattern

    from sb2n.notion_service import NotionService

logger = logging.getLogger(__name__)


class LinkRestorer:
    """Restore Scrapbox internal links in Notion pages.

    This class processes Notion pages to find Scrapbox-style internal links
    ([PageName] format) and converts them to actual Notion page mentions.
    """

    # Pattern to detect Scrapbox internal links: [PageName]
    # Excludes: URLs, images, decorations, and already-linked text
    INTERNAL_LINK_PATTERN: Final[Pattern[str]] = re.compile(
        r"(?<!\[)"  # Not preceded by [
        r"\[(?!"  # Start with [ but not followed by:
        r"https?://|"  # URLs
        r"[*\-/_\[]|"  # Decorations: *, -, /, _, [
        r"[^\]]+\.(?:jpg|jpeg|png|gif|webp|svg)\]"  # Image extensions (non-capturing)
        r")"
        r"([^\]]+)"  # Capture the page name
        r"\]"  # End with ]
        r"(?!\])"  # Not followed by ]
    )

    # Block types that contain rich_text
    TEXT_BLOCK_TYPES: Final[set[str]] = {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "quote",
        "callout",
        "toggle",
    }

    def __init__(self, notion_service: NotionService, *, dry_run: bool = False) -> None:
        """Initialize link restorer.

        Args:
            notion_service: NotionService instance
            dry_run: If True, only report changes without applying them
        """
        self.notion_service = notion_service
        self.dry_run = dry_run
        self.stats = {
            "pages_processed": 0,
            "pages_updated": 0,
            "links_found": 0,
            "links_restored": 0,
            "errors": 0,
        }

    def restore_all_links(self, page_titles: list[str] | None = None) -> dict[str, int]:
        """Restore internal links in all pages.

        Args:
            page_titles: Optional list of specific page titles to process.
                        If None, process all pages in database.

        Returns:
            Statistics dictionary with counts of processed pages, updated links, etc.
        """
        logger.info("Starting link restoration process")

        # Step 1: Build page title to ID mapping
        logger.info("Building page title to ID mapping...")
        title_to_id = self.notion_service.get_page_title_to_id_map()

        if not title_to_id:
            logger.warning("No pages found in database")
            return self.stats

        # Filter by specified page titles if provided
        if page_titles:
            title_to_id = {title: page_id for title, page_id in title_to_id.items() if title in page_titles}
            logger.info("Processing %(count)d specified pages", {"count": len(title_to_id)})
        else:
            logger.info("Processing all %(count)d pages", {"count": len(title_to_id)})

        # Step 2: Process each page
        for title, page_id in title_to_id.items():
            try:
                self._process_page(page_id, title, title_to_id)
                self.stats["pages_processed"] += 1
            except Exception:
                logger.exception("Failed to process page: %(title)s", {"title": title})
                self.stats["errors"] += 1
                continue

        # Step 3: Report summary
        self._log_summary()

        return self.stats

    def _process_page(self, page_id: str, page_title: str, title_to_id: dict[str, str]) -> None:
        """Process a single page to restore links.

        Args:
            page_id: Notion page ID
            page_title: Page title
            title_to_id: Mapping of all page titles to IDs
        """
        logger.debug("Processing page: %(title)s", {"title": page_title})

        # Get all blocks in the page
        blocks = self.notion_service.get_page_blocks(page_id, recursive=True)

        page_updated = False

        for block in blocks:
            try:
                if self._process_block(block, title_to_id):
                    page_updated = True
            except Exception:
                logger.exception("Failed to process block: %(block_id)s", {"block_id": block.get("id")})
                self.stats["errors"] += 1
                continue

        if page_updated:
            self.stats["pages_updated"] += 1
            logger.info("Updated page: %(title)s", {"title": page_title})

    def _process_block(self, block: dict[str, Any], title_to_id: dict[str, str]) -> bool:
        """Process a single block to restore links.

        Args:
            block: Block object
            title_to_id: Mapping of page titles to IDs

        Returns:
            True if block was updated, False otherwise
        """
        block_type = block.get("type")
        if block_type not in self.TEXT_BLOCK_TYPES:
            return False

        # Get rich_text array from block
        block_content = block.get(block_type, {})
        rich_text = block_content.get("rich_text", [])

        if not rich_text:
            return False

        # Process rich_text to find and replace internal links
        new_rich_text, links_found, links_replaced = self._process_rich_text(rich_text, title_to_id)

        self.stats["links_found"] += links_found

        if links_replaced == 0:
            return False

        self.stats["links_restored"] += links_replaced

        # Update block if not dry run
        if not self.dry_run:
            block_data = {block_type: {"rich_text": new_rich_text}}
            self.notion_service.update_block(block["id"], block_data)
            logger.debug(
                "Updated block %(block_id)s: %(replaced)d links restored",
                {"block_id": block["id"], "replaced": links_replaced},
            )
        else:
            logger.info(
                "[DRY RUN] Would update block %(block_id)s: %(replaced)d links",
                {"block_id": block["id"], "replaced": links_replaced},
            )

        return True

    def _process_rich_text(
        self, rich_text: list[dict[str, Any]], title_to_id: dict[str, str]
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Process rich_text array to find and replace internal links.

        Args:
            rich_text: Original rich_text array
            title_to_id: Mapping of page titles to IDs

        Returns:
            Tuple of (new_rich_text, links_found, links_replaced)
        """
        new_rich_text: list[dict[str, Any]] = []
        links_found = 0
        links_replaced = 0

        for rt_elem in rich_text:
            # Skip if already a mention or has a link
            if rt_elem.get("type") == "mention":  # noqa: PLR2004
                new_rich_text.append(rt_elem)
                continue

            if rt_elem.get("type") != "text":  # noqa: PLR2004
                new_rich_text.append(rt_elem)
                continue

            # Skip inline code elements
            annotations = rt_elem.get("annotations", {})
            if annotations.get("code"):
                new_rich_text.append(rt_elem)
                continue

            text_content = rt_elem.get("text", {}).get("content", "")
            text_link = rt_elem.get("text", {}).get("link")

            # Skip if already has a link
            if text_link:
                new_rich_text.append(rt_elem)
                continue

            # Find internal link patterns in text
            matches = list(self.INTERNAL_LINK_PATTERN.finditer(text_content))

            if not matches:
                new_rich_text.append(rt_elem)
                continue

            # Process text with internal links
            annotations = rt_elem.get("annotations", {})
            last_pos = 0

            for match in matches:
                page_name = match.group(1)
                links_found += 1

                # Check if page exists in database
                target_page_id = title_to_id.get(page_name)

                # Add text before the link
                if match.start() > last_pos:
                    before_text = text_content[last_pos : match.start()]
                    new_rich_text.append(
                        {
                            "type": "text",
                            "text": {"content": before_text},
                            "annotations": annotations,
                        }
                    )

                if target_page_id:
                    # Replace with page mention
                    new_rich_text.append(
                        {
                            "type": "mention",
                            "mention": {"type": "page", "page": {"id": target_page_id}},
                            "annotations": annotations,
                        }
                    )
                    links_replaced += 1
                    logger.debug("Found link to page: %(page_name)s", {"page_name": page_name})
                else:
                    # Keep original text if page not found
                    new_rich_text.append(
                        {
                            "type": "text",
                            "text": {"content": match.group(0)},
                            "annotations": annotations,
                        }
                    )
                    logger.debug("Page not found for link: %(page_name)s", {"page_name": page_name})

                last_pos = match.end()

            # Add remaining text after last link
            if last_pos < len(text_content):
                after_text = text_content[last_pos:]
                new_rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": after_text},
                        "annotations": annotations,
                    }
                )

        return new_rich_text, links_found, links_replaced

    def _log_summary(self) -> None:
        """Log summary of link restoration process."""
        logger.info("=" * 60)
        logger.info("LINK RESTORATION SUMMARY")
        logger.info("=" * 60)
        logger.info("Pages processed:     %(count)d", {"count": self.stats["pages_processed"]})
        logger.info("Pages updated:       %(count)d", {"count": self.stats["pages_updated"]})
        logger.info("Links found:         %(count)d", {"count": self.stats["links_found"]})
        logger.info("Links restored:      %(count)d", {"count": self.stats["links_restored"]})
        logger.info("Errors:              %(count)d", {"count": self.stats["errors"]})
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("[DRY RUN] No changes were applied")
