"""추천 점수 합성에 사용하는 팀 초기 가중치.

실제 쌍대비교표와 일관성 검증을 거친 AHP 결과가 아니라 MVP 실험용
기본값이다. 추천 결과에 적용된 최종 값은 요청 스냅샷으로 따로 저장한다.

취향(preference) 축이 태그 코드 통일로 다시 살아나면서, 서비스 정체성인
**반려동물 동반**이 사람 취향에 밀리지 않도록 pet 을 최우선(0.50)으로 두고
proximity·preference 를 뒤에 둔다. rating·popularity 는 데이터가 얕아 0.

**[Phase 5]** weather 는 점수 축에서 빠져(하루 구성 규칙으로 승격) 0 이다. 이전에
남겨 두던 0.10 은 pet .50 / proximity .28 / preference .22 로 재분배했다. 대신
`healing` 프리셋과 `user_criteria=["weather"]` 는 weather 를 배수(0×2=0)로 못 살리므로
`applied_weights.weather` 에 고정 신호(WEATHER_SIGNAL_WEIGHT)를 남긴다. 생성 시
`weights.weather > 0` 이면 실내 우선 규칙(indoor_bias)을 켠다.

`Weights` 는 6키 고정·extra 금지라 기존 `applied_weights` 스냅샷과의 하위호환을
위해 키 6개는 값이 0이어도 반드시 남긴다.
"""

INITIAL_WEIGHTS: dict[str, float] = {
    "preference": 0.22,
    "pet": 0.50,
    "proximity": 0.28,
    "rating": 0.0,
    "weather": 0.0,
    "popularity": 0.0,
}

PRESET_MULTIPLIERS: dict[str, dict[str, float]] = {
    "balanced": {},
    "taste": {"preference": 2.0},
    "pet": {"pet": 2.0},
    "proximity": {"proximity": 2.0},
    # healing 은 배수가 아니라 weather 고정 신호로 실내 우선 규칙을 켠다(아래).
    "healing": {},
}

#: healing 프리셋·weather 기준이 applied_weights.weather 에 남기는 고정 신호값.
#: 점수엔 거의 영향 없지만(장소 weather 점수는 0.5 중립) 생성기가 실내 우선을 켜는 데 쓴다.
WEATHER_SIGNAL_WEIGHT = 0.10
#: weather 신호를 켜는 프리셋.
WEATHER_SIGNAL_PRESETS = frozenset({"healing"})
#: weather 신호를 켜는 사용자 기준.
WEATHER_SIGNAL_CRITERION = "weather"

USER_CRITERIA_BOOST = 2.0

# common.geo.haversine_m 결과와 단위를 맞춘다.
MAX_DAILY_DISTANCE_M = 50_000.0
