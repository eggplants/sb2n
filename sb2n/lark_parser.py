"""Lark-based Scrapbox notation parser."""

import re
from pathlib import Path
from typing import Any, cast

from lark import Lark, Token, Transformer

from sb2n.models.ast import (
    BracketNode,
    CalloutNode,
    CodeBlockNode,
    CommandNode,
    DecorationNode,
    DocumentNode,
    FormulaNode,
    HashtagNode,
    IconNode,
    ImageNode,
    InlineCodeNode,
    InlineNode,
    LineNode,
    LinkNode,
    LocationNode,
    PageLinkNode,
    ParagraphNode,
    QuoteNode,
    StrongNode,
    TableNode,
    TextNode,
)

# 文法ファイルのパス
GRAMMAR_FILE = Path(__file__).parent / "scrapbox.lark"


class TokenType:
    """Token types used in the parser."""

    INDENT = "INDENT"
    NEWLINE = "NEWLINE"
    LOCATION_COORDS = "LOCATION_COORDS"
    LOCATION_TEXT = "LOCATION_TEXT"


class ScrapboxTransformer(Transformer):
    """Transformer to convert Lark parse tree to Scrapbox AST."""

    def document(self, items: list[Any]) -> DocumentNode:
        """Entire document."""
        lines = [item for item in items if item is not None]
        return DocumentNode(type="document", lines=lines)

    def indented_line(self, items: list[Any]) -> LineNode:
        """Indented line."""
        if not items or all(item is None for item in items):
            return LineNode(type="line", indent=0, content=None)

        indent_level = 0
        content = None

        for item in items:
            if isinstance(item, Token) and item.type == TokenType.INDENT:
                indent_level = len(str(item))
            elif item is not None and not (isinstance(item, Token) and item.type == TokenType.NEWLINE):
                content = item

        return LineNode(type="line", indent=indent_level, content=content)

    def indented_last_line(self, items: list[Any]) -> LineNode:
        """Indented last line (without newline)."""
        if not items or all(item is None for item in items):
            return LineNode(type="line", indent=0, content=None)

        indent_level = 0
        content = None

        for item in items:
            if isinstance(item, Token) and item.type == TokenType.INDENT:
                indent_level = len(str(item))
            elif item is not None:
                content = item

        return LineNode(type="line", indent=indent_level, content=content)

    def line(self, items: list[Any]) -> LineNode:
        """Line."""
        if not items or all(item is None for item in items):
            return LineNode(type="line", indent=0, content=None)

        indent_level = 0
        content = None

        for item in items:
            if isinstance(item, Token) and item.type == TokenType.INDENT:
                indent_level = len(str(item))
            elif item is not None and not (isinstance(item, Token) and item.type == TokenType.NEWLINE):
                content = item

        return LineNode(type="line", indent=indent_level, content=content)

    def last_line(self, items: list[Any]) -> LineNode:
        """Last line (without newline)."""
        # Same logic as line()
        if not items or all(item is None for item in items):
            return LineNode(type="line", indent=0, content=None)

        indent_level = 0
        content = None

        for item in items:
            if isinstance(item, Token) and item.type == TokenType.INDENT:
                indent_level = len(str(item))
            elif item is not None:
                content = item

        return LineNode(type="line", indent=indent_level, content=content)

    def indented_plain_line(self, items: list[Any]) -> ParagraphNode:
        """Plain text line (used for indented content like code blocks)."""
        # Return as plain text without parsing inline elements
        text = str(items[0]) if items else ""
        return ParagraphNode(type="paragraph", content=[text])

    def code_block_header(self, items: list[Token]) -> CodeBlockNode:
        """Code block header."""
        language = str(items[1]).strip() if len(items) > 1 else ""
        return CodeBlockNode(type="code_block", language=language)

    def table_header(self, items: list[Token]) -> TableNode:
        """Table header."""
        name = str(items[1]).strip() if len(items) > 1 else ""
        return TableNode(type="table", name=name)

    def quote(self, items: list[Any]) -> QuoteNode:
        """Quote."""
        text = str(items[1]) if len(items) > 1 else ""
        return QuoteNode(type="quote", content=text)

    def callout(self, items: list[Any]) -> CalloutNode:
        """Callout."""
        text = str(items[1]) if len(items) > 1 else ""
        return CalloutNode(type="callout", content=text)

    def command(self, items: list[Any]) -> CommandNode:
        """Command line."""
        prefix = str(items[0]) if items else "$"
        text = str(items[1]) if len(items) > 1 else ""
        return CommandNode(type="command", prefix=prefix, content=text)

    def text_content(self, items: list[Any]) -> str:
        """Text content for quote, callout, command."""
        return str(items[0]) if items else ""

    def paragraph(self, items: list[Any]) -> ParagraphNode:
        """Paragraph."""
        return ParagraphNode(type="paragraph", content=items[0] if items else [])

    def inline_elements(self, items: list[Any]) -> list[InlineNode]:
        """List of inline elements."""
        return items

    def double_bracket_content(self, items: list[Any]) -> str:
        """Content inside double brackets - concatenate all parts."""
        return "".join(str(item) for item in items)

    def double_bracket(self, items: list[Any]) -> TextNode | ImageNode | StrongNode:
        """Double bracket."""
        if len(items) < 2:
            return TextNode(type="text", text="")

        # items[0] is DOUBLE_LSQB, items[1] is content string, items[2] is DOUBLE_RSQB
        content_str = str(items[1])

        # Check if it's an image URL
        url_match = re.search(r"https?://[^\s]+", content_str)
        if url_match:
            # Parse as bracket content (might be image URL or link)
            parsed = self._parse_bracket_content(content_str)
            # If it's an image, make it large
            if isinstance(parsed, ImageNode):
                parsed.large = True
                return parsed

        # Otherwise, it's just bold/strong text
        return StrongNode(type="strong", content=TextNode(type="text", text=content_str))

    def bracket_content(self, items: list[Any]) -> str:
        """Content inside brackets - concatenate all parts and return as string."""
        return "".join(str(item) for item in items)

    def bracket(self, items: list[Any]) -> BracketNode:
        """Bracket."""
        if len(items) < 2:
            return TextNode(type="text", text="")

        # items[0] is LSQB, items[1] is content string, items[2] is RSQB
        content_str = str(items[1])
        return self._parse_bracket_content(content_str)

    def _parse_bracket_content(self, content: str) -> BracketNode:
        """Parse bracket content and return appropriate node type.

        Args:
            content: Raw bracket content string

        Returns:
            Appropriate BracketNode based on content
        """
        # Icon notation: path.icon or path.icon*N
        if ".icon" in content:
            match = re.match(r"^((?:/[^/]+/)?[^*]+)\.icon(?:\*(\d+))?$", content)
            if match:
                path = match.group(1)
                repeat = int(match.group(2)) if match.group(2) else 1
                return IconNode(type="icon", path=path, repeat=repeat)

        # Location notation: N123.45,E67.89 or N123.45,E67.89,Z10
        if content.startswith("N") and ",E" in content:
            parts = content.split(" ", 1)
            if len(parts) == 2:
                return LocationNode(type="location", coords=parts[0], text=parts[1])
            if re.match(r"^N\d+(\.\d+)?,E\d+(\.\d+)?(,Z\d+)?$", content):
                return LocationNode(type="location", coords=content, text=None)

        # Inline math: $ formula $
        if content.startswith("$ ") and content.endswith(" $"):
            formula = content[2:-2]
            return FormulaNode(type="formula", formula=formula)

        # Check for URLs (for images and links)
        url_match = re.search(r"https?://[^\s]+", content)
        has_url = url_match is not None

        if has_url:
            url = url_match.group(0)

            # Image URL patterns
            is_image = "gyazo.com" in url or any(
                url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"]
            )

            # Extract text before and after URL
            before_url = content[: url_match.start()].strip()
            after_url = content[url_match.end() :].strip()

            # Image with link: URL IMAGE_URL or IMAGE_URL URL
            if before_url.startswith("http") or after_url.startswith("http"):
                url1 = before_url if before_url.startswith("http") else after_url
                url2 = after_url if before_url.startswith("http") else before_url
                is_url1_image = "gyazo.com" in url1 or any(
                    url1.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"]
                )
                is_url2_image = "gyazo.com" in url2 or any(
                    url2.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"]
                )

                if is_url1_image and url2.startswith("http"):
                    return ImageNode(type="image", url=url1, large=False, link=url2)
                if is_url2_image and url1.startswith("http"):
                    return ImageNode(type="image", url=url2, large=False, link=url1)

            # Link with text: text URL or URL text
            text = before_url or after_url or url
            return LinkNode(type="link", url=url, text=text)

        # Cross-project link: /project/page or /project/page#fragment
        if content.startswith("/") and "/" in content[1:]:
            parts = content[1:].split("/", 1)
            if len(parts) == 2:
                project = parts[0]
                page_and_fragment = parts[1].split("#", 1)
                page = page_and_fragment[0]
                fragment = page_and_fragment[1] if len(page_and_fragment) > 1 else None
                return LinkNode(
                    type="link",
                    url=f"https://scrapbox.io/{project}/{page}",
                    project=project,
                    page=page,
                    fragment=fragment,
                )

        # Page with fragment: page#fragment
        if "#" in content and not content.startswith("#"):
            parts = content.split("#", 1)
            return PageLinkNode(type="page_link", page=parts[0], fragment=parts[1])

        # Decoration: symbols text
        if " " in content:
            parts = content.split(" ", 1)
            symbols = parts[0]
            text = parts[1]
            # Check if first part contains decoration symbols
            if any(c in symbols for c in "*/-_!#%{}<>~'\"&+,.|"):
                return DecorationNode(
                    type="decoration",
                    symbols=symbols,
                    text=text,
                    bold="*" in symbols,
                    italic="/" in symbols,
                    strike="-" in symbols,
                    underline="_" in symbols,
                )

        # Simple page link
        return PageLinkNode(type="page_link", page=content, fragment=None)

    def hashtag(self, items: list[Any]) -> HashtagNode:
        """Hashtag."""
        return HashtagNode(type="hashtag", tag=str(items[0]) if items else "")

    def inline_code(self, items: list[Any]) -> InlineCodeNode:
        """Inline code."""
        return InlineCodeNode(type="code", code=str(items[0]) if items else "")

    def plain_text(self, items: list[Any]) -> str:
        """Plain text."""
        return str(items[0]) if items else ""


class ScrapboxLarkParser:
    """Scrapbox notation parser using Lark."""

    def __init__(self, grammar_file: Path | None = None) -> None:
        """Initialize the parser.

        Args:
            grammar_file: Path to the grammar file (default if omitted)
        """
        self.grammar_file = grammar_file or GRAMMAR_FILE

        if not self.grammar_file.exists():
            msg = f"Grammar file not found: {self.grammar_file}"
            raise FileNotFoundError(msg)

        with self.grammar_file.open(encoding="utf-8") as f:
            grammar = f.read()

        self.parser = Lark(
            grammar,
            parser="lalr",
            transformer=ScrapboxTransformer(),
        )

    def parse(self, text: str) -> DocumentNode:
        """Parse Scrapbox text.

        Args:
            text: Scrapbox text to parse

        Returns:
            Parsed AST (DocumentNode)
        """
        return cast("DocumentNode", self.parser.parse(text))

    def parse_line(self, line: str) -> DocumentNode:
        """Parse a single line of Scrapbox text.

        Args:
            line: A single line of Scrapbox text

        Returns:
            Parsed AST (DocumentNode)
        """
        return self.parse(line + "\n")
