"""Tests for Notion API block content limits."""

from sb2n.converter import NotionBlockConverter
from sb2n.notion_service import NotionService


def utf16_length(s: str) -> int:
    """Calculate string length as UTF-16 code units (JavaScript string.length equivalent)."""
    return len(s.encode("utf-16-le")) // 2


class TestBlockLimits:
    """Test cases for Notion block content limits."""

    def test_code_block_under_limit(self) -> None:
        """Test that code blocks under 2000 chars return a single block."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 1999
        result = notion.create_code_block(code, "python")
        # Should be a single CodeBlock, not a list
        assert not isinstance(result, list)
        assert result.type == "code"

    def test_code_block_at_limit(self) -> None:
        """Test that code blocks at exactly 2000 chars return a single block."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 2000
        result = notion.create_code_block(code, "python")
        # Should be a single CodeBlock, not a list
        assert not isinstance(result, list)
        assert result.type == "code"

    def test_code_block_over_limit(self) -> None:
        """Test that code blocks over 2000 chars are split into multiple blocks."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 2001
        result = notion.create_code_block(code, "python")
        # Should be a list of CodeBlocks
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(block.type == "code" for block in result)
        # Check UTF-16 lengths
        assert utf16_length(result[0].code["rich_text"][0]["text"]["content"]) <= 2000
        assert utf16_length(result[1].code["rich_text"][0]["text"]["content"]) <= 2000

    def test_code_block_split_multiple_chunks(self) -> None:
        """Test that large code blocks are split into multiple chunks."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 5500  # Should create 3 blocks
        result = notion.create_code_block(code, "javascript")
        # Should be a list of CodeBlocks
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(block.type == "code" for block in result)
        # All chunks should be within UTF-16 limit
        for block in result:
            content = block.code["rich_text"][0]["text"]["content"]
            assert utf16_length(content) <= 2000

    def test_code_block_language_preserved(self) -> None:
        """Test that language is preserved when splitting code blocks."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 3000
        result = notion.create_code_block(code, "rust")
        assert isinstance(result, list)
        # All blocks should have the same language
        assert all(block.code["language"] == "rust" for block in result)

    def test_converter_handles_long_code_block(self) -> None:
        """Test that converter properly handles code blocks over 2000 chars."""
        notion = NotionService("test_key", "test_db_id")
        converter = NotionBlockConverter(notion)

        # Create a Scrapbox text with a long code block
        # In Scrapbox, first line is the title, then content follows
        # Code blocks have 1 space indent per line
        long_code_lines = ["x" * 100 for _ in range(21)]  # 21 lines * 100 chars = 2100 chars
        code_content = "\n ".join(long_code_lines)
        # Use .py extension so language is detected as python
        scrapbox_text = f"TestPage\ncode:test.py\n {code_content}"

        blocks = converter.convert_to_blocks(scrapbox_text)

        # Should have 2 code blocks (split by UTF-16 length)
        assert len(blocks) == 2
        assert all(block.type == "code" for block in blocks)
        assert blocks[0].code["language"] == "python"  # ty:ignore[unresolved-attribute]
        assert blocks[1].code["language"] == "python"  # ty:ignore[unresolved-attribute]
        # All blocks should be within UTF-16 limit
        assert utf16_length(blocks[0].code["rich_text"][0]["text"]["content"]) <= 2000  # ty:ignore[unresolved-attribute]
        assert utf16_length(blocks[1].code["rich_text"][0]["text"]["content"]) <= 2000  # ty:ignore[unresolved-attribute]

    def test_converter_handles_multiple_long_code_blocks(self) -> None:
        """Test that converter handles multiple long code blocks in the same page."""
        notion = NotionService("test_key", "test_db_id")
        converter = NotionBlockConverter(notion)

        # Create a Scrapbox text with multiple long code blocks
        long_code1_lines = ["a" * 100 for _ in range(21)]
        long_code1 = "\n ".join(long_code1_lines)
        long_code2_lines = ["b" * 100 for _ in range(36)]
        long_code2 = "\n ".join(long_code2_lines)

        scrapbox_text = f"TestPage\ncode:test.js\n {long_code1}\n\nSome text\n\ncode:script.py\n {long_code2}"

        blocks = converter.convert_to_blocks(scrapbox_text)

        # Should have: 2 code blocks (first split), 1 paragraph, 2 code blocks (second split) = 5 total
        assert len(blocks) == 5

        # First code block (split into 2)
        assert blocks[0].type == "code"
        assert blocks[0].code["language"] == "javascript"  # ty:ignore[unresolved-attribute]
        assert blocks[1].type == "code"
        assert blocks[1].code["language"] == "javascript"  # ty:ignore[unresolved-attribute]

        # Paragraph
        assert blocks[2].type == "paragraph"

        # Second code block (split into 2)
        assert blocks[3].type == "code"
        assert blocks[3].code["language"] == "python"  # ty:ignore[unresolved-attribute]
        assert utf16_length(blocks[3].code["rich_text"][0]["text"]["content"]) <= 2000  # ty:ignore[unresolved-attribute]
        assert blocks[4].type == "code"
        assert blocks[4].code["language"] == "python"  # ty:ignore[unresolved-attribute]
        assert utf16_length(blocks[4].code["rich_text"][0]["text"]["content"]) <= 2000  # ty:ignore[unresolved-attribute]

    def test_code_block_with_emojis(self) -> None:
        """Test that code blocks with emojis are split correctly based on UTF-16 length."""
        notion = NotionService("test_key", "test_db_id")

        # Create code with emojis that have different UTF-16 lengths
        # Regular emojis like 😀 are 1 code point but 2 UTF-16 code units (surrogate pair)
        code_with_emojis = "x" * 1990 + "😀" * 5  # 1990 + 5*2 = 2000 UTF-16 units

        result = notion.create_code_block(code_with_emojis, "javascript")

        # Should not be split since UTF-16 length is exactly 2000
        assert not isinstance(result, list)
        assert result.type == "code"
        assert utf16_length(result.code["rich_text"][0]["text"]["content"]) == 2000

        # Add one more character to exceed limit
        code_exceeds = code_with_emojis + "x"
        result2 = notion.create_code_block(code_exceeds, "javascript")

        # Should be split now
        assert isinstance(result2, list)
        assert len(result2) == 2
        # All chunks should be within limit
        for block in result2:
            assert utf16_length(block.code["rich_text"][0]["text"]["content"]) <= 2000
