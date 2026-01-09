"""Notion API client wrapper."""

import logging
from datetime import datetime
from typing import Any, TypedDict

from notion_client import Client

logger = logging.getLogger(__name__)


class RichText(TypedDict):
    """Rich text object for Notion blocks."""

    type: str
    text: dict[str, Any]


class ParagraphBlock(TypedDict):
    """Paragraph block object."""

    object: str
    type: str
    paragraph: dict[str, Any]


class HeadingBlock(TypedDict, total=False):
    """Heading block object."""

    object: str
    type: str
    heading_2: dict[str, Any]
    heading_3: dict[str, Any]


class BulletedListBlock(TypedDict):
    """Bulleted list item block object."""

    object: str
    type: str
    bulleted_list_item: dict[str, Any]


class CodeBlock(TypedDict):
    """Code block object."""

    object: str
    type: str
    code: dict[str, Any]


class ImageBlock(TypedDict):
    """Image block object."""

    object: str
    type: str
    image: dict[str, Any]


class BookmarkBlock(TypedDict):
    """Bookmark block object."""

    object: str
    type: str
    bookmark: dict[str, Any]


class NotionService:
    """Service for interacting with Notion API.

    This class wraps the Notion Client to provide convenient methods for
    creating database pages and adding blocks.
    """

    def __init__(self, api_key: str, database_id: str) -> None:
        """Initialize Notion service.

        Args:
            api_key: Notion Integration API key
            database_id: Target database ID for migration
        """
        self.api_key = api_key
        self.database_id = database_id
        self.client = Client(auth=api_key)

    def get_existing_page_titles(self) -> set[str]:
        """Get all existing page titles from the database.

        Returns:
            Set of page titles currently in the database
        """
        logger.info("Fetching existing pages from Notion database")
        existing_titles: set[str] = set()

        try:
            # Query the database with pagination
            has_more = True
            start_cursor = None

            while has_more:
                query_params: dict[str, Any] = {
                    "database_id": self.database_id,
                    "page_size": 100,
                }
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response: dict[str, Any] = self.client.databases.query(**query_params)  # type: ignore[assignment]

                for page in response.get("results", []):
                    # Extract title from properties
                    properties = page.get("properties", {})
                    title_prop = properties.get("Title", {}) or properties.get("Name", {})
                    title_content = title_prop.get("title", [])
                    if title_content:
                        title = title_content[0].get("text", {}).get("content", "")
                        if title:
                            existing_titles.add(title)

                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            logger.info(f"Found {len(existing_titles)} existing pages in Notion")
            return existing_titles

        except Exception:
            logger.exception("Failed to fetch existing pages from Notion")
            raise

    def create_database_page(
        self,
        title: str,
        scrapbox_url: str,
        created_date: datetime,
        tags: list[str],
    ) -> dict[str, Any]:
        """Create a new page in the Notion database.

        Args:
            title: Page title
            scrapbox_url: URL to the original Scrapbox page
            created_date: Original creation date from Scrapbox
            tags: List of tags

        Returns:
            Created page object from Notion API

        Raises:
            Exception: If page creation fails
        """
        logger.debug(f"Creating Notion page: {title}")

        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Scrapbox URL": {"url": scrapbox_url},
            "Created Date": {"date": {"start": created_date.isoformat()}},
        }

        if tags:
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

        try:
            response: dict[str, Any] = self.client.pages.create(  # type: ignore[assignment]
                parent={"database_id": self.database_id},
                properties=properties,
            )
            logger.info(f"Created page: {title} (ID: {response['id']})")
            return response
        except Exception:
            logger.exception(f"Failed to create page: {title}")
            raise

    def append_blocks(self, page_id: str, blocks: list[dict[str, Any]]) -> None:
        """Append blocks to a Notion page.

        Args:
            page_id: Notion page ID
            blocks: List of block objects to append

        Raises:
            Exception: If block append fails
        """
        if not blocks:
            logger.debug(f"No blocks to append for page: {page_id}")
            return

        logger.debug(f"Appending {len(blocks)} blocks to page: {page_id}")

        try:
            # Notion API has a limit of 100 blocks per request
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i : i + batch_size]
                self.client.blocks.children.append(block_id=page_id, children=batch)
                logger.debug(f"Appended batch {i // batch_size + 1} ({len(batch)} blocks)")

            logger.info(f"Successfully appended {len(blocks)} blocks")
        except Exception:
            logger.exception(f"Failed to append blocks to page: {page_id}")
            raise

    def create_paragraph_block(self, text: str) -> ParagraphBlock:
        """Create a paragraph block.

        Args:
            text: Paragraph text content

        Returns:
            Paragraph block object
        """
        return ParagraphBlock(
            object="block",
            type="paragraph",
            paragraph={"rich_text": [{"type": "text", "text": {"content": text}}]},
        )

    def create_heading_block(self, text: str, level: int = 2) -> HeadingBlock:
        """Create a heading block.

        Args:
            text: Heading text content
            level: Heading level (2 or 3)

        Returns:
            Heading block object
        """
        heading_type = f"heading_{level}"
        block: HeadingBlock = {
            "object": "block",
            "type": heading_type,
        }
        block[heading_type] = {"rich_text": [{"type": "text", "text": {"content": text}}]}  # type: ignore[literal-required]
        return block

    def create_bulleted_list_block(self, text: str) -> BulletedListBlock:
        """Create a bulleted list item block.

        Args:
            text: List item text content

        Returns:
            Bulleted list item block object
        """
        return BulletedListBlock(
            object="block",
            type="bulleted_list_item",
            bulleted_list_item={"rich_text": [{"type": "text", "text": {"content": text}}]},
        )

    def create_code_block(self, code: str, language: str = "plain text") -> CodeBlock:
        """Create a code block.

        Args:
            code: Code content
            language: Programming language (default: "plain text")

        Returns:
            Code block object
        """
        return CodeBlock(
            object="block",
            type="code",
            code={
                "rich_text": [{"type": "text", "text": {"content": code}}],
                "language": language,
            },
        )

    def create_image_block(self, url: str) -> ImageBlock:
        """Create an external image block.

        Args:
            url: External image URL

        Returns:
            Image block object
        """
        return ImageBlock(
            object="block",
            type="image",
            image={"type": "external", "external": {"url": url}},
        )

    def create_bookmark_block(self, url: str) -> BookmarkBlock:
        """Create a bookmark block.

        Args:
            url: URL to bookmark

        Returns:
            Bookmark block object
        """
        return BookmarkBlock(object="block", type="bookmark", bookmark={"url": url})
