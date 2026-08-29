"""장소 데이터 정정 스크립트 테스트."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models import Place
from scripts import repair_place_data


def test_known_accommodations_are_corrected_once(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    corrections = (
        repair_place_data.CategoryCorrection(
            uuid.uuid4(), "테스트 바다 펜션", "beach", "accommodation"
        ),
        repair_place_data.CategoryCorrection(
            uuid.uuid4(), "테스트 해변 게스트하우스", "beach", "accommodation"
        ),
    )
    monkeypatch.setattr(repair_place_data, "CATEGORY_CORRECTIONS", corrections)
    for correction in corrections:
        db.add(
            Place(
                id=correction.place_id,
                name=correction.name,
                category=correction.from_category,
                latitude=33.5,
                longitude=126.5,
            )
        )
    db.flush()

    pending = repair_place_data.pending_category_corrections(db)
    assert pending == list(corrections)
    assert repair_place_data.apply_category_corrections(db, pending) == 2
    db.flush()

    assert repair_place_data.pending_category_corrections(db) == []
    assert repair_place_data.apply_category_corrections(db, []) == 0
