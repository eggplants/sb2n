"""Tests for Lark-based Scrapbox parser."""

from __future__ import annotations

import pytest

from sb2n.lark_parser import ScrapboxLarkParser
from sb2n.models.ast import (
    CalloutNode,
    CodeBlockNode,
    CommandNode,
    DocumentNode,
    HashtagNode,
    InlineCodeNode,
    LineNode,
    ParagraphNode,
    QuoteNode,
    TableNode,
)


@pytest.fixture
def parser() -> ScrapboxLarkParser:
    """Create parser instance."""
    return ScrapboxLarkParser()


def test_parse_plain_text(parser: ScrapboxLarkParser) -> None:
    """Test parsing plain text."""
    result = parser.parse_line("これは通常のテキストです")

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 1

    line = result.lines[0]
    assert isinstance(line, LineNode)
    assert line.indent == 0
    assert isinstance(line.content, ParagraphNode)
    assert len(line.content.content) == 1
    assert line.content.content[0] == "これは通常のテキストです"


def test_parse_hashtag(parser: ScrapboxLarkParser) -> None:
    """Test parsing hashtag."""
    result = parser.parse_line("#ハッシュタグ")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    content = line.content.content[0]
    assert isinstance(content, HashtagNode)
    assert content.type == "hashtag"
    assert content.tag == "ハッシュタグ"


def test_parse_inline_code(parser: ScrapboxLarkParser) -> None:
    """Test parsing inline code."""
    result = parser.parse_line("`インラインコード`")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    content = line.content.content[0]
    assert isinstance(content, InlineCodeNode)
    assert content.type == "code"
    assert content.code == "インラインコード"


def test_parse_quote(parser: ScrapboxLarkParser) -> None:
    """Test parsing quote."""
    result = parser.parse_line("> 引用文")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, QuoteNode)
    assert line.content.type == "quote"
    assert line.content.content == " 引用文"


def test_parse_callout(parser: ScrapboxLarkParser) -> None:
    """Test parsing callout."""
    result = parser.parse_line("? コールアウト")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CalloutNode)
    assert line.content.type == "callout"
    assert line.content.content == " コールアウト"


def test_parse_command(parser: ScrapboxLarkParser) -> None:
    """Test parsing command line."""
    result = parser.parse_line("$ git status")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CommandNode)
    assert line.content.type == "command"
    assert line.content.prefix == "$"
    assert line.content.content == " git status"


def test_parse_command_with_percent(parser: ScrapboxLarkParser) -> None:
    """Test parsing command line with % prefix."""
    result = parser.parse_line("% npm install")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CommandNode)
    assert line.content.type == "command"
    assert line.content.prefix == "%"
    assert line.content.content == " npm install"


def test_parse_code_block_header(parser: ScrapboxLarkParser) -> None:
    """Test parsing code block header."""
    result = parser.parse_line("code:python")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.type == "code_block"
    assert line.content.language == "python"


def test_parse_table_header(parser: ScrapboxLarkParser) -> None:
    """Test parsing table header."""
    result = parser.parse_line("table:sample")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, TableNode)
    assert line.content.type == "table"
    assert line.content.name == "sample"


def test_parse_indented_line(parser: ScrapboxLarkParser) -> None:
    """Test parsing indented line."""
    result = parser.parse_line("  インデントされたテキスト")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert line.indent == 2
    assert isinstance(line.content, ParagraphNode)


def test_parse_empty_line(parser: ScrapboxLarkParser) -> None:
    """Test parsing empty line."""
    result = parser.parse_line("")

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.indent == 0
    assert line.content is None


def test_parse_mixed_inline_elements(parser: ScrapboxLarkParser) -> None:
    """Test parsing mixed inline elements."""
    result = parser.parse_line("テキストと#タグと`コード`")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    content = line.content.content
    assert len(content) == 3
    assert content[0] == "テキストと"
    assert isinstance(content[1], HashtagNode)
    assert content[1].tag == "タグと"
    assert isinstance(content[2], InlineCodeNode)
    assert content[2].code == "コード"


