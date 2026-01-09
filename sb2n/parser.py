"""Parser for Scrapbox notation."""

import re
from dataclasses import dataclass


@dataclass
class RichTextElement:
    """Rich text element with styling.

    Attributes:
        text: Text content
        bold: Bold styling
        italic: Italic styling
        strikethrough: Strikethrough styling
        underline: Underline styling
        code: Inline code styling
        link_url: URL if this is a link
    """

    text: str
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    link_url: str | None = None


@dataclass
class ParsedLine:
    """Parsed line from Scrapbox text.

    Attributes:
        original: Original line text
        line_type: Type of line (paragraph, heading_2, heading_3, code, list, image, url, quote, table_start)
        content: Processed content
        indent_level: Indentation level (for lists)
        language: Language for code blocks
        rich_text: Rich text elements with styling (for paragraphs, lists, headings)
        link_text: Display text for links
        table_name: Name for table blocks
    """

    original: str
    line_type: str
    content: str
    indent_level: int = 0
    language: str = "plain text"
    rich_text: list[RichTextElement] | None = None
    link_text: str | None = None
    table_name: str | None = None


class ScrapboxParser:
    """Parser for Scrapbox notation.

    This parser extracts tags, image URLs, and converts Scrapbox syntax
    into structured data that can be transformed into Notion blocks.
    """

    # Regex patterns
    TAG_PATTERN = re.compile(r"#([^\s\[\]]+)")
    IMAGE_PATTERN = re.compile(r"\[(https?://[^\]]+\.(?:jpg|jpeg|png|gif|webp|svg))\]", re.IGNORECASE)
    URL_PATTERN = re.compile(r"\[(https?://[^\]]+)\]")
    GYAZO_PATTERN = re.compile(r"\[(https?://(?:gyazo\.com|i\.gyazo\.com)/[^\]]+)\]", re.IGNORECASE)
    SCRAPBOX_FILE_PATTERN = re.compile(r"\[(https://scrapbox\.io/api/pages/[^/]+/[^/]+/[^\]]+)\]", re.IGNORECASE)
    HEADING_PATTERN = re.compile(r"^\[(\*+)\s+(.+)\]$")
    CODE_BLOCK_PATTERN = re.compile(r"^code:(.+)$")
    TABLE_PATTERN = re.compile(r"^table:(.+)$")
    QUOTE_PATTERN = re.compile(r"^>\s+(.+)$")
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]")
    # External link with display text: [text url] or [url text]
    EXTERNAL_LINK_PATTERN = re.compile(r"\[([^\s\]]+)\s+(https?://[^\]]+)\]|\[(https?://[^\s\]]+)\s+([^\]]+)\]")
    # Text decorations
    BOLD_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
    STRIKETHROUGH_PATTERN = re.compile(r"\[-\s+([^\]]+)\]")
    UNDERLINE_PATTERN = re.compile(r"\[_\s+([^\]]+)\]")
    INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")

    @staticmethod
    def extract_tags(text: str) -> list[str]:
        """Extract hashtags from text.

        Excludes hashtags inside inline code (backticks).

        Args:
            text: Text to parse

        Returns:
            List of tag names (without # prefix)
        """
        # Remove inline code (backticks) to avoid extracting tags from code
        # Match both single backticks and triple backticks
        text_without_code = re.sub(r"`[^`]*`", "", text)
        return ScrapboxParser.TAG_PATTERN.findall(text_without_code)

    @staticmethod
    def extract_image_urls(text: str) -> list[str]:
        """Extract image URLs from text.

        This includes Gyazo URLs and other image URLs.

        Args:
            text: Text to parse

        Returns:
            List of image URLs
        """
        # First try Gyazo URLs
        gyazo_urls = ScrapboxParser.GYAZO_PATTERN.findall(text)

        # Then try general image URLs
        image_urls = ScrapboxParser.IMAGE_PATTERN.findall(text)

        # Combine and deduplicate
        return gyazo_urls + [url for url in image_urls if url not in gyazo_urls]

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        """Extract all URLs from text.

        Args:
            text: Text to parse

        Returns:
            List of URLs
        """
        return ScrapboxParser.URL_PATTERN.findall(text)

    @staticmethod
    def parse_line(line: str) -> ParsedLine:  # noqa: C901, PLR0911
        """Parse a single line of Scrapbox text.

        Args:
            line: Line to parse

        Returns:
            Parsed line with type and content
        """
        stripped = line.strip()

        # Empty line
        if not stripped:
            return ParsedLine(original=line, line_type="paragraph", content="")

        # Calculate indentation level
        indent_level = (len(line) - len(line.lstrip())) // 1  # Scrapbox uses spaces for indent

        # Heading: [* Title], [** Title], [*** Title]
        heading_match = ScrapboxParser.HEADING_PATTERN.match(stripped)
        if heading_match:
            asterisks = heading_match.group(1)
            title = heading_match.group(2)
            level = min(len(asterisks) + 1, 3)  # [*] -> heading_2, [**] -> heading_3
            # Parse rich text in heading
            rich_text = ScrapboxParser._parse_rich_text(title)
            return ParsedLine(
                original=line,
                line_type=f"heading_{level}",
                content=title,
                rich_text=rich_text,
            )

        # Quote: > quote text
        quote_match = ScrapboxParser.QUOTE_PATTERN.match(stripped)
        if quote_match:
            quote_text = quote_match.group(1)
            rich_text = ScrapboxParser._parse_rich_text(quote_text)
            return ParsedLine(
                original=line,
                line_type="quote",
                content=quote_text,
                rich_text=rich_text,
            )

        # Code block start: code:filename
        code_match = ScrapboxParser.CODE_BLOCK_PATTERN.match(stripped)
        if code_match:
            filename = code_match.group(1)
            # Try to detect language from filename extension
            language = ScrapboxParser._detect_language(filename)
            return ParsedLine(original=line, line_type="code_start", content=filename, language=language)

        # Table start: table:name
        table_match = ScrapboxParser.TABLE_PATTERN.match(stripped)
        if table_match:
            table_name = table_match.group(1)
            return ParsedLine(
                original=line,
                line_type="table_start",
                content=table_name,
                table_name=table_name,
            )

        # Image URL
        image_urls = ScrapboxParser.extract_image_urls(stripped)
        if image_urls:
            return ParsedLine(original=line, line_type="image", content=image_urls[0])

        # External link with display text: [text url] or [url text]
        external_link_match = ScrapboxParser.EXTERNAL_LINK_PATTERN.search(stripped)
        if external_link_match:
            # Check which group matched
            if external_link_match.group(1):  # [text url] format
                link_text = external_link_match.group(1)
                url = external_link_match.group(2)
            else:  # [url text] format
                url = external_link_match.group(3)
                link_text = external_link_match.group(4)
            return ParsedLine(
                original=line,
                line_type="external_link",
                content=url,
                link_text=link_text,
            )

        # Regular URL (bookmark)
        urls = ScrapboxParser.extract_urls(stripped)
        if urls and stripped.startswith("[") and stripped.endswith("]"):
            return ParsedLine(original=line, line_type="url", content=urls[0])

        # List item (indented)
        if indent_level > 0:
            # Parse rich text for list items
            rich_text = ScrapboxParser._parse_rich_text(stripped)
            content = ScrapboxParser._clean_links(stripped)
            return ParsedLine(
                original=line,
                line_type="list",
                content=content,
                indent_level=indent_level,
                rich_text=rich_text,
            )

        # Regular paragraph
        rich_text = ScrapboxParser._parse_rich_text(stripped)
        content = ScrapboxParser._clean_links(stripped)
        return ParsedLine(
            original=line,
            line_type="paragraph",
            content=content,
            rich_text=rich_text,
        )

    @staticmethod
    def parse_text(text: str) -> list[ParsedLine]:
        """Parse entire Scrapbox text into structured lines.

        Args:
            text: Full text content from Scrapbox

        Returns:
            List of parsed lines
        """
        lines = text.split("\n")
        parsed_lines = []
        in_code_block = False
        code_buffer = []
        code_language = "plain text"

        for line in lines:
            parsed = ScrapboxParser.parse_line(line)

            # Handle code blocks
            if parsed.line_type == "code_start":
                in_code_block = True
                code_language = parsed.language
                code_buffer = []
                continue

            if in_code_block:
                # Empty line or unindented line ends code block
                if not line.strip() or (line and not line.startswith(" ") and not line.startswith("\t")):
                    # Save code block
                    if code_buffer:
                        code_content = "\n".join(code_buffer)
                        parsed_lines.append(
                            ParsedLine(
                                original=code_content,
                                line_type="code",
                                content=code_content,
                                language=code_language,
                            )
                        )
                    in_code_block = False
                    code_buffer = []
                    # Process current line normally
                    if line.strip():
                        parsed = ScrapboxParser.parse_line(line)
                        parsed_lines.append(parsed)
                else:
                    # Add to code buffer (remove one level of indent)
                    code_buffer.append(line.removeprefix(" "))
                continue

            parsed_lines.append(parsed)

        # Handle unclosed code block
        if in_code_block and code_buffer:
            code_content = "\n".join(code_buffer)
            parsed_lines.append(
                ParsedLine(
                    original=code_content,
                    line_type="code",
                    content=code_content,
                    language=code_language,
                )
            )

        return parsed_lines

    @staticmethod
    def _parse_rich_text(text: str) -> list[RichTextElement]:  # noqa: C901
        """Parse text with decorations into rich text elements.

        Args:
            text: Text with potential decorations

        Returns:
            List of rich text elements with styling
        """
        # Track positions and stylings
        elements: list[RichTextElement] = []

        # For simplicity, we'll process decorations in order and create segments
        # This is a basic implementation that handles non-nested decorations

        # First, let's find all decoration matches with their positions
        decorations: list[tuple[int, int, str, str]] = [
            # Bold: `[[text]]`
            *[
                (match.start(), match.end(), "bold", match.group(1))
                for match in ScrapboxParser.BOLD_PATTERN.finditer(text)
            ],
            # Strikethrough: `[- text]`
            *[
                (match.start(), match.end(), "strikethrough", match.group(1))
                for match in ScrapboxParser.STRIKETHROUGH_PATTERN.finditer(text)
            ],
            # Underline: `[_ text]`
            *[
                (match.start(), match.end(), "underline", match.group(1))
                for match in ScrapboxParser.UNDERLINE_PATTERN.finditer(text)
            ],
            # Inline code: `code`
            *[
                (match.start(), match.end(), "code", match.group(1))
                for match in ScrapboxParser.INLINE_CODE_PATTERN.finditer(text)
            ],
        ]

        # If no decorations found, return plain text
        if not decorations:
            return [RichTextElement(text=text)]

        # Sort by position
        decorations.sort(key=lambda x: x[0])

        # Build elements
        last_pos = 0
        for start, end, style, content in decorations:
            # Add plain text before this decoration
            if start > last_pos:
                plain_text = text[last_pos:start]
                if plain_text:
                    elements.append(RichTextElement(text=plain_text))

            # Add styled text
            element = RichTextElement(text=content)
            if style == "bold":
                element.bold = True
            elif style == "strikethrough":
                element.strikethrough = True
            elif style == "underline":
                element.underline = True
            elif style == "code":
                element.code = True
            elements.append(element)

            last_pos = end

        # Add remaining plain text
        if last_pos < len(text):
            remaining = text[last_pos:]
            if remaining:
                elements.append(RichTextElement(text=remaining))

        return elements if elements else [RichTextElement(text=text)]

    @staticmethod
    def _clean_links(text: str) -> str:
        """Remove Scrapbox link syntax from text.

        Args:
            text: Text with potential Scrapbox links

        Returns:
            Text with links converted to plain text
        """

        # Remove Scrapbox internal links: [Link Text] -> Link Text
        # But preserve URLs
        def replace_link(match: re.Match[str]) -> str:
            content = match.group(1)
            # If it's a URL, keep the brackets
            if content.startswith(("http://", "https://")):
                return match.group(0)
            # Otherwise, just return the content
            return content

        return ScrapboxParser.LINK_PATTERN.sub(replace_link, text)

    @staticmethod
    def _detect_language(filename: str) -> str:
        """Detect programming language from filename.

        Args:
            filename: File name with extension

        Returns:
            Language identifier for Notion code blocks
        """
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "c++",
            ".c": "c",
            ".cs": "c#",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".sh": "shell",
            ".bash": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".md": "markdown",
        }

        for ext, lang in extension_map.items():
            if filename.lower().endswith(ext):
                return lang

        return "plain text"
