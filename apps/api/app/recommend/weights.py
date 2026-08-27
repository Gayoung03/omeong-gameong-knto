"""사용자의 우선순위를 6개 추천 가중치로 해석한다."""

from collections.abc import Collection

from app.recommend.config.weights import (
    INITIAL_WEIGHTS,
    PRESET_MULTIPLIERS,
    USER_CRITERIA_BOOST,
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

    resolved = dict(INITIAL_WEIGHTS)
    multipliers = PRESET_MULTIPLIERS.get(preset or "balanced", {})

    for criterion, multiplier in multipliers.items():
        resolved[criterion] *= multiplier

    invalid = set(user_criteria or ()) - set(resolved)
    if invalid:
        raise ValueError(f"알 수 없는 추천 기준: {', '.join(sorted(invalid))}")

    for criterion in set(user_criteria or ()):
        resolved[criterion] *= USER_CRITERIA_BOOST

    total = sum(resolved.values())
    return Weights(**{criterion: value / total for criterion, value in resolved.items()})
