"""Parser for Scrapbox notation."""

import re
from dataclasses import dataclass


@dataclass
class ParsedLine:
    """Parsed line from Scrapbox text.

    Attributes:
        original: Original line text
        line_type: Type of line (paragraph, heading_2, heading_3, code, list, image, url)
        content: Processed content
        indent_level: Indentation level (for lists)
        language: Language for code blocks
    """

    original: str
    line_type: str
    content: str
    indent_level: int = 0
    language: str = "plain text"


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
    HEADING_PATTERN = re.compile(r"^\[(\*+)\s+(.+)\]$")
    CODE_BLOCK_PATTERN = re.compile(r"^code:(.+)$")
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]")

    @staticmethod
    def extract_tags(text: str) -> list[str]:
        """Extract hashtags from text.

        Args:
            text: Text to parse

        Returns:
            List of tag names (without # prefix)
        """
        return ScrapboxParser.TAG_PATTERN.findall(text)

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
        all_urls = gyazo_urls + [url for url in image_urls if url not in gyazo_urls]
        return all_urls

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
    def parse_line(line: str) -> ParsedLine:
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
            return ParsedLine(original=line, line_type=f"heading_{level}", content=title)

        # Code block start: code:filename
        code_match = ScrapboxParser.CODE_BLOCK_PATTERN.match(stripped)
        if code_match:
            filename = code_match.group(1)
            # Try to detect language from filename extension
            language = ScrapboxParser._detect_language(filename)
            return ParsedLine(original=line, line_type="code_start", content=filename, language=language)

        # Image URL
        image_urls = ScrapboxParser.extract_image_urls(stripped)
        if image_urls:
            return ParsedLine(original=line, line_type="image", content=image_urls[0])

        # Regular URL (bookmark)
        urls = ScrapboxParser.extract_urls(stripped)
        if urls and stripped.startswith("[") and stripped.endswith("]"):
            return ParsedLine(original=line, line_type="url", content=urls[0])

        # List item (indented)
        if indent_level > 0:
            # Remove Scrapbox link syntax for plain text
            content = ScrapboxParser._clean_links(stripped)
            return ParsedLine(
                original=line,
                line_type="list",
                content=content,
                indent_level=indent_level,
            )

        # Regular paragraph
        content = ScrapboxParser._clean_links(stripped)
        return ParsedLine(original=line, line_type="paragraph", content=content)

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
                    code_buffer.append(line[1:] if line.startswith(" ") else line)
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
            if content.startswith("http://") or content.startswith("https://"):
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
