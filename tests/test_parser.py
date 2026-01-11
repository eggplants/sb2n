"""Tests for parser module."""

from __future__ import annotations

from sb2n.parser import LineType, RichTextElement, ScrapboxParser


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
    assert parsed.line_type == LineType.HEADING_2
    assert parsed.content == "Main Heading"

    line = "[** Sub Heading]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.HEADING_3
    assert parsed.content == "Sub Heading"


def test_parse_code_block_start() -> None:
    """Test code block start parsing."""
    line = "code:example.py"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.CODE_START
    assert parsed.language == "python"


def test_parse_list_item() -> None:
    """Test list item parsing."""
    line = " List item with indent"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.LIST
    assert "List item" in parsed.content


def test_parse_text_with_multiple_lines() -> None:
    """Test parsing multiple lines."""
    text = "Title\n[* Title]\nThis is a paragraph.\n List item 1\n List item 2\n#tag1 #tag2"
    parsed_lines = ScrapboxParser.parse_text(text)
    assert len(parsed_lines) > 0
    assert parsed_lines[0].line_type == LineType.HEADING_2
    assert any(line.line_type == LineType.LIST for line in parsed_lines)


def test_parse_bold_text() -> None:
    """Test bold text parsing."""
    line = "This is [[bold text]] in a paragraph"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert len(parsed.rich_text) == 3  # plain + bold + plain
    assert parsed.rich_text[1].bold is True
    assert parsed.rich_text[1].text == "bold text"


def test_parse_bold_asterisk_text() -> None:
    """Test bold text parsing with asterisk notation."""
    line = "This is [* bold text] in a paragraph"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert any(elem.bold for elem in parsed.rich_text)
    bold_elem = next(elem for elem in parsed.rich_text if elem.bold)
    assert bold_elem.text == "bold text"


def test_parse_strikethrough_text() -> None:
    """Test strikethrough text parsing."""
    line = "This has [- strikethrough] text"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert any(elem.strikethrough for elem in parsed.rich_text)


def test_parse_italic_text() -> None:
    """Test italic text parsing."""
    line = "This has [/ italic] text"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert any(elem.italic for elem in parsed.rich_text)
    italic_elem = next(elem for elem in parsed.rich_text if elem.italic)
    assert italic_elem.text == "italic"


def test_parse_underline_text() -> None:
    """Test underline text parsing."""
    line = "This has [_ underline] text"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert any(elem.underline for elem in parsed.rich_text)


def test_parse_inline_code() -> None:
    """Test inline code parsing."""
    line = "Use `print()` to output text"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert any(elem.code for elem in parsed.rich_text)
    code_elem = next(elem for elem in parsed.rich_text if elem.code)
    assert code_elem.text == "print()"


def test_parse_external_link_with_text() -> None:
    """Test external link with display text parsing."""
    # Format: [text url]
    line = "[Google https://google.com]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.EXTERNAL_LINK
    assert parsed.content == "https://google.com"
    assert parsed.link_text == "Google"

    # Format: [url text]
    line = "[https://google.com Google]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.EXTERNAL_LINK
    assert parsed.content == "https://google.com"
    assert parsed.link_text == "Google"

    # Format: [multi word text url]
    line = "[simple syntax https://scrapbox.io/help/Syntax]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.EXTERNAL_LINK
    assert parsed.content == "https://scrapbox.io/help/Syntax"
    assert parsed.link_text == "simple syntax"


def test_parse_quote() -> None:
    """Test quote block parsing."""
    line = "> This is a quote"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.QUOTE
    assert parsed.content == "This is a quote"
    assert parsed.rich_text is not None

    # Test quote without space after >
    line = ">quote without space"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.QUOTE
    assert parsed.content == "quote without space"
    assert parsed.rich_text is not None


def test_parse_table_start() -> None:
    """Test table start parsing."""
    line = "table:MyTable"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.TABLE_START
    assert parsed.content == "MyTable"
    assert parsed.table_name == "MyTable"


def test_parse_rich_text_elements() -> None:
    """Test rich text element creation."""
    elem = RichTextElement(text="Hello", bold=True)
    assert elem.text == "Hello"
    assert elem.bold is True
    assert elem.italic is False


def test_parse_mixed_decorations() -> None:
    """Test parsing text with multiple decorations."""
    line = "Normal [[bold]] and `code` text"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.PARAGRAPH
    assert parsed.rich_text is not None
    assert len(parsed.rich_text) >= 3
    assert any(elem.bold for elem in parsed.rich_text)
    assert any(elem.code for elem in parsed.rich_text)


def test_parse_inline_link_with_decorations() -> None:
    """Test parsing text with inline links and decorations."""
    lines = [
        " Highlight text to [* bold], [- strikethrough], and [/ italicize]",
        "or use our [simple syntax https://scrapbox.io/help/Syntax] to style",
    ]
    parsed = ScrapboxParser.parse_line(" ".join(lines))
    assert parsed.line_type == LineType.LIST
    assert parsed.rich_text is not None

    # Check for bold element
    bold_elems = [elem for elem in parsed.rich_text if elem.bold]
    assert len(bold_elems) > 0
    assert bold_elems[0].text == "bold"

    # Check for strikethrough element
    strike_elems = [elem for elem in parsed.rich_text if elem.strikethrough]
    assert len(strike_elems) > 0
    assert strike_elems[0].text == "strikethrough"

    # Check for italic element
    italic_elems = [elem for elem in parsed.rich_text if elem.italic]
    assert len(italic_elems) > 0
    assert italic_elems[0].text == "italicize"

    # Check for link element
    link_elems = [elem for elem in parsed.rich_text if elem.link_url]
    assert len(link_elems) > 0
    assert link_elems[0].text == "simple syntax"
    assert link_elems[0].link_url == "https://scrapbox.io/help/Syntax"
