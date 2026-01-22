"""Tests for notion_service module."""

from sb2n.legacy_parser import RichTextElement
from sb2n.notion_service import NotionService


class TestNotionService:
    """Test cases for NotionService."""

    def test_sanitize_url_valid_http(self) -> None:
        """Test sanitizing a valid HTTP URL."""
        url = "http://example.com/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001  # noqa: SLF001
        assert result == "http://example.com/path"

    def test_sanitize_url_valid_https(self) -> None:
        """Test sanitizing a valid HTTPS URL."""
        url = "https://example.com/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://example.com/path"

    def test_sanitize_url_with_query(self) -> None:
        """Test sanitizing URL with query parameters."""
        url = "https://example.com/path?key=value&foo=bar"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://example.com/path?key=value&foo=bar"

    def test_sanitize_url_with_fragment(self) -> None:
        """Test sanitizing URL with fragment."""
        url = "https://scrapbox.io/project/page#6722f8544d2e880000132e24"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://scrapbox.io/project/page#6722f8544d2e880000132e24"

    def test_sanitize_url_with_japanese_characters(self) -> None:
        """Test sanitizing URL with Japanese characters."""
        url = "https://scrapbox.io/project/日本語ページ"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        # Should be properly encoded
        assert result is not None
        assert "scrapbox.io" in result

    def test_sanitize_url_with_spaces(self) -> None:
        """Test sanitizing URL with spaces."""
        url = "https://example.com/path with spaces"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is not None
        assert " " not in result  # Spaces should be encoded

    def test_sanitize_url_no_scheme(self) -> None:
        """Test sanitizing URL without scheme."""
        url = "example.com/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_invalid_scheme(self) -> None:
        """Test sanitizing URL with invalid scheme."""
        url = "ftp://example.com/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_empty(self) -> None:
        """Test sanitizing empty URL."""
        url = ""
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_special_characters_in_fragment(self) -> None:
        """Test sanitizing URL with special characters in fragment."""
        url = "https://scrapbox.io/project/page#section!@#$%^&*()"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is not None
        assert "scrapbox.io" in result

    def test_sanitize_url_with_port(self) -> None:
        """Test sanitizing URL with port number."""
        url = "https://example.com:8080/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://example.com:8080/path"

    def test_sanitize_url_localhost(self) -> None:
        """Test sanitizing localhost URL (should return None to treat as plain text)."""
        url = "http://localhost:3000/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_0_0_0_0(self) -> None:
        """Test sanitizing 0.0.0.0 URL (should return None to treat as plain text)."""
        url = "http://0.0.0.0:8000"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_127_0_0_1(self) -> None:
        """Test sanitizing 127.0.0.1 URL (should return None to treat as plain text)."""
        url = "http://127.0.0.1:8000"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_with_trailing_quote(self) -> None:
        """Test sanitizing URL with trailing single quote."""
        url = "https://github.com/example/repo.git'"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://github.com/example/repo.git"

    def test_sanitize_url_with_trailing_html(self) -> None:
        """Test sanitizing URL with trailing HTML characters (localhost should be treated as plain text)."""
        url = 'http://localhost:3000/addText">'
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result is None

    def test_sanitize_url_with_trailing_parenthesis(self) -> None:
        """Test sanitizing URL with trailing parenthesis."""
        url = "https://example.com/path)"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://example.com/path"

    def test_sanitize_url_with_multiple_trailing_chars(self) -> None:
        """Test sanitizing URL with multiple trailing characters."""
        url = "https://example.com/path'\">"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "https://example.com/path"

    def test_create_paragraph_with_long_url(self) -> None:
        """Test creating paragraph with URL exceeding 2000 characters."""
        # Create a service instance (note: this won't actually connect to Notion)
        service = NotionService(api_key="test_key", database_id="test_db")

        # Create a very long URL (over 2000 characters)
        long_url = "https://example.com/path?" + "a" * 2000

        # Create rich text with long URL
        rich_text = [RichTextElement(text="Link", link_url=long_url)]

        # Create paragraph block
        block = service.create_paragraph_block(rich_text)

        # Verify the block was created
        assert block is not None
        assert block.type == "paragraph"

        # The rich text should exist
        rich_text_array = block.paragraph["rich_text"]
        assert len(rich_text_array) > 0

        # URL should NOT be in the link (should be treated as plain text)
        # because it exceeds 2000 characters
        assert "link" not in rich_text_array[0]["text"]

    def test_create_table_with_many_rows(self) -> None:
        """Test creating table with more than 100 rows (should split into multiple tables)."""
        service = NotionService(api_key="test_key", database_id="test_db")

        # Create a table with 120 rows (exceeds 100 limit)
        table_rows = [["Header1", "Header2"]]
        table_rows.extend([[f"Cell {i}A", f"Cell {i}B"] for i in range(120)])

        # Create table block
        result = service.create_table_block(table_rows, has_column_header=True)

        # Should return a list of tables (split)
        assert isinstance(result, list)
        assert len(result) > 1

        # First table should have 100 rows (including header)
        first_table = result[0]
        assert len(first_table.children) == 100

        # Second table should have remaining rows plus header
        # Total: 121 rows (1 header + 120 data)
        # First: 100 rows, Second: 22 rows (1 header + 21 data)
        second_table = result[1]
        assert len(second_table.children) == 22

    def test_create_table_exactly_100_rows(self) -> None:
        """Test creating table with exactly 100 rows (should not split)."""
        service = NotionService(api_key="test_key", database_id="test_db")

        # Create a table with exactly 100 rows (including header)
        table_rows = [["Header1", "Header2"]]
        table_rows.extend([[f"Cell {i}A", f"Cell {i}B"] for i in range(99)])

        # Create table block
        result = service.create_table_block(table_rows, has_column_header=True)

        # Should return a single table (not a list)
        assert not isinstance(result, list)
        assert len(result.children) == 100
