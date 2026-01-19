"""Parser for Scrapbox notation."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


class DecorationType(Enum):
    """Text decoration style types."""

    BOLD = "bold"
    ITALIC = "italic"
    STRIKETHROUGH = "strikethrough"
    UNDERLINE = "underline"
    CODE = "code"
    LINK = "link"
    RED_BACKGROUND = "red_background"
    GREEN_BACKGROUND = "green_background"
    BLUE_BACKGROUND = "blue_background"


class LineType(Enum):
    """Line type for parsed Scrapbox lines."""

    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    CODE = "code"
    LIST = "list"
    IMAGE = "image"
    ICON = "icon"
    URL = "url"
    QUOTE = "quote"
    TABLE = "table"
    TABLE_START = "table_start"
    CODE_START = "code_start"
    EXTERNAL_LINK = "external_link"
    IMAGE_LINK = "image_link"


class Decoration(NamedTuple):
    """Decoration match information.

    Attributes:
        start: Start position in text
        end: End position in text
        style: Style type (bold, italic, strikethrough, underline, code, link)
        content: Decorated text content
        url: URL for link decorations (None for other styles)
    """

    start: int
    end: int
    style: DecorationType
    content: str
    url: str | None


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
        background_color: Background color (red_background, green_background, blue_background, or None)
    """

    text: str
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    link_url: str | None = None
    background_color: str | None = None


@dataclass
class ParsedLine:
    """Parsed line from Scrapbox text.

    Attributes:
        original: Original line text
        line_type: Type of line
        content: Processed content
        indent_level: Indentation level (for lists)
        language: Language for code blocks
        rich_text: Rich text elements with styling (for paragraphs, lists, headings)
        link_text: Display text for links
        table_name: Name for table blocks
        table_rows: Rows for table blocks (list of lists of cell content)
    """

    original: str
    line_type: LineType
    content: str
    indent_level: int = 0
    language: str = "plain text"
    rich_text: list[RichTextElement] | None = None
    link_text: str | None = None
    table_name: str | None = None
    table_rows: list[list[str]] | None = None
    icon_page_name: str | None = None
    icon_project: str | None = None
    image_url: str | None = None