def test_parse_multiline_document(parser: ScrapboxLarkParser) -> None:
    """Test parsing multiline document."""
    text = """ページタイトル
これは通常のテキスト
 インデントされた行
code:python
> 引用文
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 5

    # First line: plain text
    assert isinstance(result.lines[0].content, ParagraphNode)

    # Second line: plain text
    assert isinstance(result.lines[1].content, ParagraphNode)

    # Third line: indented
    assert result.lines[2].indent == 1

    # Fourth line: code block
    assert isinstance(result.lines[3].content, CodeBlockNode)

    # Fifth line: quote
    assert isinstance(result.lines[4].content, QuoteNode)


def test_parse_japanese_text(parser: ScrapboxLarkParser) -> None:
    """Test parsing Japanese text."""
    result = parser.parse_line("日本語のテキストです")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    assert line.content.content[0] == "日本語のテキストです"


def test_parse_special_characters(parser: ScrapboxLarkParser) -> None:
    """Test parsing special characters."""
    result = parser.parse_line("特殊文字: !@#$%^&*()")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)


def test_parse_multiple_hashtags(parser: ScrapboxLarkParser) -> None:
    """Test parsing multiple hashtags."""
    result = parser.parse_line("#タグ1 #タグ2 #タグ3")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    # Count hashtags
    hashtag_count = sum(1 for item in line.content.content if isinstance(item, HashtagNode))
    assert hashtag_count == 3


def test_parse_multiple_inline_codes(parser: ScrapboxLarkParser) -> None:
    """Test parsing multiple inline codes."""
    result = parser.parse_line("`code1` と `code2`")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    # Count inline codes
    code_count = sum(1 for item in line.content.content if isinstance(item, InlineCodeNode))
    assert code_count == 2


def test_parse_edge_case_empty_hashtag(parser: ScrapboxLarkParser) -> None:
    """Test parsing edge case with hashtag and space."""
    result = parser.parse_line("テキスト#tag")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    # Should contain both text and hashtag
    assert len(line.content.content) >= 2
    hashtags = [item for item in line.content.content if isinstance(item, HashtagNode)]
    assert len(hashtags) >= 1


def test_parse_edge_case_empty_code(parser: ScrapboxLarkParser) -> None:
    """Test parsing edge case with empty inline code."""
    result = parser.parse_line("テキスト `test`")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    # Should contain at least inline code element
    code_elements = [item for item in line.content.content if isinstance(item, InlineCodeNode)]
    assert len(code_elements) >= 1


def test_parse_max_indent(parser: ScrapboxLarkParser) -> None:
    """Test parsing maximum indent level."""
    result = parser.parse_line("          深いインデント")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert line.indent == 10
    assert isinstance(line.content, ParagraphNode)


def test_parse_code_block_with_extension(parser: ScrapboxLarkParser) -> None:
    """Test parsing code block with file extension."""
    result = parser.parse_line("code:example.py")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "example.py"


def test_parse_table_with_special_name(parser: ScrapboxLarkParser) -> None:
    """Test parsing table with special characters in name."""
    result = parser.parse_line("table:テーブル_名_2024")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, TableNode)
    assert line.content.name == "テーブル_名_2024"


def test_parse_quote_with_multiple_lines_content(parser: ScrapboxLarkParser) -> None:
    """Test parsing quote with long content."""
    long_text = "これは非常に長い引用文です。" * 10
    result = parser.parse_line(f"> {long_text}")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, QuoteNode)
    assert long_text in line.content.content


def test_parse_callout_with_long_content(parser: ScrapboxLarkParser) -> None:
    """Test parsing callout with long content."""
    long_text = "重要な情報が含まれています。" * 10
    result = parser.parse_line(f"? {long_text}")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CalloutNode)
    assert long_text in line.content.content


def test_parse_command_with_complex_command(parser: ScrapboxLarkParser) -> None:
    """Test parsing command with complex command string."""
    result = parser.parse_line("$ git commit -m 'feat: add new feature'")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CommandNode)
    assert "git commit" in line.content.content


# Tests based on specification examples


def test_example_1_paragraph(parser: ScrapboxLarkParser) -> None:
    """Example 1: Paragraph."""
    result = parser.parse_line("これは段落です。")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    assert line.content.content[0] == "これは段落です。"


def test_example_2_bulleted_list(parser: ScrapboxLarkParser) -> None:
    """Example 2: Bulleted list with multiple levels."""
    text = """通常の行
 レベル1の箇条書き
  レベル2の箇条書き
   レベル3の箇条書き
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 4

    # Normal line
    assert result.lines[0].indent == 0

    # Level 1
    assert result.lines[1].indent == 1

    # Level 2
    assert result.lines[2].indent == 2

    # Level 3
    assert result.lines[3].indent == 3


