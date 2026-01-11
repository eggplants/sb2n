"""Scrapbox API client wrapper."""

import logging
import urllib.parse
from typing import TYPE_CHECKING, Self

from scrapbox.client import PageDetail, ScrapboxClient

if TYPE_CHECKING:
    from scrapbox import PageListItem

logger = logging.getLogger(__name__)


class ScrapboxService:
    """Service for interacting with Scrapbox API.

    This class wraps the ScrapboxClient to provide convenient methods for
    fetching pages and files from a Scrapbox project.
    """

    def __init__(self, project_name: str, connect_sid: str) -> None:
        """Initialize Scrapbox service.

        Args:
            project_name: Scrapbox project name
            connect_sid: Scrapbox authentication cookie (connect.sid)
        """
        self.project_name = project_name
        self.connect_sid = connect_sid
        self._client: ScrapboxClient | None = None

    def __enter__(self) -> Self:
        """Enter context manager."""
        self._client = ScrapboxClient(connect_sid=self.connect_sid)
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        if self._client:
            self._client.close()
            self._client = None

    def get_all_pages(self) -> list[PageListItem]:
        """Get all pages from the Scrapbox project.

        Returns:
            List of all page items

        Raises:
            RuntimeError: If client is not initialized (use as context manager)
        """
        if not self._client:
            msg = "Client not initialized. Use ScrapboxService as a context manager."
            raise RuntimeError(msg)

        all_pages: list[PageListItem] = []
        skip = 0
        limit = 100

        logger.info("Fetching pages from project: %(project_name)s", {"project_name": self.project_name})

        while True:
            response = self._client.get_pages(self.project_name, skip=skip, limit=limit)
            pages = response.pages
            all_pages.extend(pages)

            logger.debug(
                "Fetched %(fetched)d pages (total: %(total)d/%(count)d)",
                {"fetched": len(pages), "total": len(all_pages), "count": response.count},
            )

            if len(all_pages) >= response.count:
                break

            skip += limit

        logger.info("Total pages fetched: %(total)d", {"total": len(all_pages)})
        return all_pages

    def get_page_detail(self, page_title: str) -> PageDetail:
        """Get detailed information about a specific page.

        Args:
            page_title: Title of the page

        Returns:
            Detailed page information

        Raises:
            RuntimeError: If client is not initialized (use as context manager)
        """
        if not self._client:
            msg = "Client not initialized. Use ScrapboxService as a context manager."
            raise RuntimeError(msg)

        logger.debug("Fetching page detail: %(page_title)s", {"page_title": page_title})
        return self._client.get_page(self.project_name, page_title)

    def get_page_text(self, page_title: str) -> str:
        """Get text content of a page.

        Args:
            page_title: Title of the page

        Returns:
            Page text content

        Raises:
            RuntimeError: If client is not initialized (use as context manager)
        """
        if not self._client:
            msg = "Client not initialized. Use ScrapboxService as a context manager."
            raise RuntimeError(msg)

        logger.debug("Fetching page text: %(page_title)s", {"page_title": page_title})
        return self._client.get_page_text(self.project_name, page_title)

    def download_file(self, file_id: str) -> bytes:
        """Download a file from Scrapbox.

        Args:
            file_id: File ID or full URL (e.g., "abc123.jpg" or "https://gyazo.com/...")

        Returns:
            File binary data

        Raises:
            RuntimeError: If client is not initialized (use as context manager)
        """
        if not self._client:
            msg = "Client not initialized. Use ScrapboxService as a context manager."
            raise RuntimeError(msg)

        logger.debug("Downloading file: %(file_id)s", {"file_id": file_id})
        return self._client.get_file(file_id)

    def get_page_url(self, page_title: str) -> str:
        """Generate Scrapbox page URL.

        Args:
            page_title: Title of the page

        Returns:
            Full URL to the Scrapbox page
        """
        return f"https://scrapbox.io/{self.project_name}/{urllib.parse.quote(page_title, safe='')}"
