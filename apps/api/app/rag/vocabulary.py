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
#: 분위기 질문("조용한 곳", "사진 예쁜 데")을 받아내는 것이 결국 이 태그다.
TAG_LABELS: dict[str, str] = {
    "sea": "바다",
    "cafe": "카페",
    "walk": "산책",
    "photo_spot": "포토스팟",
    "experience": "체험",
    "rest": "휴식",
    "indoor_tourism": "실내관광",
}

CATEGORIES: tuple[str, ...] = tuple(CATEGORY_LABELS)
TAGS: tuple[str, ...] = tuple(TAG_LABELS)
