"""Tests for Notion API block content limits."""

from sb2n.notion_service import NotionService


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
        # First block should have 2000 chars, second should have 1
        assert len(result[0].code["rich_text"][0]["text"]["content"]) == 2000
        assert len(result[1].code["rich_text"][0]["text"]["content"]) == 1

    def test_code_block_split_multiple_chunks(self) -> None:
        """Test that large code blocks are split into multiple chunks."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 5500  # Should create 3 blocks: 2000, 2000, 1500
        result = notion.create_code_block(code, "javascript")
        # Should be a list of 3 CodeBlocks
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(block.type == "code" for block in result)
        assert len(result[0].code["rich_text"][0]["text"]["content"]) == 2000
        assert len(result[1].code["rich_text"][0]["text"]["content"]) == 2000
        assert len(result[2].code["rich_text"][0]["text"]["content"]) == 1500

    def test_code_block_language_preserved(self) -> None:
        """Test that language is preserved when splitting code blocks."""
        notion = NotionService("test_key", "test_db_id")
        code = "x" * 3000
        result = notion.create_code_block(code, "rust")
        assert isinstance(result, list)
        # All blocks should have the same language
        assert all(block.code["language"] == "rust" for block in result)
