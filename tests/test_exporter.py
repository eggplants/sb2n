"""Tests for Markdown exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from sb2n.exporter import MarkdownExporter
from sb2n.scrapbox_service import ScrapboxService

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_scrapbox_service() -> MagicMock:
    """Create a mock Scrapbox service."""
    service = MagicMock(spec=ScrapboxService)
    service.project_name = "test_project"
    return service


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    return tmp_path / "output"


def test_export_txt_format(mock_scrapbox_service: MagicMock, temp_output_dir: Path) -> None:
    """Test exporting in txt format preserves raw Scrapbox content."""
    exporter = MarkdownExporter(mock_scrapbox_service, temp_output_dir, export_format="txt")

    page_title = "Test Page"
    page_text = """Test Page
This is a test
[link to another page]
 code:python
  def hello():
      print("world")"""

    result = exporter.export_page(page_title, page_text)

    assert result is not None
    assert result.exists()
    assert result.suffix == ".txt"

    # Check content is exactly the same as input
    content = result.read_text(encoding="utf-8")
    assert content == page_text


def test_export_md_format(mock_scrapbox_service: MagicMock, temp_output_dir: Path) -> None:
    """Test exporting in md format converts to Markdown."""
    exporter = MarkdownExporter(mock_scrapbox_service, temp_output_dir, export_format="md")

    page_title = "Test Page"
    page_text = """Test Page
This is a test"""

    result = exporter.export_page(page_title, page_text)

    assert result is not None
    assert result.exists()
    assert result.suffix == ".md"

    # Check content is converted to Markdown
    content = result.read_text(encoding="utf-8")
    assert "# Test Page" in content
    assert "This is a test" in content


def test_export_default_format_is_md(mock_scrapbox_service: MagicMock, temp_output_dir: Path) -> None:
    """Test that default export format is md."""
    exporter = MarkdownExporter(mock_scrapbox_service, temp_output_dir)

    assert exporter.export_format == "md"


def test_export_skip_existing_txt(mock_scrapbox_service: MagicMock, temp_output_dir: Path) -> None:
    """Test that skip_existing works with txt format."""
    exporter = MarkdownExporter(mock_scrapbox_service, temp_output_dir, export_format="txt")

    page_title = "Test Page"
    page_text = "Original content"

    # First export
    result1 = exporter.export_page(page_title, page_text)
    assert result1 is not None

    # Second export with skip_existing should return None
    result2 = exporter.export_page(page_title, "New content", skip_existing=True)
    assert result2 is None

    # Content should still be original
    content = result1.read_text(encoding="utf-8")
    assert content == "Original content"
