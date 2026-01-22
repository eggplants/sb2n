"""AST type definitions for Scrapbox notation parser."""

from typing import Literal

from pydantic import BaseModel


class DocumentNode(BaseModel):
    """Document node."""

    type: Literal["document"]
    lines: list[LineNode]


class LineNode(BaseModel):
    """Line node."""

    type: Literal["line"]
    indent: int
    content: ContentNode | None


class CodeBlockNode(BaseModel):
    """Code block header node."""

    type: Literal["code_block"]
    language: str


class TableNode(BaseModel):
    """Table header node."""

    type: Literal["table"]
    name: str


class QuoteNode(BaseModel):
    """Quote node."""

    type: Literal["quote"]
    content: str


class CalloutNode(BaseModel):
    """Callout node."""

    type: Literal["callout"]
    content: str


class CommandNode(BaseModel):
    """Command line node."""

    type: Literal["command"]
    prefix: str
    content: str


class ParagraphNode(BaseModel):
    """Paragraph node."""

    type: Literal["paragraph"]
    content: list[InlineNode]


class StrongNode(BaseModel):
    """Strong (bold) node."""

    type: Literal["strong"]
    content: BracketNode


class LocationNode(BaseModel):
    """Location notation node."""

    type: Literal["location"]
    coords: str | None
    text: str | None


class FormulaNode(BaseModel):
    """Formula (inline math) node."""

    type: Literal["formula"]
    formula: str


class IconNode(BaseModel):
    """Icon notation node."""

    type: Literal["icon"]
    path: str
    repeat: int


class ImageNode(BaseModel):
    """Image node."""

    type: Literal["image"]
    url: str
    large: bool
    link: str | None = None


class LinkNode(BaseModel):
    """External link node."""

    type: Literal["link"]
    url: str
    text: str | None = None
    project: str | None = None
    page: str | None = None
    fragment: str | None = None


class PageLinkNode(BaseModel):
    """Page link node."""

    type: Literal["page_link"]
    page: str
    fragment: str | None = None


class DecorationNode(BaseModel):
    """Text decoration node."""

    type: Literal["decoration"]
    symbols: str
    text: str
    bold: bool
    italic: bool
    strike: bool
    underline: bool


class HashtagNode(BaseModel):
    """Hashtag node."""

    type: Literal["hashtag"]
    tag: str


class InlineCodeNode(BaseModel):
    """Inline code node."""

    type: Literal["code"]
    code: str


class TextNode(BaseModel):
    """Plain text node."""

    type: Literal["text"]
    text: str


# Union types for convenience
BracketNode = LocationNode | FormulaNode | IconNode | ImageNode | LinkNode | PageLinkNode | DecorationNode | TextNode

InlineNode = BracketNode | StrongNode | HashtagNode | InlineCodeNode | str

ContentNode = CodeBlockNode | TableNode | QuoteNode | CalloutNode | CommandNode | ParagraphNode
