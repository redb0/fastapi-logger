"""Module of logging models."""

import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class LogModel(SQLModel):
    """Basic model of logging into a database."""
    id: Optional[int] = Field(
        title='ID',
        default=None,
        primary_key=True,
    )
    request_id: Optional[str] = Field(  # type: ignore[call-overload]
        default=None,
        title='Request ID',
        sa_type=sa.String(length=40),
    )
    client_address: Optional[str] = Field(  # type: ignore[call-overload]
        default=None,
        title='Client address',
        sa_type=sa.String(length=40),
    )
    timestamp: datetime.datetime = Field(
        title='Date and time of the request',
    )
    session: Optional[dict[str, Any]] = Field(
        title='User session data',
        default_factory=dict,
        sa_type=JSON,
    )
    method: Optional[str] = Field(
        default=None,
        title='HTTP method',
        sa_type=sa.Text,
    )
    path: Optional[str] = Field(
        default=None,
        title='URL',
        sa_type=sa.Text,
    )
    status_code: Optional[int] = Field(
        default=None,
        title='Status',
    )
    message: str = Field(
        title='All data',
        sa_type=sa.Text,
    )
