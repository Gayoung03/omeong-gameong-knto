"""반려동물 프로필 API 스키마."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.db.models.enums import PetSize, PetSpecies
from app.schemas.base import APISchema

KST = ZoneInfo("Asia/Seoul")
PetName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def calculate_age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = datetime.now(KST).date()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


class PetResponse(APISchema):
    id: uuid.UUID
    name: str
    species: PetSpecies
    species_detail: str | None
    breed: str | None
    size: PetSize | None
    weight_kg: float | None
    birth_date: date | None
    age: int | None
    image_url: str | None
    health_notes: str | None
    is_primary: bool
    status: Literal["active", "deleted"]


class PetListResponse(APISchema):
    items: list[PetResponse]
    total: int
    limit: int
    offset: int


class PetCreate(APISchema):
    name: PetName
    species: PetSpecies
    species_detail: str | None = Field(default=None, max_length=50)
    breed: str | None = Field(default=None, max_length=100)
    size: PetSize | None = None
    weight_kg: float | None = Field(default=None, ge=0)
    birth_date: date | None = None
    image_url: str | None = None
    health_notes: str | None = None

    @field_validator("birth_date")
    @classmethod
    def reject_future_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > datetime.now(KST).date():
            raise ValueError("birthDate는 오늘보다 미래일 수 없습니다")
        return value

    @model_validator(mode="after")
    def validate_species_detail(self) -> "PetCreate":
        detail = self.species_detail.strip() if self.species_detail else None
        if self.species is PetSpecies.OTHER and not detail:
            raise ValueError("species가 other이면 speciesDetail이 필요합니다")
        if self.species is not PetSpecies.OTHER and self.species_detail is not None:
            raise ValueError("species가 other가 아니면 speciesDetail을 보낼 수 없습니다")
        self.species_detail = detail
        return self


class PetUpdate(APISchema):
    name: PetName | None = None
    species: PetSpecies | None = None
    species_detail: str | None = Field(default=None, max_length=50)
    breed: str | None = Field(default=None, max_length=100)
    size: PetSize | None = None
    weight_kg: float | None = Field(default=None, ge=0)
    birth_date: date | None = None
    image_url: str | None = None
    health_notes: str | None = None

    @field_validator("birth_date")
    @classmethod
    def reject_future_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > datetime.now(KST).date():
            raise ValueError("birthDate는 오늘보다 미래일 수 없습니다")
        return value

    @field_validator("name", "species")
    @classmethod
    def reject_required_nulls(cls, value: object | None) -> object:
        if value is None:
            raise ValueError("name과 species는 null일 수 없습니다")
        return value