class ScrapboxParser:
    """Parser for Scrapbox notation.

    This parser extracts tags, image URLs, and converts Scrapbox syntax
    into structured data that can be transformed into Notion blocks.
    """

    # Regex patterns
    # Tag pattern: # must be preceded by whitespace or start of string
    TAG_PATTERN = re.compile(r"(?:^|\s)#([^\s\[\]]+)")
    IMAGE_PATTERN = re.compile(r"\[(https?://[^\]]+\.(?:jpg|jpeg|png|gif|webp|svg))\]", re.IGNORECASE)
    URL_PATTERN = re.compile(r"\[(https?://[^\]]+)\]")
    GYAZO_PATTERN = re.compile(r"\[(https?://(?:gyazo\.com|i\.gyazo\.com)/[^\]]+)\]", re.IGNORECASE)
    SCRAPBOX_FILE_PATTERN = re.compile(r"\[(https://scrapbox\.io/api/pages/[^/]+/[^/]+/[^\]]+)\]", re.IGNORECASE)
    HEADING_PATTERN = re.compile(r"^\[(\*+)\s+(.+)\]$")
    CODE_BLOCK_PATTERN = re.compile(r"^code:(.+)$")
    TABLE_PATTERN = re.compile(r"^table:(.+)$")
    QUOTE_PATTERN = re.compile(r"^>\s*(.+)$")
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]")
    # Image link patterns: [url image_url] or [image_url url]
    # Matches image URLs (ending in common image extensions)
    IMAGE_URL_PATTERN = r"https?://[^\s\]]+\.(?:png|jpg|jpeg|gif|webp|svg)(?:\?[^\s\]]*)?"
    # [url image_url] format
    IMAGE_LINK_URL_FIRST_PATTERN = re.compile(rf"\[(https?://[^\s\]]+)\s+({IMAGE_URL_PATTERN})\]")
    # [image_url url] format
    IMAGE_LINK_IMAGE_FIRST_PATTERN = re.compile(rf"\[({IMAGE_URL_PATTERN})\s+(https?://[^\s\]]+)\]")
    # External link with display text: [text url] or [url text]
    # Matches: [text with spaces https://url] or [https://url text with spaces]
    # Negative lookahead to exclude decoration patterns: [* ], [- ], [/ ], [_ ], [[ ]]
    EXTERNAL_LINK_PATTERN = re.compile(
        r"\[(?![*\-/_\[])"  # Not followed by decoration markers
        r"(.+?)\s+(https?://[^\s\]]+)\]"  # [text url] format
        r"|\[(https?://[^\s\]]+)\s+(.+?)\]"  # [url text] format
    )
    # Text decorations
    BOLD_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
    BOLD_ASTERISK_PATTERN = re.compile(r"\[\*+\s+([^\]]+)\]")  # [* text], [** text], [*** text] inline bold
    ITALIC_PATTERN = re.compile(r"\[/\s+([^\]]+)\]")
    STRIKETHROUGH_PATTERN = re.compile(r"\[-\s+([^\]]+)\]")
    UNDERLINE_PATTERN = re.compile(r"\[_\s+([^\]]+)\]")
    INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
    # Icon notation: [page_name.icon] or [/icons/page_name.icon]
    ICON_PATTERN = re.compile(r"^\[(/icons/)?([^\]]+)\.icon\]$")
    # Cross-project link: [/project/page] (not ending in .icon)
    CROSS_PROJECT_LINK_PATTERN = re.compile(
        r"^\[/([^/\]]+)/([^\]]+)\]$"
    )  # Internal link with fragment: [page#fragment] (not starting with /)
    INTERNAL_FRAGMENT_LINK_PATTERN = re.compile(
        r"^\[([^/\]]+)#([^\]]+)\]$"
    )  # Background colors: [! text], [# text], [% text]
    RED_BACKGROUND_PATTERN = re.compile(r"\[!\s*([^\]]+)\]")
    GREEN_BACKGROUND_PATTERN = re.compile(r"\[#\s*([^\]]+)\]")
    BLUE_BACKGROUND_PATTERN = re.compile(r"\[%\s*([^\]]+)\]")
    # Plain URL (not in brackets): https://... or http://...
    PLAIN_URL_PATTERN = re.compile(r"https?://[^\s\]]+")

    @staticmethod
    def extract_tags(text: str) -> list[str]:
        """Extract hashtags from text.

        Excludes hashtags inside inline code (backticks) and code blocks.

        Args:
            text: Text to parse

        Returns:
            List of tag names (without # prefix)
        """
        lines = text.split("\n")
        filtered_lines = []
        in_code_block = False
        code_indent_level = 0

        for line in lines:
            stripped = line.strip()

            # Check if this is a code block start
            code_match = ScrapboxParser.CODE_BLOCK_PATTERN.match(stripped)
            if code_match:
                in_code_block = True
                code_indent_level = len(line) - len(line.lstrip())
                continue

            # Check if we're exiting a code block
            if in_code_block:
                current_indent = len(line) - len(line.lstrip())
                # Exit code block if empty line or indent level decreased
                if not line.strip() or current_indent <= code_indent_level:
                    in_code_block = False
                    code_indent_level = 0
                    # Process this line normally if it's not empty
                    if line.strip():
                        filtered_lines.append(line)
                # Skip lines inside code blocks
                continue

            # Add non-code lines
            filtered_lines.append(line)

        # Rejoin filtered lines
        text_without_code_blocks = "\n".join(filtered_lines)

        # Remove inline code (backticks) to avoid extracting tags from code
        # Match both single backticks and triple backticks
        text_without_code = re.sub(r"`[^`]*`", "", text_without_code_blocks)

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
    def parse_line(line: str, project_name: str | None = None) -> ParsedLine:
        """Parse a single line of Scrapbox text.

        Args:
            line: Line to parse
            project_name: Optional Scrapbox project name for internal fragment links

        Returns:
            Parsed line with type and content
        """
        stripped = line.strip()

        # Empty line
        if not stripped:
            return ParsedLine(original=line, line_type=LineType.PARAGRAPH, content="", indent_level=0)

        # Calculate indentation level
        indent_level = (len(line) - len(line.lstrip())) // 1  # Scrapbox uses spaces for indent

        # Check for quote + heading combination: > [* Title]
        # If line starts with '>' and contains only a heading, ignore quote and treat as heading
        if stripped.startswith(">"):
            quote_prefix_removed = stripped[1:].lstrip()
            # Check if the remaining content is a heading
            heading_check = ScrapboxParser.HEADING_PATTERN.match(quote_prefix_removed)
            if heading_check:
                # This is a heading with quote prefix - ignore the quote
                stripped = quote_prefix_removed

        # Heading: [* Title], [** Title], [*** Title]
        heading_match = ScrapboxParser.HEADING_PATTERN.match(stripped)
        if heading_match:
            asterisks = heading_match.group(1)
            title = heading_match.group(2)
            asterisk_count = len(asterisks)

            # Map: [*] -> H3, [**] -> H2, [***+] -> H1
            # (Reverse of Markdown: more asterisks = larger text in Scrapbox)
            if asterisk_count == 1:
                line_type = LineType.HEADING_3
            elif asterisk_count == 2:
                line_type = LineType.HEADING_2
            else:
                line_type = LineType.HEADING_1

            # Parse rich text in heading
            rich_text = ScrapboxParser._parse_rich_text(title)
            return ParsedLine(
                original=line,
                line_type=line_type,
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
                line_type=LineType.QUOTE,
                content=quote_text,
                rich_text=rich_text,
            )

        # Code block start: code:filename
        code_match = ScrapboxParser.CODE_BLOCK_PATTERN.match(stripped)
        if code_match:
            filename = code_match.group(1)
            # Try to detect language from filename extension
            language = ScrapboxParser._detect_language(filename)
            return ParsedLine(
                original=line,
                line_type=LineType.CODE_START,
                content=filename,
                language=language,
                indent_level=indent_level,
            )

        # Table start: table:name
        table_match = ScrapboxParser.TABLE_PATTERN.match(stripped)
        if table_match:
            table_name = table_match.group(1)
            return ParsedLine(
                original=line,
                line_type=LineType.TABLE_START,
                content=table_name,
                table_name=table_name,
                indent_level=indent_level,
            )

        # Image link: [url image_url] or [image_url url]
        # Check this BEFORE regular image check to avoid false positives
        # Check URL-first format: [url image_url]
        image_link_url_first = ScrapboxParser.IMAGE_LINK_URL_FIRST_PATTERN.match(stripped)
        if image_link_url_first:
            url = image_link_url_first.group(1)
            image_url = image_link_url_first.group(2)
            return ParsedLine(
                original=line,
                line_type=LineType.IMAGE_LINK,
                content=url,
                image_url=image_url,
                indent_level=indent_level,
            )

        # Check image-first format: [image_url url]
        image_link_image_first = ScrapboxParser.IMAGE_LINK_IMAGE_FIRST_PATTERN.match(stripped)
        if image_link_image_first:
            image_url = image_link_image_first.group(1)
            url = image_link_image_first.group(2)
            return ParsedLine(
                original=line,
                line_type=LineType.IMAGE_LINK,
                content=url,
                image_url=image_url,
                indent_level=indent_level,
            )

        # Image URL
        image_urls = ScrapboxParser.extract_image_urls(stripped)
        if image_urls:
            return ParsedLine(original=line, line_type=LineType.IMAGE, content=image_urls[0], indent_level=indent_level)

        # Icon notation: [page_name.icon] or [/icons/page_name.icon]
        icon_match = ScrapboxParser.ICON_PATTERN.match(stripped)
        if icon_match:
            is_icons_project = icon_match.group(1) is not None  # /icons/ prefix
            page_name = icon_match.group(2)
            project = "icons" if is_icons_project else None
            return ParsedLine(
                original=line,
                line_type=LineType.ICON,
                content=page_name,
                icon_page_name=page_name,
                icon_project=project,
                indent_level=indent_level,
            )

        # Cross-project link: [/project/page]
        cross_project_match = ScrapboxParser.CROSS_PROJECT_LINK_PATTERN.match(stripped)
        if cross_project_match:
            project = cross_project_match.group(1)
            page = cross_project_match.group(2)
            # Don't match if it ends with .icon (that should be handled by ICON_PATTERN)
            if not page.endswith(".icon"):
                url = f"https://scrapbox.io/{project}/{page}"
                return ParsedLine(
                    original=line,
                    line_type=LineType.URL,
                    content=url,
                    indent_level=indent_level,
                )

        # Internal link with fragment: [page#fragment] (same project)
        if project_name:
            internal_fragment_match = ScrapboxParser.INTERNAL_FRAGMENT_LINK_PATTERN.match(stripped)
            if internal_fragment_match:
                page_title = internal_fragment_match.group(1)
                fragment = internal_fragment_match.group(2)
                url = f"https://scrapbox.io/{project_name}/{page_title}#{fragment}"
                return ParsedLine(
                    original=line,
                    line_type=LineType.URL,
                    content=url,
                    indent_level=indent_level,
                )

        # External link with display text: [text url] or [url text]
        # Only treat as external_link if the entire line is the link
        external_link_match = ScrapboxParser.EXTERNAL_LINK_PATTERN.search(stripped)
        if external_link_match and external_link_match.group(0) == stripped:
            # Check which group matched
            if external_link_match.group(1):  # [text url] format
                link_text = external_link_match.group(1)
                url = external_link_match.group(2)
            else:  # [url text] format
                url = external_link_match.group(3)
                link_text = external_link_match.group(4)
            return ParsedLine(
                original=line,
                line_type=LineType.EXTERNAL_LINK,
                content=url,
                link_text=link_text,
            )

        # Regular URL (bookmark)
        urls = ScrapboxParser.extract_urls(stripped)
        if urls and stripped.startswith("[") and stripped.endswith("]"):
            return ParsedLine(
                original=line, line_type=LineType.URL, content=urls[0], indent_level=indent_level
            )  # List item (indented)
        if indent_level > 0:
            # Parse rich text for list items
            rich_text = ScrapboxParser._parse_rich_text(stripped)
            content = ScrapboxParser._clean_links(stripped)
            return ParsedLine(
                original=line,
                line_type=LineType.LIST,
                content=content,
                indent_level=indent_level,
                rich_text=rich_text,
            )

        # Regular paragraph
        rich_text = ScrapboxParser._parse_rich_text(stripped)
        content = ScrapboxParser._clean_links(stripped)
        return ParsedLine(
            original=line,
            line_type=LineType.PARAGRAPH,
            content=content,
            rich_text=rich_text,
        )

    @staticmethod
    def parse_text(text: str, project_name: str | None = None) -> list[ParsedLine]:
        """Parse entire Scrapbox text into structured lines.

        Args:
            text: Full text content from Scrapbox
            project_name: Optional Scrapbox project name for internal fragment links

        Returns:
            List of parsed lines
        """
        lines = text.split("\n")[1:]  # Skip title line
        parsed_lines, code_buffer, table_buffer = [], [], []
        in_code_block, in_table_block = False, False
        code_language = "plain text"
        code_indent_level = 0  # Track indent level of code block start
        table_name = ""
        table_indent_level = 0

        for line in lines:
            parsed = ScrapboxParser.parse_line(line, project_name)

            # Handle code blocks
            if parsed.line_type == LineType.CODE_START:
                in_code_block = True
                code_language = parsed.language
                code_buffer = []
                # Store the indent level of the code block start line
                code_indent_level = parsed.indent_level
                continue

            if in_code_block:
                # Calculate current line's indent level
                current_indent = len(line) - len(line.lstrip())

                # Code block ends if:
                # 1. Empty line
                # 2. Line with indent <= code block start indent
                if not line.strip() or current_indent <= code_indent_level:
                    # Save code block
                    if code_buffer:
                        code_content = "\n".join(code_buffer)
                        parsed_lines.append(
                            ParsedLine(
                                original=code_content,
                                line_type=LineType.CODE,
                                content=code_content,
                                language=code_language,
                            )
                        )
                    in_code_block = False
                    code_buffer = []
                    code_indent_level = 0
                    # Process current line normally
                    if line.strip():
                        parsed = ScrapboxParser.parse_line(line)
                        parsed_lines.append(parsed)
                else:
                    # Add to code buffer, removing the base indent level + 1
                    # Code content should be indented one level more than the code: line
                    indent_to_remove = code_indent_level + 1
                    line_indent = len(line) - len(line.lstrip())
                    if line_indent >= indent_to_remove:
                        code_buffer.append(line[indent_to_remove:])
                    else:
                        # Line has less indent than expected, keep as-is
                        code_buffer.append(line.lstrip())
                continue

            # Handle table blocks
            if parsed.line_type == LineType.TABLE_START:
                in_table_block = True
                table_name = parsed.content
                table_buffer = []
                table_indent_level = parsed.indent_level
                continue

            if in_table_block:
                # Empty line or unindented line ends table block
                if not line.strip() or (line and not line.startswith(" ") and not line.startswith("\t")):
                    # Save table block
                    if table_buffer:
                        parsed_lines.append(
                            ParsedLine(
                                original=f"table:{table_name}",
                                line_type=LineType.TABLE,
                                content=table_name,
                                table_name=table_name,
                                table_rows=table_buffer,
                                indent_level=table_indent_level,
                            )
                        )
                    in_table_block = False
                    table_buffer = []
                    # Process current line normally
                    if line.strip():
                        parsed = ScrapboxParser.parse_line(line)
                        parsed_lines.append(parsed)
                else:
                    # Add to table buffer (split by tabs, remove one level of indent)
                    row_content = line.removeprefix(" ").removeprefix("\t")
                    cells = row_content.split("\t")
                    table_buffer.append(cells)
                continue

            parsed_lines.append(parsed)

        # Handle unclosed code block
        if in_code_block and code_buffer:
            code_content = "\n".join(code_buffer)
            parsed_lines.append(
                ParsedLine(
                    original=code_content,
                    line_type=LineType.CODE,
                    content=code_content,
                    language=code_language,
                )
            )

        # Handle unclosed table block
        if in_table_block and table_buffer:
            parsed_lines.append(
                ParsedLine(
                    original=f"table:{table_name}",
                    line_type=LineType.TABLE,
                    content=table_name,
                    table_name=table_name,
                    indent_level=table_indent_level,
                    table_rows=table_buffer,
                )
            )

        return parsed_lines

    @staticmethod
    def _parse_rich_text(text: str) -> list[RichTextElement]:
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
        decorations: list[Decoration] = [
            # Bold: `[[text]]`
            *[
                Decoration(match.start(), match.end(), DecorationType.BOLD, match.group(1), None)
                for match in ScrapboxParser.BOLD_PATTERN.finditer(text)
            ],
            # Bold asterisk: `[* text]`
            *[
                Decoration(match.start(), match.end(), DecorationType.BOLD, match.group(1), None)
                for match in ScrapboxParser.BOLD_ASTERISK_PATTERN.finditer(text)
            ],
            # Italic: `[/ text]`
            *[
                Decoration(match.start(), match.end(), DecorationType.ITALIC, match.group(1), None)
                for match in ScrapboxParser.ITALIC_PATTERN.finditer(text)
            ],
            # Strikethrough: `[- text]`
            *[
                Decoration(match.start(), match.end(), DecorationType.STRIKETHROUGH, match.group(1), None)
                for match in ScrapboxParser.STRIKETHROUGH_PATTERN.finditer(text)
            ],
            # Underline: `[_ text]`
            *[
                Decoration(match.start(), match.end(), DecorationType.UNDERLINE, match.group(1), None)
                for match in ScrapboxParser.UNDERLINE_PATTERN.finditer(text)
            ],
            # Inline code: `code`
            *[
                Decoration(match.start(), match.end(), DecorationType.CODE, match.group(1), None)
                for match in ScrapboxParser.INLINE_CODE_PATTERN.finditer(text)
            ],
            # External links: [text url] or [url text]
            *[
                Decoration(
                    match.start(),
                    match.end(),
                    DecorationType.LINK,
                    match.group(1) if match.group(1) else match.group(4),
                    match.group(2) if match.group(1) else match.group(3),
                )
                for match in ScrapboxParser.EXTERNAL_LINK_PATTERN.finditer(text)
            ],
            # Plain URLs: https://... or http://...
            *[
                Decoration(
                    match.start(),
                    match.end(),
                    DecorationType.LINK,
                    match.group(0),  # Use the URL itself as the text
                    match.group(0),  # And as the link URL
                )
                for match in ScrapboxParser.PLAIN_URL_PATTERN.finditer(text)
            ],
            # Red background: [! text]
            *[
                Decoration(match.start(), match.end(), DecorationType.RED_BACKGROUND, match.group(1), None)
                for match in ScrapboxParser.RED_BACKGROUND_PATTERN.finditer(text)
            ],
            # Green background: [# text]
            *[
                Decoration(match.start(), match.end(), DecorationType.GREEN_BACKGROUND, match.group(1), None)
                for match in ScrapboxParser.GREEN_BACKGROUND_PATTERN.finditer(text)
            ],
            # Blue background: [% text]
            *[
                Decoration(match.start(), match.end(), DecorationType.BLUE_BACKGROUND, match.group(1), None)
                for match in ScrapboxParser.BLUE_BACKGROUND_PATTERN.finditer(text)
            ],
        ]

        # If no decorations found, return plain text
        if not decorations:
            return [RichTextElement(text=text)]

        # Sort by position, then by length (shorter matches first to handle nested patterns)
        decorations.sort(key=lambda x: (x.start, x.end - x.start))

        # Remove overlapping decorations (keep the first one at each position)
        filtered_decorations: list[Decoration] = []
        last_end = 0
        for decoration in decorations:
            start = decoration.start
            if start >= last_end:
                filtered_decorations.append(decoration)
                last_end = decoration.end

        # Build elements
        last_pos = 0
        for decoration in filtered_decorations:
            start = decoration.start
            end = decoration.end
            style = decoration.style
            content = decoration.content
            url = decoration.url
            # Add plain text before this decoration
            if start > last_pos:
                plain_text = text[last_pos:start]
                if plain_text:
                    elements.append(RichTextElement(text=plain_text))

            # Add styled text
            element = RichTextElement(text=content)
            if style == DecorationType.BOLD:
                element.bold = True
            elif style == DecorationType.ITALIC:
                element.italic = True
            elif style == DecorationType.STRIKETHROUGH:
                element.strikethrough = True
            elif style == DecorationType.UNDERLINE:
                element.underline = True
            elif style == DecorationType.CODE:
                element.code = True
            elif style == DecorationType.LINK:
                element.link_url = url
            elif style == DecorationType.RED_BACKGROUND:
                element.background_color = "red_background"
            elif style == DecorationType.GREEN_BACKGROUND:
                element.background_color = "green_background"
            elif style == DecorationType.BLUE_BACKGROUND:
                element.background_color = "blue_background"
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
