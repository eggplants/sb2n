"""Block models for Notion API.

These models are simplified versions that contain only the fields
we actually use in this application.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ParagraphBlock(BaseModel):
    """Paragraph block."""

    type: Literal["paragraph"] = "paragraph"
    paragraph: dict[str, Any]

    @classmethod
    def new(cls, rich_text: str) -> ParagraphBlock:
        """Create a new paragraph block with plain text.

        Args:
            rich_text: Plain text content

        Returns:
            ParagraphBlock instance
        """
        return cls(
            paragraph={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": rich_text},
                    }
                ],
                "color": "default",
            }
        )


class Heading2Block(BaseModel):
    """Heading 2 block."""

    type: Literal["heading_2"] = "heading_2"
    heading_2: dict[str, Any] = Field(alias="heading_2")

    @classmethod
    def new(cls, rich_text: str) -> Heading2Block:
        """Create a new heading 2 block with plain text.

        Args:
            rich_text: Plain text content

        Returns:
            Heading2Block instance
        """
        return cls(
            heading_2={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": rich_text},
                    }
                ],
                "color": "default",
                "is_toggleable": False,
            }
        )


class Heading3Block(BaseModel):
    """Heading 3 block."""

    type: Literal["heading_3"] = "heading_3"
    heading_3: dict[str, Any] = Field(alias="heading_3")

    @classmethod
    def new(cls, rich_text: str) -> Heading3Block:
        """Create a new heading 3 block with plain text.

        Args:
            rich_text: Plain text content

        Returns:
            Heading3Block instance
        """
        return cls(
            heading_3={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": rich_text},
                    }
                ],
                "color": "default",
                "is_toggleable": False,
            }
        )


class BulletedListItemBlock(BaseModel):
    """Bulleted list item block."""

    type: Literal["bulleted_list_item"] = "bulleted_list_item"
    bulleted_list_item: dict[str, Any]

    @classmethod
    def new(cls, rich_text: str, *, children: list[dict[str, Any]] | None = None) -> BulletedListItemBlock:
        """Create a new bulleted list item block with plain text.

        Args:
            rich_text: Plain text content
            children: Optional nested child blocks

        Returns:
            BulletedListItemBlock instance
        """
        item_data = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": rich_text},
                }
            ],
            "color": "default",
        }
        if children:
            item_data["children"] = children
        return cls(bulleted_list_item=item_data)


class CodeBlock(BaseModel):
    """Code block."""

    type: Literal["code"] = "code"
    code: dict[str, Any]

    @classmethod
    def new(cls, code: str, language: str = "plain text") -> CodeBlock:
        """Create a new code block.

        Args:
            code: Code content
            language: Programming language

        Returns:
            CodeBlock instance
        """
        return cls(
            code={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": code},
                    }
                ],
                "language": language,
            }
        )


class ImageBlock(BaseModel):
    """Image block."""

    type: Literal["image"] = "image"
    image: dict[str, Any]

    @classmethod
    def new(cls, *, url: str) -> ImageBlock:
        """Create a new image block with external URL.

        Args:
            url: External image URL

        Returns:
            ImageBlock instance
        """
        return cls(
            image={
                "type": "external",
                "external": {"url": url},
            }
        )

    @classmethod
    def new_file_upload(cls, file_upload_id: str) -> ImageBlock:
        """Create a new image block with file upload ID.

        Args:
            file_upload_id: File upload ID from Notion

        Returns:
            ImageBlock instance
        """
        return cls(
            image={
                "type": "file_upload",
                "file_upload": {"id": file_upload_id},
            }
        )


class BookmarkBlock(BaseModel):
    """Bookmark block."""

    type: Literal["bookmark"] = "bookmark"
    bookmark: dict[str, Any]

    @classmethod
    def new(cls, url: str) -> BookmarkBlock:
        """Create a new bookmark block.

        Args:
            url: URL to bookmark

        Returns:
            BookmarkBlock instance
        """
        return cls(
            bookmark={
                "url": url,
            }
        )


class QuoteBlock(BaseModel):
    """Quote block."""

    type: Literal["quote"] = "quote"
    quote: dict[str, Any]

    @classmethod
    def new(cls, rich_text: str) -> QuoteBlock:
        """Create a new quote block with plain text.

        Args:
            rich_text: Plain text content

        Returns:
            QuoteBlock instance
        """
        return cls(
            quote={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": rich_text},
                    }
                ],
                "color": "default",
            }
        )


class TableBlock(BaseModel):
    """Table block."""

    type: Literal["table"] = "table"
    table: dict[str, Any]

    @classmethod
    def new(cls, table_width: int, *, has_column_header: bool = True, has_row_header: bool = False) -> TableBlock:
        """Create a new table block.

        Args:
            table_width: Number of columns in the table
            has_column_header: Whether the first row is a header
            has_row_header: Whether the first column is a header

        Returns:
            TableBlock instance
        """
        return cls(
            table={
                "table_width": table_width,
                "has_column_header": has_column_header,
                "has_row_header": has_row_header,
            }
        )


class TableRowBlock(BaseModel):
    """Table row block."""

    type: Literal["table_row"] = "table_row"
    table_row: dict[str, Any]

    @classmethod
    def new(cls, cells: list[str]) -> TableRowBlock:
        """Create a new table row block.

        Args:
            cells: List of cell contents

        Returns:
            TableRowBlock instance
        """
        return cls(
            table_row={
                "cells": [
                    [
                        {
                            "type": "text",
                            "text": {"content": cell},
                        }
                    ]
                    for cell in cells
                ]
            }
        )


class TableBlockWithChildren(BaseModel):
    """Table block with children (table rows).

    This is used as an intermediate representation before converting to Notion API format.
    """

    block: TableBlock
    children: list[TableRowBlock]


# Union type for all block types
BlockObject = (
    ParagraphBlock
    | Heading2Block
    | Heading3Block
    | BulletedListItemBlock
    | CodeBlock
    | ImageBlock
    | BookmarkBlock
    | QuoteBlock
    | TableBlock
    | TableRowBlock
    | TableBlockWithChildren
)
