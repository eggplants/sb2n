"""Tests for link_restorer module."""

from unittest.mock import MagicMock

import pytest

from sb2n.link_restorer import LinkRestorer
from sb2n.notion_service import NotionService


@pytest.fixture
def mock_notion_service() -> MagicMock:
    """Create a mock NotionService."""
    return MagicMock(spec=NotionService)


@pytest.fixture
def link_restorer(mock_notion_service: MagicMock) -> LinkRestorer:
    """Create a LinkRestorer instance with mock service."""
    return LinkRestorer(mock_notion_service, dry_run=False)


@pytest.fixture
def link_restorer_dry_run(mock_notion_service: MagicMock) -> LinkRestorer:
    """Create a LinkRestorer instance in dry-run mode."""
    return LinkRestorer(mock_notion_service, dry_run=True)


class TestInternalLinkPattern:
    """Tests for internal link pattern detection."""

    def test_detects_simple_internal_link(self, link_restorer: LinkRestorer) -> None:
        """Test detection of simple internal link."""
        text = "See [HomePage] for details"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(1) == "HomePage"

    def test_detects_multiple_links(self, link_restorer: LinkRestorer) -> None:
        """Test detection of multiple internal links."""
        text = "Check [Page1] and [Page2] for info"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 2
        assert matches[0].group(1) == "Page1"
        assert matches[1].group(1) == "Page2"

    def test_detects_japanese_page_names(self, link_restorer: LinkRestorer) -> None:
        """Test detection of Japanese page names."""
        text = "これは[ホームページ]です"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(1) == "ホームページ"

    def test_excludes_urls(self, link_restorer: LinkRestorer) -> None:
        """Test that URLs are excluded."""
        text = "[https://example.com] is a link"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_images(self, link_restorer: LinkRestorer) -> None:
        """Test that image URLs are excluded."""
        text = "[https://example.com/image.png]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_bold_decoration(self, link_restorer: LinkRestorer) -> None:
        """Test that bold decoration is excluded."""
        text = "This is [* bold text]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_strikethrough(self, link_restorer: LinkRestorer) -> None:
        """Test that strikethrough is excluded."""
        text = "This is [- strikethrough]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_italic(self, link_restorer: LinkRestorer) -> None:
        """Test that italic is excluded."""
        text = "This is [/ italic]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_underline(self, link_restorer: LinkRestorer) -> None:
        """Test that underline is excluded."""
        text = "This is [_ underline]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0

    def test_excludes_double_bracket(self, link_restorer: LinkRestorer) -> None:
        """Test that double bracket is excluded."""
        text = "This is [[strong]]"
        matches = list(link_restorer.INTERNAL_LINK_PATTERN.finditer(text))
        assert len(matches) == 0


class TestProcessRichText:
    """Tests for _process_rich_text method."""

    def test_no_links_returns_unchanged(self, link_restorer: LinkRestorer) -> None:
        """Test that text without links is returned unchanged."""
        rich_text = [{"type": "text", "text": {"content": "Plain text"}, "annotations": {}}]
        title_to_id = {}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["text"]["content"] == "Plain text"
        assert found == 0
        assert replaced == 0

    def test_replaces_existing_page_link(self, link_restorer: LinkRestorer) -> None:
        """Test replacement of link when target page exists."""
        rich_text = [{"type": "text", "text": {"content": "See [HomePage]"}, "annotations": {}}]
        title_to_id = {"HomePage": "page-123"}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 2  # "See " + mention
        assert result[0]["text"]["content"] == "See "
        assert result[1]["type"] == "mention"
        assert result[1]["mention"]["page"]["id"] == "page-123"
        assert found == 1
        assert replaced == 1

    def test_keeps_link_when_page_not_found(self, link_restorer: LinkRestorer) -> None:
        """Test that link is kept as text when page doesn't exist."""
        rich_text = [{"type": "text", "text": {"content": "[NonExistent]"}, "annotations": {}}]
        title_to_id = {}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["text"]["content"] == "[NonExistent]"
        assert found == 1
        assert replaced == 0

    def test_preserves_annotations(self, link_restorer: LinkRestorer) -> None:
        """Test that annotations are preserved in replaced links."""
        rich_text = [
            {
                "type": "text",
                "text": {"content": "[HomePage]"},
                "annotations": {"bold": True, "italic": False},
            }
        ]
        title_to_id = {"HomePage": "page-123"}

        result, _found, _replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert result[0]["annotations"]["bold"] is True
        assert result[0]["annotations"]["italic"] is False

    def test_handles_multiple_links_in_one_text(self, link_restorer: LinkRestorer) -> None:
        """Test handling of multiple links in single text element."""
        rich_text = [{"type": "text", "text": {"content": "See [Page1] and [Page2]"}, "annotations": {}}]
        title_to_id = {"Page1": "page-1", "Page2": "page-2"}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 4  # "See " + mention + " and " + mention
        assert result[0]["text"]["content"] == "See "
        assert result[1]["mention"]["page"]["id"] == "page-1"
        assert result[2]["text"]["content"] == " and "
        assert result[3]["mention"]["page"]["id"] == "page-2"
        assert found == 2
        assert replaced == 2

    def test_skips_existing_mentions(self, link_restorer: LinkRestorer) -> None:
        """Test that existing mentions are skipped."""
        rich_text = [{"type": "mention", "mention": {"type": "page", "page": {"id": "existing"}}}]
        title_to_id = {"HomePage": "page-123"}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["type"] == "mention"
        assert found == 0
        assert replaced == 0

    def test_skips_text_with_existing_link(self, link_restorer: LinkRestorer) -> None:
        """Test that text with existing link is skipped."""
        rich_text = [
            {
                "type": "text",
                "text": {"content": "[HomePage]", "link": {"url": "https://example.com"}},
                "annotations": {},
            }
        ]
        title_to_id = {"HomePage": "page-123"}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["text"].get("link") is not None
        assert found == 0
        assert replaced == 0

    def test_skips_inline_code(self, link_restorer: LinkRestorer) -> None:
        """Test that inline code with brackets is skipped."""
        rich_text = [
            {
                "type": "text",
                "text": {"content": "[HomePage]"},
                "annotations": {"code": True},
            }
        ]
        title_to_id = {"HomePage": "page-123"}

        result, found, replaced = link_restorer._process_rich_text(rich_text, title_to_id)  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["text"]["content"] == "[HomePage]"
        assert result[0]["annotations"]["code"] is True
        assert found == 0
        assert replaced == 0


