"""Tests for notion_service module."""

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
        """Test sanitizing localhost URL."""
        url = "http://localhost:3000/path"
        result = NotionService._sanitize_url(url)  # noqa: SLF001
        assert result == "http://localhost:3000/path"
