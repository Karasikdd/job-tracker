from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    model_validator,
)

from app.enums import Status


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    status: Status = Status.saved
    url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=10000)


class ApplicationPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str | None = Field(default=None, min_length=1, max_length=200)
    position: str | None = Field(default=None, min_length=1, max_length=200)
    status: Status | None = None
    url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def forbid_null_required_fields(self):
        for name in ("company", "position", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    position: str
    status: Status
    url: str | None
    location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    old_status: Status
    new_status: Status
    changed_at: datetime