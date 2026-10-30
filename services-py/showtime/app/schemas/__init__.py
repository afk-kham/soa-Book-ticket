"""Pydantic request/response models for the public camelCase API."""

from datetime import datetime
import re
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationInfo,
    field_validator,
    model_validator,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowtimeCreate(ApiModel):
    movie_id: StrictInt = Field(
        gt=0,
        alias="movieId",
        validation_alias=AliasChoices("movieId", "movie_id"),
    )
    cinema: str
    room: str
    time: str
    price: StrictInt = Field(ge=0)

    @field_validator("movie_id", "price", mode="before")
    @classmethod
    def parse_integer(cls, value: object) -> object:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and re.fullmatch(r"-?\d+", value):
            return int(value)
        return value

    @field_validator("cinema", "room")
    @classmethod
    def validate_text(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        max_length = 150 if info.field_name == "cinema" else 50
        if not normalized:
            raise ValueError(f"{info.field_name} là bắt buộc")
        if len(normalized) > max_length:
            raise ValueError(f"{info.field_name} tối đa {max_length} ký tự")
        return normalized

    @field_validator("time")
    @classmethod
    def normalize_time(cls, value: str) -> str:
        normalized = value.strip().replace("T", " ")
        for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(normalized, date_format)
            except ValueError:
                continue
            if parsed.strftime(date_format) == normalized:
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
        raise ValueError("time phải có dạng YYYY-MM-DD HH:MM[:SS]")


class ShowtimeUpdate(ApiModel):
    movie_id: StrictInt | None = Field(
        default=None,
        gt=0,
        alias="movieId",
        validation_alias=AliasChoices("movieId", "movie_id"),
    )
    cinema: str | None = None
    room: str | None = None
    time: str | None = None
    price: StrictInt | None = Field(default=None, ge=0)

    @field_validator("movie_id", "price", mode="before")
    @classmethod
    def parse_integer(cls, value: object) -> object:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and re.fullmatch(r"-?\d+", value):
            return int(value)
        return value

    @field_validator("cinema", "room")
    @classmethod
    def validate_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        max_length = 150 if info.field_name == "cinema" else 50
        if not normalized:
            raise ValueError(f"{info.field_name} là bắt buộc")
        if len(normalized) > max_length:
            raise ValueError(f"{info.field_name} tối đa {max_length} ký tự")
        return normalized

    @field_validator("time")
    @classmethod
    def normalize_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ShowtimeCreate.normalize_time(value)

    @model_validator(mode="after")
    def require_fields(self) -> "ShowtimeUpdate":
        if not self.model_fields_set:
            raise ValueError("Cần ít nhất một trường để cập nhật")
        if any(getattr(self, field_name) is None for field_name in self.model_fields_set):
            raise ValueError("Giá trị trường cập nhật không được để trống")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ShowtimeResponse(ApiModel):
    id: int
    movie_id: int = Field(alias="movieId")
    cinema: str
    room: str
    time: str
    price: int


class DeleteShowtimeResponse(ApiModel):
    id: int
    deleted: bool


class SuccessEnvelope(ApiModel):
    status: str = "success"
    data: Any


class ErrorEnvelope(ApiModel):
    status: str = "error"
    code: str
    message: str
