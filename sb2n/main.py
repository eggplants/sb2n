"""Command-line interface for sb2n."""

import argparse
import logging
import sys
from enum import Enum
from pathlib import Path

from sb2n.config import Config
from sb2n.migrator import Migrator

logger = logging.getLogger(__name__)


class Command(Enum):
    """Available CLI commands."""

    MIGRATE = "migrate"


class Args(argparse.Namespace):
    """Type definition for command-line arguments."""

    command: Command | None
    env_file: str | None
    dry_run: bool
    limit: int | None
    skip_existing: bool
    verbose: bool


def setup_logging(*, verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, set log level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
        config = Config.from_env(env_file)
        config.validate()

        # Create and run migrator
        migrator = Migrator(config, dry_run=args.dry_run, limit=args.limit, skip_existing=args.skip_existing)
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
        "--skip-existing",
        action="store_true",
        help="Skip pages that already exist in Notion database",
    )

    args = parser.parse_args(namespace=Args())

    # Set up logging
    setup_logging(verbose=args.verbose)

    # Handle commands
    if args.command == Command.MIGRATE.value:
        exit_code = migrate_command(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
