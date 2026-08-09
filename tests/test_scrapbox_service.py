"""Tests for Scrapbox service authentication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scrapbox.client import PAT_HEADER

from sb2n.scrapbox_service import ScrapboxService

if TYPE_CHECKING:
    import httpx


def _build_request(service: ScrapboxService, url: str) -> httpx.Request:
    """Build a request through the service's HTTP client so hooks/cookies apply."""
    client = service._client  # noqa: SLF001
    assert client is not None
    request = client.client.build_request("GET", url)
    for hook in client.client.event_hooks["request"]:
        hook(request)
    return request


def test_connect_sid_is_used_when_no_pat() -> None:
    """Test that connect.sid is sent as a cookie when no PAT is given."""
    with ScrapboxService("test-project", connect_sid="test-sid") as service:
        request = _build_request(service, "https://scrapbox.io/api/pages/test-project")
        assert PAT_HEADER not in request.headers
        assert "connect.sid=test-sid" in request.headers["cookie"]


def test_pat_takes_precedence_over_connect_sid() -> None:
    """Test that the PAT is used and connect.sid is not sent when both are given."""
    with ScrapboxService("test-project", connect_sid="test-sid", pat="test-pat") as service:
        request = _build_request(service, "https://scrapbox.io/api/pages/test-project")
        assert request.headers[PAT_HEADER] == "test-pat"
        assert "cookie" not in request.headers


def test_pat_is_not_sent_to_third_party_hosts() -> None:
    """Test that the PAT is not leaked to hosts other than scrapbox.io."""
    with ScrapboxService("test-project", pat="test-pat") as service:
        request = _build_request(service, "https://i.gyazo.com/abc123.png")
        assert PAT_HEADER not in request.headers
