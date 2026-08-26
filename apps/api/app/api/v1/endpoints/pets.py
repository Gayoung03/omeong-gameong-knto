"""반려동물 프로필 엔드포인트."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Pet, User
from app.db.models.enums import PetSpecies
from app.db.session import get_db
from app.schemas.pet import PetCreate, PetListResponse, PetResponse, PetUpdate, calculate_age

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _to_response(pet: Pet) -> PetResponse:
    return PetResponse(
        id=pet.id,
        name=pet.name,
        species=pet.species,
        species_detail=pet.species_detail,
        breed=pet.breed,
        size=pet.size,
        weight_kg=float(pet.weight_kg) if pet.weight_kg is not None else None,
        birth_date=pet.birth_date,
        age=calculate_age(pet.birth_date),
        image_url=pet.image_url,
        health_notes=pet.health_notes,
        is_primary=pet.is_primary,
        status="deleted" if pet.deleted_at else "active",
    )


def _load_active_pet(db: Session, pet_id: uuid.UUID, user: User) -> Pet:
    pet = db.get(Pet, pet_id)
    if pet is None or pet.deleted_at is not None:
        raise HTTPException(status_code=404, detail="반려동물을 찾을 수 없습니다")
    if pet.user_id != user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 반려동물입니다")
    return pet


@router.get("/pets", response_model=PetListResponse, summary="내 반려동물 목록")
def list_pets(
    current_user: CurrentUser,
    db: DbSession,
    include_deleted: Annotated[bool, Query(alias="includeDeleted")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PetListResponse:
    conditions = [Pet.user_id == current_user.id]
    if not include_deleted:
        conditions.append(Pet.deleted_at.is_(None))

    total = db.scalar(select(func.count(Pet.id)).where(*conditions)) or 0
    pets = db.scalars(
        select(Pet)
        .where(*conditions)
        .order_by(Pet.is_primary.desc(), Pet.created_at, Pet.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return PetListResponse(
        items=[_to_response(pet) for pet in pets], total=total, limit=limit, offset=offset
    )


@router.post(
    "/pets",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="반려동물 등록",
)
def create_pet(payload: PetCreate, current_user: CurrentUser, db: DbSession) -> PetResponse:
    has_active_pet = db.scalar(
        select(Pet.id).where(Pet.user_id == current_user.id, Pet.deleted_at.is_(None)).limit(1)
    )
    pet = Pet(
        user_id=current_user.id,
        is_primary=has_active_pet is None,
        **payload.model_dump(),
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _to_response(pet)


@router.patch("/pets/{pet_id}", response_model=PetResponse, summary="반려동물 수정")
def update_pet(
    pet_id: uuid.UUID,
    payload: PetUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PetResponse:
    pet = _load_active_pet(db, pet_id, current_user)
    changes = payload.model_dump(exclude_unset=True)

    species = changes.get("species", pet.species)
    if "species" in changes and species is not PetSpecies.OTHER and "species_detail" not in changes:
        changes["species_detail"] = None
    species_detail = changes.get("species_detail", pet.species_detail)
    if isinstance(species_detail, str):
        species_detail = species_detail.strip() or None
        changes["species_detail"] = species_detail
    if species is PetSpecies.OTHER and species_detail is None:
        raise HTTPException(
            status_code=422, detail="species가 other이면 speciesDetail이 필요합니다"
        )
    if species is not PetSpecies.OTHER and species_detail is not None:
        raise HTTPException(
            status_code=422,
            detail="species가 other가 아니면 speciesDetail을 보낼 수 없습니다",
        )

    for field, value in changes.items():
        setattr(pet, field, value)
    db.commit()
    db.refresh(pet)
    return _to_response(pet)


@router.delete(
    "/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT, summary="반려동물 삭제"
)
def delete_pet(
    pet_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> Response:
    pet = _load_active_pet(db, pet_id, current_user)
    was_primary = pet.is_primary
    pet.is_primary = False
    pet.deleted_at = datetime.now(UTC)
    db.flush()

    if was_primary:
        next_pet = db.scalar(
            select(Pet)
            .where(Pet.user_id == current_user.id, Pet.deleted_at.is_(None))
            .order_by(Pet.created_at, Pet.id)
            .limit(1)
        )
        if next_pet is not None:
            next_pet.is_primary = True

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
