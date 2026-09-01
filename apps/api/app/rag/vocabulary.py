"""챗봇이 고를 수 있는 값의 목록.

GPT 에게 "지역을 골라라"고 하려면 **고를 목록**이 있어야 한다. 아무 문자열이나
넘기게 두면 `region="제주 동쪽"` 같은 값을 만들어 보내고, DB 에는 그런 값이 없어
검색이 조용히 0건이 된다.

여기 적힌 값은 회의에서 새로 정한 것이 아니라 **`places` 테이블에 실제로 들어 있는
값**이다(2026-08-27 기준 1299건 확인). 도구 인자 검증과 시스템 프롬프트가 **같은
목록을 본다** — 둘이 어긋나면 GPT 가 프롬프트에서 본 값을 넘겼는데 검증에서 튕긴다.

데이터가 바뀌면 여기도 바뀐다. 확인 쿼리는 docs/planning/chatbot-design-decisions.md
4장에 적어뒀다.
"""

#: 관광권역. `places.region` 의 실제 값이다.
#: `제주시`·`서귀포시`(합계 4건)는 seed_dev.py 잔여물이라 목록에 넣지 않는다.
REGIONS: tuple[str, ...] = (
    "제주시/제주국제공항",
    "애월/한림/협재",
    "함덕/김녕/세화",
    "표선/성산",
    "서귀포시/모슬포",
    "중문",
)

#: 방위 → 권역. 사용자는 "제주 동부"라고 묻지 "함덕/김녕/세화"라고 묻지 않는다.
#: 스키마를 바꾸지 않고 이 표를 프롬프트에 실어 GPT 가 번역하게 한다.
AREA_TO_REGIONS: dict[str, tuple[str, ...]] = {
    "동부": ("함덕/김녕/세화", "표선/성산"),
    "서부": ("애월/한림/협재",),
    "남부": ("중문", "서귀포시/모슬포"),
    "제주시권": ("제주시/제주국제공항",),
}

#: `places.category` 의 실제 값과 한글 뜻.
#:
#: `etc` 는 **일부러 뺐다.** 278건(전체의 21%)이 여기 몰려 있는데 무슨 장소인지
#: 알 수 없어서, 목록에 넣으면 GPT 가 "기타"를 고르고 엉뚱한 곳을 추천한다.
#: 분류가 정리되면 그때 넣는다(장소 데이터 회의 안건).
CATEGORY_LABELS: dict[str, str] = {
    "cafe": "카페",
    "restaurant": "식당",
    "restaurant_cafe": "식당 겸 카페",
    "accommodation": "숙소",
    "attraction": "관광지",
    "beach": "해변",
    "oreum": "오름",
    "walking_trail": "산책로",
    "veterinary_hospital": "동물병원",
    "pet_service": "반려동물 서비스(미용·용품 등)",
    "rental_experience": "대여·체험",
}

#: `place_tags.code` 와 이름. 7종 전부다.
#:
#: **분위기 태그가 아니다.** 실제로 붙어 있는 값을 세어 보면 장소의 종류에 가깝다 —
#: `rest` 를 가진 곳 중 대부분이 숙소고, 카페 카테고리에는 `cafe` 말고 어떤 태그도
#: 붙어 있지 않다(2026-08-29 팀 DB 확인). "조용한 곳"을 `rest` 로 옮기면 카페를
#: 물었는데 숙소가 나온다. 그래서 라벨을 **실제 의미대로** 적는다 — 프롬프트가 이
#: 문구를 그대로 싣기 때문에, 여기서 "휴식"이라고 쓰면 GPT 가 분위기로 읽는다.
#:
#: 분위기 검색은 리뷰처럼 진짜 자연어가 쌓인 뒤에 다시 본다.
TAG_LABELS: dict[str, str] = {
    "sea": "바다·해변",
    "cafe": "카페류",
    "walk": "산책로",
    "photo_spot": "포토스팟",
    "experience": "체험",
    "rest": "숙박·휴식 시설",
    "indoor_tourism": "실내 관광",
}

#: 챗봇이 고를 수 있는 동반정책. **`not_allowed` 는 없다.**
#:
#: 우리는 동반 가능한 장소만 소개하고, 검색도 동반 불가인 곳을 항상 뺀다
#: (`services/place_query.py` 의 `pet_friendly_condition`, 2026-08-31 확정).
#: 그런데 선택지로 남겨 두면 "강아지 못 데려가는 카페도 있어?" 같은 질문에
#: GPT 가 `not_allowed` 를 골라 빈 결과를 받고, 검색이 고장난 줄 알고 조건을
#: 바꿔가며 몇 번씩 재시도한다. 아예 없는 값으로 두는 편이 낫다.
#:
#: `unknown` 은 **넣는다.** 우리 장소의 절반이 여기 속하는데, "동반 가능 여부를
#: 모름"이 아니라 **"동반은 되는데 실내·야외 세부를 모름"** 이다.
PET_POLICY_LABELS: dict[str, str] = {
    "indoor_allowed": "실내까지 동반 가능",
    "outdoor_only": "야외만 가능",
    "partial_allowed": "일부 구역만 가능",
    "unknown": "동반은 가능하나 실내·야외 세부가 확인되지 않음",
}

CATEGORIES: tuple[str, ...] = tuple(CATEGORY_LABELS)
TAGS: tuple[str, ...] = tuple(TAG_LABELS)
#: 도구 스키마의 `pet_policy` enum. 시스템 프롬프트와 **같은 목록을 본다.**
SELECTABLE_PET_POLICIES: tuple[str, ...] = tuple(PET_POLICY_LABELS)
