"""Page and database models for Notion API.

These models are simplified versions that contain only the fields
we actually use in this application.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from uuid import UUID


class CreatePageRequest(BaseModel):
    """Request model for creating a page."""

    parent: dict[str, Any]
    properties: dict[str, Any]
    children: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class QueryDatabaseRequest(BaseModel):
    """Request model for querying a database."""

    database_id: UUID
    page_size: int = Field(default=100, ge=1, le=100)
    start_cursor: str | None = None
    filter: dict[str, Any] | None = Field(default=None, alias="filter")
    sorts: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class QueryDatabaseResponse(BaseModel):
    """Response model for database query."""

    results: list[dict[str, Any]]
    has_more: bool
    next_cursor: str | None = None

    model_config = {"extra": "allow"}
