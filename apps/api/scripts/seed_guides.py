"""여행 가이드 콘텐츠 씨앗 데이터.

본문은 ``scripts/data/guides/*.md`` 에 따로 두고 여기서는 **값과 출처만** 다룬다.
긴 한글 마크다운을 파이썬 문자열에 넣으면 읽기도 고치기도 어렵기 때문.

원자료와 판단 근거: ``docs/planning/travel-guide-collection.md``
규정이 바뀌면 **그 문서와 여기 둘 다** 고친다.

⚠️ 값이 ``None`` 인 것은 "0" 이나 "불가" 가 아니라 **"확인 안 됨"** 이다.
원문이 「불가」라고 밝힌 것만 ``False`` 로 넣는다.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    GuideDocument,
    GuideDocumentSource,
    TransportPetRule,
)
from app.db.models.enums import CarrierType, GuideCategory

KST = timezone(timedelta(hours=9))
DATA_DIR = Path(__file__).parent / "data" / "guides"


def _at(d: str) -> datetime:
    """확인일(YYYY-MM-DD) → 그날 정오(KST). 시각은 의미 없고 날짜만 쓴다."""
    return datetime.combine(date.fromisoformat(d), time(12, 0), tzinfo=KST)


# ─── 문서 15편 ────────────────────────────────────────────────
# (slug, 제목, 분류, 확인일, 출처 목록[(이름, url, 비고)])
GUIDE_DOCUMENTS = [
    (
        "airline-korean-air",
        "대한항공",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("대한항공 반려동물 동반 안내", None, None)],
    ),
    (
        "airline-asiana",
        "아시아나항공",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("아시아나항공 반려동물 운송 안내", None, None)],
    ),
    (
        "airline-jeju-air",
        "제주항공",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("제주항공 「반려동물 운송 서비스」 안내 페이지", None, None)],
    ),
    (
        "airline-tway",
        "티웨이항공",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("티웨이항공 t'pet 국내선 반려동물 운송규정", None, None)],
    ),
    (
        "airline-jin-air",
        "진에어",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("진에어 JINI PET 반려동물 동반 여행 서비스", None, None)],
    ),
    (
        "airline-air-busan",
        "에어부산",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("에어부산 반려동물 운송 안내 페이지", None, None)],
    ),
    (
        "airline-eastar-jet",
        "이스타항공",
        GuideCategory.AIRLINE,
        "2026-08-26",
        [("이스타항공 「반려동물을 동반하는 고객」 안내 페이지", None, None)],
    ),
    (
        "ferry-hanil-wando",
        "한일고속페리 (완도↔제주)",
        GuideCategory.FERRY,
        "2026-08-27",
        [
            ("한일고속페리 승선절차 — 반려동물 동반", None, None),
            ("한일고속페리 선박 정보 · 예매 페이지", None, "소요 시간·도착 시각 확인"),
        ],
    ),
    (
        "ferry-seaworld-mokpo-jindo",
        "씨월드고속훼리 (목포·진도↔제주)",
        GuideCategory.FERRY,
        "2026-08-27",
        [
            ("씨월드고속훼리 반려동물 예약 안내", None, None),
            ("씨월드고속훼리 운항 스케줄", None, "소요 시간·정기휴항 확인"),
        ],
    ),
    (
        "ferry-oceanvista-samcheonpo",
        "오션비스타제주 (삼천포↔제주)",
        GuideCategory.FERRY,
        "2026-08-27",
        [
            ("오션비스타제주 펫룸 안내 · 펫티켓 가이드", None, None),
            ("오션비스타제주 운항 시간표", None, "소요 시간·휴항 확인"),
        ],
    ),
    (
        "ferry-arion-nokdong",
        "아리온제주 (고흥 녹동↔제주)",
        GuideCategory.FERRY,
        "2026-08-27",
        [
            ("남해고속 운항시간표", None, None),
            (
                "남해고속 FAQ 「선박 승선 시 애완견 동승은 가능하나요?」",
                None,
                "동반 원칙적 불가 확인",
            ),
        ],
    ),
    ("prep-rental-car", "제주에서 렌터카 이용하기", GuideCategory.PREPARATION, "2026-08-27", []),
    (
        "prep-packing",
        "제주 갈 때 챙길 것",
        GuideCategory.PREPARATION,
        "2026-08-27",
        [("항공사 7곳 · 여객선 4개 항로 운송 규정", None, "각 운송사 안내 페이지에서 파생")],
    ),
    (
        "prep-first-trip",
        "반려동물과 첫 여행",
        GuideCategory.PREPARATION,
        "2026-08-27",
        [("항공사 7곳 · 여객선 4개 항로 운송 규정", None, "각 운송사 안내 페이지에서 파생")],
    ),
    (
        "prep-jeju-entry",
        "제주도 동물 반입 규정",
        GuideCategory.PREPARATION,
        "2026-08-27",
        [
            (
                "제주특별자치도 동물위생시험소 「가축 및 생산물 반입 신청 요령」",
                "https://www.jeju.go.kr/animal/prevention/quarantine/carry.htm",
                None,
            ),
            (
                "제주특별자치도 「우제류 가축 및 그 생산물 등 반입 시 방역요령 변경 고시」",
                None,
                "고시 제2026-109호 (2026-04-08 시행) — 현행",
            ),
            (
                "제주특별자치도 「반출·반입 가축 및 그 생산물 등에 관한 방역요령 변경 고시」",
                None,
                "고시 제2023-64호 — 돼지 ASF 반입금지",
            ),
        ],
    ),
]


# ─── 운송사별 규정 값 12건 ────────────────────────────────────
# 무게는 전부 **케이지 포함** 기준. 요금은 국내선 편도.
# duration_minutes: 한 노선에 배가 여러 척이면 **가장 긴 값**을 넣고 범위는 notes 에 적는다.
D = Decimal
TRANSPORT_RULES = [
    # ── 항공사 7곳 ──
    {
        "doc": "airline-korean-air",
        "carrier_name": "대한항공",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("7.00"),
        "cabin_fee_krw": 30000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "cargo_allowed": True,
        "cargo_max_weight_kg": D("45.00"),
        "cargo_fee_threshold_kg": D("32.00"),
        "cargo_fee_light_krw": 30000,
        "cargo_fee_heavy_krw": 60000,
        "min_age_weeks_cargo": 16,
        "request_deadline_hours": 24,
        "notes": "위탁은 1인 2마리까지. 보잉 737·에어버스 A321은 국내선 혹서기(6~9월) 위탁 제한. "
        "마일리지·SKYPETS 포인트로 결제 가능. 단두종은 위탁 불가.",
    },
    {
        "doc": "airline-asiana",
        "carrier_name": "아시아나항공",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("7.00"),
        "cabin_fee_krw": 30000,
        "min_age_weeks_cabin": 16,
        "max_pets_per_person_cabin": 1,
        "cargo_allowed": True,
        "cargo_max_weight_kg": D("45.00"),
        "cargo_fee_threshold_kg": D("32.00"),
        "cargo_fee_light_krw": 30000,
        "cargo_fee_heavy_krw": 60000,
        "min_age_weeks_cargo": 16,
        "same_day_request_allowed": False,
        "request_deadline_hours": 24,
        "airport_cage_price_krw": 45000,
        "notes": "기내도 생후 16주 이상 — 일곱 곳 중 유일. 성인 탑승객만 신청할 수 있다. "
        "예약·확약 없이 공항에 오면 기내·위탁 모두 운송 불가. "
        "에어부산 공동운항편은 위탁 서비스 없음. 단두종은 위탁 불가.",
    },
    {
        "doc": "airline-jeju-air",
        "carrier_name": "제주항공",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("9.00"),
        "cabin_fee_krw": 25000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "max_pets_per_trip": 6,
        "cargo_allowed": False,
        "pledge_required": True,
        "online_checkin_allowed": False,
        "notes": "화물칸 위탁 자체가 없다 — 케이지 포함 9kg을 넘으면 이 항공사로는 갈 수 없다. "
        "반려동물 전용 좌석 6석(10A·13F·18A·21F·25A·30F)만 이용 가능. "
        "위탁이 없어 단두종 제한도 없다.",
    },
    {
        "doc": "airline-tway",
        "carrier_name": "티웨이항공",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("9.00"),
        "cabin_fee_krw": 30000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "max_pets_per_trip": 6,
        "cargo_allowed": False,
        "pledge_required": True,
        "online_checkin_allowed": False,
        "same_day_request_allowed": True,
        "request_deadline_hours": 24,
        "airport_cage_price_krw": 5000,
        "notes": "신청 경로가 셋 — 온라인 출발 1일 전, 유선 2시간 30분 전, 현장 탑승 수속 마감 전. "
        "여정을 변경하면 반려동물 신청이 자동 취소되므로 재신청해야 한다. "
        "반려동물 유모차·카시트 1개를 무료로 위탁할 수 있다. 위탁이 없어 단두종 제한 없음.",
    },
    {
        "doc": "airline-jin-air",
        "carrier_name": "진에어",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("9.00"),
        "cabin_fee_krw": 20000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "cargo_allowed": True,
        "cargo_max_weight_kg": D("45.00"),
        "cargo_fee_threshold_kg": D("32.00"),
        "cargo_fee_light_krw": 30000,
        "cargo_fee_heavy_krw": 60000,
        "min_age_weeks_cargo": 16,
        "pledge_required": True,
        "online_checkin_allowed": False,
        "airport_cage_price_krw": 25000,
        "notes": "위탁은 1인 2마리·항공기당 최대 5마리. 사전 신청 마감 시점은 안내에 없다. "
        "단두종은 위탁 불가.",
    },
    {
        "doc": "airline-air-busan",
        "carrier_name": "에어부산",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("9.00"),
        "cabin_fee_krw": 20000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "cargo_allowed": True,
        "cargo_max_weight_kg": D("32.00"),
        "min_age_weeks_cargo": 8,
        "pledge_required": True,
        "airport_cage_price_krw": 6000,
        "notes": "위탁 상한이 32kg으로 다른 곳(45kg)보다 낮다. 위탁 요금은 확인되지 않았다. "
        "혹한기에는 위탁이 제한될 수 있어 예약센터(1666-3060) 확약이 필요하다. "
        "반려동물 동반 시 창가 좌석에 배정되며 복도측은 이용할 수 없다.",
    },
    {
        "doc": "airline-eastar-jet",
        "carrier_name": "이스타항공",
        "carrier_type": CarrierType.AIRLINE,
        "cabin_allowed": True,
        "cabin_max_weight_kg": D("9.00"),
        "cabin_fee_krw": 30000,
        "min_age_weeks_cabin": 8,
        "max_pets_per_person_cabin": 1,
        "max_pets_per_trip": 6,
        "cargo_allowed": False,
        "pledge_required": True,
        "online_checkin_allowed": False,
        "same_day_request_allowed": True,
        "request_deadline_hours": 24,
        "notes": "운송 가능 노선을 명시한 유일한 항공사 — 김포·제주·청주·군산·부산. "
        "취소·환불도 출발 24시간 전까지만 가능하다. "
        "탑승 전 반려동물이 케이지에 들어가 있어야 하며, 거부하면 운송할 수 없다. "
        "전용 좌석 6A·6F·18A·18F·29A·29F. 단두종 제한은 국제선에만 적용.",
    },
    # ── 여객선 5개 항로 ──
    {
        "doc": "ferry-hanil-wando",
        "carrier_name": "한일고속페리",
        "carrier_type": CarrierType.FERRY,
        "route": "완도↔제주",
        "cabin_allowed": True,
        "max_pets_per_person_cabin": 1,
        "duration_minutes": 160,
        "notes": "무게 제한이 명시되어 있지 않아 대형견도 함께 갈 수 있다. "
        "반려동물 객실을 구매하지 않으면 동반 승선이 불가하다. "
        "케이지 필수이며 유모차·슬링백은 사용할 수 없다. 갑판 산책 불가. "
        "골드스텔라 완도발 02:30·15:00, 실버클라우드 09:20. 두 척 모두 2시간 40분.",
    },
    {
        "doc": "ferry-seaworld-mokpo-jindo",
        "carrier_name": "씨월드고속훼리",
        "carrier_type": CarrierType.FERRY,
        "route": "목포↔제주",
        "cabin_allowed": True,
        "duration_minutes": 290,
        "notes": "객실 등급이 무게로 갈린다 — 펫코노미 4kg 미만, "
        "펫스탠다드룸·퀸메리 의자석 10kg 미만, "
        "펫스위트룸은 제한 없음. 소요 시간은 배마다 4시간 15분~4시간 50분. "
        "야외 갑판에 펫가든이 있어 전용공간에서 케이지를 열 수 있다. 가방 형태 케이지 허용. "
        "정기휴항이 배마다 달라 왕복을 다른 배로 잡으면 돌아오는 날이 휴항일일 수 있다. "
        "삼학부두 여객터미널 출발.",
    },
    {
        "doc": "ferry-seaworld-mokpo-jindo",
        "carrier_name": "씨월드고속훼리",
        "carrier_type": CarrierType.FERRY,
        "route": "진도↔제주",
        "cabin_allowed": True,
        "duration_minutes": 120,
        "notes": "산타모니카. 네 항로 중 가장 짧지만 "
        "객실이 아니라 좌석제라 항해 내내 케이지 안에 있어야 한다. "
        "추자도를 25분 경유하며 그동안에도 케이지를 열 수 없다. 펫가든 없음. "
        "무게 제한 없음. 1·3주 수요일 휴항.",
    },
    {
        "doc": "ferry-oceanvista-samcheonpo",
        "carrier_name": "오션비스타제주",
        "carrier_type": CarrierType.FERRY,
        "route": "삼천포↔제주",
        "cabin_allowed": True,
        "duration_minutes": 390,
        "notes": "네 항로 중 유일한 심야 운항 — 23:30 출발 06:00 도착. 숙박을 하루 아낄 수 있다. "
        "다만 펫룸 안에서도 케이지·입마개·목줄을 계속 착용해야 하는 유일한 선사라 "
        "아이는 밤새 6시간 30분을 케이지 안에서 보내게 된다. "
        "소프트케이지·슬링백·유모차형 불가. 인식표 요구. 개인 이불 지참 필수. "
        "차량 내부는 케이지 규정이 없다. 매주 토요일 휴항.",
    },
    {
        "doc": "ferry-arion-nokdong",
        "carrier_name": "아리온제주(남해고속)",
        "carrier_type": CarrierType.FERRY,
        "route": "고흥(녹동)↔제주",
        "cabin_allowed": False,
        "duration_minutes": 220,
        "notes": "선사 안내상 애완견 동승이 원칙적으로 불가하다. 부득이한 경우에만 케이지에 넣어 "
        "예외적으로 허용되며, 객실은 이용할 수 없고 승무원이 지정한 곳에 보관해야 한다. "
        "다른 승객의 민원이 우려되면 승선이 제한될 수 있다. 대형견은 입마개 필수. "
        "반려동물과 함께라면 완도·목포·진도·삼천포 노선을 권한다.",
    },
]


def _body(slug: str) -> str:
    path = DATA_DIR / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(f"본문 파일이 없습니다: {path}")
    return path.read_text(encoding="utf-8").strip()


def seed_guides(db: Session) -> None:
    """가이드 문서·출처·운송 규정을 심는다. 이미 있으면 건너뛴다."""
    existing = set(db.scalars(select(GuideDocument.slug)).all())
    docs: dict[str, GuideDocument] = {}
    created = 0

    for slug, title, category, verified, sources in GUIDE_DOCUMENTS:
        if slug in existing:
            docs[slug] = db.scalar(select(GuideDocument).where(GuideDocument.slug == slug))
            continue
        doc = GuideDocument(
            id=uuid.uuid4(),
            slug=slug,
            title=title,
            category=category,
            body=_body(slug),
            display_order=len(docs) + created,
            verified_at=_at(verified),
        )
        db.add(doc)
        db.flush()
        docs[slug] = doc
        created += 1
        for order, (name, url, note) in enumerate(sources):
            db.add(
                GuideDocumentSource(
                    id=uuid.uuid4(),
                    guide_document_id=doc.id,
                    source_name=name,
                    source_url=url,
                    source_note=note,
                    verified_at=_at(verified),
                    display_order=order,
                )
            )

    skipped = len(GUIDE_DOCUMENTS) - created
    print(f"  가이드   {created}개 생성 / {skipped}개 건너뜀")

    rule_keys = {(r.carrier_name, r.route) for r in db.scalars(select(TransportPetRule)).all()}
    rules_created = 0
    for spec in TRANSPORT_RULES:
        spec = dict(spec)
        slug = spec.pop("doc")
        key = (spec["carrier_name"], spec.get("route"))
        if key in rule_keys:
            continue
        doc = docs.get(slug)
        if doc is None:
            raise ValueError(f"운송 규정이 가리키는 문서가 없습니다: {slug}")
        verified = next(d[3] for d in GUIDE_DOCUMENTS if d[0] == slug)
        db.add(
            TransportPetRule(
                id=uuid.uuid4(),
                guide_document_id=doc.id,
                verified_at=_at(verified),
                **spec,
            )
        )
        rules_created += 1

    print(f"  운송규정 {rules_created}개 생성 / {len(TRANSPORT_RULES) - rules_created}개 건너뜀")
    db.flush()
