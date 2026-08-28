"""추천 점수 합성에 사용하는 팀 초기 가중치.

실제 쌍대비교표와 일관성 검증을 거친 AHP 결과가 아니라 MVP 실험용
기본값이다. 추천 결과에 적용된 최종 값은 요청 스냅샷으로 따로 저장한다.
"""

INITIAL_WEIGHTS: dict[str, float] = {
    "preference": 0.30,
    "pet": 0.32,
    "proximity": 0.23,
    "rating": 0.0,
    "weather": 0.15,
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
