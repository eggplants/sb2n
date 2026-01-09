"""Tests for parser module."""

from __future__ import annotations

from sb2n.parser import ScrapboxParser


def test_extract_tags() -> None:
    """Test tag extraction from text."""
    text = "This is a #test with #multiple #tags"
    tags = ScrapboxParser.extract_tags(text)
    assert tags == ["test", "multiple", "tags"]


def test_extract_tags_ignores_inline_code() -> None:
    """Test that tags inside inline code are ignored."""
    text = "Link internal pages with brackets like this: `[link text]` or like this `#link`"
    tags = ScrapboxParser.extract_tags(text)
    assert tags == []

    text_with_real_tag = "This is a real #tag but `#notag` is in code"
    tags = ScrapboxParser.extract_tags(text_with_real_tag)
    assert tags == ["tag"]


def test_extract_image_urls() -> None:
    """Test image URL extraction."""
    text = "[https://example.com/image.jpg] and [https://gyazo.com/abc123]"
    urls = ScrapboxParser.extract_image_urls(text)
    assert len(urls) == 2
    assert "https://gyazo.com/abc123" in urls


def test_parse_heading() -> None:
    """Test heading parsing."""
    line = "[* Main Heading]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == "heading_2"
    assert parsed.content == "Main Heading"

    line = "[** Sub Heading]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == "heading_3"
    assert parsed.content == "Sub Heading"


def test_parse_code_block_start() -> None:
    """Test code block start parsing."""
    line = "code:example.py"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == "code_start"
    assert parsed.language == "python"


def test_parse_list_item() -> None:
    """Test list item parsing."""
    line = " List item with indent"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == "list"
    assert "List item" in parsed.content


def test_parse_text_with_multiple_lines() -> None:
    """Test parsing multiple lines."""
    text = """[* Title]
This is a paragraph.
 List item 1
 List item 2
#tag1 #tag2"""

    parsed_lines = ScrapboxParser.parse_text(text)
    assert len(parsed_lines) > 0
    assert parsed_lines[0].line_type == "heading_2"
    assert any(line.line_type == "list" for line in parsed_lines)
