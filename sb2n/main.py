"""Command-line interface for sb2n."""

import argparse
import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo

from sb2n.config import Config
from sb2n.exporter import MarkdownExporter
from sb2n.link_restorer import LinkRestorer
from sb2n.migrator import Migrator
from sb2n.notion_service import NotionService
from sb2n.scrapbox_service import ScrapboxService

logger = logging.getLogger(__name__)


class Command(Enum):
    """Available CLI commands."""

    MIGRATE = "migrate"
    RESTORE_LINK = "restore-link"
    EXPORT = "export"


class Args(argparse.Namespace):
    """Type definition for command-line arguments."""

    command: Command | None
    env_file: str | None
    dry_run: bool
    limit: int | None
    skip_existing: bool
    verbose: bool
    pages: str | None
    enable_icon: bool
    output_dir: str
    log: bool
    project: str | None
    sid: str | None
    ntn: str | None
    db: str | None


def setup_logging(*, verbose: bool = False, log_file: str | None = None) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, set log level to DEBUG
        log_file: If specified, write logs to this file in addition to console.
                  If set to True (boolean), automatically generates filename.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Set up handlers
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        # Create log file handler
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        handlers.append(file_handler)
        logger.info("Logging to file: %(log_file)s", {"log_file": log_file})

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def generate_log_filename() -> str:
    """Generate a log filename with current timestamp.

    Returns:
        Log filename in the format: sb2n.YYYYmmDD_HHMMSS.log
    """
    timestamp = datetime.now(tz=ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d_%H%M%S")
    return f"sb2n.{timestamp}.log"


def migrate_command(args: Args) -> int:
    """Execute the migrate command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load configuration
        env_file = Path(args.env_file) if args.env_file else None
        config = Config.from_env(
            env_file,
            project=args.project,
            sid=args.sid,
            ntn=args.ntn,
            db=args.db,
        )
        config.validate()

        # Parse page filter
        page_titles = None
        if args.pages:
            page_titles = [title.strip() for title in args.pages.split(",")]

        # Create and run migrator
        migrator = Migrator(
            config,
            dry_run=args.dry_run,
            limit=args.limit,
            skip_existing=args.skip_existing,
            enable_icon=args.enable_icon,
            page_titles=page_titles,
        )
        summary = migrator.migrate_all()

    except ValueError:
        logger.exception("Configuration error")
        return 1
    except Exception:
        logger.exception("Migration failed")
        return 1
    else:
        # Return success only if all pages migrated successfully
        return summary.failed


def restore_link_command(args: Args) -> int:
    """Execute the restore-link command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load configuration
        env_file = Path(args.env_file) if args.env_file else None
        config = Config.from_env(
            env_file,
            project=args.project,
            sid=args.sid,
            ntn=args.ntn,
            db=args.db,
        )
        config.validate()

        # Create restorer
        notion_service = NotionService(
            api_key=config.notion_api_key,
            database_id=config.notion_database_id,
        )
        restorer = LinkRestorer(notion_service, dry_run=args.dry_run)

        # Parse page filter
        page_titles = None
        if args.pages:
            page_titles = [title.strip() for title in args.pages.split(",")]

        # Run restore
        summary = restorer.restore_all_links(page_titles=page_titles)

        # Print summary
        logger.info("=" * 60)
        logger.info("LINK RESTORATION SUMMARY")
        logger.info("=" * 60)
        logger.info("Total pages processed: %d", summary["total_pages"])
        logger.info("Successful: %d", summary["successful"])
        logger.info("Failed: %d", summary["failed"])
        logger.info("=" * 60)

        return summary["failed"]

    except ValueError:
        logger.exception("Configuration error")
        return 1
    except Exception:
        logger.exception("Link restoration failed")
        return 1


def export_command(args: Args) -> int:
    """Execute the export command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load configuration
        env_file = Path(args.env_file) if args.env_file else None
        config = Config.from_env(
            env_file,
            project=args.project,
            sid=args.sid,
            ntn=args.ntn,
            db=args.db,
        )

        # Set up output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Exporting to: %s", output_dir.absolute())

        # Create services
        scrapbox_service = ScrapboxService(
            project_name=config.scrapbox_project,
            connect_sid=config.scrapbox_connect_sid,
        )

        # Get pages and export
        with scrapbox_service:
            exporter = MarkdownExporter(scrapbox_service, output_dir)

            # Get pages
            logger.info("Fetching pages from Scrapbox project: %s", config.scrapbox_project)
            all_pages = scrapbox_service.get_all_pages(limit=args.limit or 1000)

            # Apply page title filter if specified
            if args.pages:
                page_titles_filter = [title.strip() for title in args.pages.split(",")]
                pages = [p for p in all_pages if p.title in page_titles_filter]
                logger.info(
                    "Found %(total)d pages, filtering to %(filtered)d pages by --pages option",
                    {"total": len(all_pages), "filtered": len(pages)},
                )
            else:
                pages = all_pages

            logger.info("Found %d pages to export", len(pages))

            # Export each page
            successful = 0
            failed = 0
            skipped = 0
            failed_pages = []

            for i, page in enumerate(pages, 1):
                page_title = page.title
                logger.info("Processing page %d/%d: %s", i, len(pages), page_title)

                try:
                    # Get page content
                    page_text = scrapbox_service.get_page_text(page_title)
                    if not page_text:
                        logger.warning("Empty page content for: %s", page_title)
                        continue

                    # Export to Markdown (use skip_existing for export command)
                    result = exporter.export_page(page_title, page_text, skip_existing=args.skip_existing)
                    if result is None:
                        skipped += 1
                        logger.info("⊘ Skipped (already exists): %s", page_title)
                    else:
                        successful += 1
                        logger.info("✓ Exported: %s", page_title)

                except Exception as e:
                    logger.exception("Error exporting page: %s", page_title)
                    failed += 1
                    failed_pages.append((page_title, str(e)))

        # Print summary
        logger.info("=" * 60)
        logger.info("EXPORT SUMMARY")
        logger.info("=" * 60)
        logger.info("Total pages:      %d", len(pages))
        logger.info("Successful:       %d", successful)
        logger.info("Skipped:          %d", skipped)
        logger.info("Failed:           %d", failed)
        logger.info("=" * 60)

        if failed_pages:
            logger.info("Failed pages:")
            for title, error in failed_pages:
                logger.info("  - %s: %s", title, error)
    except ValueError:
        logger.exception("Configuration error")
        return 1
    except Exception:
        logger.exception("Export failed")
        return 1
    return 0 if failed == 0 else 1


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="sb2n",
        description="Scrapbox to Notion migration tool",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging)",
    )

    parser.add_argument(
        "-P",
        "--project",
        type=str,
        help="Scrapbox project name (overrides SCRAPBOX_PROJECT env var)",
    )

    parser.add_argument(
        "-S",
        "--sid",
        type=str,
        help="Scrapbox connect.sid cookie (overrides SCRAPBOX_COOKIE_CONNECT_SID env var)",
    )

    parser.add_argument(
        "-N",
        "--ntn",
        type=str,
        help="Notion API token (overrides NOTION_API_KEY env var)",
    )

    parser.add_argument(
        "-D",
        "--db",
        type=str,
        help="Notion database ID (overrides NOTION_DATABASE_ID env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # migrate command
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate all pages from Scrapbox to Notion",
    )

    migrate_parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)",
    )

    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making actual changes to Notion",
    )

    migrate_parser.add_argument(
        "-n",
        "--limit",
        type=int,
        help="Limit the number of pages to migrate (default: all pages)",
    )

    migrate_parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        dest="skip_existing",
        help="Skip pages that already exist in Notion database",
    )

    migrate_parser.add_argument(
        "--icon",
        action="store_true",
        dest="enable_icon",
        help="Enable icon notation migration (fetch icons from Scrapbox pages)",
    )

    migrate_parser.add_argument(
        "-l",
        "--log",
        action="store_true",
        help="Enable logging to file with auto-generated filename (sb2n.YYYYmmDD_HHMMSS.log)",
    )

    migrate_parser.add_argument(
        "--pages",
        type=str,
        help="Comma-separated list of specific page titles to migrate",
    )

    # restore-link command
    restore_link_parser = subparsers.add_parser(
        "restore-link",
        help="Restore Scrapbox internal links in migrated Notion pages",
    )

    restore_link_parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)",
    )

    restore_link_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making actual changes to Notion",
    )

    restore_link_parser.add_argument(
        "--pages",
        type=str,
        help="Comma-separated list of specific page titles to process",
    )

    restore_link_parser.add_argument(
        "-l",
        "--log",
        action="store_true",
        help="Enable logging to file with auto-generated filename (sb2n.YYYYmmDD_HHMMSS.log)",
    )

    # export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export Scrapbox pages to Markdown format",
    )

    export_parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)",
    )

    export_parser.add_argument(
        "-d",
        "--output-dir",
        type=str,
        default="./out",
        help="Output directory for exported Markdown files (default: ./out)",
    )

    export_parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of pages to export",
    )

    export_parser.add_argument(
        "-l",
        "--log",
        action="store_true",
        help="Enable logging to file with auto-generated filename (sb2n.YYYYmmDD_HHMMSS.log)",
    )

    export_parser.add_argument(
        "--pages",
        type=str,
        help="Comma-separated list of specific page titles to export",
    )

    export_parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        dest="skip_existing",
        help="Skip exporting pages that already exist in the output directory",
    )

    args = parser.parse_args(namespace=Args())

    # Determine log file path
    log_file_path = None
    if hasattr(args, "log") and args.log:
        # Auto-generate log filename
        log_file_path = generate_log_filename()

    # Set up logging
    setup_logging(verbose=args.verbose, log_file=log_file_path)

    # Handle commands
    if args.command == Command.MIGRATE.value:
        exit_code = migrate_command(args)
        sys.exit(exit_code)
    elif args.command == Command.RESTORE_LINK.value:
        exit_code = restore_link_command(args)
        sys.exit(exit_code)
    elif args.command == Command.EXPORT.value:
        exit_code = export_command(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
