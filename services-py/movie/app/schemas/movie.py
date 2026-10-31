"""Schemas Pydantic của Movie Service: chuẩn hóa request/response theo API_CONTRACT (camelCase)."""
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.entities.movie import Movie


class MovieCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Avengers: Secret Wars",
                "genre": "Hành động, Viễn tưởng",
                "duration": 180,
                "poster": "poster_avengers.jpg",
            }
        }
    )

    title: str = Field(
        ...,
        description="Tên phim (bắt buộc, không được để trống)",
        examples=["Avengers: Secret Wars"],
    )
    genre: str | None = Field(
        default=None,
        description="Thể loại phim",
        examples=["Hành động, Viễn tưởng"],
    )
    duration: int | None = Field(
        default=None,
        description="Thời lượng phim tính bằng phút (nếu có phải > 0)",
        examples=[180],
    )
    poster: str | None = Field(
        default=None,
        description="Đường dẫn áp phích hoặc URL ảnh",
        examples=["poster_avengers.jpg"],
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        s = v.strip() if isinstance(v, str) else ""
        if not s:
            raise ValueError("Trường 'title' là bắt buộc và không được để trống")
        return s

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Thời lượng phim ('duration') phải lớn hơn 0")
        return v

    @field_validator("genre", "poster")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            trimmed = v.strip()
            return trimmed if trimmed else None
        return v


class MovieUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Inception (Bản đặc biệt)",
                "genre": "Khoa học viễn tưởng",
                "duration": 150,
                "poster": "poster2.jpg",
            }
        }
    )

    title: str | None = Field(
        default=None,
        description="Tên phim (nếu cập nhật thì không được để rỗng)",
        examples=["Inception (Bản đặc biệt)"],
    )
    genre: str | None = Field(
        default=None,
        description="Thể loại phim",
        examples=["Khoa học viễn tưởng"],
    )
    duration: int | None = Field(
        default=None,
        description="Thời lượng phim tính bằng phút",
        examples=[150],
    )
    poster: str | None = Field(
        default=None,
        description="Đường dẫn áp phích hoặc URL ảnh",
        examples=["poster2.jpg"],
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Tên phim ('title') không được để rỗng")
            return s
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Thời lượng phim ('duration') phải lớn hơn 0")
        return v

    @field_validator("genre", "poster")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            trimmed = v.strip()
            return trimmed if trimmed else None
        return v


class MovieResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Avengers: Endgame",
                "genre": "Hành động",
                "duration": 181,
                "poster": "poster1.jpg",
                "createdAt": "2026-10-01 09:00:00",
            }
        },
    )

    id: int = Field(..., description="ID định danh duy nhất của phim", examples=[1])
    title: str = Field(..., description="Tên phim", examples=["Avengers: Endgame"])
    genre: str | None = Field(default=None, description="Thể loại phim", examples=["Hành động"])
    duration: int | None = Field(default=None, description="Thời lượng phim (phút)", examples=[181])
    poster: str | None = Field(default=None, description="Tên tệp áp phích hoặc URL", examples=["poster1.jpg"])
    created_at: str | None = Field(
        default=None,
        serialization_alias="createdAt",
        alias="createdAt",
        description="Thời điểm khởi tạo (YYYY-MM-DD HH:MM:SS)",
        examples=["2026-10-01 09:00:00"],
    )

    @classmethod
    def from_entity(cls, movie: Movie) -> "MovieResponse":
        return cls(
            id=movie.id,
            title=movie.title,
            genre=movie.genre,
            duration=movie.duration,
            poster=movie.poster,
            created_at=movie.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
