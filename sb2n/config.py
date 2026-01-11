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
        scrapbox_project: Scrapbox project name
        scrapbox_connect_sid: Scrapbox authentication cookie (connect.sid)
        notion_api_key: Notion Integration API key
        notion_database_id: Notion database ID for migration target
    """

    scrapbox_project: str
    scrapbox_connect_sid: str
    notion_api_key: str
    notion_database_id: str

    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> Config:
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file. If None, uses default .env file in current directory.

        Returns:
            Config instance with loaded values

        Raises:
            ValueError: If required environment variables are missing
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        scrapbox_project = os.getenv("SCRAPBOX_PROJECT")
        scrapbox_connect_sid = os.getenv("SCRAPBOX_COOKIE_CONNECT_SID")
        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        missing = []
        if not scrapbox_project:
            missing.append("SCRAPBOX_PROJECT")
        if not scrapbox_connect_sid:
            missing.append("SCRAPBOX_COOKIE_CONNECT_SID")
        if not notion_api_key:
            missing.append("NOTION_API_KEY")
        if not notion_database_id:
            missing.append("NOTION_DATABASE_ID")

        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(msg)

        # At this point, all values are guaranteed to be non-None
        assert scrapbox_project is not None
        assert scrapbox_connect_sid is not None
        assert notion_api_key is not None
        assert notion_database_id is not None

        return cls(
            scrapbox_project=scrapbox_project,
            scrapbox_connect_sid=scrapbox_connect_sid,
            notion_api_key=notion_api_key,
            notion_database_id=notion_database_id,
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        if not self.scrapbox_project.strip():
            msg = "SCRAPBOX_PROJECT cannot be empty"
            raise ValueError(msg)
        if not self.scrapbox_connect_sid.strip():
            msg = "SCRAPBOX_COOKIE_CONNECT_SID cannot be empty"
            raise ValueError(msg)
        if not self.notion_api_key.strip():
            msg = "NOTION_API_KEY cannot be empty"
            raise ValueError(msg)
        if not self.notion_database_id.strip():
            msg = "NOTION_DATABASE_ID cannot be empty"
            raise ValueError(msg)
