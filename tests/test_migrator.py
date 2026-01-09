"""Tests for migrator module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sb2n.config import Config
from sb2n.migrator import Migrator


def test_migrator_with_limit() -> None:
    """Test that migrator respects the limit parameter."""
    # Create a mock config
    config = Config(
        scrapbox_project="test-project",
        scrapbox_connect_sid="test-sid",
        notion_api_key="test-key",
        notion_database_id="test-db-id",
    )

    # Test with limit
    migrator = Migrator(config, dry_run=True, limit=5)
    assert migrator.limit == 5
    assert migrator.dry_run is True

    # Test without limit
    migrator_no_limit = Migrator(config, dry_run=False)
    assert migrator_no_limit.limit is None
    assert migrator_no_limit.dry_run is False
