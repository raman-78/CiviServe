"""Common Pydantic base + shared envelope schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class APIModel(BaseModel):
    """Base schema: camelCase JSON aliases, populate from snake_case attrs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | list | None = None
    requestId: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class Paginated(APIModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
