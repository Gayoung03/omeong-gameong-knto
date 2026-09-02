"""여행 가이드 API 테스트."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    GuideDocument,
    GuideDocumentSource,
    TransportPetRule,
    TransportRestrictedBreed,
)
from app.db.models.enums import (
    BreedRestrictionScope,
    BreedRestrictionType,
    CarrierType,
    GuideCategory,
)

KST = timezone(timedelta(hours=9))


def _make_document(
    db: Session,
    *,
    slug: str,
    title: str,
    category: GuideCategory = GuideCategory.AIRLINE,
    body: str = "테스트 가이드 첫 문장입니다.\n\n자세한 본문입니다.",
    display_order: int = -100,
    is_active: bool = True,
) -> GuideDocument:
    document = GuideDocument(
        id=uuid.uuid4(),
        slug=slug,
        title=title,
        category=category,
        body=body,
        display_order=display_order,
        verified_at=datetime(2026, 8, 30, 12, 0, tzinfo=KST),
        is_active=is_active,
    )
    db.add(document)
    db.flush()
    return document


def _add_source(db: Session, document: GuideDocument, name: str) -> None:
    db.add(
        GuideDocumentSource(
            id=uuid.uuid4(),
            guide_document_id=document.id,
            source_name=name,
            source_url="https://example.com/pet",
            verified_at=document.verified_at,
        )
    )
    db.flush()


def test_가이드_목록은_활성_문서와_출처를_내린다(client: TestClient, db: Session) -> None:
    active = _make_document(db, slug=f"test-guide-{uuid.uuid4().hex}", title="테스트항공")
    inactive = _make_document(
        db,
        slug=f"test-hidden-{uuid.uuid4().hex}",
        title="숨긴항공",
        is_active=False,
    )
    _add_source(db, active, "테스트항공 공식 안내")
    _add_source(db, inactive, "숨긴항공 공식 안내")

    body = client.get("/api/v1/guides", params={"category": "airline", "limit": 100}).json()
    slugs = [item["slug"] for item in body["items"]]
    item = next(item for item in body["items"] if item["slug"] == active.slug)

    assert active.slug in slugs
    assert inactive.slug not in slugs
    assert item["summary"] == "테스트 가이드 첫 문장입니다."
    assert item["verifiedAt"].startswith("2026-08-30")
    assert item["sources"][0]["sourceName"] == "테스트항공 공식 안내"


def test_가이드_상세는_본문을_함께_내린다(client: TestClient, db: Session) -> None:
    document = _make_document(
        db,
        slug=f"test-detail-{uuid.uuid4().hex}",
        title="상세항공",
        body="첫 문장입니다.\n\n상세 본문입니다.",
    )

    response = client.get(f"/api/v1/guides/{document.slug}")

    assert response.status_code == 200
    assert response.json()["body"] == "첫 문장입니다.\n\n상세 본문입니다."


def test_운송_규정_목록은_문서와_규정값을_함께_내린다(
    client: TestClient,
    db: Session,
) -> None:
    document = _make_document(
        db,
        slug=f"test-rule-{uuid.uuid4().hex}",
        title="테스트항공",
    )
    _add_source(db, document, "테스트항공 공식 안내")
    rule = TransportPetRule(
        id=uuid.uuid4(),
        guide_document_id=document.id,
        carrier_name="테스트항공",
        carrier_type=CarrierType.AIRLINE,
        cabin_allowed=True,
        cabin_max_weight_kg=Decimal("7.00"),
        cabin_fee_krw=30000,
        cargo_allowed=False,
        pledge_required=True,
        request_deadline_hours=24,
        notes="운송 서약서가 필요해요.",
        verified_at=document.verified_at,
    )
    db.add(rule)
    db.flush()

    response = client.get(
        "/api/v1/guides/transport-rules",
        params={"carrierType": "airline", "q": "테스트항공"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == str(rule.id)
    assert item["guideSlug"] == document.slug
    assert item["carrierName"] == "테스트항공"
    assert item["cabinMaxWeightKg"] == 7.0
    assert item["cargoAllowed"] is False
    # 무제한 플래그 3값 중 "미확인" — 값을 안 넣었으니 null 로 내려와야 한다.
    assert item["cabinWeightUnlimited"] is None
    assert item["cargoWeightUnlimited"] is None
    assert item["cabinConditions"] is None
    assert item["sources"][0]["sourceName"] == "테스트항공 공식 안내"


def test_운송_규정은_무게_무제한과_조건부_문구를_내린다(
    client: TestClient,
    db: Session,
) -> None:
    document = _make_document(
        db,
        slug=f"test-ferry-{uuid.uuid4().hex}",
        title="테스트페리",
    )
    rule = TransportPetRule(
        id=uuid.uuid4(),
        guide_document_id=document.id,
        carrier_name="테스트페리",
        carrier_type=CarrierType.FERRY,
        cabin_allowed=True,
        # CHECK 제약: 무제한이면 max_weight 는 NULL 이어야 한다.
        cabin_weight_unlimited=True,
        cabin_conditions="원칙적으로 불가, 부득이한 경우 케이지 동반 허용",
        cargo_allowed=None,
        verified_at=document.verified_at,
    )
    db.add(rule)
    db.flush()

    response = client.get(f"/api/v1/guides/transport-rules/{rule.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["cabinWeightUnlimited"] is True
    assert body["cabinMaxWeightKg"] is None
    assert body["cabinConditions"] == "원칙적으로 불가, 부득이한 경우 케이지 동반 허용"
    assert body["cargoWeightUnlimited"] is None


def test_없는_운송_규정은_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/guides/transport-rules/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 운송 규정 제한 견종 노출
# ---------------------------------------------------------------------------


def _make_rule(db: Session) -> TransportPetRule:
    document = GuideDocument(
        id=uuid.uuid4(),
        slug=f"test-breeds-{uuid.uuid4().hex}",
        title="견종테스트항공",
        category=GuideCategory.AIRLINE,
        body="본문",
        display_order=999,
    )
    db.add(document)
    db.flush()
    rule = TransportPetRule(
        id=uuid.uuid4(),
        guide_document_id=document.id,
        carrier_name="견종테스트항공",
        carrier_type=CarrierType.AIRLINE,
        cabin_allowed=True,
    )
    db.add(rule)
    db.flush()
    return rule


def test_운송_규정_응답에_제한_견종이_실린다(client: TestClient, db: Session) -> None:
    rule = _make_rule(db)
    db.add_all(
        [
            TransportRestrictedBreed(
                id=uuid.uuid4(),
                transport_pet_rule_id=rule.id,
                breed_name_ko="도사견",
                restriction_type=BreedRestrictionType.DANGEROUS,
                applies_to=BreedRestrictionScope.BOTH,
                is_example_only=False,
            ),
            TransportRestrictedBreed(
                id=uuid.uuid4(),
                transport_pet_rule_id=rule.id,
                breed_name_ko="퍼그",
                restriction_type=BreedRestrictionType.BRACHYCEPHALIC,
                applies_to=BreedRestrictionScope.CARGO,
                is_example_only=False,
            ),
        ]
    )
    db.flush()

    response = client.get(f"/api/v1/guides/transport-rules/{rule.id}")

    assert response.status_code == 200
    breeds = response.json()["restrictedBreeds"]
    assert [b["breedNameKo"] for b in breeds] == ["도사견", "퍼그"]
    assert breeds[0]["restrictionType"] == "dangerous"
    assert breeds[0]["appliesTo"] == "both"
    assert breeds[1]["restrictionType"] == "brachycephalic"
    assert breeds[1]["isExampleOnly"] is False


def test_견종_제한이_없는_운송사는_빈_배열이다(client: TestClient, db: Session) -> None:
    rule = _make_rule(db)

    response = client.get(f"/api/v1/guides/transport-rules/{rule.id}")

    assert response.status_code == 200
    assert response.json()["restrictedBreeds"] == []
