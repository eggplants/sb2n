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
    def new(cls, rich_text: str) -> BulletedListItemBlock:
        """Create a new bulleted list item block with plain text.

        Args:
            rich_text: Plain text content

        Returns:
            BulletedListItemBlock instance
        """
        return cls(
            bulleted_list_item={
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": rich_text},
                    }
                ],
                "color": "default",
            }
        )


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
    def new(cls, url: str) -> ImageBlock:
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
)
