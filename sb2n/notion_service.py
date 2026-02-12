"""Notion API client wrapper."""

import logging
import urllib.parse
from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal, cast

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
    QueryDatabaseResponse,
    QuoteBlock,
)
from sb2n.models.blocks import Heading1Block, TableBlock, TableBlockWithChildren, TableRowBlock

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from notion_client.typing import SyncAsync

    from sb2n.parser import RichTextElement

logger = logging.getLogger(__name__)


class DatabasePropertyValidationError(Exception):
    """Raised when database properties are invalid or missing."""


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
    filename: str | None = None
    content_type: str | None = None
    content_length: int | None = None


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

    def validate_database_properties(self) -> None:
        """Validate that required database properties exist.

        Checks that the database has the following required properties:
        - Title (or Name) - title type
        - Scrapbox URL - url type
        - Created Date - date type

        Optional properties:
        - Tags - multi_select type

        Raises:
            DatabasePropertyValidationError: If required properties are missing or have incorrect types
        """
        logger.info("Validating Notion database properties")

        try:
            # Retrieve database schema
            database = self.client.databases.retrieve(database_id=self.database_id)
            properties = database.get("properties", {})  # ty:ignore[possibly-missing-attribute]

            if not properties:
                msg = "Database has no properties"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301

            # Check for title property (Title or Name)
            title_prop = properties.get("Title") or properties.get("Name")
            if not title_prop:
                msg = "Database must have a 'Title' or 'Name' property"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301
            if title_prop.get("type") != "title":  # noqa: PLR2004
                msg = f"'Title' or 'Name' property must be of type 'title', got '{title_prop.get('type')}'"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301

            # Check for Scrapbox URL property
            url_prop = properties.get("Scrapbox URL")
            if not url_prop:
                msg = "Database must have a 'Scrapbox URL' property"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301
            if url_prop.get("type") != "url":  # noqa: PLR2004
                msg = f"'Scrapbox URL' property must be of type 'url', got '{url_prop.get('type')}'"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301

            # Check for Created Date property
            date_prop = properties.get("Created Date")
            if not date_prop:
                msg = "Database must have a 'Created Date' property"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301
            if date_prop.get("type") != "date":  # noqa: PLR2004
                msg = f"'Created Date' property must be of type 'date', got '{date_prop.get('type')}'"
                raise DatabasePropertyValidationError(msg)  # noqa: TRY301

            # Check for optional Tags property (warn if missing or wrong type)
            tags_prop = properties.get("Tags")
            if not tags_prop:
                logger.warning("Database does not have a 'Tags' property (optional)")
            elif tags_prop.get("type") != "multi_select":  # noqa: PLR2004
                logger.warning(
                    "'Tags' property should be of type 'multi_select', got '%(type)s'",
                    {"type": tags_prop.get("type")},
                )

            logger.info("✓ Database properties validation passed")

        except Exception as e:
            logger.exception(
                "Database property validation failed"
                if isinstance(e, DatabasePropertyValidationError)  # noqa: TRY401
                else "Failed to validate database properties"
            )
            raise

    def get_existing_page_titles(self) -> set[str]:
        """Get all existing page titles from the database.

        Returns:
            Set of page titles currently in the database
        """
        logger.info("Fetching existing pages from Notion database")
        existing_titles: set[str] = set()

        try:
            # Step 1: Retrieve database to get data sources
            database = self.client.databases.retrieve(database_id=self.database_id)
            data_sources = database.get("data_sources", [])  # ty:ignore[possibly-missing-attribute]

            if not data_sources:
                logger.warning("No data sources found in database")
                return existing_titles

            # Step 2: Query each data source for pages
            for data_source in data_sources:
                data_source_id = data_source.get("id")
                if not data_source_id:
                    continue

                logger.debug("Querying data source: %(id)s", {"id": data_source_id})

                # Query data source with pagination
                has_more = True
                start_cursor = None

                while has_more:
                    # Build request body for data_sources query
                    body: dict[str, Any] = {"page_size": 100}
                    if start_cursor:
                        body["start_cursor"] = start_cursor

                    # Execute query using data_sources API
                    response_dict = self.client.request(
                        method="POST",
                        path=f"data_sources/{data_source_id}/query",
                        body=body,
                    )
                    response = QueryDatabaseResponse.model_validate(response_dict)

                    for page in response.results:
                        # Extract title from properties
                        properties = page.get("properties", {})
                        title_prop = properties.get("Title") or properties.get("Name")
                        if title_prop and title_prop.get("type") == "title":  # noqa: PLR2004
                            title_content = title_prop.get("title", [])
                            if title_content:
                                title_text = title_content[0].get("plain_text", "")
                                if title_text:
                                    existing_titles.add(title_text)

                    has_more = response.has_more
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
    ) -> dict:
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
            response: dict | SyncAsync = self.client.pages.create(
                **create_request.model_dump(mode="json", exclude_none=True)
            )

            # Return raw dict instead of validating with Page model
            # because pydantic-api-models-notion may not support all parent types (e.g., data_source_id)
            # Type assertion: client is used synchronously, so response is a dict
            response_dict = cast("dict", response)
            logger.info("Created page: %(title)s (ID: %(id)s)", {"title": title, "id": response_dict["id"]})
        except Exception:
            logger.exception("Failed to create page: %(title)s", {"title": title})
            raise
        else:
            return response_dict

    def delete_page(self, page_id: UUID | str) -> None:
        """Delete (archive) a Notion page.

        Args:
            page_id: Notion page ID to delete

        Raises:
            Exception: If page deletion fails
        """
        try:
            self.client.pages.update(page_id=str(page_id), archived=True)
            logger.info("Deleted page: %(page_id)s", {"page_id": page_id})
        except Exception:
            logger.exception("Failed to delete page: %(page_id)s", {"page_id": page_id})
            raise

    def update_page_title(self, page_id: UUID | str, title: str) -> None:
        """Update the title of a Notion page.

        Args:
            page_id: Notion page ID to update
            title: New title for the page

        Raises:
            Exception: If page update fails
        """
        try:
            properties = {"Title": {"title": [{"text": {"content": title}}]}}
            self.client.pages.update(page_id=str(page_id), properties=properties)
            logger.info("Updated page title: %(page_id)s -> '%(title)s'", {"page_id": page_id, "title": title})
        except Exception:
            logger.exception("Failed to update page title: %(page_id)s", {"page_id": page_id})
            raise

    def append_blocks(self, page_id: UUID, blocks: list[BlockObject]) -> None:
        """Append blocks to a Notion page.

        Args:
            page_id: Notion page ID
            blocks: List of block objects to append (can include table blocks with children)

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
                batch_dicts = []
                for block in batch:
                    # Handle table blocks with children
                    if isinstance(block, TableBlockWithChildren):
                        # Convert table block and its children
                        table_dict = block.block.model_dump(mode="json", exclude_none=True)
                        # Add children to the table object, not at the top level
                        table_dict["table"]["children"] = [
                            child.model_dump(mode="json", exclude_none=True) for child in block.children
                        ]
                        batch_dicts.append(table_dict)
                    elif hasattr(block, "model_dump"):
                        batch_dicts.append(block.model_dump(mode="json", exclude_none=True))
                    else:
                        batch_dicts.append(block)

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

    def create_heading_block(
        self, text: str | list[RichTextElement], level: int = 1
    ) -> Heading1Block | Heading2Block | Heading3Block:
        """Create a heading block.

        Args:
            text: Heading text content (plain string or rich text elements)
            level: Heading level (1, 2, or 3)

        Returns:
            Heading block object
        """
        if isinstance(text, str):
            if level == 1:
                return Heading1Block.new(rich_text=text)
            if level == 2:
                return Heading2Block.new(rich_text=text)
            return Heading3Block.new(rich_text=text)
        rich_text_array = self._convert_rich_text_elements(text)
        if level == 1:
            return Heading1Block(
                type="heading_1",
                heading_1={"rich_text": rich_text_array, "color": "default", "is_toggleable": False},
            )
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

    def create_code_block(self, code: str, language: str = "plain text") -> CodeBlock | list[CodeBlock]:
        """Create a code block.

        Args:
            code: Code content
            language: Programming language (default: "plain text")

        Returns:
            Code block object, or list of code blocks if content exceeds 2000 characters
        """
        # Notion API limit: code.rich_text[0].text.content.length should be ≤ 2000
        # Note: Notion API uses JavaScript's string.length which counts UTF-16 code units
        MAX_CODE_LENGTH = 2000  # noqa: N806

        def utf16_length(s: str) -> int:
            """Calculate string length as UTF-16 code units (JavaScript string.length equivalent)."""
            return len(s.encode("utf-16-le")) // 2

        def split_at_utf16_boundary(s: str, max_utf16_length: int) -> str:
            """Split string at UTF-16 boundary, ensuring we don't exceed max_utf16_length."""
            # Binary search for the right split point
            left, right = 0, len(s)
            while left < right:
                mid = (left + right + 1) // 2
                if utf16_length(s[:mid]) <= max_utf16_length:
                    left = mid
                else:
                    right = mid - 1
            return s[:left]

        if utf16_length(code) <= MAX_CODE_LENGTH:
            return CodeBlock.new(code=code, language=language)

        # Split code into chunks based on UTF-16 code units
        num_blocks = (utf16_length(code) + MAX_CODE_LENGTH - 1) // MAX_CODE_LENGTH
        logger.warning(
            "Code block exceeds %(max)d characters (%(length)d UTF-16 code units, language=%(lang)s). "
            "Splitting into %(num_blocks)d blocks.",
            {"max": MAX_CODE_LENGTH, "length": utf16_length(code), "lang": language, "num_blocks": num_blocks},
        )

        blocks = []
        remaining = code
        while remaining:
            # Find the split point that doesn't exceed MAX_CODE_LENGTH UTF-16 code units
            chunk = split_at_utf16_boundary(remaining, MAX_CODE_LENGTH)
            if not chunk:  # Safety check
                # If we can't fit even one character, something is very wrong
                logger.error("Cannot split code block - single character exceeds limit")
                break

            blocks.append(CodeBlock.new(code=chunk, language=language))
            remaining = remaining[len(chunk) :]

            logger.debug(
                "Created code block chunk %(current)d/%(total)d (%(size)d UTF-16 code units)",
                {"current": len(blocks), "total": num_blocks, "size": utf16_length(chunk)},
            )

        return blocks

    def create_image_block(self, url: str, file_upload_id: str | None = None) -> ImageBlock | None:
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
        # Use external URL - sanitize it first
        sanitized_url = self._sanitize_url(url)
        if not sanitized_url:
            logger.warning("Invalid image URL, skipping: %(url)s", {"url": url})
            return None  # Skip invalid image URLs
        return ImageBlock.new(url=sanitized_url)

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
            raw_response = self.client.file_uploads.create(mode="single_part")
            logger.debug("Raw file upload response: %s", raw_response)
            file_upload = FileUploadResponse.model_validate(raw_response)
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

    def create_bookmark_block(self, url: str) -> BookmarkBlock | None:
        """Create a bookmark block.

        Args:
            url: URL to bookmark

        Returns:
            Bookmark block object or None if URL is invalid
        """
        sanitized_url = self._sanitize_url(url)
        if not sanitized_url:
            logger.warning("Invalid bookmark URL, skipping: %(url)s", {"url": url})
            return None  # Skip invalid bookmark URLs
        return BookmarkBlock.new(url=sanitized_url)

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

    def create_table_block(
        self, table_rows: list[list[str]], *, has_column_header: bool = True, has_row_header: bool = False
    ) -> TableBlockWithChildren | list[TableBlockWithChildren]:
        """Create a table block with rows.

        Args:
            table_rows: List of rows, each row is a list of cell contents
            has_column_header: Whether the first row is a header
            has_row_header: Whether the first column is a header

        Returns:
            TableBlockWithChildren instance, or list of instances if table exceeds 100 rows
        """
        # Notion API limit: table.children.length should be ≤ 100
        MAX_TABLE_ROWS = 100  # noqa: N806

        if not table_rows:
            msg = "Table must have at least one row"
            raise ValueError(msg)

        # Determine table width from the maximum row length
        table_width = max(len(row) for row in table_rows)

        # Normalize all rows to have the same width (pad with empty strings)
        normalized_rows = [
            row + [""] * (table_width - len(row)) if len(row) < table_width else row for row in table_rows
        ]

        # Check if table exceeds max rows limit
        if len(normalized_rows) > MAX_TABLE_ROWS:
            logger.warning(
                "Table has %(count)d rows (max %(max)d). Splitting into multiple tables.",
                {"count": len(normalized_rows), "max": MAX_TABLE_ROWS},
            )

            # Split table into chunks
            result_tables = []
            header_row = normalized_rows[0] if has_column_header else None

            # Calculate effective max rows per table (including header if present)
            effective_max = MAX_TABLE_ROWS - 1 if has_column_header else MAX_TABLE_ROWS

            # Start from index 1 if there's a header, otherwise from 0
            start_idx = 1 if has_column_header else 0

            for i in range(start_idx, len(normalized_rows), effective_max):
                chunk_rows = normalized_rows[i : i + effective_max]

                # Add header to each chunk if has_column_header
                if has_column_header and header_row:
                    chunk_rows = [header_row, *chunk_rows]

                # Create table block for this chunk
                table_block = TableBlock.new(
                    table_width=table_width, has_column_header=has_column_header, has_row_header=has_row_header
                )

                # Create table row blocks
                row_blocks = [TableRowBlock.new(cells=row) for row in chunk_rows]

                result_tables.append(TableBlockWithChildren(block=table_block, children=row_blocks))

            return result_tables

        # Single table (within limit)
        # Create table block
        table_block = TableBlock.new(
            table_width=table_width, has_column_header=has_column_header, has_row_header=has_row_header
        )

        # Create table row blocks
        row_blocks = [TableRowBlock.new(cells=row) for row in normalized_rows]

        return TableBlockWithChildren(block=table_block, children=row_blocks)

    def _convert_rich_text_elements(self, elements: list[RichTextElement]) -> list[dict]:
        """Convert RichTextElement list to Notion rich_text format.

        Args:
            elements: List of rich text elements

        Returns:
            List of Notion rich_text objects
        """
        # Notion API limit: text.link.url.length should be ≤ 2000
        MAX_URL_LENGTH = 2000  # noqa: N806

        result = []
        for elem in elements:
            annotations = {
                "bold": elem.bold,
                "italic": elem.italic,
                "strikethrough": elem.strikethrough,
                "underline": elem.underline,
                "code": elem.code,
                "color": elem.background_color or "default",
            }

            if elem.link_url:
                # Sanitize and validate URL
                sanitized_url = self._sanitize_url(elem.link_url)
                if sanitized_url:
                    # Check URL length limit
                    if len(sanitized_url) > MAX_URL_LENGTH:
                        logger.warning(
                            "URL exceeds %(max)d characters (%(length)d), treating as plain text: %(url)s",
                            {"max": MAX_URL_LENGTH, "length": len(sanitized_url), "url": sanitized_url[:100] + "..."},
                        )
                        # If URL is too long, treat as plain text
                        result.append(
                            {
                                "type": "text",
                                "text": {"content": elem.text},
                                "annotations": annotations,
                            }
                        )
                    else:
                        # Link with annotations
                        result.append(
                            {
                                "type": "text",
                                "text": {"content": elem.text, "link": {"url": sanitized_url}},
                                "annotations": annotations,
                            }
                        )
                else:
                    # If URL is invalid, treat as plain text
                    logger.warning("Invalid URL, treating as plain text: %(url)s", {"url": elem.link_url})
                    result.append(
                        {
                            "type": "text",
                            "text": {"content": elem.text},
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

    @staticmethod
    def _sanitize_url(url: str) -> str | None:
        """Sanitize and validate URL for Notion API.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL or None if invalid
        """
        if not url:
            return None

        try:
            # Remove trailing characters that are likely from text extraction errors
            # These patterns often appear when URLs are extracted from code or markdown
            original_url = url
            url = url.rstrip("'\">`)")

            # Parse the URL
            parsed = urllib.parse.urlparse(url)

            # Check if scheme is present and valid
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                logger.debug(
                    "Invalid URL scheme: %(url)s (scheme: %(scheme)s)", {"url": original_url, "scheme": parsed.scheme}
                )
                return None

            # Check if netloc (domain) is present
            if not parsed.netloc:
                logger.debug("Invalid URL, missing netloc: %(url)s", {"url": original_url})
                return None

            # Skip localhost URLs - treat them as plain text
            if parsed.netloc in ("localhost", "127.0.0.1", "0.0.0.0") or parsed.netloc.startswith(  # noqa: S104
                ("localhost:", "127.0.0.1:", "0.0.0.0:")
            ):
                logger.debug("Skipping localhost URL (treating as plain text): %(url)s", {"url": url})
                return None

            # Decode then re-encode to avoid double-encoding
            # unquote handles %XX encoded characters
            decoded_path = urllib.parse.unquote(parsed.path)
            decoded_query = urllib.parse.unquote(parsed.query)
            decoded_fragment = urllib.parse.unquote(parsed.fragment)

            # Remove trailing slash from .git/ paths (common in git URLs)
            if decoded_path.endswith(".git/"):
                decoded_path = decoded_path[:-1]

            # Reconstruct URL with proper encoding
            # This ensures that fragments and query parameters are properly encoded
            # For fragments, preserve common characters used in URL fragments:
            # : (colon), ~ (tilde), = (equals), ; (semicolon), - (hyphen)
            sanitized = urllib.parse.urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    urllib.parse.quote(decoded_path, safe="/"),
                    parsed.params,
                    urllib.parse.quote(decoded_query, safe="=&:"),
                    urllib.parse.quote(decoded_fragment, safe=":~=;-"),
                )
            )

            if sanitized != original_url:
                logger.debug(
                    "Sanitized URL: %(original)s -> %(sanitized)s", {"original": original_url, "sanitized": sanitized}
                )
        except Exception:
            logger.exception("Failed to sanitize URL: %(url)s", {"url": url})
            return None
        return sanitized

    def get_page_title_to_id_map(self) -> dict[str, str]:
        """Get mapping of page titles to page IDs from the database.

        Returns:
            Dictionary mapping page titles to page IDs
        """
        logger.info("Building page title to ID mapping")
        title_to_id: dict[str, str] = {}

        try:
            # Step 1: Retrieve database to get data sources
            database = self.client.databases.retrieve(database_id=self.database_id)
            data_sources = database.get("data_sources", [])  # ty:ignore[possibly-missing-attribute]

            if not data_sources:
                logger.warning("No data sources found in database")
                return title_to_id

            # Step 2: Query each data source for pages
            for data_source in data_sources:
                data_source_id = data_source.get("id")
                if not data_source_id:
                    continue

                # Query data source with pagination
                has_more = True
                start_cursor = None

                while has_more:
                    body: dict[str, Any] = {"page_size": 100}
                    if start_cursor:
                        body["start_cursor"] = start_cursor

                    response_dict = self.client.request(
                        method="POST",
                        path=f"data_sources/{data_source_id}/query",
                        body=body,
                    )
                    response = QueryDatabaseResponse.model_validate(response_dict)

                    for page in response.results:
                        page_id = page.get("id")
                        properties = page.get("properties", {})
                        title_prop = properties.get("Title") or properties.get("Name")
                        if title_prop and title_prop.get("type") == "title":  # noqa: PLR2004
                            title_content = title_prop.get("title", [])
                            if title_content and page_id:
                                title_text = title_content[0].get("plain_text", "")
                                if title_text:
                                    title_to_id[title_text] = page_id

                    has_more = response.has_more
                    start_cursor = response.next_cursor

            logger.info("Found %(count)d pages in database", {"count": len(title_to_id)})
        except Exception:
            logger.exception("Failed to build page title to ID mapping")
            raise
        else:
            return title_to_id

    def get_page_blocks(self, page_id: str, *, recursive: bool = True) -> list[dict[str, Any]]:
        """Get all blocks from a page, optionally including child blocks.

        Args:
            page_id: Notion page ID
            recursive: Whether to recursively fetch child blocks

        Returns:
            List of block objects
        """
        all_blocks: list[dict[str, Any]] = []

        try:
            # Fetch top-level blocks with pagination
            has_more = True
            start_cursor = None

            while has_more:
                params: dict[str, Any] = {"block_id": page_id}
                if start_cursor:
                    params["start_cursor"] = start_cursor

                response = self.client.blocks.children.list(**params)
                blocks = response.get("results", [])  # ty:ignore[possibly-missing-attribute]
                all_blocks.extend(blocks)

                has_more = response.get("has_more", False)  # ty:ignore[possibly-missing-attribute]
                start_cursor = response.get("next_cursor")  # ty:ignore[possibly-missing-attribute]

            # Recursively fetch child blocks if requested
            if recursive:
                for block in all_blocks[:]:  # Copy list to avoid modification during iteration
                    if block.get("has_children"):
                        child_blocks = self.get_page_blocks(block["id"], recursive=True)
                        all_blocks.extend(child_blocks)

        except Exception:
            logger.exception("Failed to fetch blocks for page: %(page_id)s", {"page_id": page_id})
            raise
        else:
            return all_blocks

    def update_block(self, block_id: str, block_data: dict[str, Any]) -> None:
        """Update a block.

        Args:
            block_id: Block ID to update
            block_data: Block data to update (should contain block type and content)

        Raises:
            Exception: If block update fails
        """
        try:
            self.client.blocks.update(block_id=block_id, **block_data)
        except Exception:
            logger.exception("Failed to update block: %(block_id)s", {"block_id": block_id})
            raise
