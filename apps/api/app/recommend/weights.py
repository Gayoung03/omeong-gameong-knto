"""사용자의 우선순위를 6개 추천 가중치로 해석한다."""

from collections.abc import Collection

from app.recommend.config.weights import (
    INITIAL_WEIGHTS,
    PRESET_MULTIPLIERS,
    USER_CRITERIA_BOOST,
    WEATHER_SIGNAL_CRITERION,
    WEATHER_SIGNAL_PRESETS,
    WEATHER_SIGNAL_WEIGHT,
)
from app.recommend.schemas import Weights


def resolve_weights(
    preset: str | None = None,
    user_criteria: Collection[str] | None = None,
) -> Weights:
    """프리셋과 사용자 선택을 적용하고 합이 1이 되도록 정규화한다.

    프리셋 미선택과 알 수 없는 프리셋은 안전하게 balanced로 돌아간다.
    사용자 기준의 오타는 조용히 무시하지 않고 계약 오류로 알린다.
    """

    selected_preset = preset or "balanced"
    selected_criteria = set(user_criteria or ())
    if selected_preset != "balanced" and selected_criteria:
        raise ValueError("프리셋과 직접 선택 기준은 동시에 적용할 수 없습니다")

    resolved = dict(INITIAL_WEIGHTS)
    multipliers = PRESET_MULTIPLIERS.get(selected_preset, {})

    for criterion, multiplier in multipliers.items():
        resolved[criterion] *= multiplier

    invalid = selected_criteria - set(resolved)
    if invalid:
        raise ValueError(f"알 수 없는 추천 기준: {', '.join(sorted(invalid))}")

    for criterion in selected_criteria:
        resolved[criterion] *= USER_CRITERIA_BOOST

    # weather 는 점수 축에서 빠졌지만(0), healing 프리셋·weather 기준은 스냅샷에 고정
    # 신호를 남겨 생성기가 실내 우선 규칙을 켜게 한다(배수로는 0×2=0 이라 못 살린다).
    if selected_preset in WEATHER_SIGNAL_PRESETS or WEATHER_SIGNAL_CRITERION in selected_criteria:
        resolved["weather"] = WEATHER_SIGNAL_WEIGHT

    total = sum(resolved.values())
    return Weights(**{criterion: value / total for criterion, value in resolved.items()})
