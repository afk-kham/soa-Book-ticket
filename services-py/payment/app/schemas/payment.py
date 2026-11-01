"""Pydantic schemas cho request/response Payment API."""
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    bookingId: StrictInt = Field(gt=0, le=9223372036854775807)
    amount: StrictInt = Field(ge=-9223372036854775808, le=9223372036854775807)
    method: StrictStr = Field(min_length=1, max_length=100)

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("method là bắt buộc")
        return value.strip()


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    bookingId: int
    amount: int
    method: str
    status: str
    paidAt: str
