"""Configuration management for sb2n."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Config:
    """Configuration for Scrapbox to Notion migration.

    Attributes:
        scrapbox_project: Scrapbox project name (optional for Notion-only commands)
        scrapbox_connect_sid: Scrapbox authentication cookie (optional for Notion-only commands)
        notion_api_key: Notion Integration API key (optional for Scrapbox-only commands)
        notion_database_id: Notion database ID (optional for Scrapbox-only commands)
    """

    scrapbox_project: str | None
    scrapbox_connect_sid: str | None
    notion_api_key: str | None
    notion_database_id: str | None

    @classmethod
    def from_env(  # noqa: PLR0913
        cls,
        env_file: Path | str | None = None,
        *,
        project: str | None = None,
        sid: str | None = None,
        ntn: str | None = None,
        db: str | None = None,
        require_scrapbox: bool = True,
        require_notion: bool = True,
    ) -> Config:
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file. If None, uses default .env file in current directory.
            project: Scrapbox project name (overrides env var if provided)
            sid: Scrapbox connect.sid cookie (overrides env var if provided)
            ntn: Notion API token (overrides env var if provided)
            db: Notion database ID (overrides env var if provided)
            require_scrapbox: If True, require Scrapbox credentials
            require_notion: If True, require Notion credentials

        Returns:
            Config instance with loaded values

        Raises:
            ValueError: If required environment variables are missing
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Use command-line options if provided, otherwise use environment variables
        scrapbox_project = project or os.getenv("SCRAPBOX_PROJECT")
        scrapbox_connect_sid = sid or os.getenv("SCRAPBOX_COOKIE_CONNECT_SID")
        notion_api_key = ntn or os.getenv("NOTION_API_KEY")
        notion_database_id = db or os.getenv("NOTION_DATABASE_ID")

        missing = []
        if require_scrapbox:
            if not scrapbox_project:
                missing.append("SCRAPBOX_PROJECT")
            if not scrapbox_connect_sid:
                missing.append("SCRAPBOX_COOKIE_CONNECT_SID")
        if require_notion:
            if not notion_api_key:
                missing.append("NOTION_API_KEY")
            if not notion_database_id:
                missing.append("NOTION_DATABASE_ID")

        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(msg)

        return cls(
            scrapbox_project=scrapbox_project,
            scrapbox_connect_sid=scrapbox_connect_sid,
            notion_api_key=notion_api_key,
            notion_database_id=notion_database_id,
        )

    def validate(self, *, require_scrapbox: bool = True, require_notion: bool = True) -> None:
        """Validate configuration values.

        Args:
            require_scrapbox: If True, validate Scrapbox credentials
            require_notion: If True, validate Notion credentials

        Raises:
            ValueError: If any required configuration value is invalid
        """
        if require_scrapbox:
            if not self.scrapbox_project or not self.scrapbox_project.strip():
                msg = "SCRAPBOX_PROJECT cannot be empty"
                raise ValueError(msg)
            if not self.scrapbox_connect_sid or not self.scrapbox_connect_sid.strip():
                msg = "SCRAPBOX_COOKIE_CONNECT_SID cannot be empty"
                raise ValueError(msg)
        if require_notion:
            if not self.notion_api_key or not self.notion_api_key.strip():
                msg = "NOTION_API_KEY cannot be empty"
                raise ValueError(msg)
            if not self.notion_database_id or not self.notion_database_id.strip():
                msg = "NOTION_DATABASE_ID cannot be empty"
                raise ValueError(msg)
