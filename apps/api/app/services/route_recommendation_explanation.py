"""규칙 결과 → 여행 설명 LLM 입력 요약(라벨 매핑 포함).

`route_recommendation.generate_route` 가 LLM 호출 직전에 쓴다. 실제 LLM 호출은
`app.integrations.llm.route_explanation` 이 한다. 이 모듈은 상위 orchestrator 를
import 하지 않는다(단방향).
"""

from app.db.models.enums import TransportType, TripPace
from app.integrations.llm.route_explanation import TripExplanationInput
from app.recommend.itinerary import Itinerary
from app.recommend.schemas import PetProfile, ScoredCandidate, Weights

#: 여행 설명 프롬프트에 넣을 한글 라벨(설명 전용 — API 계약이 아님).
_PACE_LABELS = {
    TripPace.RELAXED: "여유로운",
    TripPace.NORMAL: "보통",
    TripPace.PACKED: "빠듯한",
}
_TRANSPORT_LABELS = {
    TransportType.RENTAL_CAR: "렌터카",
    TransportType.OWN_CAR: "자가용",
    TransportType.TAXI: "택시",
    TransportType.PUBLIC_TRANSPORT: "대중교통",
    TransportType.WALK: "도보",
    TransportType.FERRY: "배",
    TransportType.AIRPLANE: "비행기",
}


def _explanation_summary(
    request,
    itinerary: Itinerary,
    selected: list[ScoredCandidate],
    pet_profiles: tuple[PetProfile, ...],
    weights: Weights,
) -> TripExplanationInput:
    """규칙 결과에서 설명 프롬프트 입력을 만든다. request_text 원문은 넣지 않는다."""
    pet_notes: list[str] = []
    if pet_profiles:
        pet_notes.append(f"{len(pet_profiles)}마리 동반")
        if any(pet.car_sickness for pet in pet_profiles):
            pet_notes.append("차멀미 배려 동선")
    return TripExplanationInput(
        day_count=len(itinerary.days),
        place_count=len(selected),
        unfilled_count=sum(len(day.unfilled) for day in itinerary.days),
        pace_label=_PACE_LABELS.get(request.pace, request.pace.value),
        transport_label=_TRANSPORT_LABELS.get(request.transport, request.transport.value),
        pet_notes=tuple(pet_notes),
        weather_note=("비·더위를 고려해 실내 비중을 높였습니다" if weights.weather > 0 else None),
    )
