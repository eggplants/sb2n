"""Main migration logic."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sb2n.converter import NotionBlockConverter
from sb2n.notion_service import NotionService
from sb2n.parser import ScrapboxParser
from sb2n.scrapbox_service import ScrapboxService

if TYPE_CHECKING:
    from uuid import UUID

    from sb2n.config import Config

logger = logging.getLogger(__name__)


def _count_blocks_recursive(block) -> int:
    """Count blocks recursively including nested children.

    Args:
        block: A Notion block object

    Returns:
        Total count of blocks including nested children
    """
    count = 1  # Count the block itself
    # Check for children in bulleted_list_item
    if hasattr(block, "bulleted_list_item") and isinstance(block.bulleted_list_item, dict):
        children = block.bulleted_list_item.get("children", [])
        for child in children:
            count += _count_blocks_recursive(child)
    return count


def _split_blocks_into_chunks(blocks: list, max_blocks: int = 1000) -> list[list]:
    """Split blocks into chunks that don't exceed max_blocks (including nested children).

    Args:
        blocks: List of top-level blocks
        max_blocks: Maximum number of blocks per chunk (including nested children)

    Returns:
        List of block chunks
    """
    chunks = []
    current_chunk = []
    current_count = 0

    for block in blocks:
        block_count = _count_blocks_recursive(block)

        # If adding this block would exceed the limit, start a new chunk
        if current_chunk and current_count + block_count > max_blocks:
            chunks.append(current_chunk)
            current_chunk = []
            current_count = 0

        current_chunk.append(block)
        current_count += block_count

    # Add the last chunk if it has any blocks
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class SpecialPageId(str, Enum):
    """Special Notion page IDs used in migration."""

    DRY_RUN_ID = "dry-run-id"
    SKIPPED_ID = "skipped"


@dataclass
class MigrationResult:
    """Result of a single page migration.

    Attributes:
        page_title: Title of the migrated page
        success: Whether migration was successful
        error: Error message if migration failed
        notion_page_id: Notion page ID if successful
    """

    page_title: str
    success: bool
    error: str | None = None
    notion_page_id: SpecialPageId | UUID | None = None


@dataclass
class MigrationSummary:
    """Summary of migration results.

    Attributes:
        total_pages: Total number of pages processed
        successful: Number of successfully migrated pages
        failed: Number of failed migrations
        skipped: Number of skipped pages
        results: List of individual migration results
    """

    total_pages: int
    successful: int
    failed: int
    skipped: int
    results: list[MigrationResult]


class Migrator:
    """Main migration orchestrator.

    This class coordinates the migration process from Scrapbox to Notion,
    including progress tracking, error handling, and summary reporting.
    """

    def __init__(  # noqa: PLR0913
        self,
        config: Config,
        *,
        dry_run: bool = False,
        limit: int | None = None,
        skip_existing: bool = False,
        enable_icon: bool = False,
        page_titles: list[str] | None = None,
    ) -> None:
        """Initialize the migrator.

        Args:
            config: Configuration for migration
            dry_run: If True, do not actually create pages in Notion
            limit: Maximum number of pages to migrate (None for all pages)
            skip_existing: If True, skip pages that already exist in Notion
            enable_icon: If True, fetch and migrate Scrapbox icon notation
            page_titles: List of specific page titles to migrate (None for all pages)
        """
        self.config = config
        self.dry_run = dry_run
        self.limit = limit
        self.skip_existing = skip_existing
        self.enable_icon = enable_icon
        self.page_titles = page_titles
        self.notion_service = NotionService(config.notion_api_key, config.notion_database_id)
        # Converter will be initialized with scrapbox_service in migrate_all
        self.converter: NotionBlockConverter | None = None

    def migrate_all(self) -> MigrationSummary:
        """Migrate all pages from Scrapbox to Notion.

        Returns:
            Summary of migration results
        """
        logger.info("Starting migration from Scrapbox to Notion")
        if self.dry_run:
            logger.info("DRY RUN MODE: No actual changes will be made")

        # Get existing pages if skip_existing is enabled
        existing_titles: set[str] = set()
        if self.skip_existing:
            try:
                existing_titles = self.notion_service.get_existing_page_titles()
            except Exception:
                logger.exception("Failed to get existing pages")
                logger.info("Continuing without skip-existing functionality")

        results: list[MigrationResult] = []

        with ScrapboxService(self.config.scrapbox_project, self.config.scrapbox_connect_sid) as scrapbox:
            # Initialize converter with scrapbox service for image downloads
            self.converter = NotionBlockConverter(self.notion_service, scrapbox, enable_icon=self.enable_icon)

            # If specific pages are requested, process them directly
            if self.page_titles:
                logger.info(
                    "Processing %(count)d specific pages by --pages option",
                    {"count": len(self.page_titles)},
                )
                pages_to_process = self.page_titles
                # Apply limit if specified
                if self.limit is not None:
                    pages_to_process = pages_to_process[: self.limit]
                    logger.info(
                        "Limiting to %(migrating)d pages by -n option",
                        {"migrating": len(pages_to_process)},
                    )
            else:
                # Get all pages
                all_pages = scrapbox.get_all_pages()

                # Apply limit if specified
                if self.limit is not None:
                    pages_list = all_pages[: self.limit]
                    logger.info(
                        "Found %(total)d pages, migrating %(migrating)d pages (limited by -n option)",
                        {"total": len(all_pages), "migrating": len(pages_list)},
                    )
                else:
                    pages_list = all_pages
                    logger.info("Found %(count)d pages to migrate", {"count": len(pages_list)})

                pages_to_process = [p.title for p in pages_list]

            total = len(pages_to_process)

            # Migrate each page
            for i, page_title in enumerate(pages_to_process, 1):
                logger.info(
                    "Processing page %(current)d/%(total)d: %(title)s",
                    {"current": i, "total": total, "title": page_title},
                )

                # Check if page already exists and should be skipped
                if self.skip_existing and page_title in existing_titles:
                    logger.info("⊘ Skipping existing page: %(title)s", {"title": page_title})
                    results.append(
                        MigrationResult(
                            page_title=page_title,
                            success=True,
                            notion_page_id=SpecialPageId.SKIPPED_ID,
                        )
                    )
                    continue

                try:
                    result = self._migrate_page(scrapbox, page_title, existing_titles)
                    results.append(result)

                    if result.success:
                        logger.info("✓ Successfully migrated: %(title)s", {"title": page_title})
                    else:
                        logger.error(
                            "✗ Failed to migrate: %(title)s - %(error)s", {"title": page_title, "error": result.error}
                        )

                except Exception as e:
                    logger.exception("Unexpected error migrating %(title)s", {"title": page_title})
                    results.append(
                        MigrationResult(
                            page_title=page_title,
                            success=False,
                            error=str(e),
                        )
                    )

        # Calculate summary
        skipped_count = sum(1 for r in results if r.success and r.notion_page_id == SpecialPageId.SKIPPED_ID)
        successful_count = sum(1 for r in results if r.success and r.notion_page_id != SpecialPageId.SKIPPED_ID)
        summary = MigrationSummary(
            total_pages=total,
            successful=successful_count,
            failed=sum(1 for r in results if not r.success),
            skipped=skipped_count,
            results=results,
        )

        self._print_summary(summary)
        return summary

    def _migrate_page(
        self,
        scrapbox: ScrapboxService,
        page_title: str,
        existing_titles: set[str],
    ) -> MigrationResult:
        """Migrate a single page.

        Args:
            scrapbox: Scrapbox service
            page_title: Title of the page to migrate
            existing_titles: Set of existing page titles in Notion (for skip-existing check)

        Returns:
            Migration result for this page
        """
        try:
            # Get page text
            page_text = scrapbox.get_page_text(page_title)

            page_detail = scrapbox.get_page_detail(page_title)
            created_timestamp = page_detail.created

            # Extract tags
            tags = [tag.replace(",", "") for tag in ScrapboxParser.extract_tags(page_text)]

            # Convert creation date
            created_date = datetime.fromtimestamp(created_timestamp, tz=UTC)

            # Generate Scrapbox URL
            scrapbox_url = scrapbox.get_page_url(page_title)

            if self.dry_run:
                logger.debug("[DRY RUN] Would create page: %(title)s", {"title": page_title})
                logger.debug("  Tags: %(tags)s", {"tags": tags})
                logger.debug("  Created: %(created)s", {"created": created_date})
                logger.debug("  URL: %(url)s", {"url": scrapbox_url})
                return MigrationResult(
                    page_title=page_title,
                    success=True,
                    notion_page_id=SpecialPageId.DRY_RUN_ID,
                )

            # Convert blocks first to determine if splitting is needed
            blocks = []
            total_block_count = 0
            chunks = []
            total_chunks = 1

            if self.converter:
                blocks = self.converter.convert_to_blocks(page_text)
                total_block_count = sum(_count_blocks_recursive(block) for block in blocks)
                max_block_count = 1000

                # Check if we need to split into multiple pages
                if total_block_count > max_block_count:
                    chunks = _split_blocks_into_chunks(blocks, max_block_count)
                    total_chunks = len(chunks)

                    logger.warning(
                        "Page '%(title)s' has %(total)d blocks (including nested children), "
                        "which exceeds the limit of %(max)d. This page will be split into %(chunks)d pages.",
                        {
                            "title": page_title,
                            "total": total_block_count,
                            "max": max_block_count,
                            "chunks": total_chunks,
                        },
                    )

            # Check if split pages already exist (for skip-existing)
            if self.skip_existing and total_chunks > 1:
                all_split_pages_exist = True
                for i in range(1, total_chunks + 1):
                    split_title = f"{page_title} - {i}/{total_chunks}"
                    if split_title not in existing_titles:
                        all_split_pages_exist = False
                        break

                if all_split_pages_exist:
                    logger.info(
                        "⊘ Skipping page '%(title)s' - all %(chunks)d split pages already exist",
                        {"title": page_title, "chunks": total_chunks},
                    )
                    return MigrationResult(
                        page_title=page_title,
                        success=True,
                        notion_page_id=SpecialPageId.SKIPPED_ID,
                    )

            # Determine the title for the first page
            first_page_title = f"{page_title} - 1/{total_chunks}" if total_chunks > 1 else page_title

            # Check if the first page already exists (for skip-existing with split pages)
            if self.skip_existing and total_chunks > 1 and first_page_title in existing_titles:
                logger.info(
                    "⊘ Skipping first split page: '%(title)s' (already exists)",
                    {"title": first_page_title},
                )
                # Skip creating the first page, but continue to check other pages
                notion_page_id = None
            else:
                # Create Notion page with appropriate title
                notion_page = self.notion_service.create_database_page(
                    title=first_page_title,
                    scrapbox_url=scrapbox_url,
                    created_date=created_date,
                    tags=tags,
                )
                notion_page_id = notion_page["id"]

            # Append blocks
            if self.converter and blocks:
                try:
                    # Log block statistics
                    block_types = {}
                    for block in blocks:
                        block_type = block.type
                        block_types[block_type] = block_types.get(block_type, 0) + 1

                    logger.debug(
                        "Block statistics for page '%(title)s': %(stats)s (total: %(total)d including nested)",
                        {"title": page_title, "stats": block_types, "total": total_block_count},
                    )

                    if total_chunks > 1:
                        # Append first chunk to the already created page (if not skipped)
                        if notion_page_id is not None:
                            first_chunk = chunks[0]
                            first_chunk_count = sum(_count_blocks_recursive(block) for block in first_chunk)
                            logger.info(
                                "Appending chunk 1/%(total)d to page '%(title)s' (%(count)d blocks)",
                                {"total": total_chunks, "title": first_page_title, "count": first_chunk_count},
                            )
                            self.notion_service.append_blocks(notion_page_id, first_chunk)

                        # Create additional pages for remaining chunks
                        for i, chunk in enumerate(chunks[1:], start=2):
                            chunk_count = sum(_count_blocks_recursive(block) for block in chunk)
                            chunk_page_title = f"{page_title} - {i}/{total_chunks}"

                            # Check if this split page already exists (for skip-existing)
                            if self.skip_existing and chunk_page_title in existing_titles:
                                logger.info(
                                    "⊘ Skipping split page %(page_num)d/%(total)d: '%(title)s' (already exists)",
                                    {"page_num": i, "total": total_chunks, "title": chunk_page_title},
                                )
                                continue

                            logger.info(
                                "Creating additional page %(page_num)d/%(total)d: '%(title)s' (%(count)d blocks)",
                                {"page_num": i, "total": total_chunks, "title": chunk_page_title, "count": chunk_count},
                            )

                            # Create new page with the same metadata
                            chunk_page = self.notion_service.create_database_page(
                                title=chunk_page_title,
                                scrapbox_url=scrapbox_url,
                                created_date=created_date,
                                tags=tags,
                            )
                            chunk_page_id = chunk_page["id"]

                            # Append blocks to the new page
                            self.notion_service.append_blocks(chunk_page_id, chunk)

                    elif notion_page_id is not None:
                        logger.debug(
                            "Appending %(count)d blocks to page '%(title)s'",
                            {"count": len(blocks), "title": page_title},
                        )
                        self.notion_service.append_blocks(notion_page_id, blocks)

                except Exception:
                    # If block append fails, delete the created page
                    logger.exception(
                        "Failed to append blocks to page '%(title)s'. Deleting the page...",
                        {"title": page_title},
                    )
                    if notion_page_id is not None:
                        try:
                            self.notion_service.delete_page(notion_page_id)
                            logger.info("Successfully deleted incomplete page: %(title)s", {"title": page_title})
                        except Exception:
                            logger.exception(
                                "Failed to delete incomplete page '%(title)s'",
                                {"title": page_title},
                            )
                    # Re-raise the original error
                    raise

            return MigrationResult(
                page_title=page_title,
                success=True,
                notion_page_id=notion_page_id,
            )

        except Exception as e:
            logger.exception("Error migrating page: %(title)s", {"title": page_title})
            return MigrationResult(
                page_title=page_title,
                success=False,
                error=str(e),
            )

    def _print_summary(self, summary: MigrationSummary) -> None:
        """Print migration summary.

        Args:
            summary: Migration summary to print
        """
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info("Total pages:      %(total)d", {"total": summary.total_pages})
        logger.info("Successful:       %(successful)d", {"successful": summary.successful})
        logger.info("Failed:           %(failed)d", {"failed": summary.failed})
        logger.info("Skipped:          %(skipped)d", {"skipped": summary.skipped})
        logger.info("=" * 60)

        if summary.failed > 0:
            logger.info("Failed pages:")
            for result in summary.results:
                if not result.success:
                    logger.info("  - %(title)s: %(error)s", {"title": result.page_title, "error": result.error})

        if self.dry_run:
            logger.info("\n[DRY RUN] No actual changes were made to Notion")