class TestProcessBlock:
    """Tests for _process_block method."""

    def test_processes_paragraph_block(self, link_restorer: LinkRestorer) -> None:
        """Test processing of paragraph block."""
        block = {
            "id": "block-123",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "[HomePage]"}, "annotations": {}}]},
        }
        title_to_id = {"HomePage": "page-123"}

        result = link_restorer._process_block(block, title_to_id)  # noqa: SLF001

        assert result is True
        assert link_restorer.stats["links_found"] == 1
        assert link_restorer.stats["links_restored"] == 1

    def test_skips_non_text_blocks(self, link_restorer: LinkRestorer) -> None:
        """Test that non-text blocks are skipped."""
        block = {"id": "block-123", "type": "image", "image": {"type": "external"}}
        title_to_id = {}

        result = link_restorer._process_block(block, title_to_id)  # noqa: SLF001

        assert result is False

    def test_skips_empty_rich_text(self, link_restorer: LinkRestorer) -> None:
        """Test that blocks with empty rich_text are skipped."""
        block = {"id": "block-123", "type": "paragraph", "paragraph": {"rich_text": []}}
        title_to_id = {}

        result = link_restorer._process_block(block, title_to_id)  # noqa: SLF001

        assert result is False

    def test_dry_run_does_not_update(self, link_restorer_dry_run: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test that dry-run mode doesn't call update."""
        block = {
            "id": "block-123",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "[HomePage]"}, "annotations": {}}]},
        }
        title_to_id = {"HomePage": "page-123"}

        result = link_restorer_dry_run._process_block(block, title_to_id)  # noqa: SLF001

        assert result is True
        mock_notion_service.update_block.assert_not_called()

    def test_normal_mode_updates_block(self, link_restorer: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test that normal mode calls update."""
        block = {
            "id": "block-123",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "[HomePage]"}, "annotations": {}}]},
        }
        title_to_id = {"HomePage": "page-123"}

        result = link_restorer._process_block(block, title_to_id)  # noqa: SLF001

        assert result is True
        mock_notion_service.update_block.assert_called_once()


class TestRestoreAllLinks:
    """Tests for restore_all_links method."""

    def test_processes_all_pages(self, link_restorer: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test that all pages are processed."""
        mock_notion_service.get_page_title_to_id_map.return_value = {"Page1": "id1", "Page2": "id2"}
        mock_notion_service.get_page_blocks.return_value = []

        stats = link_restorer.restore_all_links()

        assert stats["pages_processed"] == 2
        assert mock_notion_service.get_page_blocks.call_count == 2

    def test_filters_by_page_titles(self, link_restorer: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test filtering by specific page titles."""
        mock_notion_service.get_page_title_to_id_map.return_value = {
            "Page1": "id1",
            "Page2": "id2",
            "Page3": "id3",
        }
        mock_notion_service.get_page_blocks.return_value = []

        stats = link_restorer.restore_all_links(page_titles=["Page1", "Page3"])

        assert stats["pages_processed"] == 2
        assert mock_notion_service.get_page_blocks.call_count == 2

    def test_handles_empty_database(self, link_restorer: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test handling of empty database."""
        mock_notion_service.get_page_title_to_id_map.return_value = {}

        stats = link_restorer.restore_all_links()

        assert stats["pages_processed"] == 0
        mock_notion_service.get_page_blocks.assert_not_called()

    def test_continues_on_error(self, link_restorer: LinkRestorer, mock_notion_service: MagicMock) -> None:
        """Test that processing continues when one page fails."""
        mock_notion_service.get_page_title_to_id_map.return_value = {"Page1": "id1", "Page2": "id2"}
        mock_notion_service.get_page_blocks.side_effect = [Exception("API error"), []]

        stats = link_restorer.restore_all_links()

        assert stats["pages_processed"] == 1
        assert stats["errors"] == 1
