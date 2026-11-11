from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Problem(Contract):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str


class Health(Contract):
    status: Literal["ok"]


class Pagination(Contract):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)


class Money(Contract):
    amount_minor: int = Field(ge=0, strict=True)
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$", examples=["MAD"])]


class StayDates(Contract):
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def valid_interval(self) -> "StayDates":
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class Timestamp(Contract):
    occurred_at: AwareDatetime
