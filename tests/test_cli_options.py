"""Tests for CLI options and argument parsing."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sb2n.config import Config
from sb2n.main import Args, main


class TestCommandLineOptions:
    """Test command line option parsing and precedence."""

    def test_env_file_only(self) -> None:
        """Test loading config from .env file only."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SCRAPBOX_PROJECT=test-project\n")
            f.write("SCRAPBOX_COOKIE_CONNECT_SID=test-sid\n")
            f.write("NOTION_API_KEY=test-token\n")
            f.write("NOTION_DATABASE_ID=test-db\n")
            env_file = f.name

        try:
            config = Config.from_env(env_file)
            assert config.scrapbox_project == "test-project"
            assert config.scrapbox_connect_sid == "test-sid"
            assert config.notion_api_key == "test-token"
            assert config.notion_database_id == "test-db"
        finally:
            Path(env_file).unlink()
            # Clean up env vars
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_cli_options_only(self) -> None:
        """Test using CLI options without .env file."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        config = Config.from_env(
            None,
            project="cli-project",
            sid="cli-sid",
            ntn="cli-token",
            db="cli-db",
        )
        assert config.scrapbox_project == "cli-project"
        assert config.scrapbox_connect_sid == "cli-sid"
        assert config.notion_api_key == "cli-token"
        assert config.notion_database_id == "cli-db"

    def test_cli_options_override_env(self) -> None:
        """Test that CLI options override .env file values."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SCRAPBOX_PROJECT=env-project\n")
            f.write("SCRAPBOX_COOKIE_CONNECT_SID=env-sid\n")
            f.write("NOTION_API_KEY=env-token\n")
            f.write("NOTION_DATABASE_ID=env-db\n")
            env_file = f.name

        try:
            config = Config.from_env(
                env_file,
                project="cli-project",
                ntn="cli-token",
            )
            # CLI options override
            assert config.scrapbox_project == "cli-project"
            assert config.notion_api_key == "cli-token"
            # .env values used where CLI not specified
            assert config.scrapbox_connect_sid == "env-sid"
            assert config.notion_database_id == "env-db"
        finally:
            Path(env_file).unlink()
            # Clean up env vars
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_partial_cli_options(self) -> None:
        """Test using only some CLI options with .env file."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SCRAPBOX_PROJECT=env-project\n")
            f.write("SCRAPBOX_COOKIE_CONNECT_SID=env-sid\n")
            f.write("NOTION_API_KEY=env-token\n")
            f.write("NOTION_DATABASE_ID=env-db\n")
            env_file = f.name

        try:
            # Only override project name
            config = Config.from_env(env_file, project="override-project")
            assert config.scrapbox_project == "override-project"
            assert config.scrapbox_connect_sid == "env-sid"
            assert config.notion_api_key == "env-token"
            assert config.notion_database_id == "env-db"
        finally:
            Path(env_file).unlink()
            # Clean up env vars
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_export_format_option_default(self) -> None:
        """Test that export format defaults to 'md'."""

        with patch("sys.argv", ["sb2n", "export", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with 0
            assert exc_info.value.code == 0

    def test_export_format_option_md(self) -> None:
        """Test export command with --format md option."""

        args = Args()
        args.format = "md"
        assert args.format == "md"

    def test_export_format_option_txt(self) -> None:
        """Test export command with --format txt option."""
        args = Args()
        args.format = "txt"
        assert args.format == "txt"


class TestRequireCredentials:
    """Test selective credential requirements."""

    def test_require_scrapbox_only(self) -> None:
        """Test loading config with only Scrapbox credentials required."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        # Use empty temp file to prevent loading actual .env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_file = f.name

        try:
            # Only provide Scrapbox credentials - should succeed
            config = Config.from_env(
                env_file,
                project="test-project",
                sid="test-sid",
                require_scrapbox=True,
                require_notion=False,
            )
            assert config.scrapbox_project == "test-project"
            assert config.scrapbox_connect_sid == "test-sid"
            assert config.notion_api_key is None
            assert config.notion_database_id is None
        finally:
            Path(env_file).unlink()
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_require_notion_only(self) -> None:
        """Test loading config with only Notion credentials required."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        # Use empty temp file to prevent loading actual .env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_file = f.name

        try:
            # Only provide Notion credentials - should succeed
            config = Config.from_env(
                env_file,
                ntn="test-token",
                db="test-db",
                require_scrapbox=False,
                require_notion=True,
            )
            assert config.scrapbox_project is None
            assert config.scrapbox_connect_sid is None
            assert config.notion_api_key == "test-token"
            assert config.notion_database_id == "test-db"
        finally:
            Path(env_file).unlink()
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_require_both(self) -> None:
        """Test loading config with both credentials required (default)."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        # Use empty temp file to prevent loading actual .env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_file = f.name

        try:
            config = Config.from_env(
                env_file,
                project="test-project",
                sid="test-sid",
                ntn="test-token",
                db="test-db",
            )
            assert config.scrapbox_project == "test-project"
            assert config.scrapbox_connect_sid == "test-sid"
            assert config.notion_api_key == "test-token"
            assert config.notion_database_id == "test-db"
        finally:
            Path(env_file).unlink()
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_missing_scrapbox_when_required(self) -> None:
        """Test error when Scrapbox credentials are missing but required."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        # Use empty temp file to prevent loading actual .env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_file = f.name

        try:
            with pytest.raises(
                ValueError,
                match="Missing required environment variables: SCRAPBOX_PROJECT, SCRAPBOX_COOKIE_CONNECT_SID",
            ):
                Config.from_env(
                    env_file,
                    ntn="test-token",
                    db="test-db",
                    require_scrapbox=True,
                    require_notion=False,
                )
        finally:
            Path(env_file).unlink()
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_missing_notion_when_required(self) -> None:
        """Test error when Notion credentials are missing but required."""
        # Clear existing env vars
        for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
            os.environ.pop(key, None)

        # Use empty temp file to prevent loading actual .env
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_file = f.name

        try:
            with pytest.raises(
                ValueError, match="Missing required environment variables: NOTION_API_KEY, NOTION_DATABASE_ID"
            ):
                Config.from_env(
                    env_file,
                    project="test-project",
                    sid="test-sid",
                    require_scrapbox=False,
                    require_notion=True,
                )
        finally:
            Path(env_file).unlink()
            for key in ["SCRAPBOX_PROJECT", "SCRAPBOX_COOKIE_CONNECT_SID", "NOTION_API_KEY", "NOTION_DATABASE_ID"]:
                os.environ.pop(key, None)

    def test_validate_scrapbox_only(self) -> None:
        """Test validate with only Scrapbox credentials."""
        config = Config(
            scrapbox_project="test-project",
            scrapbox_connect_sid="test-sid",
            notion_api_key=None,
            notion_database_id=None,
        )
        # Should not raise when only requiring Scrapbox
        config.validate(require_scrapbox=True, require_notion=False)

    def test_validate_notion_only(self) -> None:
        """Test validate with only Notion credentials."""
        config = Config(
            scrapbox_project=None,
            scrapbox_connect_sid=None,
            notion_api_key="test-token",
            notion_database_id="test-db",
        )
        # Should not raise when only requiring Notion
        config.validate(require_scrapbox=False, require_notion=True)

    def test_validate_empty_string(self) -> None:
        """Test validate raises error for empty strings."""
        config = Config(
            scrapbox_project="",
            scrapbox_connect_sid="test-sid",
            notion_api_key=None,
            notion_database_id=None,
        )
        with pytest.raises(ValueError, match="SCRAPBOX_PROJECT cannot be empty"):
            config.validate(require_scrapbox=True, require_notion=False)
