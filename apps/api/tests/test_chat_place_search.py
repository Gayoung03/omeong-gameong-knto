"""챗봇 장소 검색 도구 테스트.

검색 함수는 순수 SQL 이라 **OpenAI 없이 전부 검증된다.** GPT 가 붙는 부분은
"어떤 인자를 고를까"뿐이고, 고른 뒤의 동작이 여기 있다.
"""

import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Place, PlacePetPolicy, PlaceTag, PlaceTagLink, Review, User
from app.db.models.enums import DataProvider, PetPolicyType, PlaceEnvironment
from app.rag.prompts.system import build_system_prompt
from app.rag.retrieval.place_search import (
    DESCRIPTION_LENGTH,
    MAX_LIMIT,
    PlaceSort,
    UnknownVocabularyError,
    search_places,
)
from app.rag.vocabulary import CATEGORIES, REGIONS, TAGS


@pytest.fixture(autouse=True)
def only_test_places(db: Session) -> None:
    """이 파일은 `places` 가 비어 있는 상태에서 시작한다.

    검색은 다섯 곳만 돌려준다. 로컬 개발 DB 에는 실제 장소가 1000건 넘게 들어
    있어서, 비우지 않으면 **테스트가 만든 장소가 상한에 밀려 아예 올라오지
    못한다.** 그러면 "필터가 동작한다"를 검사할 수가 없다.

    바깥 트랜잭션이 통째로 롤백되므로 진짜로 지워지지는 않는다. `places` 를
    가리키는 외래키는 전부 `CASCADE` 아니면 `SET NULL` 이라 함께 정리된다.
    """
    db.execute(delete(Place))
    db.flush()


def _place(
    db: Session,
    name: str,
    *,
    region: str = "애월/한림/협재",
    category: str = "cafe",
    environment: PlaceEnvironment | None = None,
    policy: PetPolicyType | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    created_by: uuid.UUID | None = None,
) -> Place:
    place = Place(
        id=uuid.uuid4(),
        name=name,
        category=category,
        region=region,
        environment=environment,
        description=description,
        latitude=33.4,
        longitude=126.3,
        created_by_user_id=created_by,
    )
    db.add(place)
    db.flush()

    if policy is not None:
        # `source` 는 NOT NULL 이다 — 어느 출처에서 온 정책인지 항상 남긴다.
        db.add(
            PlacePetPolicy(
                id=uuid.uuid4(),
                place_id=place.id,
                policy_type=policy,
                source=DataProvider.INTERNAL,
            )
        )
    for code in tags or []:
        # place_tags.id 는 자동 증가하는 정수라 직접 넣지 않는다.
        tag = db.query(PlaceTag).filter_by(code=code).first()
        if tag is None:
            tag = PlaceTag(code=code, name=code)
            db.add(tag)
            db.flush()
        db.add(PlaceTagLink(place_id=place.id, tag_id=tag.id, source=DataProvider.INTERNAL))
    db.flush()
    return place


def _review(db: Session, place: Place, user: User, rating: int) -> None:
    db.add(
        Review(
            id=uuid.uuid4(),
            place_id=place.id,
            user_id=user.id,
            rating=rating,
            content="테스트 후기",
        )
    )
    db.flush()


def test_동반정책_필터가_동반불가인_곳을_걸러낸다(db: Session, owner: User) -> None:
    """이 프로젝트에서 가장 중요한 필터다.

    벡터 검색을 쓰지 않기로 한 이유가 이것 — "실내 동반 가능"과 "출입 불가"는
    문장이 거의 같아서, 뜻으로 고르면 동반 불가인 곳이 섞여 나온다.
    """
    좋은곳 = _place(db, "동반 가능 카페", policy=PetPolicyType.INDOOR_ALLOWED)
    _place(db, "동반 불가 카페", policy=PetPolicyType.NOT_ALLOWED)

    hits = search_places(db, pet_policy=[PetPolicyType.INDOOR_ALLOWED])

    assert [hit.name for hit in hits] == [좋은곳.name]


def test_정책을_안_고르면_동반불가만_빠진다(db: Session) -> None:
    """GPT 는 "애월 카페 알려줘" 같은 질문에서 정책을 굳이 안 고른다.

    그때 전부 돌려주면 반려묘 전용 카페가 추천에 섞인다. `unknown` 은 우리
    데이터에서 "동반은 되는데 세부를 모름"이라 **넣는다** — 빼면 절반이 사라진다.
    """
    _place(db, "실내 가능", policy=PetPolicyType.INDOOR_ALLOWED)
    _place(db, "야외만", policy=PetPolicyType.OUTDOOR_ONLY)
    _place(db, "일부 가능", policy=PetPolicyType.PARTIAL_ALLOWED)
    _place(db, "세부 미확인", policy=PetPolicyType.UNKNOWN)
    _place(db, "정책행 자체가 없음")
    _place(db, "반려묘 전용", policy=PetPolicyType.NOT_ALLOWED)

    names = {hit.name for hit in search_places(db, limit=MAX_LIMIT)}

    assert "반려묘 전용" not in names
    assert names == {"실내 가능", "야외만", "일부 가능", "세부 미확인", "정책행 자체가 없음"}


