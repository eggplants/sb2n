"""Markdown exporter for Scrapbox pages."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import TYPE_CHECKING

from sb2n.parser import LineType, ParsedLine, RichTextElement, ScrapboxParser

if TYPE_CHECKING:
    from pathlib import Path

    from sb2n.scrapbox_service import ScrapboxService

logger = logging.getLogger(__name__)


class MarkdownExporter:
    """Convert Scrapbox pages to Markdown format."""

    def __init__(self, scrapbox_service: ScrapboxService, output_dir: Path) -> None:
        """Initialize the Markdown exporter.

        Args:
            scrapbox_service: Scrapbox API service
            output_dir: Base output directory
        """
        self.scrapbox_service = scrapbox_service
        self.output_dir = output_dir
        self.assets_dir = output_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def export_page(self, page_title: str, page_text: str, *, skip_existing: bool = False) -> Path | None:
        """Export a single page as Markdown.

        Args:
            page_title: Title of the page
            page_text: Full text content
            skip_existing: If True, skip exporting if the file already exists

        Returns:
            Path to the exported Markdown file, or None if skipped
        """
        logger.info("Exporting page: %s", page_title)

        # Check if file already exists
        safe_filename = self._sanitize_filename(page_title)
        output_path = self.output_dir / f"{safe_filename}.md"

        if skip_existing and output_path.exists():
            logger.debug("Skipping existing file: %s", output_path)
            return None

        # Parse the page with project name for internal fragment links
        parsed_lines = ScrapboxParser.parse_text(page_text, self.scrapbox_service.project_name)

        # Convert to Markdown
        markdown_lines = []
        markdown_lines.append(f"# {page_title}\n")

        for parsed_line in parsed_lines:
            md_line = self._convert_line_to_markdown(parsed_line)
            if md_line:
                markdown_lines.append(md_line)

        # Write to file
        output_path.write_text("\n".join(markdown_lines), encoding="utf-8")

        logger.info("Exported to: %s", output_path)
        return output_path

    def _convert_line_to_markdown(self, parsed_line: ParsedLine) -> str | None:
        """Convert a parsed line to Markdown.

        Args:
            parsed_line: Parsed Scrapbox line

        Returns:
            Markdown string or None if line should be skipped
        """
        # Skip empty paragraphs
        if not parsed_line.content and parsed_line.line_type == LineType.PARAGRAPH:
            return None

        # Headings
        if parsed_line.line_type in [LineType.HEADING_1, LineType.HEADING_2, LineType.HEADING_3]:
            level = int(parsed_line.line_type.value.split("_")[1])
            hashes = "#" * (level + 1)  # +1 because title is already H1
            if parsed_line.rich_text:
                content = self._convert_rich_text_to_markdown(parsed_line.rich_text)
            else:
                content = parsed_line.content
            return f"{hashes} {content}\n"

        # Quote
        if parsed_line.line_type == LineType.QUOTE:
            if parsed_line.rich_text:
                content = self._convert_rich_text_to_markdown(parsed_line.rich_text)
            else:
                content = parsed_line.content
            return f"> {content}\n"

        # Code block
        if parsed_line.line_type == LineType.CODE:
            language = parsed_line.language if parsed_line.language != "plain text" else ""  # noqa: PLR2004
            # Apply indent if needed
            indent = "  " * max(0, parsed_line.indent_level - 1)
            if indent:
                # Add indent to each line of the code block
                code_lines = (
                    [f"{indent}```{language}"]
                    + [f"{indent}{line}" for line in parsed_line.content.split("\n")]
                    + [f"{indent}```"]
                )
                return "\n".join(code_lines) + "\n"
            return f"```{language}\n{parsed_line.content}\n```\n"

        # Image
        if parsed_line.line_type == LineType.IMAGE:
            # Download image and save to assets
            image_path = self._download_image(parsed_line.content)
            if image_path:
                relative_path = image_path.relative_to(self.output_dir)
                return f"![image]({relative_path})\n"
            return f"![image]({parsed_line.content})\n"

        # URL
        if parsed_line.line_type == LineType.URL:
            return f"[{parsed_line.content}]({parsed_line.content})\n"

        # External link with text
        if parsed_line.line_type == LineType.EXTERNAL_LINK:
            link_text = parsed_line.link_text or parsed_line.content
            return f"[{link_text}]({parsed_line.content})\n"

        # Image link (link with thumbnail image)
        if parsed_line.line_type == LineType.IMAGE_LINK:
            # Download the thumbnail image
            image_path = self._download_image(str(parsed_line.image_url))
            if image_path:
                relative_path = image_path.relative_to(self.output_dir)
                # Create a linked image in Markdown
                return f"[![image]({relative_path})]({parsed_line.content})\n"
            # Fallback if image download fails
            return f"[![image]({parsed_line.image_url})]({parsed_line.content})\n"

        # List item
        if parsed_line.line_type == LineType.LIST:
            indent = "  " * max(0, parsed_line.indent_level - 1)
            if parsed_line.rich_text:
                content = self._convert_rich_text_to_markdown(parsed_line.rich_text)
            else:
                content = parsed_line.content
            return f"{indent}- {content}\n"

        # Table
        if parsed_line.line_type == LineType.TABLE:
            if not parsed_line.table_rows:
                return None

            # Find maximum column count
            max_columns = max(len(row) for row in parsed_line.table_rows)

            # Apply indent if needed
            indent = "  " * max(0, parsed_line.indent_level - 1)

            # Build Markdown table
            table_lines = []

            # Add rows, padding to max column count
            for row in parsed_line.table_rows:
                # Ensure all cells are strings and handle empty cells
                cells = [str(cell) if cell else "" for cell in row]
                # Pad with empty cells to match max column count
                cells.extend([""] * (max_columns - len(cells)))
                table_lines.append(indent + "|" + "|".join(cells) + "|")

            # Insert header separator after first row (if exists)
            if table_lines:
                separator = indent + "|" + "|".join(["-"] * max_columns) + "|"
                table_lines.insert(1, separator)

            return "\n".join(table_lines) + "\n"

        # Paragraph (includes text with inline decorations)
        if parsed_line.rich_text:
            content = self._convert_rich_text_to_markdown(parsed_line.rich_text)
            return f"{content}\n"

        return f"{parsed_line.content}\n"

    def _convert_rich_text_to_markdown(self, rich_text: list[RichTextElement]) -> str:
        """Convert rich text elements to Markdown.

        Args:
            rich_text: List of rich text elements

        Returns:
            Markdown formatted string
        """
        result = []
        for elem in rich_text:
            text = elem.text

            # Apply decorations
            if elem.code:
                text = f"`{text}`"
            if elem.bold:
                text = f"**{text}**"
            if elem.italic:
                text = f"*{text}*"
            if elem.strikethrough:
                text = f"~~{text}~~"
            if elem.underline:
                # Markdown doesn't have native underline, use HTML
                text = f"<u>{text}</u>"
            if elem.link_url:
                text = f"[{text}]({elem.link_url})"

            # Background colors - use HTML/CSS
            if elem.background_color:
                color_map = {
                    "red": "#ffebee",
                    "green": "#e8f5e9",
                    "blue": "#e3f2fd",
                }
                bg_color = color_map.get(elem.background_color, "#f0f0f0")
                text = f'<span style="background-color: {bg_color}">{text}</span>'

            result.append(text)

        return "".join(result)

    def _download_image(self, url: str) -> Path | None:
        """Download an image and save to assets directory.

        Args:
            url: Image URL

        Returns:
            Path to saved image or None if download failed
        """
        try:
            # Generate filename from URL hash
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
            # Try to get extension from URL
            match = re.search(r"\.([a-zA-Z0-9]+)(?:\?|$)", url)
            ext = match.group(1) if match else "jpg"
            filename = f"{url_hash}.{ext}"

            image_path = self.assets_dir / filename

            # Skip if already downloaded
            if image_path.exists():
                return image_path

            # Download image
            image_data = self.scrapbox_service.download_file(url)
            if image_data:
                image_path.write_bytes(image_data)
                logger.debug("Downloaded image: %s -> %s", url, image_path)
                return image_path

            logger.warning("Failed to download image: %s", url)

        except Exception:
            logger.exception("Error downloading image: %s", url)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for filesystem.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(". ")
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized or "untitled"
