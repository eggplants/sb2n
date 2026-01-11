"""Notion API client wrapper."""

import logging
from io import BytesIO
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from notion_client import Client
from pydantic import BaseModel

from sb2n.models import (
    BlockObject,
    BookmarkBlock,
    BulletedListItemBlock,
    CodeBlock,
    CreatePageRequest,
    Heading2Block,
    Heading3Block,
    ImageBlock,
    ParagraphBlock,
    QueryDatabaseRequest,
    QueryDatabaseResponse,
    QuoteBlock,
)

if TYPE_CHECKING:
    from datetime import datetime

    from notion_client.typing import SyncAsync

    from sb2n.parser import RichTextElement

logger = logging.getLogger(__name__)


class FileUploadResponse(BaseModel):
    """Response from file_uploads.create() API.

    Reference: https://developers.notion.com/reference/create-a-file-upload

    Note: this schema is not yet included in pydantic-api-models-notion.
    """

    id: str
    object: Literal["file_upload"]
    created_time: str
    last_edited_time: str
    expiry_time: str
    upload_url: str
    archived: bool
    status: Literal["pending", "completed", "failed"]
    filename: str
    content_type: str
    content_length: int


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
                # Create query request
                query_request = QueryDatabaseRequest(
                    database_id=UUID(self.database_id),
                    page_size=100,
                    start_cursor=start_cursor,
                )

                # Execute query
                response_dict = self.client.databases.query(**query_request.model_dump(mode="json", exclude_none=True))  # ty:ignore[possibly-missing-attribute]
                response = QueryDatabaseResponse.model_validate(response_dict)

                for page in response.results:
                    # Extract title from properties
                    properties = page.properties if hasattr(page, "properties") else {}
                    title_prop = properties.get("Title") or properties.get("Name")  # ty:ignore[unresolved-attribute]
                    if title_prop and hasattr(title_prop, "title"):
                        title_content = title_prop.title
                        if title_content:
                            title_text = title_content[0].plain_text if hasattr(title_content[0], "plain_text") else ""
                            if title_text:
                                existing_titles.add(title_text)

                has_more = response.has_more or False
                start_cursor = response.next_cursor

            logger.info("Found %(count)d existing pages in Notion", {"count": len(existing_titles)})
        except Exception:
            logger.exception("Failed to fetch existing pages from Notion")
            raise
        else:
            return existing_titles

    def create_database_page(
        self,
        title: str,
        scrapbox_url: str,
        created_date: datetime,
        tags: list[str],
    ) -> dict | SyncAsync:
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
        logger.debug("Creating Notion page: %(title)s", {"title": title})

        properties = {
            "Title": {
                "type": "title",
                "title": [{"type": "text", "text": {"content": title}}],
            },
            "Scrapbox URL": {"type": "url", "url": scrapbox_url},
            "Created Date": {
                "type": "date",
                "date": {"start": created_date.isoformat()},
            },
        }

        if tags:
            properties["Tags"] = {
                "type": "multi_select",
                "multi_select": [{"name": tag} for tag in tags],
            }

        try:
            # Create request object
            create_request = CreatePageRequest(
                parent={"database_id": self.database_id},
                properties=properties,
            )

            # Execute request
            response_dict = self.client.pages.create(**create_request.model_dump(mode="json", exclude_none=True))

            # Return raw dict instead of validating with Page model
            # because pydantic-api-models-notion may not support all parent types (e.g., data_source_id)
            logger.info("Created page: %(title)s (ID: %(id)s)", {"title": title, "id": response_dict["id"]})  # ty:ignore[not-subscriptable]
        except Exception:
            logger.exception("Failed to create page: %(title)s", {"title": title})
            raise
        else:
            return response_dict

    def append_blocks(self, page_id: UUID, blocks: list[BlockObject]) -> None:
        """Append blocks to a Notion page.

        Args:
            page_id: Notion page ID
            blocks: List of block objects to append

        Raises:
            Exception: If block append fails
        """
        if not blocks:
            logger.debug("No blocks to append for page: %(page_id)s", {"page_id": page_id})
            return

        logger.debug("Appending %(count)d blocks to page: %(page_id)s", {"count": len(blocks), "page_id": page_id})

        try:
            # Notion API has a limit of 100 blocks per request
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i : i + batch_size]
                # Convert pydantic models to dicts, or use dict directly
                batch_dicts = [
                    block.model_dump(mode="json", exclude_none=True) if hasattr(block, "model_dump") else block
                    for block in batch
                ]
                self.client.blocks.children.append(block_id=str(page_id), children=batch_dicts)
                logger.debug(
                    "Appended batch %(batch_num)d (%(count)d blocks)",
                    {"batch_num": i // batch_size + 1, "count": len(batch)},
                )

            logger.info("Successfully appended %(count)d blocks", {"count": len(blocks)})
        except Exception:
            logger.exception("Failed to append blocks to page: %(page_id)s", {"page_id": page_id})
            raise

    def create_paragraph_block(self, text: str | list[RichTextElement]) -> ParagraphBlock:
        """Create a paragraph block.

        Args:
            text: Paragraph text content (plain string or rich text elements)

        Returns:
            Paragraph block object
        """
        if isinstance(text, str):
            return ParagraphBlock.new(rich_text=text)
        rich_text_array = self._convert_rich_text_elements(text)
        return ParagraphBlock(
            type="paragraph",
            paragraph={"rich_text": rich_text_array, "color": "default"},
        )

    def create_heading_block(self, text: str | list[RichTextElement], level: int = 2) -> Heading2Block | Heading3Block:
        """Create a heading block.

        Args:
            text: Heading text content (plain string or rich text elements)
            level: Heading level (2 or 3)

        Returns:
            Heading block object
        """
        if isinstance(text, str):
            if level == 2:
                return Heading2Block.new(rich_text=text)
            return Heading3Block.new(rich_text=text)
        rich_text_array = self._convert_rich_text_elements(text)
        if level == 2:
            return Heading2Block(
                type="heading_2",
                heading_2={"rich_text": rich_text_array, "color": "default", "is_toggleable": False},
            )
        return Heading3Block(
            type="heading_3",
            heading_3={"rich_text": rich_text_array, "color": "default", "is_toggleable": False},
        )

    def create_bulleted_list_block(self, text: str | list[RichTextElement]) -> BulletedListItemBlock:
        """Create a bulleted list item block.

        Args:
            text: List item text content (plain string or rich text elements)

        Returns:
            Bulleted list item block object
        """
        if isinstance(text, str):
            return BulletedListItemBlock.new(rich_text=text)
        rich_text_array = self._convert_rich_text_elements(text)
        return BulletedListItemBlock(
            type="bulleted_list_item",
            bulleted_list_item={"rich_text": rich_text_array, "color": "default"},
        )

    def create_code_block(self, code: str, language: str = "plain text") -> CodeBlock:
        """Create a code block.

        Args:
            code: Code content
            language: Programming language (default: "plain text")

        Returns:
            Code block object
        """
        return CodeBlock.new(code=code, language=language)

    def create_image_block(self, url: str, file_upload_id: str | None = None) -> ImageBlock:
        """Create an image block.

        Args:
            url: External image URL (used if file_upload_id is not provided)
            file_upload_id: Optional file upload ID from Notion's file_uploads API

        Returns:
            Image block object
        """
        if file_upload_id:
            # Use uploaded file from Notion - return ImageBlock instance
            return ImageBlock.new_file_upload(file_upload_id=file_upload_id)
        # Use external URL
        return ImageBlock.new(url=url)

    def upload_image(self, image_data: bytes, filename: str = "image.png") -> str:
        """Upload an image to Notion using file_uploads API.

        Args:
            image_data: Binary image data
            filename: Filename for the image (optional)

        Returns:
            File upload ID to use in blocks

        Raises:
            Exception: If upload fails
        """
        try:
            # Step 1: Create file upload
            file_upload = FileUploadResponse.model_validate(self.client.file_uploads.create(mode="single_part"))
            logger.debug("Created file upload with ID: %(file_upload_id)s", {"file_upload_id": file_upload.id})

            # Step 2: Send file data
            file_obj = BytesIO(image_data)
            file_obj.name = filename
            self.client.file_uploads.send(
                file_upload_id=file_upload.id,
                file=file_obj,
            )
            logger.debug("Uploaded image to Notion: %(filename)s", {"filename": filename})
        except Exception:
            logger.exception("Failed to upload image: %(filename)s", {"filename": filename})
            raise
        else:
            return file_upload.id

    def create_bookmark_block(self, url: str) -> BookmarkBlock:
        """Create a bookmark block.

        Args:
            url: URL to bookmark

        Returns:
            Bookmark block object
        """
        return BookmarkBlock.new(url=url)

    def create_quote_block(self, text: str | list[RichTextElement]) -> QuoteBlock:
        """Create a quote block.

        Args:
            text: Quote text content (plain string or rich text elements)

        Returns:
            Quote block object
        """
        if isinstance(text, str):
            return QuoteBlock.new(rich_text=text)
        rich_text_array = self._convert_rich_text_elements(text)
        return QuoteBlock(
            type="quote",
            quote={"rich_text": rich_text_array, "color": "default"},
        )

    def _convert_rich_text_elements(self, elements: list[RichTextElement]) -> list[dict]:
        """Convert RichTextElement list to Notion rich_text format.

        Args:
            elements: List of rich text elements

        Returns:
            List of Notion rich_text objects
        """
        result = []
        for elem in elements:
            annotations = {
                "bold": elem.bold,
                "italic": elem.italic,
                "strikethrough": elem.strikethrough,
                "underline": elem.underline,
                "code": elem.code,
                "color": "default",
            }

            if elem.link_url:
                # Link with annotations
                result.append(
                    {
                        "type": "text",
                        "text": {"content": elem.text, "link": {"url": elem.link_url}},
                        "annotations": annotations,
                    }
                )
            else:
                # Plain text with annotations
                result.append(
                    {
                        "type": "text",
                        "text": {"content": elem.text},
                        "annotations": annotations,
                    }
                )

        return result