def test_example_3_code_block(parser: ScrapboxLarkParser) -> None:
    """Example 3: Code block."""
    text = """code:example.js
 function hello() {
   console.log("Hello");
 }
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "example.js"


def test_example_4_code_block_python(parser: ScrapboxLarkParser) -> None:
    """Example 4: Code block with language name."""
    result = parser.parse_line("code:python")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "python"


def test_example_5_table(parser: ScrapboxLarkParser) -> None:
    """Example 5: Table."""
    result = parser.parse_line("table:サンプル")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, TableNode)
    assert line.content.name == "サンプル"


def test_example_6_quote(parser: ScrapboxLarkParser) -> None:
    """Example 6: Quote."""
    result = parser.parse_line("> これは引用です。")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, QuoteNode)
    assert "これは引用です。" in line.content.content


def test_example_7_math_block(parser: ScrapboxLarkParser) -> None:
    """Example 7: Math block (tex code block)."""
    result = parser.parse_line("code:tex")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "tex"


def test_example_8_mermaid_diagram(parser: ScrapboxLarkParser) -> None:
    """Example 8: Mermaid diagram."""
    result = parser.parse_line("code:mermaid")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "mermaid"


def test_example_9_callout(parser: ScrapboxLarkParser) -> None:
    """Example 9: Callout (Helpfeel notation)."""
    result = parser.parse_line("? よくある質問の内容")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CalloutNode)
    assert "よくある質問の内容" in line.content.content


def test_example_10_command_line(parser: ScrapboxLarkParser) -> None:
    """Example 10: Command line."""
    # Test with $
    result = parser.parse_line("$ git status")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CommandNode)
    assert line.content.prefix == "$"
    assert "git status" in line.content.content

    # Test with %
    result = parser.parse_line("% ls -la")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CommandNode)
    assert line.content.prefix == "%"
    assert "ls -la" in line.content.content


def test_example_18_hashtag(parser: ScrapboxLarkParser) -> None:
    """Example 18: Hashtag."""
    # Japanese hashtag
    result = parser.parse_line("#タグ名")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    content = line.content.content[0]
    assert isinstance(content, HashtagNode)
    assert content.tag == "タグ名"

    # Alphanumeric hashtag
    result = parser.parse_line("#tag-name")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)
    content = line.content.content[0]
    assert isinstance(content, HashtagNode)
    assert content.tag == "tag-name"


def test_example_35_inline_code(parser: ScrapboxLarkParser) -> None:
    """Example 35: Inline code."""
    result = parser.parse_line("これは `code` です。")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    # Should contain text, inline code, and text
    assert len(line.content.content) == 3
    assert line.content.content[0] == "これは "
    assert isinstance(line.content.content[1], InlineCodeNode)
    assert line.content.content[1].code == "code"
    assert line.content.content[2] == " です。"


def test_multiple_code_blocks_language_variants(parser: ScrapboxLarkParser) -> None:
    """Test code blocks with various language names."""
    languages = ["javascript", "js", "python", "py", "ruby", "rb", "java", "c", "cpp"]

    for lang in languages:
        result = parser.parse_line(f"code:{lang}")

        assert isinstance(result, DocumentNode)
        line = result.lines[0]
        assert isinstance(line.content, CodeBlockNode)
        assert line.content.language == lang


def test_multiline_quote(parser: ScrapboxLarkParser) -> None:
    """Test multiline quote."""
    text = """> 引用行1
> 引用行2
> 引用行3
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 3

    for line in result.lines:
        assert isinstance(line.content, QuoteNode)


