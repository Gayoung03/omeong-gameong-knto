"""추천 점수 합성에 사용하는 팀 초기 가중치.

실제 쌍대비교표와 일관성 검증을 거친 AHP 결과가 아니라 MVP 실험용
기본값이다. 추천 결과에 적용된 최종 값은 요청 스냅샷으로 따로 저장한다.

취향(preference) 축이 태그 코드 통일로 다시 살아나면서, 서비스 정체성인
**반려동물 동반**이 사람 취향에 밀리지 않도록 pet 을 최우선(0.45)으로 두고
proximity·preference 를 뒤에 둔다. rating·popularity 는 데이터가 얕아 0.

weather 는 예보 연동이 불안정하지만 0 으로 빼면 `healing` 프리셋과
`user_criteria=["weather"]` 가 balanced 와 동일해져(2배가 0×2=0) 앱의 두 선택지가
조용히 무효화된다. 재설계 Phase 5(날씨를 하루 구성 규칙으로 승격)가 들어가기 전까지
0.10 으로 남겨 선택지를 살려 둔다. **Phase 5에서 weather 축을 제거할 때 healing 은
가중치가 아니라 규칙으로 재정의한다.**

`Weights` 는 6키 고정·extra 금지라 기존 `applied_weights` 스냅샷과의 하위호환을
위해 키 6개는 값이 0이어도 반드시 남긴다.
"""

INITIAL_WEIGHTS: dict[str, float] = {
    "preference": 0.20,
    "pet": 0.45,
    "proximity": 0.25,
    "rating": 0.0,
    "weather": 0.10,
    "popularity": 0.0,
}

PRESET_MULTIPLIERS: dict[str, dict[str, float]] = {
    "balanced": {},
    "taste": {"preference": 2.0},
    "pet": {"pet": 2.0},
    "proximity": {"proximity": 2.0},
    "healing": {"weather": 2.0},
}

USER_CRITERIA_BOOST = 2.0

# common.geo.haversine_m 결과와 단위를 맞춘다.
MAX_DAILY_DISTANCE_M = 50_000.0
