"""Main migration logic."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sb2n.config import Config
from sb2n.converter import NotionBlockConverter
from sb2n.notion_service import NotionService
from sb2n.parser import ScrapboxParser
from sb2n.scrapbox_service import ScrapboxService

logger = logging.getLogger(__name__)


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
    notion_page_id: str | None = None


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

    def __init__(
        self, config: Config, dry_run: bool = False, limit: int | None = None, skip_existing: bool = False
    ) -> None:
        """Initialize the migrator.

        Args:
            config: Configuration for migration
            dry_run: If True, do not actually create pages in Notion
            limit: Maximum number of pages to migrate (None for all pages)
            skip_existing: If True, skip pages that already exist in Notion
        """
        self.config = config
        self.dry_run = dry_run
        self.limit = limit
        self.skip_existing = skip_existing
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
            except Exception as e:
                logger.error(f"Failed to get existing pages: {e}")
                logger.info("Continuing without skip-existing functionality")

        results: list[MigrationResult] = []

        with ScrapboxService(self.config.scrapbox_project, self.config.scrapbox_connect_sid) as scrapbox:
            # Initialize converter with scrapbox service for image downloads
            self.converter = NotionBlockConverter(self.notion_service, scrapbox)

            # Get all pages
            all_pages = scrapbox.get_all_pages()

            # Apply limit if specified
            if self.limit is not None:
                pages = all_pages[: self.limit]
                logger.info(f"Found {len(all_pages)} pages, migrating {len(pages)} pages (limited by -n option)")
            else:
                pages = all_pages
                logger.info(f"Found {len(pages)} pages to migrate")

            total = len(pages)

            # Migrate each page
            for i, page in enumerate(pages, 1):
                logger.info(f"[{i}/{total}] Processing: {page.title}")

                # Check if page already exists and should be skipped
                if self.skip_existing and page.title in existing_titles:
                    logger.info(f"⊘ Skipping existing page: {page.title}")
                    results.append(
                        MigrationResult(
                            page_title=page.title,
                            success=True,
                            notion_page_id="skipped",
                        )
                    )
                    continue

                try:
                    result = self._migrate_page(scrapbox, page.title)
                    results.append(result)

                    if result.success:
                        logger.info(f"✓ Successfully migrated: {page.title}")
                    else:
                        logger.error(f"✗ Failed to migrate: {page.title} - {result.error}")

                except Exception as e:
                    logger.exception(f"Unexpected error migrating {page.title}")
                    results.append(
                        MigrationResult(
                            page_title=page.title,
                            success=False,
                            error=str(e),
                        )
                    )

        # Calculate summary
        skipped_count = sum(1 for r in results if r.success and r.notion_page_id == "skipped")
        successful_count = sum(1 for r in results if r.success and r.notion_page_id != "skipped")
        summary = MigrationSummary(
            total_pages=total,
            successful=successful_count,
            failed=sum(1 for r in results if not r.success),
            skipped=skipped_count,
            results=results,
        )

        self._print_summary(summary)
        return summary

    def _migrate_page(self, scrapbox: ScrapboxService, page_title: str) -> MigrationResult:
        """Migrate a single page.

        Args:
            scrapbox: Scrapbox service
            page_title: Title of the page to migrate

        Returns:
            Migration result for this page
        """
        try:
            # Get page text
            page_text = scrapbox.get_page_text(page_title)

            page_detail = scrapbox.get_page_detail(page_title)
            created_timestamp = page_detail.created

            # Extract tags
            tags = ScrapboxParser.extract_tags(page_text)

            # Convert creation date
            created_date = datetime.fromtimestamp(created_timestamp, tz=UTC)

            # Generate Scrapbox URL
            scrapbox_url = scrapbox.get_page_url(page_title)

            if self.dry_run:
                logger.debug(f"[DRY RUN] Would create page: {page_title}")
                logger.debug(f"  Tags: {tags}")
                logger.debug(f"  Created: {created_date}")
                logger.debug(f"  URL: {scrapbox_url}")
                return MigrationResult(
                    page_title=page_title,
                    success=True,
                    notion_page_id="dry-run-id",
                )

            # Create Notion page
            notion_page = self.notion_service.create_database_page(
                title=page_title,
                scrapbox_url=scrapbox_url,
                created_date=created_date,
                tags=tags,
            )

            # Convert and append blocks
            if self.converter:
                blocks = self.converter.convert_to_blocks(page_text)
                if blocks:
                    self.notion_service.append_blocks(notion_page["id"], blocks)

            return MigrationResult(
                page_title=page_title,
                success=True,
                notion_page_id=notion_page["id"],
            )

        except Exception as e:
            logger.exception(f"Error migrating page: {page_title}")
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
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total pages:      {summary.total_pages}")
        logger.info(f"Successful:       {summary.successful}")
        logger.info(f"Failed:           {summary.failed}")
        logger.info(f"Skipped:          {summary.skipped}")
        logger.info("=" * 60)

        if summary.failed > 0:
            logger.info("\nFailed pages:")
            for result in summary.results:
                if not result.success:
                    logger.info(f"  - {result.page_title}: {result.error}")

        if self.dry_run:
            logger.info("\n[DRY RUN] No actual changes were made to Notion")