def test_multiline_callout(parser: ScrapboxLarkParser) -> None:
    """Test multiline callout."""
    text = """? 質問1
? 質問2
? 質問3
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 3

    for line in result.lines:
        assert isinstance(line.content, CalloutNode)


def test_mixed_command_symbols(parser: ScrapboxLarkParser) -> None:
    """Test mixed command symbols."""
    text = """$ git status
% npm install
$ echo "Hello"
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 3

    assert isinstance(result.lines[0].content, CommandNode)
    assert result.lines[0].content.prefix == "$"

    assert isinstance(result.lines[1].content, CommandNode)
    assert result.lines[1].content.prefix == "%"

    assert isinstance(result.lines[2].content, CommandNode)
    assert result.lines[2].content.prefix == "$"


def test_code_block_with_filename(parser: ScrapboxLarkParser) -> None:
    """Test code block with filename."""
    filenames = ["example.js", "script.py", "main.rb", "App.java", "program.c"]

    for filename in filenames:
        result = parser.parse_line(f"code:{filename}")

        assert isinstance(result, DocumentNode)
        line = result.lines[0]
        assert isinstance(line.content, CodeBlockNode)
        assert line.content.language == filename


def test_table_with_various_names(parser: ScrapboxLarkParser) -> None:
    """Test table with various names."""
    table_names = ["サンプル", "example", "table-1", "データ_2024", "test123"]

    for name in table_names:
        result = parser.parse_line(f"table:{name}")

        assert isinstance(result, DocumentNode)
        line = result.lines[0]
        assert isinstance(line.content, TableNode)
        assert line.content.name == name


def test_nested_indentation(parser: ScrapboxLarkParser) -> None:
    """Test deeply nested indentation."""
    text = """ Level 1
  Level 2
   Level 3
    Level 4
     Level 5
"""
    result = parser.parse(text)

    assert isinstance(result, DocumentNode)
    assert len(result.lines) == 5

    for i, line in enumerate(result.lines):
        assert line.indent == i + 1


def test_mixed_inline_elements_complex(parser: ScrapboxLarkParser) -> None:
    """Test complex mixed inline elements."""
    result = parser.parse_line("テキスト #タグ1 `code` #タグ2 more text")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    # Should contain multiple elements
    assert len(line.content.content) > 5

    # Count different types
    hashtag_count = sum(1 for item in line.content.content if isinstance(item, HashtagNode))
    code_count = sum(1 for item in line.content.content if isinstance(item, InlineCodeNode))

    assert hashtag_count == 2
    assert code_count == 1


def test_empty_code_block_header(parser: ScrapboxLarkParser) -> None:
    """Test code block with minimal language name."""
    result = parser.parse_line("code:x")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, CodeBlockNode)
    assert line.content.language == "x"


def test_empty_table_header(parser: ScrapboxLarkParser) -> None:
    """Test table with minimal name."""
    result = parser.parse_line("table:t")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, TableNode)
    assert line.content.name == "t"


def test_inline_code_empty(parser: ScrapboxLarkParser) -> None:
    """Test parsing empty inline code."""
    result = parser.parse_line("Empty code: ``")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert isinstance(line.content, ParagraphNode)

    # Should have plain text "Empty code: " and empty inline code
    assert len(line.content.content) == 2
    assert line.content.content[0] == "Empty code: "
    content = line.content.content[1]
    assert isinstance(content, InlineCodeNode)
    assert content.code == ""


def test_inline_code_unclosed(parser: ScrapboxLarkParser) -> None:
    """Test parsing unclosed inline code at end of line."""
    result = parser.parse_line(" バッククオート`\\``で囲む")

    assert isinstance(result, DocumentNode)
    line = result.lines[0]
    assert line.indent == 1  # Leading space is indent
    assert isinstance(line.content, ParagraphNode)

    # Parses as: plain text "バッククオート", code `\`, code `で囲む (unclosed)
    assert len(line.content.content) == 3
    assert line.content.content[0] == "バッククオート"
    content1 = line.content.content[1]
    assert isinstance(content1, InlineCodeNode)
    assert content1.code == "\\"
    content2 = line.content.content[2]
    assert isinstance(content2, InlineCodeNode)
    assert content2.code == "で囲む"  # Unclosed inline code (backtick excluded from CODE_TEXT_EOL)
