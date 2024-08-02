"""Module of logging models."""

import datetime
import json
from typing import Any, Optional, Union

import sqlalchemy as sa
from pydantic import field_validator
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
    logger: Optional[str] = Field(
        default=None,
        title='Logger name',
        sa_type=sa.Text,
    )
    level: Optional[str] = Field(
        default=None,
        title='Level',
        sa_type=sa.Text,
    )
    message: dict[str, Any] = Field(
        title='All data',
        sa_type=sa.JSON,
    )

    @field_validator('message', mode='before')
    @classmethod
    def _convert(cls, value: Union[str, dict[str, Any]]) -> Any:  # noqa: ANN401
        if isinstance(value, str):
            return json.loads(value)
        return value