def test_정책_행이_없는_장소는_unknown_으로_나온다(db: Session) -> None:
    place = _place(db, "정책 모르는 카페")

    hits = search_places(db, region=place.region)

    assert hits[0].pet_policy_type is PetPolicyType.UNKNOWN


def test_사용자가_등록한_장소는_검색에_안_걸린다(db: Session, stranger: User) -> None:
    """남이 자기만 보려고 등록한 장소를 챗봇이 온 세상에 추천하면 안 된다."""
    공개 = _place(db, "공개 카페")
    _place(db, "남이 등록한 카페", created_by=stranger.id)

    hits = search_places(db, category="cafe")

    assert [hit.name for hit in hits] == [공개.name]


def test_조건은_전부_and_로_걸린다(db: Session) -> None:
    맞는곳 = _place(
        db,
        "애월 실내 카페",
        region="애월/한림/협재",
        category="cafe",
        environment=PlaceEnvironment.INDOOR,
    )
    _place(db, "애월 야외 카페", environment=PlaceEnvironment.OUTDOOR)
    _place(db, "중문 실내 카페", region="중문", environment=PlaceEnvironment.INDOOR)

    hits = search_places(
        db,
        region="애월/한림/협재",
        category="cafe",
        environment=PlaceEnvironment.INDOOR,
    )

    assert [hit.name for hit in hits] == [맞는곳.name]


def test_태그를_여러개_주면_전부_가진_곳만_나온다(db: Session) -> None:
    둘다 = _place(db, "바다 보이는 쉼터", tags=["sea", "rest"])
    _place(db, "바다만", tags=["sea"])

    hits = search_places(db, tags=["sea", "rest"])

    assert [hit.name for hit in hits] == [둘다.name]


def test_목록에_없는_값을_넘기면_무엇이_틀렸는지_알려준다(db: Session) -> None:
    """조용히 0건을 주면 GPT 가 "그런 곳이 없다"고 답한다. 실제로는 값을 잘못 골랐다."""
    with pytest.raises(UnknownVocabularyError) as error:
        search_places(db, region="제주 동쪽")

    assert "제주 동쪽" in str(error.value)
    # 고를 수 있는 값을 함께 알려줘야 다시 시도할 수 있다.
    assert "애월/한림/협재" in str(error.value)

    with pytest.raises(UnknownVocabularyError):
        search_places(db, category="펜션")
    with pytest.raises(UnknownVocabularyError):
        search_places(db, tags=["조용함"])


def test_평점순은_리뷰없는_곳을_뒤로_보낸다(db: Session, owner: User) -> None:
    """`desc()` 만 쓰면 PostgreSQL 이 NULL 을 가장 큰 값으로 쳐서 맨 앞에 온다."""
    평점있음 = _place(db, "리뷰 있는 카페")
    _review(db, 평점있음, owner, 4)
    _place(db, "리뷰 없는 카페")

    hits = search_places(db, category="cafe", sort=PlaceSort.RATING)

    assert hits[0].name == 평점있음.name
    assert hits[0].rating == 4.0
    assert hits[0].review_count == 1
    assert hits[1].rating is None


def test_설명은_분류줄을_걷어내고_짧게_준다(db: Session) -> None:
    """KCISA 원본 설명은 카테고리와 중복되는 분류 줄이 절반을 차지한다."""
    _place(
        db,
        "미용실",
        category="pet_service",
        description=(
            "[KCISA]\n강아지미용, 호텔, 유치원, 놀이방\n"
            "[KCISA 원본 분류] 반려동물업 > 반려동물 서비스 > 미용\n[입장료] 없음"
        ),
    )

    hit = search_places(db, category="pet_service")[0]

    assert "원본 분류" not in hit.description
    assert "강아지미용" in hit.description
    assert "\n" not in hit.description
    assert len(hit.description) <= DESCRIPTION_LENGTH


def test_기본은_다섯곳까지만_준다(db: Session) -> None:
    for index in range(7):
        _place(db, f"카페 {index}")

    assert len(search_places(db)) == 5
    assert len(search_places(db, limit=3)) == 3
    # 상한을 넘겨 달라고 해도 열 곳까지다.
    assert len(search_places(db, limit=100)) == 7


def test_프롬프트와_도구가_같은_목록을_본다(db: Session) -> None:
    """둘이 어긋나면 GPT 는 프롬프트에서 본 값을 넘겼는데 검증에서 튕긴다."""
    prompt = build_system_prompt()

    for region in REGIONS:
        assert region in prompt
    for category in CATEGORIES:
        assert category in prompt
    for tag in TAGS:
        assert tag in prompt

    # etc 는 무슨 장소인지 알 수 없어 일부러 뺐다. 프롬프트에도 없어야 한다.
    assert "`etc`" not in prompt
